# Bitmap -> PNG and sound -> WAV extraction for Director 8.5 casts (pure Python, no third-party deps).
# Layout facts derived empirically from the I SPY Spooky Mansion Deluxe casts; see notes inline.
import struct
import wave
import zlib

from .container import FOURCC, kBitmapMember, kSoundMember, fourcc_to_string, warn

BITD = FOURCC('B', 'I', 'T', 'D')
ALFA = FOURCC('A', 'L', 'F', 'A')
SND_H = FOURCC('s', 'n', 'd', 'H')
SND_S = FOURCC('s', 'n', 'd', 'S')


def decompress_snd(data, uncompressed_len, chunk_id):
    # Only reached for Afterburner files with the SND compression GUID; the I SPY discs don't use it.
    raise NotImplementedError('Afterburner snd decompression (chunk %d) is not supported' % chunk_id)


# ---- helpers ---------------------------------------------------------------------------------
def owned_chunks(d, member, four_cc):
    """Raw data of every chunk of four_cc the KEY* table assigns to this CASt member, in table order."""
    out = []
    seen = set()
    for e in d.key_table.entries:
        if e.cast_id == member.section_id and e.four_cc == four_cc and d.chunk_exists(four_cc, e.section_id):
            # The I SPY key tables list some voice-over sndS chunks 50-150 times; each section counts once.
            if e.section_id in seen:
                continue
            seen.add(e.section_id)
            out.append(d.get_chunk_data(four_cc, e.section_id))
    return out


def write_png(path, width, height, rgba):
    """Minimal RGBA PNG writer. rgba is bytes of length width*height*4."""
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    stride = width * 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(bytes(raw), 6)))
        f.write(chunk(b'IEND', b''))


# ---- bitmaps ---------------------------------------------------------------------------------
class BitmapInfo:
    """28-byte CASt specific data of a Director 8.5 bitmap member (offsets verified on I SPY data):
       0  u16  pitch (bytes per row) in low 12 bits, flags in high bits
       2  4xi16 initial rect (top, left, bottom, right) -> image size
       10 8 bytes (unknown / bounding data, ignored)
       18 i16  reg y    20 i16 reg x
       22 u8   flags    23 u8  bits per pixel
       24 i16  palette cast lib   26 i16 palette member (-1 = built-in, see palette_id)"""

    def __init__(self, sd):
        if len(sd) < 22:
            raise ValueError('bitmap specific data too short (%d)' % len(sd))
        self.pitch = struct.unpack('>H', sd[0:2])[0] & 0x0FFF
        self.top, self.left, self.bottom, self.right = struct.unpack('>4h', sd[2:10])
        self.reg_y, self.reg_x = struct.unpack('>2h', sd[18:22])
        # Short (23-byte) info blocks have no bpp byte: Director treats those as 1-bit.
        self.flags = sd[22] if len(sd) > 22 else 0
        self.bpp = sd[23] if len(sd) > 23 else 1
        self.pal_cast, self.pal_id = struct.unpack('>2h', sd[24:28]) if len(sd) >= 28 else (-1, 0)
        self.width = self.right - self.left
        self.height = self.bottom - self.top

    @property
    def reg_point(self):
        # Stored in the same coordinates as the initial rect; Cast Ripper reports it relative to the rect's top-left.
        return (self.reg_x - self.left, self.reg_y - self.top)


def rle_unpack(data, size):
    """Director/PackBits RLE: n>=0 (as signed) -> n+1 literals; n<0 -> repeat next byte 1-n times."""
    out = bytearray()
    i = 0
    n_data = len(data)
    while i < n_data and len(out) < size:
        n = data[i]
        i += 1
        if n < 0x80:
            out += data[i:i + n + 1]
            i += n + 1
        elif n != 0x80:
            if i >= n_data:
                break
            out += bytes((data[i],)) * (257 - n)
            i += 1
    if len(out) < size:
        out += bytes(size - len(out))
    return bytes(out[:size])


def _expand5(v):
    return (v << 3) | (v >> 2)


# 5-5-5 pixel = hi byte (x RRRRR GG) + lo byte (GGG BBBBB). Lookup tables for bytes.translate.
_T_R = bytes(_expand5((i >> 2) & 31) for i in range(256))      # hi -> expanded red
_T_B = bytes(_expand5(i & 31) for i in range(256))             # lo -> expanded blue
_T_GH = bytes((i & 3) << 3 for i in range(256))                # hi -> top 2 bits of green (already shifted)
_T_GL = bytes(i >> 5 for i in range(256))                      # lo -> low 3 bits of green
_T_E5 = bytes(_expand5(i & 31) for i in range(256))            # 5-bit green -> 8-bit


def _build_mac_palette():
    # Standard Macintosh 8-bit system palette: 6x6x6 cube (white first, black omitted), then 10-step
    # red/green/blue/gray ramps, black last.
    pal = []
    levels = (0xFF, 0xCC, 0x99, 0x66, 0x33, 0x00)
    for r in levels:
        for g in levels:
            for b in levels:
                pal.append(bytes((r, g, b)))
    pal = pal[:215]
    ramp = (0xEE, 0xDD, 0xBB, 0xAA, 0x88, 0x77, 0x55, 0x44, 0x22, 0x11)
    for chan in range(3):
        for v in ramp:
            c = [0, 0, 0]
            c[chan] = v
            pal.append(bytes(c))
    for v in ramp:
        pal.append(bytes((v, v, v)))
    pal.append(bytes((0, 0, 0)))
    return pal


MAC_PALETTE = _build_mac_palette()


