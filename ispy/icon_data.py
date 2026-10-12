"""Window icon: read the bundled ispy/icon.png (written by tools/extract_icon.py).

Only the bundled PNG is used; the game's Fantasy.ico (copied from the disc) is never read.
If icon.png is missing nothing happens and the default pygame icon stays.

The ICO helpers below (_read_icon_entries, read_ico_file, dib_to_rgba) are kept for
tools/extract_icon.py, which can pull an icon out of a Windows .exe or a standalone .ico file.
"""
import io
import os
import struct

PNG_SIG = b'\x89PNG\r\n\x1a\n'


def read_ico_file(path):
    """Return a list of (width, height, bitcount, data) for every image in an .ico file.
    data is a DIB (BITMAPINFOHEADER + pixels + AND mask) or, in newer files, a complete PNG."""
    with open(path, 'rb') as f:
        d = f.read()
    _reserved, kind, count = struct.unpack_from('<HHH', d, 0)
    if kind != 1:
        return []
    out = []
    for i in range(count):
        w, h, _cc, _res, _planes, bc, size, off = struct.unpack_from('<BBBBHHII', d, 6 + i * 16)
        data = d[off:off + size]
        if data[:8] == PNG_SIG:
            w, h = struct.unpack('>II', data[16:24])
        else:
            w, h = w or 256, h or 256
            if not bc and len(data) >= 16:
                bc = struct.unpack_from('<H', data, 14)[0]
        out.append((w, h, bc, data))
    return out


def _read_icon_entries(path):
    """Return a list of (width, height, bitcount, dib_bytes) for the first icon group in an exe."""
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


def dib_to_rgba(dib):
    """ICO-style DIB (BITMAPINFOHEADER with doubled height, XOR bitmap + AND mask) -> (w, h, rgba bytes).
    Handles 1/4/8-bit palette, 24-bit and 32-bit images."""
    hsize, w, h2, _planes, bc, comp, _isz, _xp, _yp, clrused, _clrimp = struct.unpack_from('<IiiHHIIiiII', dib, 0)
    if comp != 0:
        raise ValueError('compressed icon bitmap (%d) not supported' % comp)
    h = abs(h2) // 2
    pal_n = clrused or ((1 << bc) if bc <= 8 else 0)
    pal = [dib[hsize + i * 4:hsize + i * 4 + 3] for i in range(pal_n)]          # stored B, G, R
    pix = hsize + pal_n * 4
    rowb = ((w * bc + 31) // 32) * 4
    mask_off = pix + rowb * h
    mrow = ((w + 31) // 32) * 4
    have_mask = mask_off + mrow * h <= len(dib)
    out = bytearray(w * h * 4)
    any_alpha = False
    for y in range(h):
        base = pix + (h - 1 - y) * rowb                     # rows are stored bottom-up
        row = dib[base:base + rowb]
        o = y * w * 4
        for x in range(w):
            if bc == 32:
                b, g, r, a = row[x * 4:x * 4 + 4]
            elif bc == 24:
                b, g, r = row[x * 3:x * 3 + 3]
                a = 255
            else:
                if bc == 8:
                    i = row[x]
                elif bc == 4:
                    i = (row[x >> 1] >> (4 * (1 - (x & 1)))) & 15
                elif bc == 1:
                    i = (row[x >> 3] >> (7 - (x & 7))) & 1
                else:
                    raise ValueError('%d-bit icon not supported' % bc)
                b, g, r = pal[i]
                a = 255
            if a:
                any_alpha = True
            out[o:o + 4] = bytes((r, g, b, a))
            o += 4
    if have_mask and (bc < 32 or not any_alpha):
        for y in range(h):
            mbase = mask_off + (h - 1 - y) * mrow
            for x in range(w):
                transparent = (dib[mbase + (x >> 3)] >> (7 - (x & 7))) & 1
                idx = (y * w + x) * 4
                if bc == 32 and not any_alpha:
                    out[idx + 3] = 0 if transparent else 255
                elif transparent:
                    out[idx + 3] = 0
    return w, h, bytes(out)


def _entry_to_surface(pg, data):
    if data[:8] == PNG_SIG:
        return pg.image.load(io.BytesIO(data))
    w, h, rgba = dib_to_rgba(data)
    return pg.image.frombuffer(rgba, (w, h), 'RGBA')        # no convert_alpha(): may run before the window exists


def _bundled_png():
    """icon.png next to this file (written by tools/extract_icon.py; build.py bundles it into the app)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(here, 'icon.png'), os.path.join(os.path.dirname(here), 'packaging', 'icon.png')):
        if os.path.isfile(p):
            return p
    return None


def load_icon_surface(pg, exports_root=None, game_root=None, project_root=None):
    # only the bundled PNG is used; the game's Fantasy.ico is deliberately ignored
    try:
        png = _bundled_png()
        if png:
            return pg.image.load(png)
    except Exception:
        pass
    return None