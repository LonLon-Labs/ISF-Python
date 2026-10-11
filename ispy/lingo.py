"""Lingo-compatibility helpers.

Lingo lists are 1-based, symbols are case-insensitive, and propLists are ordered. The port keeps
Python's native 0-based lists/dicts but funnels every place the original relied on those quirks
through this module so the translated code stays recognisably close to the Lingo.
"""
import random as _random


class Sym(str):
    """Lingo symbol (#name). Case-insensitive equality/hash, like Director."""
    __slots__ = ()

    def __eq__(self, other):
        if isinstance(other, str):
            return self.lower() == other.lower()
        return NotImplemented

    def __ne__(self, other):
        r = self.__eq__(other)
        return r if r is NotImplemented else not r

    def __hash__(self):
        return hash(self.lower())

    def __repr__(self):
        return '#' + str(self)


class Point(tuple):
    """point(h, v) with Lingo arithmetic."""
    def __new__(cls, h=0, v=0):
        return tuple.__new__(cls, (h, v))

    h = property(lambda s: s[0])
    v = property(lambda s: s[1])

    def __add__(self, o):
        return Point(self[0] + o[0], self[1] + o[1])

    def __sub__(self, o):
        return Point(self[0] - o[0], self[1] - o[1])


class Rect(tuple):
    def __new__(cls, l=0, t=0, r=0, b=0):
        return tuple.__new__(cls, (l, t, r, b))

    left = property(lambda s: s[0])
    top = property(lambda s: s[1])
    right = property(lambda s: s[2])
    bottom = property(lambda s: s[3])
    width = property(lambda s: s[2] - s[0])
    height = property(lambda s: s[3] - s[1])

    def inside(self, p):
        return self[0] <= p[0] < self[2] and self[1] <= p[1] < self[3]


def decode(v):
    """Turn converter JSON ({"$sym":..}, {"$point":..}) back into Sym/Point/Rect, recursively."""
    if isinstance(v, dict):
        if '$sym' in v:
            return Sym(v['$sym'])
        if '$point' in v:
            return Point(*v['$point'])
        if '$rect' in v:
            return Rect(*v['$rect'])
        return {k: decode(x) for k, x in v.items()}
    if isinstance(v, list):
        return [decode(x) for x in v]
    return v


# ---- list helpers from "General Handlers" (MovieScript 24) ------------------------------------

def random_(n):
    """Lingo random(n): integer 1..n inclusive."""
    return _random.randint(1, n)


def pop_one(lst):
    return lst.pop(0)


def pop_last(lst):
    return lst.pop()


def pop_list(lst, n):
    return [lst.pop(0) for _ in range(n)]


def pop_last_range(lst, n):
    """Lingo popLastRange removes (n+1) items when there are more than n (its loop is inclusive).
    Reproduced faithfully because sprite allocation depends on it."""
    count = len(lst)
    first = count - n  # 1-based index of first removed item
    if first > 0:
        out = lst[first - 1:]
        del lst[first - 1:]
        return out
    return lst


def randomize_list(lst):
    src = list(lst)
    _random.shuffle(src)
    return src


def get_range_list(lo, hi):
    return list(range(lo, hi + 1))


def get_def(val, default):
    return default if val is None else val


def lingo_get(lst, i):
    """1-based getAt()."""
    return lst[i - 1]


def set_properties(data, obj):
    """setProperties(theObjectData, me): copy every key onto the object as an attribute."""
    if not data:
        return
    for k, v in data.items():
        setattr(obj, k, v)


def ease(progress):
    import math
    return (math.sin(progress * math.pi - math.pi / 2) + 1) / 2


def stage_constrain_h(src, rng):
    return src if 0 + rng < src < 640 - rng else (640 - rng if src >= 640 - rng else 0 + rng)


def stage_constrain_v(src, rng):
    return src if 0 + rng < src < 480 - rng else (480 - rng if src >= 480 - rng else 0 + rng)
