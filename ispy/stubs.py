"""Placeholder for parent scripts that haven't been ported yet.

It swallows every call so the game can boot, and records which scripts/methods were hit. That list
is the porting to-do (see `python -m ispy.main --report`).
"""
from .runtime import LObject
import re

MISSING = {}    # script name -> set(method names called)
_SEEN_CTOR = set()


def _log(msg):
    print(msg, flush=True)


class MissingScript(LObject):
    def __init__(self, name):
        object.__setattr__(self, '_name', str(name))
        MISSING.setdefault(self._name, set())
        if self._name not in _SEEN_CTOR:                 # live log: first time each unported script is built
            _SEEN_CTOR.add(self._name)
            _log('[unported] %s constructed' % self._name)

    def __getattr__(self, attr):
        if attr.startswith('__'):
            raise AttributeError(attr)
        if re.match(r'^m[A-Z]', attr):
            if attr not in MISSING[self._name]:          # live log: first call of each method
                _log('[unported] %s.%s() called' % (self._name, attr))
            MISSING[self._name].add(attr)

            def _noop(*a, **k):
                return None
            return _noop
        return None          # unknown property reads are VOID, as in Lingo

    def mInit(self, data, alloc):
        # keep the raw data so a later port can see what it was given
        object.__setattr__(self, 'data', data)
        object.__setattr__(self, 'alloc', alloc)
        for k, v in (data or {}).items():
            object.__setattr__(self, k, v)
        return self

    def mGetName(self):
        return self.__dict__.get('pName')

    def mGetType(self):
        return '#MISSING:' + self._name
