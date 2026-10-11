# Port of ProjectorRays src/director/{dirfile,chunk,subchunk,guid,util,castmember,fontmap}.* and
# src/io/fileio's cleanFileName (MPL-2.0).
import os
import struct
import warnings

from .lingo_names import StandardNames  # noqa: F401  (kept so lingo_* import order is stable)
from .lingo_script import Script, ScriptContext, ScriptNames
from .stream import ReadStream

UINT32_MAX = 0xFFFFFFFF


def FOURCC(a, b, c, d):
    return (ord(a) << 24) | (ord(b) << 16) | (ord(c) << 8) | ord(d)


def fourcc_to_string(v):
    return struct.pack('>I', v & 0xFFFFFFFF).decode('latin-1')


def warn(msg):
    warnings.warn(msg, stacklevel=2)


# ---- guid.* ---------------------------------------------------------------------------------
class MoaID:
    __slots__ = ('data1', 'data2', 'data3', 'data4')

    def __init__(self, d1=0, d2=0, d3=0, *d4):
        self.data1, self.data2, self.data3 = d1, d2, d3
        self.data4 = tuple(d4) if d4 else (0,) * 8

    def read(self, stream):
        self.data1 = stream.read_u32()
        self.data2 = stream.read_u16()
        self.data3 = stream.read_u16()
        self.data4 = tuple(stream.read_u8() for _ in range(8))
        return self

    def to_string(self):
        return '%08X-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X' % ((self.data1, self.data2, self.data3) + self.data4)

    def _key(self):
        return (self.data1, self.data2, self.data3, self.data4)

    def __eq__(self, other):
        return isinstance(other, MoaID) and self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def __repr__(self):
        return 'MoaID(%s)' % self.to_string()


FONTMAP_COMPRESSION_GUID = MoaID(0x8A4679A1, 0x3720, 0x11D0, 0x92, 0x23, 0x00, 0xA0, 0xC9, 0x08, 0x68, 0xB1)
NULL_COMPRESSION_GUID = MoaID(0xAC99982E, 0x005D, 0x0D50, 0x00, 0x00, 0x08, 0x00, 0x07, 0x37, 0x7A, 0x34)
SND_COMPRESSION_GUID = MoaID(0x7204A889, 0xAFD0, 0x11CF, 0xA2, 0x22, 0x00, 0xA0, 0x24, 0x53, 0x44, 0x4C)
ZLIB_COMPRESSION_GUID = MoaID(0xAC99E904, 0x0070, 0x0B36, 0x00, 0x00, 0x08, 0x00, 0x07, 0x37, 0x7A, 0x34)


# ---- util.* ---------------------------------------------------------------------------------
def human_version(ver):
    # Based on Lingo's `the fileVersion`, with a correction for Director 12.
    if ver >= 1951: return 1200
    if ver >= 1922: return 1150
    if ver >= 1921: return 1100
    if ver >= 1851: return 1000
    if ver >= 1700: return 850
    if ver >= 1410: return 800
    if ver >= 1224: return 700
    if ver >= 1218: return 600
    if ver >= 1201: return 500
    if ver >= 1117: return 404
    if ver >= 1115: return 400
    if ver >= 1029: return 310
    if ver >= 1028: return 300
    return 200


def clean_file_name(name):
    """IO::cleanFileName: replace <>:"/\\|?* with _."""
    return ''.join('_' if c in '<>:"/\\|?*' else c for c in name)


# ---- castmember.* ---------------------------------------------------------------------------
kNullMember, kBitmapMember, kFilmLoopMember, kTextMember, kPaletteMember, kPictureMember, kSoundMember, \
    kButtonMember, kShapeMember, kMovieMember, kDigitalVideoMember, kScriptMember, kRTEMember = range(13)
kXtraMember = 15

kScoreScript = 1
kMovieScript = 3
kParentScript = 7


class CastMember:
    def __init__(self, dir_, type_):
        self.dir = dir_
        self.type = type_

    def read(self, stream):
        pass


class ScriptMember(CastMember):
    def __init__(self, dir_):
        CastMember.__init__(self, dir_, kScriptMember)
        self.script_type = 0

    def read(self, stream):
        self.script_type = stream.read_u16()


