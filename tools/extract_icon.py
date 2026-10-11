"""Extract the game's icon from spooky2.exe (the Director projector) for the window and for PyInstaller.

    python tools/extract_icon.py                      # looks for ..\\I SPY Spooky Mansion Deluxe\\spooky2.exe
    python tools/extract_icon.py "D:\\path\\spooky2.exe"

Writes (all from the exe's first icon group, nothing is resized or redrawn):
    packaging/icon.ico   every size in the exe's icon group; PyInstaller embeds it as the app's exe icon
    packaging/icon.png   the largest image as PNG (Linux AppImage icon, macOS fallback)
    ispy/icon.png        the same PNG; the game loads it for the window / taskbar icon (build.py bundles it)
Pure Python, standard library only.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from ispy.icon_data import _read_icon_entries         # noqa: E402  (PE resource walker, already used by the game)

DEFAULT_EXE = os.path.join(os.path.dirname(ROOT), 'I SPY Spooky Mansion Deluxe', 'spooky2.exe')
PNG_SIG = b'\x89PNG\r\n\x1a\n'


def dib_to_rgba(dib):
    """ICO-style DIB (BITMAPINFOHEADER with doubled height, XOR bitmap + AND mask) -> (w, h, rgba bytes)."""
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


def write_png(path, w, h, rgba):
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b''.join(b'\x00' + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    with open(path, 'wb') as f:
        f.write(PNG_SIG + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def write_ico(path, entries):
    """entries: (width, height, bitcount, data) as found in the exe; data is a DIB or a PNG, copied unchanged."""
    entries = sorted(entries, key=lambda e: (e[0], e[2]))
    head = struct.pack('<HHH', 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    table, blobs = b'', b''
    for w, h, bc, data in entries:
        colors = (1 << bc) if bc < 8 else 0
        table += struct.pack('<BBBBHHII', w if w < 256 else 0, h if h < 256 else 0, colors, 0, 1, bc, len(data), offset)
        blobs += data
        offset += len(data)
    with open(path, 'wb') as f:
        f.write(head + table + blobs)


def main():
    exe = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXE
    if not os.path.isfile(exe):
        print('spooky2.exe not found: %s\nPass its path as an argument.' % exe)
        return 1
    entries = _read_icon_entries(exe)
    if not entries:
        print('No icon group found in %s' % exe)
        return 1
    print('icon sizes in the exe:', ', '.join('%dx%d@%dbpp%s' % (w, h, bc, ' (PNG)' if d[:8] == PNG_SIG else '')
                                                for w, h, bc, d in entries))

    best = max(entries, key=lambda e: (e[0], e[2]))
    if best[3][:8] == PNG_SIG:
        png = best[3]
    else:
        w, h, rgba = dib_to_rgba(best[3])
        tmp = os.path.join(HERE, '_icon_tmp.png')
        write_png(tmp, w, h, rgba)
        with open(tmp, 'rb') as f:
            png = f.read()
        os.remove(tmp)

    pkg = os.path.join(ROOT, 'packaging')
    os.makedirs(pkg, exist_ok=True)
    write_ico(os.path.join(pkg, 'icon.ico'), entries)
    for p in (os.path.join(pkg, 'icon.png'), os.path.join(ROOT, 'ispy', 'icon.png')):
        with open(p, 'wb') as f:
            f.write(png)
    print('wrote packaging/icon.ico, packaging/icon.png and ispy/icon.png (largest image %dx%d)' % (best[0], best[1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
