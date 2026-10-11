"""Sound + text-field support (what Director gave the Lingo for free).

SoundSystem  : puppetSound(chan, member) / sound playFile / soundBusy(chan). Sound *duration* is read
               from the file header (WAV and AIFF) so soundBusy() behaves correctly even with no audio
               device -- a lot of the original logic is "wait until the voice-over finishes".
Field        : member(n).text / line[] / font / scrollTop for field + text members.
"""
import os
import struct
import wave


# ---------------------------------------------------------------------------------------------
# durations
# ---------------------------------------------------------------------------------------------

def _aiff_duration(path):
    with open(path, 'rb') as f:
        data = f.read(4096)
    if data[:4] != b'FORM':
        return None
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack('>I', data[pos + 4:pos + 8])[0]
        if cid == b'COMM':
            frames = struct.unpack('>I', data[pos + 10:pos + 14])[0]
            exp = struct.unpack('>H', data[pos + 16:pos + 18])[0] & 0x7FFF
            mant = struct.unpack('>Q', data[pos + 18:pos + 26])[0]
            rate = mant / float(1 << 63) * (2.0 ** (exp - 16383))
            return frames / rate if rate else None
        pos += 8 + size + (size & 1)
    return None


def duration_ms(path):
    try:
        ext = path.lower().rsplit('.', 1)[-1]
        if ext == 'wav':
            with wave.open(path, 'rb') as w:
                return int(1000 * w.getnframes() / float(w.getframerate()))
        if ext in ('aif', 'aiff'):
            d = _aiff_duration(path)
            if d:
                return int(d * 1000)
    except Exception:
        pass
    return 1000


class SoundSystem:
    def __init__(self, rt):
        self.rt = rt
        self.end = {}
        self._cache = {}
        self._ext_index = None

    # -- lookup -----------------------------------------------------------------------------
    def find_external(self, name):
        """gSoundPath & name  ->  real file (searches the installed game's AIFF folder and Exports)."""
        if self._ext_index is None:
            self._ext_index = {}
            roots = [self.rt.game_root, self.rt.exports_root]
            for root in roots:
                if not root or not os.path.isdir(root):
                    continue
                for dp, _dn, fns in os.walk(root):
                    for fn in fns:
                        if fn.lower().endswith(('.aif', '.aiff', '.wav')):
                            self._ext_index.setdefault(fn.lower(), os.path.join(dp, fn))
        n = os.path.basename(str(name).replace('\\', '/')).lower()
        for cand in (n, n + '.aif', n + '.aiff', n + '.wav'):
            if cand in self._ext_index:
                return self._ext_index[cand]
        stem = n.rsplit('.', 1)[0]
        for ext in ('.aif', '.aiff', '.wav'):
            if stem + ext in self._ext_index:
                return self._ext_index[stem + ext]
        return None

    # -- playback ---------------------------------------------------------------------------
    def stop(self, chan):
        self.end.pop(chan, None)
        pg = self.rt._pg
        if pg and pg.mixer.get_init():
            try:
                pg.mixer.Channel(chan - 1).stop()
            except Exception:
                pass

    def _start(self, chan, path):
        self.end[chan] = self.rt.milliseconds() + duration_ms(path)
        pg = self.rt._pg
        if pg and pg.mixer.get_init():
            try:
                snd = self._cache.get(path)
                if snd is None:
                    snd = self._cache[path] = pg.mixer.Sound(path)
                pg.mixer.Channel(chan - 1).play(snd)
            except Exception:
                pass

    def puppet(self, chan, member):
        """puppetSound(chan, member).  0 / non-sound member / the silent 'flush' sound = stop."""
        from . import movie
        if not member or member == movie.gFlushSound:
            self.stop(chan)
            return
        if isinstance(member, str):
            # a member *name* (e.g. member("DOORNAV")): look it up by name in the room cast, then main
            p = self.rt.member_path_by_name(member, ('wav', 'aif', 'aiff')) or self.find_external(member)
        else:
            p = self.rt.member_path(member, ('wav', 'aif', 'aiff'))
        if p:
            self._start(chan, p)
        else:
            print('[sound] missing member:', member)
            self.stop(chan)

    def play_file(self, chan, name):
        p = self.find_external(name)
        if p:
            self._start(chan, p)
        else:
            print('[sound] missing external sound:', name)
            self.stop(chan)

    def busy(self, chan):
        e = self.end.get(chan)
        if e is None:
            return False
        if self.rt.milliseconds() >= e:
            del self.end[chan]
            return False
        return True


# ---------------------------------------------------------------------------------------------
# text fields
# ---------------------------------------------------------------------------------------------

class Field:
    def __init__(self, num, kind='field'):
        self.num = num
        self.kind = kind
        self.lines = [' ']
        self.font = 'Arial'
        self.fontSize = 12
        self.foreColor = None
        self.alignment = 'left'
        self.scrollTop = 0
        self.pageHeight = 130
        self.width = 295
        self.fontStyle = 'plain'
        self.lineColors = {}
        self.lineSpace = 0

    # member.text
    @property
    def text(self):
        return '\r'.join(self.lines)

    @text.setter
    def text(self, v):
        self.lines = str(v).replace('\n', '\r').split('\r')
        self.lineColors = {}

    def line_count(self):
        return len(self.lines)

    def get_line(self, n):
        return self.lines[n - 1] if 1 <= n <= len(self.lines) else ''

    def set_line(self, n, v):
        while len(self.lines) < n:
            self.lines.append('')
        self.lines[n - 1] = v