def decode_bitmap(d, member, mode16='planar'):
    """Return (info, rgba_bytes) for a bitmap CASt member. Raises NotImplementedError for <=8bpp (palette) images.
       mode16: how 16bpp rows are laid out -- 'planar' (hi-byte plane then lo-byte plane) or 'interleaved' (BE words)."""
    info = BitmapInfo(member.specific_data)
    w, h, pitch, bpp = info.width, info.height, info.pitch, info.bpp
    if w <= 0 or h <= 0:
        raise ValueError('empty bitmap %dx%d' % (w, h))
    bitd = owned_chunks(d, member, BITD)
    if not bitd:
        raise ValueError('bitmap has no BITD chunk')
    data = bitd[0]
    expected = pitch * h
    is_raw = len(data) == expected
    px = data[:expected] if is_raw else rle_unpack(data, expected)
    if is_raw and bpp == 16:
        # Uncompressed 16bpp rows are interleaved big-endian words; only the RLE'd form is planar (hi plane,
        # lo plane). Found because every mismatch against Cast Ripper's PNGs had BITD size == pitch*height.
        mode16 = 'interleaved'
    rgba = bytearray(w * h * 4)

    if bpp == 32:
        alfa = owned_chunks(d, member, ALFA)
        for y in range(h):
            row = px[y * pitch:(y + 1) * pitch]
            a, r, g, b = (row[c * w:(c + 1) * w] for c in range(4))
            o = y * w * 4
            rgba[o:o + w * 4:4] = r
            rgba[o + 1:o + w * 4:4] = g
            rgba[o + 2:o + w * 4:4] = b
            rgba[o + 3:o + w * 4:4] = a
    elif bpp == 16:
        # Vectorised with bytes.translate / big-int OR instead of a Python loop per pixel (~8,000 of these on disc).
        hi_rows, lo_rows = [], []
        for y in range(h):
            row = px[y * pitch:(y + 1) * pitch]
            if mode16 == 'planar':
                hi_rows.append(row[:w])
                lo_rows.append(row[w:2 * w])
            else:
                hi_rows.append(row[0:2 * w:2])
                lo_rows.append(row[1:2 * w:2])
        hi = b''.join(hi_rows)
        lo = b''.join(lo_rows)
        n = len(hi)
        if len(lo) != n:
            raise ValueError('16-bit bitmap data too short')
        r = hi.translate(_T_R)
        b = lo.translate(_T_B)
        g = (int.from_bytes(hi.translate(_T_GH), 'big') | int.from_bytes(lo.translate(_T_GL), 'big')) \
            .to_bytes(n, 'big').translate(_T_E5)
        rgba[0::4] = r
        rgba[1::4] = g
        rgba[2::4] = b
        rgba[3::4] = b'\xff' * n
    elif bpp == 1:
        # 1 = black, 0 = white; rows are MSB-first bit-packed, `pitch` bytes per row.
        for y in range(h):
            row = px[y * pitch:(y + 1) * pitch]
            o = y * w * 4
            for x in range(w):
                v = 0 if (row[x >> 3] >> (7 - (x & 7))) & 1 else 255
                rgba[o] = rgba[o + 1] = rgba[o + 2] = v
                rgba[o + 3] = 255
                o += 4
    elif bpp == 8:
        # No palette members exist on the I SPY discs, so use the standard Mac system palette (approximation).
        pal = MAC_PALETTE
        for y in range(h):
            row = px[y * pitch:y * pitch + w]
            o = y * w * 4
            for x in range(w):
                rgba[o:o + 3] = pal[row[x]]
                rgba[o + 3] = 255
                o += 4
        info.approx_palette = True
    else:
        raise NotImplementedError('%d-bit bitmap (palette id %d/%d)' % (bpp, info.pal_cast, info.pal_id))
    return info, bytes(rgba)


# ---- sounds ----------------------------------------------------------------------------------
class SoundInfo:
    """sndH (100 bytes, big endian): 0x04 byte length, 0x20 byte length again, 0x24 frame count, 0x2C sample rate."""

    def __init__(self, hdr):
        if len(hdr) < 0x30:
            raise ValueError('sndH too short (%d)' % len(hdr))
        self.byte_len, = struct.unpack('>I', hdr[0x20:0x24])
        self.frames, = struct.unpack('>I', hdr[0x24:0x28])
        self.rate, = struct.unpack('>I', hdr[0x2C:0x30])
        self.sample_bytes = (self.byte_len // self.frames) if self.frames else 0
        self.channels = 1


def decode_sound(d, member):
    """Return (info, pcm_le_bytes). 16-bit samples are big-endian signed in the file -> converted to little endian;
       8-bit samples are unsigned. Channel count/bit depth are inferred from byte_len / frames."""
    hdrs = owned_chunks(d, member, SND_H)
    if not hdrs:
        raise ValueError('sound has no sndH chunk')
    info = SoundInfo(hdrs[0])
    pcm = b''.join(owned_chunks(d, member, SND_S))
    if len(pcm) != info.byte_len:
        warn('sound %d: sndS total %d bytes but header says %d' % (member.id, len(pcm), info.byte_len))
    if info.sample_bytes == 2:
        n = len(pcm) // 2
        pcm = struct.pack('<%dh' % n, *struct.unpack('>%dh' % n, pcm[:n * 2]))
    elif info.sample_bytes != 1:
        raise NotImplementedError('sound %d: %d bytes/frame' % (member.id, info.sample_bytes))
    return info, pcm


def write_wav(path, info, pcm):
    with wave.open(path, 'wb') as w:
        w.setnchannels(info.channels)
        w.setsampwidth(info.sample_bytes)
        w.setframerate(info.rate)
        w.writeframes(pcm)
