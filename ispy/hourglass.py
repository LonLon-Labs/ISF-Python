"""The classic hourglass "busy" cursor (the Windows/Director wait cursor), drawn procedurally.

pygame's SYSTEM_CURSOR_WAIT is the blue spinning ring on modern Windows; the original game showed the old
hourglass, so waitCursor() uses this instead.  Returns None if custom colour cursors aren't supported.
"""

_cache = {}


def make_hourglass(pg):
    if 'c' in _cache:
        return _cache['c']
    cur = None
    try:
        S = 32
        surf = pg.Surface((S, S), pg.SRCALPHA)
        K = (0, 0, 0, 255)
        W = (255, 255, 255, 255)
        G = (150, 150, 150, 255)        # sand
        # glass (white fill, black outline)
        top = [(8, 6), (23, 6), (17, 15), (17, 16), (23, 25), (8, 25), (14, 16), (14, 15)]
        pg.draw.polygon(surf, W, top)
        pg.draw.polygon(surf, K, top, 1)
        # sand: a little left in the top bulb, a pile in the bottom bulb
        pg.draw.polygon(surf, G, [(11, 9), (20, 9), (16, 14)])
        pg.draw.polygon(surf, G, [(11, 24), (20, 24), (17, 20), (14, 20)])
        pg.draw.line(surf, G, (16, 15), (16, 19))
        # top and bottom plates
        pg.draw.rect(surf, K, pg.Rect(6, 3, 19, 3))
        pg.draw.rect(surf, K, pg.Rect(6, 26, 19, 3))
        pg.draw.rect(surf, W, pg.Rect(7, 4, 17, 1))
        cur = pg.cursors.Cursor((16, 16), surf)
    except Exception:
        cur = None
    _cache['c'] = cur
    return cur