# ---- subchunk.* -----------------------------------------------------------------------------
class CastListEntry:
    def __init__(self):
        self.name = ''
        self.file_path = ''
        self.preload_settings = 0
        self.min_member = 0
        self.max_member = 0
        self.id = 0


class MemoryMapEntry:
    def read(self, stream):
        self.four_cc = stream.read_u32()
        self.len = stream.read_u32()
        self.offset = stream.read_u32()
        self.flags = stream.read_i16() & 0xFFFF
        self.unknown0 = stream.read_i16()
        self.next = stream.read_i32()


class KeyTableEntry:
    def read(self, stream):
        self.section_id = stream.read_i32()
        self.cast_id = stream.read_i32()
        self.four_cc = stream.read_u32()


class ChunkInfo:
    __slots__ = ('id', 'four_cc', 'len', 'uncompressed_len', 'offset', 'compression_id')

    def __init__(self):
        self.id = 0
        self.four_cc = 0
        self.len = 0
        self.uncompressed_len = 0
        self.offset = 0
        self.compression_id = NULL_COMPRESSION_GUID


# ---- chunk.* --------------------------------------------------------------------------------
class Chunk:
    def __init__(self, dir_):
        self.dir = dir_

    def read(self, stream):
        raise NotImplementedError


class ListChunk(Chunk):
    def __init__(self, dir_):
        Chunk.__init__(self, dir_)
        self.data_offset = 0
        self.offset_table_len = 0
        self.offset_table = []
        self.items_len = 0
        self.item_endian = '>'
        self.items = []

    def read(self, stream):
        self.read_header(stream)
        self.read_offset_table(stream)
        self.read_items(stream)

    def read_header(self, stream):
        self.data_offset = stream.read_u32()

    def read_offset_table(self, stream):
        stream.seek(self.data_offset)
        self.offset_table_len = stream.read_u16()
        self.offset_table = [stream.read_u32() for _ in range(self.offset_table_len)]

    def read_items(self, stream):
        self.items_len = stream.read_u32()
        self.item_endian = stream.endian
        list_offset = stream.pos
        self.items = []
        n = self.offset_table_len
        for i in range(n):
            offset = self.offset_table[i]
            next_offset = self.items_len if i == n - 1 else self.offset_table[i + 1]
            stream.seek(list_offset + offset)
            self.items.append(stream.read_bytes(max(0, next_offset - offset)))

    def read_string(self, index):
        if index >= self.offset_table_len:
            return ''
        s = ReadStream(self.items[index], self.item_endian)
        return s.read_string(s.size)

    def read_pascal_string(self, index):
        if index >= self.offset_table_len:
            return ''
        s = ReadStream(self.items[index], self.item_endian)
        if s.size == 0:
            return ''
        return s.read_pascal_string()

    def read_u16_item(self, index):
        if index >= self.offset_table_len:
            return 0
        return ReadStream(self.items[index], self.item_endian).read_u16()

    def read_u32_item(self, index):
        if index >= self.offset_table_len:
            return 0
        return ReadStream(self.items[index], self.item_endian).read_u32()


class CastChunk(Chunk):
    def __init__(self, dir_):
        Chunk.__init__(self, dir_)
        self.member_ids = []
        self.name = ''
        self.members = {}
        self.lctx = None

    def read(self, stream):
        stream.endian = '>'
        while not stream.eof():
            self.member_ids.append(stream.read_i32())

    def populate(self, cast_name, id_, min_member):
        self.name = cast_name
        d = self.dir
        for entry in d.key_table.entries:
            if (entry.cast_id == id_
                    and entry.four_cc in (FOURCC('L', 'c', 't', 'x'), FOURCC('L', 'c', 't', 'X'))
                    and d.chunk_exists(entry.four_cc, entry.section_id)):
                self.lctx = d.get_chunk(entry.four_cc, entry.section_id)
                break

        for i, section_id in enumerate(self.member_ids):
            if section_id > 0:
                member = d.get_chunk(FOURCC('C', 'A', 'S', 't'), section_id)
                member.id = (i + min_member) & 0xFFFF
                member.section_id = section_id
                if self.lctx is not None:
                    script = self.lctx.scripts.get(member.get_script_id())
                    if script is not None:
                        member.script = script
                        script.member = member
                self.members[member.id] = member


