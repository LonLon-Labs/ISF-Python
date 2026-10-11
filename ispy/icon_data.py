"""Window icon: read the original game icon straight out of spooky2.exe (the Director projector).

The icon lives in the exe's resource section (RT_GROUP_ICON + RT_ICON).  We parse the PE file by hand, pick the
largest 32-bit entry and turn its DIB into a pygame surface.  If the exe can't be found nothing happens and the
default pygame icon stays.  (This file used to hold an embedded copy of the icon; reading the exe avoids that.)
"""
import os
import struct

EXE_NAME = 'spooky2.exe'
FOLDER_NAME = 'I SPY Spooky Mansion Deluxe'


def _find_exe(exports_root, game_root, project_root):
    cands = []
    for base in (exports_root, game_root, project_root):
        if not base:
            continue
        base = os.path.abspath(base)
        for up in (base, os.path.dirname(base), os.path.dirname(os.path.dirname(base))):
            cands.append(os.path.join(up, FOLDER_NAME, EXE_NAME))
            cands.append(os.path.join(up, EXE_NAME))
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def _read_icon_entries(path):
    """Return a list of (width, height, bitcount, dib_bytes) for the first icon group in the exe."""
    d = open(path, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3C)[0]
    nsec = struct.unpack_from('<H', d, pe + 6)[0]
    opt = struct.unpack_from('<H', d, pe + 20)[0]
    magic = struct.unpack_from('<H', d, pe + 24)[0]
    dd = pe + 24 + (96 if magic == 0x10B else 112)
    rva, _size = struct.unpack_from('<II', d, dd + 16)
    if not rva:
        return []
    so = pe + 24 + opt
    secs = [struct.unpack_from('<8sIIII', d, so + i * 40) for i in range(nsec)]

    def off(r):
        for _n, vs, va, rs, ro in secs:
            if va <= r < va + max(vs, rs):
                return r - va + ro
        return None

    base = off(rva)

    def entries(o):
        nn, ni = struct.unpack_from('<HH', d, o + 12)
        return [struct.unpack_from('<II', d, o + 16 + i * 8) for i in range(nn + ni)]

    leaves = []

    def rec(o, path):
        for nid, x in entries(o):
            if x & 0x80000000:
                rec(base + (x & 0x7FFFFFFF), path + [nid])
            else:
                dr, sz, _cp, _r = struct.unpack_from('<IIII', d, base + x)
                leaves.append((path + [nid], d[off(dr):off(dr) + sz]))

    rec(base, [])
    icons = {p[1]: b for p, b in leaves if p[0] == 3}
    groups = [b for p, b in leaves if p[0] == 14]
    if not groups:
        return []
    g = groups[0]
    cnt = struct.unpack_from('<H', g, 4)[0]
    out = []
    for i in range(cnt):
        w, h, _cc, _res, _pl, bc, _sz, iid = struct.unpack_from('<BBBBHHIH', g, 6 + i * 14)
        if iid in icons:
            out.append((w or 256, h or 256, bc, icons[iid]))
    return out


def _dib_to_surface(pg, dib):
    """32-bit BGRA bottom-up DIB (BITMAPINFOHEADER + pixels) -> pygame surface with per-pixel alpha."""
    hdr = struct.unpack_from('<IiiHH', dib, 0)
    w, h2, bc = hdr[1], hdr[2], hdr[4]
    h = h2 // 2
    if bc != 32:
        return None
    px = dib[hdr[0]:hdr[0] + w * h * 4]
    rows = [px[(h - 1 - y) * w * 4:(h - y) * w * 4] for y in range(h)]   # flip to top-down
    flat = b''.join(rows)
    return pg.image.frombuffer(flat, (w, h), 'BGRA').convert_alpha()


def _bundled_png():
    """icon.png next to this file (written by tools/extract_icon.py; build.py bundles it into the app)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(here, 'icon.png'), os.path.join(os.path.dirname(here), 'packaging', 'icon.png')):
        if os.path.isfile(p):
            return p
    return None


def load_icon_surface(pg, exports_root=None, game_root=None, project_root=None):
    try:
        png = _bundled_png()
        if png:
            return pg.image.load(png)          # no convert_alpha(): this may run before the window exists
    except Exception:
        pass
    try:
        exe = _find_exe(exports_root, game_root, project_root)
        if not exe:
            return None
        best = None
        for w, h, bc, dib in _read_icon_entries(exe):
            if bc == 32 and (best is None or w > best[0]):
                best = (w, h, dib)
        if not best:
            return None
        return _dib_to_surface(pg, best[2])
    except Exception:
        return None
