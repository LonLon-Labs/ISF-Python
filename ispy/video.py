"""Bink video playback (ParentScript 107, BINK) using ffmpeg.

The original drove the RAD Bink Director xtra. Here the .bik files in <game>\\DATA\\BINK are decoded by
ffmpeg (system `ffmpeg`, or the one bundled with `pip install imageio-ffmpeg`): frames are streamed
through a pipe and drawn over the stage, the soundtrack is extracted once to a temp .wav and played
through pygame.mixer. If no ffmpeg is found the BINK script takes the original's own
`not binkLoaded()` path (wait ~10 updates, then show the still), as before.
"""
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time

from . import runtime, movie as M
from .runtime import LObject, lingo_script
from .lingo import Sym, set_properties, pop_one
from .ui import R, S, load_mem, set_behavior, remove_behavior, blank

_NOWIN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_ffmpeg = False          # False = not looked up yet, None = not available
_warned = False


def find_ffmpeg():
    global _ffmpeg
    if _ffmpeg is False:
        _ffmpeg = shutil.which('ffmpeg')
        if not _ffmpeg:
            try:
                import imageio_ffmpeg
                _ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                _ffmpeg = None
    return _ffmpeg


class VideoClip:
    def __init__(self, rt, path, pos=(0, 0)):
        self.rt, self.path = rt, path
        self.pos = tuple(pos) if isinstance(pos, (tuple, list)) else (0, 0)
        self.w, self.h, self.fps = 640, 480, 15.0
        self.proc = None
        self.q = None
        self.eof = True
        self.frame = None
        self.idx = 0
        self.t0 = 0.0
        self.chan = None
        self.finished = False
        self.wav = None
        self._stop = False
        self._probe()
        self._prep_audio()

    def _probe(self):
        try:
            r = subprocess.run([find_ffmpeg(), '-hide_banner', '-i', self.path], capture_output=True,
                               text=True, errors='replace', creationflags=_NOWIN, timeout=20)
            txt = r.stderr
            m = re.search(r'Video:.*?,\s*(\d{2,5})x(\d{2,5})', txt)
            if m:
                self.w, self.h = int(m.group(1)), int(m.group(2))
            m = re.search(r'(\d+(?:\.\d+)?)\s*fps', txt) or re.search(r'(\d+(?:\.\d+)?)\s*tbr', txt)
            if m and float(m.group(1)) > 0:
                self.fps = float(m.group(1))
        except Exception as e:
            print('[bink] probe failed:', e)

    def _prep_audio(self):
        try:
            d = os.path.join(tempfile.gettempdir(), 'ispy_bink')
            os.makedirs(d, exist_ok=True)
            wav = os.path.join(d, os.path.splitext(os.path.basename(self.path))[0] + '.wav')
            if not os.path.exists(wav):
                subprocess.run([find_ffmpeg(), '-v', 'error', '-y', '-i', self.path, '-vn', '-acodec', 'pcm_s16le',
                                '-ar', '44100', '-ac', '2', wav], capture_output=True, creationflags=_NOWIN,
                               timeout=120)
            if os.path.exists(wav) and os.path.getsize(wav) > 1000:
                self.wav = wav
            elif os.path.exists(wav):
                os.remove(wav)
        except Exception as e:
            print('[bink] audio extract failed:', e)

    def _read(self, proc, q):
        size = self.w * self.h * 3
        try:
            while not self._stop:
                buf = proc.stdout.read(size)
                if len(buf) < size:
                    break
                while not self._stop:
                    try:
                        q.put(buf, timeout=0.1)
                        break
                    except queue.Full:
                        pass
        except Exception:
            pass
        self.eof = True

    def start(self):
        self.stop()
        self._stop = False
        self.finished = False
        self.frame = None
        self.idx = 0
        self.eof = False
        self.q = queue.Queue(6)
        self.proc = subprocess.Popen([find_ffmpeg(), '-v', 'error', '-i', self.path, '-f', 'rawvideo',
                                      '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, creationflags=_NOWIN)
        threading.Thread(target=self._read, args=(self.proc, self.q), daemon=True).start()
        pg = self.rt._pg
        if self.wav and pg and pg.mixer.get_init():
            try:
                self.chan = pg.mixer.Channel(pg.mixer.get_num_channels() - 1)
                self.chan.play(pg.mixer.Sound(self.wav))
            except Exception:
                self.chan = None
        self.t0 = time.monotonic()
        self.rt.video = self

    def update(self):
        """Advance to the frame the clock says; True once the clip has ended."""
        if self.finished:
            return True
        target = int((time.monotonic() - self.t0) * self.fps) + 1
        buf = None
        while self.idx < target:
            try:
                buf = self.q.get_nowait()
            except queue.Empty:
                break
            self.idx += 1
        if buf is not None:
            self.frame = self.rt._pg.image.frombuffer(buf, (self.w, self.h), 'RGB').convert()
        if self.eof and self.q.empty():
            self.finished = True
        return self.finished

    def stop(self):
        self._stop = True
        if self.proc is not None:
            try:
                self.proc.kill()
            except Exception:
                pass
            self.proc = None
        if self.chan is not None:
            try:
                self.chan.stop()
            except Exception:
                pass
            self.chan = None
        if getattr(self.rt, 'video', None) is self:
            self.rt.video = None
        self.finished = True


@lingo_script('BINK')                                    # ParentScript 107 (replaces the stub in ui.py)
class Bink(LObject):
    def __init__(self):
        self.pParent = 0
        self.pPlayed = 0
        self.pBinkObject = 0
        self.pFlushCount = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pButtonSprite = pop_one(alloc)
        self.pBackSprite = pop_one(alloc)
        base = R().game_root or ''
        self.pFilePath = os.path.join(base, 'DATA', 'BINK', str(self.pFileName))
        self.pInterruptable = 1
        self.pPlayed = 0
        self.pFlushCount = 0
        self.pSavedList = [Sym('pPlayed')]
        M.addObjectGlob(self)
        return self

    def binkLoaded(self):
        global _warned
        if find_ffmpeg() and os.path.exists(self.pFilePath):
            return True
        if not _warned:
            _warned = True
            why = 'ffmpeg not found (pip install imageio-ffmpeg)' if not find_ffmpeg() else 'file missing: ' + self.pFilePath
            print('[bink] videos disabled -', why)
        return False

    def mDestroy(self): pass
    def mSetParent(self, o): self.pParent = o
    def mGetType(self): return Sym('Bink')
    def mGetName(self): return self.pName
    def mSetEventTag(self, t): self.pEventTag = t
    def mGetEventTag(self): return self.pEventTag
    def mBinkLoaded(self): return isinstance(self.pBinkObject, VideoClip)
    def mEnable(self): set_behavior(self.pButtonSprite, self)
    def mDisable(self): remove_behavior(self.pButtonSprite, self)
    def mLoadList(self, lst): lst.append(self)

    def mLoad(self):
        if self.pRepeatable or not self.pPlayed:
            if not self.pBinkObject and self.binkLoaded():
                self.pBinkObject = VideoClip(R(), self.pFilePath, self.pLoc)
        load_mem(self.pBackMember)

    def mUnload(self):
        if isinstance(self.pBinkObject, VideoClip):
            self.pBinkObject.stop()
        self.pBinkObject = 0

    def mShow(self):
        if self.pPlayed and self.pBackMember and not self.pRepeatable:
            s = S(self.pBackSprite)
            s.member, s.ink = self.pBackMember, 8
        elif self.pButtonMember:
            S(self.pButtonSprite).member = self.pButtonMember

    def mHide(self):
        blank(self.pButtonSprite)
        blank(self.pBackSprite)

    def mouseDown(self):
        if self.pParent:
            self.pParent.mButtonActivated(self)

    def _finish(self):
        M.removeUpdateList(self)
        if self.pParent:
            self.pParent.mPlayDone(self)

    def _show_back(self):
        if self.pBackMember:
            s = S(self.pBackSprite)
            s.member, s.ink = self.pBackMember, 8

    def mPlay(self):
        if not self.binkLoaded():
            self.pPlayed = 1
            self.pFlushCount = 10
            M.addUpdateList(self)
            return
        self.pPlayed += 1
        if isinstance(self.pBinkObject, VideoClip):
            self.pBinkObject.start()
            M.addUpdateList(self)
        else:
            S(self.pBackSprite).member = self.pBackMember
            if self.pParent:
                self.pParent.mPlayDone(self)

    def mUpdate(self):
        if not self.binkLoaded():
            self.pFlushCount -= 1
            if not self.pFlushCount:
                self._show_back()
                self._finish()
            return
        clip = self.pBinkObject
        if not isinstance(clip, VideoClip):
            M.removeUpdateList(self)
            return
        if clip.update():
            clip.stop()
            if not self.pRepeatable:
                self.pBinkObject = 0
            self._show_back()
            self._finish()

    def mStop(self):
        if isinstance(self.pBinkObject, VideoClip):
            self.pBinkObject.stop()
            self.pBinkObject = 0
            S(self.pBackSprite).member = self.pBackMember
            self._finish()