class CastListChunk(ListChunk):
    def __init__(self, dir_):
        ListChunk.__init__(self, dir_)
        self.entries = []

    def read(self, stream):
        stream.endian = '>'
        ListChunk.read(self, stream)
        self.entries = []
        for i in range(self.cast_count):
            e = CastListEntry()
            if self.items_per_cast >= 1:
                e.name = self.read_pascal_string(i * self.items_per_cast + 1)
            if self.items_per_cast >= 2:
                e.file_path = self.read_pascal_string(i * self.items_per_cast + 2)
            if self.items_per_cast >= 3:
                e.preload_settings = self.read_u16_item(i * self.items_per_cast + 3)
            if self.items_per_cast >= 4:
                item = ReadStream(self.items[i * self.items_per_cast + 4], self.item_endian)
                e.min_member = item.read_u16()
                e.max_member = item.read_u16()
                e.id = item.read_i32()
            self.entries.append(e)

    def read_header(self, stream):
        self.data_offset = stream.read_u32()
        self.unk0 = stream.read_u16()
        self.cast_count = stream.read_u16()
        self.items_per_cast = stream.read_u16()
        self.unk1 = stream.read_u16()


class CastInfoChunk(ListChunk):
    def __init__(self, dir_):
        ListChunk.__init__(self, dir_)
        self.script_id = 0
        self.script_src_text = ''
        self.name = ''

    def read(self, stream):
        ListChunk.read(self, stream)
        self.script_src_text = self.read_string(0)
        self.name = self.read_pascal_string(1)
        if self.offset_table_len == 0:     # workaround: at least one entry for decompilation results
            self.offset_table_len = 1
            self.offset_table = [0]

    def read_header(self, stream):
        self.data_offset = stream.read_u32()
        self.unk1 = stream.read_u32()
        self.unk2 = stream.read_u32()
        self.flags = stream.read_u32()
        self.script_id = stream.read_u32()


class CastMemberChunk(Chunk):
    def __init__(self, dir_):
        Chunk.__init__(self, dir_)
        self.id = 0
        self.section_id = 0
        self.script = None
        self.info = None
        self.member = None
        self.type = 0
        self.has_flags1 = False
        self.flags1 = 0
        self.specific_data = b''

    def read(self, stream):
        stream.endian = '>'
        d = self.dir
        if d.version >= 500:
            self.type = stream.read_u32()
            self.info_len = stream.read_u32()
            self.specific_data_len = stream.read_u32()
            if self.info_len:
                info_stream = ReadStream(stream.read_bytes(self.info_len), stream.endian)
                self.info = CastInfoChunk(d)
                self.info.read(info_stream)
            self.has_flags1 = False
            self.specific_data = stream.read_bytes(self.specific_data_len)
        else:
            self.specific_data_len = stream.read_u16()
            self.info_len = stream.read_u32()
            left = self.specific_data_len
            self.type = stream.read_u8()
            left -= 1
            if left:
                self.has_flags1 = True
                self.flags1 = stream.read_u8()
                left -= 1
            else:
                self.has_flags1 = False
            self.specific_data = stream.read_bytes(left)
            info_stream = ReadStream(stream.read_bytes(self.info_len), stream.endian)
            if self.info_len:
                self.info = CastInfoChunk(d)
                self.info.read(info_stream)

        if self.type == kScriptMember:
            self.member = ScriptMember(d)
        else:
            self.member = CastMember(d, self.type)
        self.member.read(ReadStream(self.specific_data, stream.endian))

    def get_script_id(self):
        return self.info.script_id if self.info else 0

    def get_script_text(self):
        return self.info.script_src_text if self.info else ''

    def set_script_text(self, val):
        if self.info is None:
            warn('Tried to set scriptText on member with no info!')
            return
        self.info.script_src_text = val

    def get_name(self):
        return self.info.name if self.info else ''


