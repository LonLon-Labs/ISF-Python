"""Parser for Lingo literal data (lists, propLists, symbols, point(), rect(), strings, numbers)
as found in the decompiled getSpookyData_* / getGlobalGameData handlers.

Output mapping:
  [a, b]            -> list
  [#k: v, ...]      -> dict (keys without '#')
  [:]               -> {}
  #sym              -> {"$sym": "sym"}
  point(x, y)       -> {"$point": [x, y]}
  rect(l,t,r,b)     -> {"$rect": [...]}
  "text"            -> str
  VOID / EMPTY      -> None / ""
"""
import json
import re
import sys

TOKEN = re.compile(r'''
    \s*(?:
      (?P<str>"[^"]*")
     |(?P<sym>\#[A-Za-z_][A-Za-z0-9_]*)
     |(?P<num>-?\d+\.\d+|-?\d+)
     |(?P<id>[A-Za-z_][A-Za-z0-9_]*)
     |(?P<p>[\[\](),:])
    )''', re.X)


class Sym(str):
    pass


def tokenize(s):
    pos, out = 0, []
    while pos < len(s):
        m = TOKEN.match(s, pos)
        if not m or m.end() == pos:
            if s[pos:].strip() == '':
                break
            raise ValueError('bad token at %d: %r' % (pos, s[pos:pos + 40]))
        pos = m.end()
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
    return out


class P:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, off=0):
        j = self.i + off
        return self.t[j] if j < len(self.t) else (None, None)

    def next(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def expect(self, v):
        k, x = self.next()
        if x != v:
            raise ValueError('expected %r got %r at token %d' % (v, x, self.i))

    def value(self):
        k, x = self.next()
        if k == 'str':
            return x[1:-1]
        if k == 'sym':
            return Sym(x[1:])
        if k == 'num':
            return float(x) if '.' in x else int(x)
        if k == 'id':
            low = x.lower()
            if low == 'void':
                return None
            if low == 'empty':
                return ''
            if low in ('point', 'rect'):
                self.expect('(')
                a = []
                while self.peek()[1] != ')':
                    a.append(self.value())
                    if self.peek()[1] == ',':
                        self.next()
                self.expect(')')
                return {'$' + low: a}
            raise ValueError('unknown identifier ' + x)
        if x == '[':
            return self.list_()
        raise ValueError('unexpected %r' % x)

    def list_(self):
        # called after '['
        if self.peek()[1] == ':':
            self.next()
            self.expect(']')
            return {}
        if self.peek()[1] == ']':
            self.next()
            return []
        is_prop = self.peek(1)[1] == ':'
        if is_prop:
            d = {}
            while True:
                kk, kv = self.next()
                key = kv[1:] if kk == 'sym' else (kv[1:-1] if kk == 'str' else kv)
                self.expect(':')
                d[str(key)] = self.value()
                k, x = self.next()
                if x == ']':
                    return d
                if x != ',':
                    raise ValueError('expected , or ] got %r' % x)
        out = []
        while True:
            out.append(self.value())
            k, x = self.next()
            if x == ']':
                return out
            if x != ',':
                raise ValueError('expected , or ] got %r' % x)


def to_json_safe(v):
    if isinstance(v, Sym):
        return {'$sym': str(v)}
    if isinstance(v, dict):
        return {k: to_json_safe(x) for k, x in v.items()}
    if isinstance(v, list):
        return [to_json_safe(x) for x in v]
    return v


def parse_handler_file(text):
    """Return the first '<var> = [ ... ]' literal in a handler."""
    text = text.replace('\r', '')
    m = re.search(r'^\s*(\w+)\s*=\s*(\[)', text, re.M)
    if not m:
        raise ValueError('no literal assignment found')
    start = m.start(2)
    depth, i, instr = 0, start, False
    while i < len(text):
        c = text[i]
        if instr:
            # Lingo strings have no backslash escapes (Windows paths like "C:\\DATA\\" end in one)
            if c == '"':
                instr = False
        else:
            if c == '"':
                instr = True
            elif c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    break
        i += 1
    p = P(tokenize(text[start:i + 1]))
    p.expect('[')
    return p.list_()


if __name__ == '__main__':
    src = open(sys.argv[1], encoding='utf-8', errors='replace').read()
    json.dump(to_json_safe(parse_handler_file(src)), sys.stdout, indent=1)
