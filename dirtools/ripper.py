"""Pure-Python replacement for the DirectorCastRipper.exe + ProjectorRays.exe first-run rip stage.

Reads <data_dir>/ISPYMAIN8.dxr and <data_dir>/CASTS/*.cxt and writes, per file, under <out_root>/<fileBaseName>/:
    Members.csv, Casts.csv        (CRLF; columns Number,Type,Name,Registration Point,Filename)
    <memberNum>.png / .wav / .txt (no name suffix)
    casts/<castName>/<ScriptType> <n>[ - name].ls     (only for the script-bearing files, see SCRIPT_TARGETS)
"""
import csv
import os
import re
import struct
import warnings

from . import container as c
from . import media

# file name (lowercase) -> required.  convert_data.py reads only BHP's scripts; ISPYMAIN8's are best effort.
SCRIPT_TARGETS = {'bhp.cxt': True, 'ispymain8.dxr': False}

STXT = c.FOURCC('S', 'T', 'X', 'T')

# Lingo `the type of member` names for Director 5-8 cast member type ids.
TYPE_NAMES = {1: 'bitmap', 2: 'filmLoop', 3: 'field', 4: 'palette', 5: 'picture', 6: 'sound', 7: 'button',
              8: 'shape', 9: 'movie', 10: 'digitalVideo', 11: 'script', 12: 'richText'}
XTRA_TYPES = (14, 15)


class RipError(Exception):
    def __init__(self, message, detail=''):
        Exception.__init__(self, message)
        self.message = message
        self.detail = detail


class RipCancelled(Exception):
    pass


def _check(cancel):
    if cancel is not None and cancel.is_set():
        raise RipCancelled()


def xtra_name(member):
    """Xtra / transition members are listed by the Xtra's own name (e.g. DMFade, text, font)."""
    m = re.search(rb'[A-Za-z][ -~]{2,}', member.specific_data)
    return m.group(0).decode('latin-1') if m else 'xtra'


def member_type_name(m):
    if m.type in XTRA_TYPES:
        return xtra_name(m)
    return TYPE_NAMES.get(m.type, 'unknown%d' % m.type)


def field_text(d, m):
    """Text of a field member: the STXT chunk is  u32 offset, u32 textLen, u32 dataLen, ...text..."""
    chunks = media.owned_chunks(d, m, STXT)
    if not chunks:
        return None
    data = chunks[0]
    if len(data) < 12:
        return None
    for fmt in ('>III', '<III'):
        off, tlen, _dlen = struct.unpack(fmt, data[:12])
        if off == 12 and 12 + tlen <= len(data):
            return data[off:off + tlen].decode('latin-1')
    return None