class ConfigChunk(Chunk):
    def read(self, stream):
        stream.endian = '>'
        stream.seek(36)
        self.director_version = stream.read_i16()
        ver = human_version(self.director_version)

        stream.seek(0)
        self.len = stream.read_i16()
        self.file_version = stream.read_i16()
        self.movie_top = stream.read_i16()
        self.movie_left = stream.read_i16()
        self.movie_bottom = stream.read_i16()
        self.movie_right = stream.read_i16()
        self.min_member = stream.read_i16()
        self.max_member = stream.read_i16()
        self.field9 = stream.read_i8()
        self.field10 = stream.read_i8()
        if ver < 700:
            self.pre_d7_field11 = stream.read_i16()
        else:
            self.d7_stage_color_g = stream.read_u8()
            self.d7_stage_color_b = stream.read_u8()
        self.comment_font = stream.read_i16()
        self.comment_size = stream.read_i16()
        self.comment_style = stream.read_u16()
        if ver < 700:
            self.pre_d7_stage_color = stream.read_i16()
        else:
            self.d7_stage_color_is_rgb = stream.read_u8()
            self.d7_stage_color_r = stream.read_u8()
        self.bit_depth = stream.read_i16()
        self.field17 = stream.read_u8()
        self.field18 = stream.read_u8()
        self.field19 = stream.read_i32()
        stream.read_i16()                       # directorVersion (already read)
        self.field21 = stream.read_i16()
        self.field22 = stream.read_i32()
        self.field23 = stream.read_i32()
        self.field24 = stream.read_i32()
        self.field25 = stream.read_i8()
        self.field26 = stream.read_u8()
        self.frame_rate = stream.read_i16()
        self.platform = stream.read_i16()
        self.protection = stream.read_i16()
        self.field29 = stream.read_i32()
        self.checksum = stream.read_u32()
        self.remnants = stream.read_bytes(self.len - stream.pos)
        # (ProjectorRays only warns when the stored checksum differs; nothing depends on it here.)

    def compute_checksum(self):
        M = 0xFFFFFFFF
        ver = human_version(self.director_version)

        def udiv(a, b):
            b &= M
            return (a // b) if b else a

        check = (self.len + 1) & M
        check = (check * (self.file_version + 2)) & M
        check = udiv(check, self.movie_top + 3)
        check = (check * (self.movie_left + 4)) & M
        check = udiv(check, self.movie_bottom + 5)
        check = (check * (self.movie_right + 6)) & M
        check = (check - (self.min_member + 7)) & M
        check = (check * (self.max_member + 8)) & M
        check = (check - (self.field9 + 9)) & M
        check = (check - (self.field10 + 10)) & M
        if ver < 700:
            operand11 = self.pre_d7_field11
        else:
            little = (self.dir.endian == '<')
            v = ((self.d7_stage_color_b << 8) | self.d7_stage_color_g) if little \
                else ((self.d7_stage_color_g << 8) | self.d7_stage_color_b)
            operand11 = v - 0x10000 if v >= 0x8000 else v
        check = (check + operand11 + 11) & M
        check = (check * (self.comment_font + 12)) & M
        check = (check + self.comment_size + 13) & M
        operand14 = ((self.comment_style >> 8) & 0xFF) if ver < 800 else self.comment_style
        check = (check * (operand14 + 14)) & M
        operand15 = self.pre_d7_stage_color if ver < 700 else self.d7_stage_color_r
        check = (check + operand15 + 15) & M
        check = (check + self.bit_depth + 16) & M
        check = (check + self.field17 + 17) & M
        check = (check * (self.field18 + 18)) & M
        check = (check + self.field19 + 19) & M
        check = (check * (self.director_version + 20)) & M
        check = (check + self.field21 + 21) & M
        check = (check + self.field22 + 22) & M
        check = (check + self.field23 + 23) & M
        check = (check + self.field24 + 24) & M
        check = (check * (self.field25 + 25)) & M
        check = (check + self.frame_rate + 26) & M
        check = (check * (self.platform + 27)) & M
        check = (check * ((self.protection * 0xE06) + 0xFF450000)) & M
        check ^= FOURCC('r', 'a', 'l', 'f')
        return check & M

    def unprotect(self):
        self.file_version = self.director_version
        if self.protection % 23 == 0:
            self.protection += 1


class InitialMapChunk(Chunk):
    def read(self, stream):
        self.version = stream.read_u32()
        self.mmap_offset = stream.read_u32()
        self.director_version = stream.read_u32()
        self.unused1 = stream.read_u32()
        self.unused2 = stream.read_u32()
        self.unused3 = stream.read_u32()


class KeyTableChunk(Chunk):
    def read(self, stream):
        self.entry_size = stream.read_u16()
        self.entry_size2 = stream.read_u16()
        self.entry_count = stream.read_u32()
        self.used_count = stream.read_u32()
        self.entries = []
        for _ in range(self.entry_count):
            e = KeyTableEntry()
            e.read(stream)
            self.entries.append(e)


class MemoryMapChunk(Chunk):
    def read(self, stream):
        self.header_length = stream.read_i16()
        self.entry_length = stream.read_i16()
        self.chunk_count_max = stream.read_i32()
        self.chunk_count_used = stream.read_i32()
        self.junk_head = stream.read_i32()
        self.junk_head2 = stream.read_i32()
        self.free_head = stream.read_i32()
        self.map_array = []
        for _ in range(self.chunk_count_used):
            e = MemoryMapEntry()
            e.read(stream)
            self.map_array.append(e)


class ScriptChunk(Chunk, Script):
    def __init__(self, dir_):
        Chunk.__init__(self, dir_)
        Script.__init__(self, dir_.version)
        self.member = None

    def read(self, stream):
        Script.read(self, stream)


class ScriptContextChunk(Chunk, ScriptContext):
    def __init__(self, dir_):
        Chunk.__init__(self, dir_)
        ScriptContext.__init__(self, dir_.version, dir_)

    def read(self, stream):
        ScriptContext.read(self, stream)


class ScriptNamesChunk(Chunk, ScriptNames):
    def __init__(self, dir_):
        Chunk.__init__(self, dir_)
        ScriptNames.__init__(self, dir_.version)

    def read(self, stream):
        ScriptNames.read(self, stream)


# ---- dirfile.* ------------------------------------------------------------------------------
class DirectorFile:
    """A Director movie (.dir/.dxr/.dcr) or cast (.cst/.cxt/.cct). Also the chunk resolver for the Lingo parts."""

    def __init__(self):
        self._ils_body_offset = 0
        self._cached_views = {}
        self.stream = None
        self.key_table = None
        self.config = None
        self.endian = '>'
        self.fver_version_string = ''
        self.version = 0
        self.dot_syntax = False
        self.codec = 0
        self.afterburned = False
        self.chunk_ids_by_four_cc = {}
        self.chunk_info = {}
        self.deserialized_chunks = {}
        self.casts = []
        self.initial_map = None
        self.memory_map = None

    # ---- opening ----------------------------------------------------------------------------
    @classmethod
    def open(cls, path):
        with open(path, 'rb') as f:
            data = f.read()
        d = cls()
        if not d.read(ReadStream(data)):
            raise ValueError('%s: not a readable Director file' % path)
        return d

    def read(self, s):
        self.stream = s
        s.endian = '>'
        meta = s.read_u32()
        if meta == FOURCC('X', 'F', 'I', 'R'):
            s.endian = '<'
        self.endian = s.endian
        s.read_u32()                                    # meta length
        self.codec = s.read_u32()

        if self.codec in (FOURCC('M', 'V', '9', '3'), FOURCC('M', 'C', '9', '5')):
            self.read_memory_map()
        elif self.codec in (FOURCC('F', 'G', 'D', 'M'), FOURCC('F', 'G', 'D', 'C')):
            self.afterburned = True
            if not self.read_afterburner_map():
                return False
        else:
            warn('Codec unsupported: ' + fourcc_to_string(self.codec))
            return False

        if not self.read_key_table():
            return False
        if not self.read_config():
            return False
        if not self.read_casts():
            return False
        return True

    def read_memory_map(self):
        imap = self.read_chunk(FOURCC('i', 'm', 'a', 'p'))
        self.deserialized_chunks[1] = imap
        self.stream.seek(imap.mmap_offset)
        mmap = self.read_chunk(FOURCC('m', 'm', 'a', 'p'))
        self.deserialized_chunks[2] = mmap
        for i, e in enumerate(mmap.map_array):
            if e.four_cc in (FOURCC('f', 'r', 'e', 'e'), FOURCC('j', 'u', 'n', 'k')):
                continue
            info = ChunkInfo()
            info.id = i
            info.four_cc = e.four_cc
            info.len = e.len
            info.uncompressed_len = e.len
            info.offset = e.offset
            info.compression_id = NULL_COMPRESSION_GUID
            self.chunk_info[i] = info
            self.chunk_ids_by_four_cc.setdefault(e.four_cc, []).append(i)

    def read_afterburner_map(self):
        s = self.stream
        if s.read_u32() != FOURCC('F', 'v', 'e', 'r'):
            warn('readAfterburnerMap(): Fver expected but not found')
            return False
        fver_length = s.read_var_int()
        start = s.pos
        fver_version = s.read_var_int()
        if fver_version >= 0x401:
            s.read_var_int()        # imapVersion
            s.read_var_int()        # directorVersion
        if fver_version >= 0x501:
            n = s.read_u8()
            self.fver_version_string = s.read_string(n)
        end = s.pos
        if end - start != fver_length:
            warn('readAfterburnerMap(): Expected Fver of length %d but read %d bytes' % (fver_length, end - start))
            s.seek(start + fver_length)

        if s.read_u32() != FOURCC('F', 'c', 'd', 'r'):
            warn('readAfterburnerMap(): Fcdr expected but not found')
            return False
        fcdr_length = s.read_var_int()
        fcdr = s.read_zlib(fcdr_length)
        if fcdr is None:
            warn('Fcdr: Could not decompress')
            return False
        fs = ReadStream(fcdr, self.endian)
        count = fs.read_u16()
        compression_ids = [MoaID().read(fs) for _ in range(count)]
        for _ in range(count):
            fs.read_cstring()       # descriptions

        if s.read_u32() != FOURCC('A', 'B', 'M', 'P'):
            warn('RIFXArchive::readAfterburnerMap(): ABMP expected but not found')
            return False
        abmp_length = s.read_var_int()
        abmp_end = s.pos + abmp_length
        s.read_var_int()            # compression type
        abmp_uncomp_length = s.read_var_int()
        abmp = s.read_zlib(abmp_end - s.pos)
        if abmp is None:
            warn('ABMP: Could not decompress')
            return False
        if len(abmp) != abmp_uncomp_length:
            warn('ABMP: Expected uncompressed length %d but got length %d' % (abmp_uncomp_length, len(abmp)))
        a = ReadStream(abmp, self.endian)
        a.read_var_int()
        a.read_var_int()
        res_count = a.read_var_int()
        for _ in range(res_count):
            res_id = a.read_var_int()
            if res_id >= 0x80000000:
                res_id -= 0x100000000
            offset = a.read_var_int()
            comp_size = a.read_var_int()
            uncomp_size = a.read_var_int()
            compression_type = a.read_var_int()
            tag = a.read_u32()
            info = ChunkInfo()
            info.id = res_id
            info.four_cc = tag
            info.len = comp_size
            info.uncompressed_len = uncomp_size
            info.offset = offset
            info.compression_id = compression_ids[compression_type]
            self.chunk_info[res_id] = info
            self.chunk_ids_by_four_cc.setdefault(tag, []).append(res_id)

        if 2 not in self.chunk_info:
            warn('readAfterburnerMap(): Map has no entry for ILS')
            return False
        if s.read_u32() != FOURCC('F', 'G', 'E', 'I'):
            warn('readAfterburnerMap(): FGEI expected but not found')
            return False
        ils_info = self.chunk_info[2]
        s.read_var_int()
        self._ils_body_offset = s.pos
        ils = s.read_zlib(ils_info.len)
        if ils is None:
            warn('ILS: Could not decompress')
            return False
        if len(ils) != ils_info.uncompressed_len:
            warn('ILS: Expected uncompressed length %d but got length %d' % (ils_info.uncompressed_len, len(ils)))
        ils_stream = ReadStream(ils, self.endian)
        while not ils_stream.eof():
            res_id = ils_stream.read_var_int()
            info = self.chunk_info.get(res_id)
            length = info.len if info else 0
            self._cached_views[res_id] = ils_stream.read_bytes(length)
        return True

    def read_key_table(self):
        info = self.get_first_chunk_info(FOURCC('K', 'E', 'Y', '*'))
        if info:
            self.key_table = self.get_chunk(info.four_cc, info.id)
            return True
        warn('No key chunk!')
        return False

    def read_config(self):
        info = self.get_first_chunk_info(FOURCC('D', 'R', 'C', 'F'))
        if not info:
            info = self.get_first_chunk_info(FOURCC('V', 'W', 'C', 'F'))
        if info:
            self.config = self.get_chunk(info.four_cc, info.id)
            self.version = human_version(self.config.director_version)
            self.dot_syntax = self.version >= 700
            return True
        warn('No config chunk!')
        return False

    def read_casts(self):
        internal = True
        if self.version >= 500:
            info = self.get_first_chunk_info(FOURCC('M', 'C', 's', 'L'))
            if info:
                cast_list = self.get_chunk(info.four_cc, info.id)
                self.cast_list = cast_list
                for ce in cast_list.entries:
                    section_id = -1
                    for ke in self.key_table.entries:
                        if ke.cast_id == ce.id and ke.four_cc == FOURCC('C', 'A', 'S', '*'):
                            section_id = ke.section_id
                            break
                    if section_id > 0:
                        cast = self.get_chunk(FOURCC('C', 'A', 'S', '*'), section_id)
                        cast.populate(ce.name, ce.id, ce.min_member)
                        cast.entry = ce
                        self.casts.append(cast)
                return True
            internal = False

        info = self.get_first_chunk_info(FOURCC('C', 'A', 'S', '*'))
        if info:
            cast = self.get_chunk(info.four_cc, info.id)
            cast.populate('Internal' if internal else 'External', 1024, self.config.min_member)
            cast.entry = None
            self.casts.append(cast)
        return True

    # ---- chunk access -----------------------------------------------------------------------
    def get_first_chunk_info(self, four_cc):
        ids = self.chunk_ids_by_four_cc.get(four_cc)
        if ids:
            return self.chunk_info[ids[0]]
        return None

    def chunk_exists(self, four_cc, id_):
        info = self.chunk_info.get(id_)
        return info is not None and info.four_cc == four_cc

    def chunks_for_owner(self, owner_id, four_cc):
        """Section IDs of chunks of the given type that the KEY* table assigns to owner (e.g. a CASt chunk)."""
        return [e.section_id for e in self.key_table.entries
                if e.cast_id == owner_id and e.four_cc == four_cc and self.chunk_exists(four_cc, e.section_id)]

    def get_chunk(self, four_cc, id_):
        c = self.deserialized_chunks.get(id_)
        if c is not None:
            return c
        view = self.get_chunk_data(four_cc, id_)
        c = self.make_chunk(four_cc, view)
        self.deserialized_chunks[id_] = c
        return c

    def get_chunk_data(self, four_cc, id_):
        info = self.chunk_info.get(id_)
        if info is None:
            raise RuntimeError('Could not find chunk %d' % id_)
        if four_cc != info.four_cc:
            raise RuntimeError("Expected chunk %d to be '%s', but is actually '%s'"
                               % (id_, fourcc_to_string(four_cc), fourcc_to_string(info.four_cc)))
        if id_ in self._cached_views:
            return self._cached_views[id_]

        s = self.stream
        if self.afterburned:
            s.seek(info.offset + self._ils_body_offset)
            if info.len == 0 and info.uncompressed_len == 0:
                view = s.read_bytes(info.len)
            elif self.compression_implemented(info.compression_id):
                if info.compression_id == ZLIB_COMPRESSION_GUID:
                    view = s.read_zlib(info.len)
                else:
                    from . import media
                    view = media.decompress_snd(s.read_bytes(info.len), info.uncompressed_len, id_)
                if view is None:
                    raise RuntimeError('Chunk %d: Could not decompress' % id_)
                if len(view) != info.uncompressed_len:
                    raise RuntimeError('Chunk %d: Expected uncompressed length %d but got length %d'
                                       % (id_, info.uncompressed_len, len(view)))
            elif info.compression_id == FONTMAP_COMPRESSION_GUID:
                view = b''      # the default font maps ProjectorRays embeds are not needed for extraction
            else:
                if info.compression_id != NULL_COMPRESSION_GUID:
                    warn('Unhandled compression type %s!' % info.compression_id.to_string())
                view = s.read_bytes(info.len)
        else:
            s.seek(info.offset)
            view = self.read_chunk_data(four_cc, info.len)
        self._cached_views[id_] = view
        return view

    def read_chunk(self, four_cc, length=UINT32_MAX):
        view = self.read_chunk_data(four_cc, length)
        return self.make_chunk(four_cc, view)

    def read_chunk_data(self, four_cc, length):
        s = self.stream
        offset = s.pos
        valid_four_cc = s.read_u32()
        valid_len = s.read_u32()
        if length == UINT32_MAX:
            length = valid_len
        if four_cc != valid_four_cc or length != valid_len:
            raise RuntimeError("At offset %d expected '%s' chunk with length %d, but got '%s' chunk with length %d"
                               % (offset, fourcc_to_string(four_cc), length,
                                  fourcc_to_string(valid_four_cc), valid_len))
        return s.read_bytes(length)

    def make_chunk(self, four_cc, view):
        T = {
            FOURCC('i', 'm', 'a', 'p'): InitialMapChunk,
            FOURCC('m', 'm', 'a', 'p'): MemoryMapChunk,
            FOURCC('C', 'A', 'S', '*'): CastChunk,
            FOURCC('C', 'A', 'S', 't'): CastMemberChunk,
            FOURCC('K', 'E', 'Y', '*'): KeyTableChunk,
            FOURCC('L', 'c', 't', 'x'): ScriptContextChunk,
            FOURCC('L', 'c', 't', 'X'): ScriptContextChunk,
            FOURCC('L', 'n', 'a', 'm'): ScriptNamesChunk,
            FOURCC('L', 's', 'c', 'r'): ScriptChunk,
            FOURCC('V', 'W', 'C', 'F'): ConfigChunk,
            FOURCC('D', 'R', 'C', 'F'): ConfigChunk,
            FOURCC('M', 'C', 's', 'L'): CastListChunk,
        }.get(four_cc)
        if T is None:
            raise RuntimeError("Could not deserialize '%s' chunk" % fourcc_to_string(four_cc))
        res = T(self)
        res.read(ReadStream(view, self.endian))
        return res

    # LingoDec::ChunkResolver
    def get_script(self, id_):
        return self.get_chunk(FOURCC('L', 's', 'c', 'r'), id_)

    def get_script_names(self, id_):
        return self.get_chunk(FOURCC('L', 'n', 'a', 'm'), id_)

    @staticmethod
    def compression_implemented(cid):
        return cid == ZLIB_COMPRESSION_GUID or cid == SND_COMPRESSION_GUID

    def is_cast(self):
        return self.codec in (FOURCC('M', 'C', '9', '5'), FOURCC('F', 'G', 'D', 'C'))

    # ---- script restoration / dumping -------------------------------------------------------
    def parse_scripts(self):
        for cast in self.casts:
            if cast.lctx is None:
                continue
            cast.lctx.parse_scripts()

    def restore_script_text(self):
        for cast in self.casts:
            if cast.lctx is None:
                continue
            for sid in sorted(cast.lctx.scripts):
                script = cast.lctx.scripts[sid]
                if script.member is not None:
                    script.member.set_script_text(script.script_text('\r', self.dot_syntax))

    def script_file_name(self, member):
        """'<ScriptType> <num>[ - <name>]', as ProjectorRays names dumped scripts (before cleanFileName)."""
        if member.type == kScriptMember:
            st = member.member.script_type
            if st == kScoreScript:
                script_type = 'BehaviorScript' if self.version >= 600 else 'ScoreScript'
            elif st == kMovieScript:
                script_type = 'MovieScript'
            elif st == kParentScript:
                script_type = 'ParentScript'
            else:
                script_type = 'UnknownScript'
        else:
            script_type = 'CastScript'
        id_ = str(member.id)
        if member.get_name():
            id_ += ' - ' + member.get_name()
        return clean_file_name(script_type + ' ' + id_)

    def dump_scripts(self, casts_dir, line_ending=None, bytecode=False):
        """Write casts_dir/<cast name>/<ScriptType> <id>[ - name].ls for every script; returns the file count."""
        if line_ending is None:
            line_ending = '\r\n' if os.name == 'nt' else '\n'
        count = 0
        for cast in self.casts:
            if cast.lctx is None:
                continue
            cast_dir = os.path.join(casts_dir, clean_file_name(cast.name))
            os.makedirs(cast_dir, exist_ok=True)
            for sid in sorted(cast.lctx.scripts):
                script = cast.lctx.scripts[sid]
                member = script.member
                if member is None:
                    continue
                base = os.path.join(cast_dir, self.script_file_name(member))
                _write_text(base + '.ls', script.script_text(line_ending, self.dot_syntax))
                if bytecode:
                    _write_text(base + '.lasm', script.bytecode_text(line_ending, self.dot_syntax))
                count += 1
        return count


def _write_text(path, text):
    with open(path, 'w', encoding='latin-1', errors='replace', newline='') as f:
        f.write(text)