def _write_csv(path, header, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\r\n')
        w.writerow(header)
        w.writerows(rows)


def _unique_dir(out_root, base, used):
    name, n = base, 1
    while name.lower() in used:
        n += 1
        name = '%s_%d' % (base, n)
    used.add(name.lower())
    return os.path.join(out_root, name)


def rip_file(path, out_dir, log=None, cancel=None, scripts=None):
    """Rip one .dxr/.cxt into out_dir. scripts: None -> decide by SCRIPT_TARGETS, True/False to force.
    Returns a dict of counts. Per-member decode problems are logged and skipped; they don't abort the file."""
    log = log or (lambda s: None)
    fname = os.path.basename(path)
    want_scripts = SCRIPT_TARGETS.get(fname.lower()) is not None if scripts is None else scripts
    scripts_required = bool(SCRIPT_TARGETS.get(fname.lower()))

    try:
        with warnings.catch_warnings(record=True) as wl:
            warnings.simplefilter('always')
            d = c.DirectorFile.open(path)
    except Exception as ex:
        raise RipError('Could not read %s: %s' % (fname, ex), detail=repr(ex))
    for w in wl:
        log('warning (%s): %s' % (fname, w.message))

    os.makedirs(out_dir, exist_ok=True)
    counts = {'png': 0, 'wav': 0, 'txt': 0, 'ls': 0, 'skipped': 0}

    # --- members ------------------------------------------------------------------------------
    populated = [cast for cast in d.casts if cast.members]
    prefix_by_cast = {}
    if len(populated) > 1:
        for i, cast in enumerate(populated, 1):
            prefix_by_cast[id(cast)] = '%d_' % i
    rows = []
    for cast in populated:
        pre = prefix_by_cast.get(id(cast), '')
        for mid in sorted(cast.members):
            _check(cancel)
            m = cast.members[mid]
            if m.type == c.kNullMember:
                continue
            reg = (0, 0)
            stem = '%s%d' % (pre, mid)
            try:
                if m.type == c.kBitmapMember:
                    info = media.BitmapInfo(m.specific_data)
                    reg = info.reg_point
                    try:
                        info, rgba = media.decode_bitmap(d, m)
                        media.write_png(os.path.join(out_dir, stem + '.png'), info.width, info.height, rgba)
                        counts['png'] += 1
                    except Exception as ex:
                        counts['skipped'] += 1
                        log('warning: %s member %d bitmap not exported: %s' % (fname, mid, ex))
                elif m.type == c.kSoundMember:
                    try:
                        sinfo, pcm = media.decode_sound(d, m)
                        media.write_wav(os.path.join(out_dir, stem + '.wav'), sinfo, pcm)
                        counts['wav'] += 1
                    except Exception as ex:
                        counts['skipped'] += 1
                        log('warning: %s member %d sound not exported: %s' % (fname, mid, ex))
                elif m.type == 3:
                    text = field_text(d, m)
                    if text is not None:
                        with open(os.path.join(out_dir, stem + '.txt'), 'w', encoding='latin-1', errors='replace',
                                  newline='') as f:
                            f.write(text)
                        counts['txt'] += 1
            except Exception as ex:
                counts['skipped'] += 1
                log('warning: %s member %d: %s' % (fname, mid, ex))
            rows.append((stem, member_type_name(m), m.get_name(), '(%d, %d)' % reg, ''))
    _write_csv(os.path.join(out_dir, 'Members.csv'),
               ['Number', 'Type', 'Name', 'Registration Point', 'Filename'], rows)

    # --- casts list ---------------------------------------------------------------------------
    cast_rows = []
    cl = getattr(d, 'cast_list', None)
    if cl is not None:
        cast_rows = [(i, e.name, '') for i, e in enumerate(cl.entries, 1)]
    _write_csv(os.path.join(out_dir, 'Casts.csv'), ['Number', 'Name', 'Filename'], cast_rows)

    # --- scripts ------------------------------------------------------------------------------
    if want_scripts:
        try:
            d.parse_scripts()
            counts['ls'] = d.dump_scripts(os.path.join(out_dir, 'casts'), line_ending='\r\n')
        except Exception as ex:
            if scripts_required:
                raise RipError('Script decompilation failed for %s: %s' % (fname, ex), detail=repr(ex))
            log('warning: scripts for %s not exported: %s' % (fname, ex))
        if scripts_required and counts['ls'] == 0:
            raise RipError('No scripts were found in %s.' % fname)
    return counts


def find_inputs(data_dir):
    inputs = []
    main = os.path.join(data_dir, 'ISPYMAIN8.dxr')
    if os.path.exists(main):
        inputs.append(main)
    cdir = os.path.join(data_dir, 'CASTS')
    if os.path.isdir(cdir):
        inputs += sorted((os.path.join(cdir, f) for f in os.listdir(cdir) if f.lower().endswith('.cxt')),
                         key=lambda p: os.path.basename(p).lower())
    return inputs


def rip_all(data_dir, out_root, progress=None, cancel=None, log=None):
    """Rip every cast under data_dir into out_root (which should be an empty / fresh folder)."""
    progress = progress or (lambda f, t: None)
    log = log or (lambda s: None)
    inputs = find_inputs(data_dir)
    if not inputs:
        raise RipError('Nothing to rip: the extracted disc files are missing.', detail=str(data_dir))
    os.makedirs(out_root, exist_ok=True)
    used = set()
    total = {}
    for i, path in enumerate(inputs):
        _check(cancel)
        name = os.path.basename(path)
        progress(i / len(inputs), 'Ripping %s (%d of %d)' % (name, i + 1, len(inputs)))
        out_dir = _unique_dir(out_root, os.path.splitext(name)[0], used)
        counts = rip_file(path, out_dir, log=log, cancel=cancel)
        log('%s: %s' % (name, ', '.join('%d %s' % (v, k) for k, v in counts.items() if v)))
        for k, v in counts.items():
            total[k] = total.get(k, 0) + v
    progress(1.0, 'Ripping complete')
    return total
