"""Hand-ported parent scripts, part 2: sounds, animation, buttons, text fields, dialogue,
save/load, and the first two screens (BUMP, SIGNIN).

Each class is a direct translation of the Lingo parent script of the same name; method names and
property names are unchanged (see ../README.md for the script-number table).
"""
import json
import os

from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, Point, Rect, decode, set_properties, pop_one, get_def, get_range_list, random_


def R():
    return runtime.rt


def S(chan):
    return runtime.rt.sprites[chan]


def load_mem(x):
    """loadMem: warm the image cache for a member number / list of them."""
    if isinstance(x, (list, tuple)):
        for i in x:
            load_mem(i)
    elif isinstance(x, int) and x:
        R().image(x)


def unload_mem(x):
    if isinstance(x, LObject):
        x.mUnload()


def load_object(x):
    if isinstance(x, (list, tuple)):
        for i in x:
            load_object(i)
    elif isinstance(x, LObject):
        x.mLoad()


def unload_object(x):
    if isinstance(x, (list, tuple)):
        for i in x:
            unload_object(i)
    elif isinstance(x, LObject):
        x.mUnload()


def call_all(objs, name, *a):
    """call(#mFoo, list, args)"""
    for o in list(objs or []):
        if isinstance(o, LObject):
            fn = getattr(o, name, None)      # Lingo's call(#mFoo, list) silently skips objects without that handler
            if fn is not None:
                fn(*a)


def remove_spaces(t):
    return t.strip(' ')


def is_enabled(chan, obj):
    return obj in S(chan).behaviors


def set_behavior(chan, obj):
    S(chan).behaviors = [obj]


def remove_behavior(chan, obj=None):
    S(chan).behaviors = []


def blank(chan):
    R().blank_sprite(chan)


def _done(parent, obj):
    if parent:
        parent.mPlayDone(obj)


# ============================================================================================
# sounds
# ============================================================================================

@lingo_script('INTERNALSOUND')                           # ParentScript 108
class InternalSound(LObject):
    def __init__(self, name=None):
        self.pName = name
        self.pSound = 0
        self.pInterrupt = 0
        self.pParent = 0
        self.pChannel = 1
        self.pPlaying = 0
        self.pEventTag = None

    def mDestroy(self): pass
    def mSetParent(self, o): self.pParent = o
    def mLoad(self): load_mem(self.pSound)
    def mLoadList(self, lst): lst.append(self.pSound)
    def mUnload(self): pass
    def mGetType(self): return Sym('INTERNALSOUND')
    def mGetName(self): return self.pName
    def mIsInterruptable(self): return self.pInterrupt
    def mSetEventTag(self, t): self.pEventTag = t
    def mGetEventTag(self): return self.pEventTag

    def mPlay(self):
        self.pPlaying = 1
        R().sound.puppet(self.pChannel, self.pSound)
        M.addUpdateList(self)

    def mKill(self, stopsound=None):
        self.pPlaying = 0
        if stopsound:
            R().sound.puppet(self.pChannel, 0)
        M.removeUpdateList(self)

    def mStop(self):
        self.pPlaying = 0
        R().sound.puppet(self.pChannel, 0)
        M.removeUpdateList(self)
        _done(self.pParent, self)

    def mUpdate(self):
        if not R().sound.busy(self.pChannel):
            self.pPlaying = 0
            M.removeUpdateList(self)
            _done(self.pParent, self)

    def mRecycle(self):
        if self.pPlaying:
            self.pPlaying = 0
            R().sound.puppet(self.pChannel, 0)
        self.pSound = 0
        self.pParent = 0
        M.removeUpdateList(self)


@lingo_script('EXTERNALSOUND')                           # ParentScript 109
class ExternalSound(LObject):
    def __init__(self, name=None, directory=''):
        self.pName = name
        self.pSound = 0
        self.pInterrupt = 0
        self.pParent = 0
        self.pChannel = 1
        self.pPlayCount = 0
        self.pDirectory = directory
        self.pPlaying = 0
        self.pEventTag = None

    def mDestroy(self): pass
    def mSetParent(self, o): self.pParent = o
    def mLoad(self): pass
    def mLoadList(self, lst): pass
    def mUnload(self): pass
    def mGetType(self): return Sym('EXTERNALSOUND')
    def mGetName(self): return self.pName
    def mSetSoundFile(self, s): self.pSound = s
    def mIsInterruptable(self): return self.pInterrupt
    def mSetEventTag(self, t): self.pEventTag = t
    def mGetEventTag(self): return self.pEventTag

    def mPlay(self):
        self.pPlaying = 1
        R().sound.play_file(self.pChannel, self.pSound)
        M.addUpdateList(self)

    def mKill(self):
        self.pPlaying = 0
        R().sound.puppet(self.pChannel, 0)
        M.removeUpdateList(self)

    def mStop(self):
        self.pPlaying = 0
        R().sound.puppet(self.pChannel, 0)
        M.removeUpdateList(self)
        _done(self.pParent, self)

    def mUpdate(self):
        if not R().sound.busy(self.pChannel):
            self.pPlaying = 0
            M.removeUpdateList(self)
            _done(self.pParent, self)

    def mRecycle(self):
        if self.pPlaying:
            R().sound.puppet(self.pChannel, 0)
            self.pPlaying = 0
        self.pSound = 0
        self.pParent = 0
        M.removeUpdateList(self)


# ============================================================================================
# animation
# ============================================================================================

@lingo_script('ANIM_LIN')                                # Fantasy ParentScript 51
class AnimLin(LObject):
    """Fantasy ANIM_LIN, one-to-one from ParentScript 51. pSpeed is data in 1/100 s and Lingo does
    `pSpeed = pSpeed * 10` (milliseconds per frame); the Spooky class divided 1000 by it. Unlike Spooky,
    mPlay does not reset pStep (mShow does), there is no pWaitForSound, and pNextUpdate replaces pLastUpdate."""

    def __init__(self):
        self.pName = None
        self.pType = None
        self.pAnimSound = 0
        self.pAnimList = []
        self.pStep = 1
        self.pInk = 0
        self.pLoc = Point(0, 0)
        self.pSprite = 0
        self.pMember = 0
        self.pParent = 0
        self.pNextUpdate = 0
        self.pSpeed = 100
        self.pPlayed = 0
        self.pSavedList = []
        self.pEventTag = None

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pStep = 1
        self.pNextUpdate = 0
        self.pSprite = pop_one(alloc)
        self.pSpeed = self.pSpeed * 10
        self.pPlayed = 0
        self.pSavedList = [Sym('pPlayed')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self): pass
    def mLoad(self): load_mem(self.pMember); load_mem(self.pAnimSound); load_mem(self.pAnimList)
    def mUnload(self): pass                              # unloadMem of members: nothing to do in the port
    mUnLoad = mUnload
    def mGetType(self): return Sym('ANIM_LIN')
    def mGetName(self): return self.pName
    def mSetParent(self, o): self.pParent = o
    def mSetEventTag(self, t): self.pEventTag = t        # not in Fantasy 51; kept for callers shared with other classes
    def mGetEventTag(self): return self.pEventTag
    def mKill(self): self.mStop()

    def mLoadList(self, lst):
        lst.append(self.pMember)
        lst.append(self.pAnimSound)
        lst.extend(self.pAnimList)                       # appendList

    def mPlay(self):
        S(self.pSprite).ink = self.pInk
        self.pPlayed += 1
        R().sound.puppet(1, self.pAnimSound)
        daFrame = min(self.pStep, len(self.pAnimList))
        S(self.pSprite).member = self.pAnimList[daFrame - 1]
        self.pNextUpdate = R().milliseconds() + self.pSpeed
        M.addUpdateList(self)

    def mStop(self):
        M.removeUpdateList(self)

    def mUpdate(self):
        if R().milliseconds() > self.pNextUpdate:
            self.pStep += 1
            if self.pStep <= len(self.pAnimList):
                daIndex = min(self.pStep, len(self.pAnimList))
                S(self.pSprite).member = self.pAnimList[daIndex - 1]
                self.pNextUpdate = R().milliseconds() + self.pSpeed
            else:
                self.mStop()
                _done(self.pParent, self)

    def mShow(self):
        s = S(self.pSprite)
        s.ink, s.loc, s.member = self.pInk, self.pLoc, self.pMember
        self.pStep = 1

    def mHide(self): blank(self.pSprite)

    def mSetAnimMemberIndex(self, member):
        if member in self.pAnimList:
            self.pStep = self.pAnimList.index(member) + 1
            S(self.pSprite).member = self.pAnimList[self.pStep - 1]


@lingo_script('ANIMPL_BUMP')                             # ParentScript 101
class AnimPlBump(LObject):
    def __init__(self):
        self.pParent = 0
        self.pInterruptable = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pAnimPos = 1
        self.pLastUpdate = 0
        self.pBGSprite = pop_one(alloc)
        self.pSprite = pop_one(alloc)
        self.pSavedList = []
        return self

    def mDestroy(self): pass
    def mSetParent(self, o): self.pParent = o
    def mSetEventTag(self, t): self.pEventTag = t
    def mGetEventTag(self): return self.pEventTag
    def mGetType(self): return Sym('ANIMPL_BUMP')
    def mLoad(self): load_mem(self.pAnimSound); load_mem(self.pAnimList)
    def mUnload(self): pass

    def mLoadList(self, lst):
        lst.append(self.pAnimSound)
        lst.append(self.pAnimList)

    def mPlay(self):
        S(self.pSprite).ink = self.pInk
        S(self.pSprite).loc = self.pLoc
        S(self.pBGSprite).member = self.pBGMember
        R().sound.puppet(1, self.pAnimSound)
        S(self.pSprite).member = self.pAnimList[self.pAnimPos - 1]
        self.pLastUpdate = R().milliseconds()
        M.addUpdateList(self)

    def mStop(self):
        M.removeUpdateList(self)
        R().sound.puppet(1, M.gFlushSound)
        self.mHide()
        _done(self.pParent, self)

    def mUpdate(self):
        if not R().sound.busy(1):
            self.mStop()
            return
        now = R().milliseconds()
        if now - self.pLastUpdate >= self.pSpeed:
            self.pLastUpdate = now
            if self.pAnimPos < len(self.pAnimList):
                self.pAnimPos += 1
                S(self.pSprite).member = self.pAnimList[self.pAnimPos - 1]

    def mShow(self):
        s = S(self.pSprite)
        s.ink, s.loc, s.member = self.pInk, self.pLoc, self.pMember
        S(self.pBGSprite).member = self.pBGMember

    def mHide(self):
        blank(self.pSprite)
        blank(self.pBGSprite)


@lingo_script('BINK')                                    # ParentScript 107
class Bink(LObject):
    """Bink video xtra is not available: this takes the original's own `not binkLoaded()` path
    (wait ~10 updates, then show the still `pBackMember`). Real video playback is a TODO."""

    def __init__(self):
        self.pParent = 0
        self.pPlayed = 0
        self.pBinkObject = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pButtonSprite = pop_one(alloc)
        self.pBackSprite = pop_one(alloc)
        self.pInterruptable = 1
        self.pPlayed = 0
        self.pFlushCount = 0
        self.pSavedList = [Sym('pPlayed')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self): pass
    def mLoad(self): load_mem(self.pBackMember)
    def mLoadList(self, lst): lst.append(self)
    def mUnload(self): pass
    def mSetParent(self, o): self.pParent = o
    def mGetType(self): return Sym('Bink')
    def mGetName(self): return self.pName
    def mSetEventTag(self, t): self.pEventTag = t
    def mGetEventTag(self): return self.pEventTag
    def mBinkLoaded(self): return 0
    def mEnable(self): set_behavior(self.pButtonSprite, self)
    def mDisable(self): remove_behavior(self.pButtonSprite, self)
    def mStop(self): pass

    def mShow(self):
        if self.pPlayed and self.pBackMember and not self.pRepeatable:
            S(self.pBackSprite).member = self.pBackMember
            S(self.pBackSprite).ink = 8
        elif self.pButtonMember:
            S(self.pButtonSprite).member = self.pButtonMember

    def mHide(self):
        blank(self.pButtonSprite)
        blank(self.pBackSprite)

    def mouseDown(self):
        if self.pParent:
            self.pParent.mButtonActivated(self)

    def mPlay(self):
        self.pPlayed = 1
        self.pFlushCount = 10
        M.addUpdateList(self)

    def mUpdate(self):
        self.pFlushCount -= 1
        if not self.pFlushCount:
            if self.pBackMember:
                S(self.pBackSprite).member = self.pBackMember
                S(self.pBackSprite).ink = 8
            M.removeUpdateList(self)
            _done(self.pParent, self)


# ============================================================================================
# buttons
# ============================================================================================

@lingo_script('BUTT_SIMPLE')                             # ParentScript 72
class ButtSimple(LObject):
    def __init__(self):
        self.pParent = 0
        self.pInk = 0
        self.pSprite = 0
        self.pMember = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pSprite = pop_one(alloc)
        self.pEnabled = 1
        return self

    def mDestroy(self): pass
    def mGetType(self): return Sym('BUTT_SIMPLE')
    def mGetName(self): return self.pName
    def mSetParent(self, o): self.pParent = o
    def mSetMember(self, m): self.pMember = m
    def mLoad(self): load_mem(self.pMember)
    def mLoadList(self, lst): lst.append(self.pMember)
    def mUnload(self): pass

    def mouseDown(self):
        if self.pParent:
            self.pParent.mButtonActivated(self)

    def mDisable(self):
        self.pEnabled = 0
        remove_behavior(self.pSprite, self)

    def mEnable(self):
        self.pEnabled = 1
        set_behavior(self.pSprite, self)

    def mShow(self):
        s = S(self.pSprite)
        s.ink, s.loc, s.member = self.pInk, self.pLoc, self.pMember
        set_behavior(self.pSprite, self)

    def mHide(self): blank(self.pSprite)


@lingo_script('BUTT_ROLL_DOWN')                          # ParentScript 71
class ButtRollDown(LObject):
    def __init__(self):
        self.pParent = 0
        self.pDownFlag = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pNeutMember = self.pMember
        self.pSprite = pop_one(alloc)
        self.pLoc = get_def(self.pLoc, M.getRegPoint())
        self.pMember = get_def(self.pMember, 0)
        self.pOrigMember = self.pMember
        self.pInk = 8
        self.pSavedList = []
        self.pDownFlag = 0
        return self

    def mDestroy(self): pass
    def mGetType(self): return Sym('BUTT_ROLL_DOWN')
    def mGetName(self): return self.pName
    def mSetParent(self, o): self.pParent = o
    def mGetParent(self): return self.pParent
    def mSetBehavior(self): set_behavior(self.pSprite, self)

    def mShow(self):
        s = S(self.pSprite)
        s.ink, s.loc, s.member = self.pInk, self.pLoc, self.pMember
        self.mSetBehavior()

    def mHide(self):
        self.pDownFlag = 0
        blank(self.pSprite)

    def mLoad(self):
        for m in (self.pMember, self.pDisMember, self.pRollMember, self.pDownMember):
            load_mem(m)

    def mLoadList(self, lst):
        for m in (self.pMember, self.pDisMember, self.pRollMember, self.pDownMember,
                  self.pUpSound, self.pDownSound, self.pRollSound):
            lst.append(m)

    def mUnload(self): pass

    def mouseDown(self):
        S(self.pSprite).member = self.pDownMember
        R().sound.puppet(1, self.pDownSound)
        self.pDownFlag = 1
        if self.pParent:
            self.pParent.mButtonActivated(self)

    def mouseUp(self):
        if self.pDownFlag:
            R().sound.puppet(1, self.pUpSound)
            S(self.pSprite).member = self.pRollMember
            self.pDownFlag = 0
            if self.pParent:
                self.pParent.mButtonDeActivated(self)

    def mouseUpOutSide(self): self.pDownFlag = 0

    def mouseEnter(self):
        if self.pDownFlag:
            S(self.pSprite).member = self.pDownMember
            if self.pParent:
                self.pParent.mButtonActivated(self)
        else:
            if not (M.gUserHasLamePC and R().sound.busy(2)):
                R().sound.puppet(1, self.pRollSound)
            S(self.pSprite).member = self.pRollMember

    def mouseLeave(self):
        S(self.pSprite).member = self.pNeutMember
        if self.pDownFlag and self.pParent:
            self.pParent.mButtonDeActivated(self)

    def mEnable(self):
        if not is_enabled(self.pSprite, self):
            S(self.pSprite).member = self.pNeutMember
            set_behavior(self.pSprite, self)

    def mDisable(self, dontUseDisMemberFlag=None):
        if is_enabled(self.pSprite, self):
            if dontUseDisMemberFlag is None and self.pDisMember:
                S(self.pSprite).member = self.pDisMember
            remove_behavior(self.pSprite, self)
            self.pDownFlag = 0
            if self.pParent:
                self.pParent.mButtonDeActivated(self)

    def mMove(self, offset):
        s = S(self.pSprite)
        s.loc = s.loc + offset


@lingo_script('BUTT_ROLL_UP')                            # ParentScript 73
class ButtRollUp(LObject):
    def __init__(self):
        self.pWaitCounter = 0
        self.pParent = 0
        self.pDownFlag = 0
        self.pLastSoundPlayed = None
        self._pending = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        if self.pDetectMember:
            self.pDetectSprite = pop_one(alloc)
            self.pSprite = pop_one(alloc)
        else:
            self.pDetectMember = self.pNeutMember
            self.pSprite = pop_one(alloc)
            self.pDetectSprite = self.pSprite
        self.pLoc = get_def(self.pLoc, M.getRegPoint())
        self.pSkipRolloverSoundFlag = 0
        self.pDownFlag = 0
        self.pSavedList = []
        return self

    def mDestroy(self): pass
    def mGetType(self): return Sym('BUTT_ROLL_UP')
    def mGetName(self): return self.pName
    def mGetDestination(self): return self.pDestination
    def mSetParent(self, o): self.pParent = o
    def mGetParent(self): return self.pParent
    def mSetBehavior(self): set_behavior(self.pDetectSprite, self)

    def mShow(self):
        rt = R()
        self.pSkipRolloverSoundFlag = 0
        if self.pDetectSprite != self.pSprite:
            d = S(self.pDetectSprite)
            d.member, d.ink, d.blend = self.pDetectMember, 32, 0
        s = S(self.pSprite)
        s.ink, s.loc, s.member = self.pInk, self.pLoc, self.pNeutMember
        if rt.will_roll_over(self.pDetectMember, self.pLoc, rt.mouse):
            self.pSkipRolloverSoundFlag = 1
        set_behavior(self.pDetectSprite, self)

    def mHide(self):
        blank(self.pDetectSprite)
        blank(self.pSprite)
        self.pDownFlag = 0
        self.pLastSoundPlayed = 0

    def mLoad(self):
        for m in (self.pDetectMember, self.pNeutMember, self.pDisMember, self.pRollMember, self.pDownMember):
            load_mem(m)

    def mLoadList(self, lst):
        for m in (self.pDetectMember, self.pNeutMember, self.pDisMember, self.pRollMember,
                  self.pDownMember, self.pUpSound, self.pDownSound, self.pRollSound):
            lst.append(m)

    def mUnload(self): pass

    def mouseDown(self):
        if not self.pDownFlag:
            S(self.pSprite).member = self.pDownMember
            self.pLastSoundPlayed = self.pDownSound
            R().sound.puppet(1, self.pDownSound)
            self.pDownFlag = 1

    def mouseUp(self):
        if not self.pDownFlag:
            return
        snd = R().sound
        S(self.pSprite).member = self.pRollMember
        self.pDownFlag = 0
        self.pWaitCounter = 0
        if self.pUpSound:
            if self.pWaitForSound:
                M.waitCursor()
            if self.pLastSoundPlayed == self.pDownSound and snd.busy(1):
                # original: `repeat while soundBusy(1)` (a blocking spin) -> wait via the update list
                self._pending = 1
                M.addUpdateList(self)
                return
            self._finish_up()
        elif self.pDownSound and snd.busy(1) and self.pWaitForSound:
            M.waitCursor()
            M.disableGame()
            M.addUpdateList(self)
        else:
            remove_behavior(self.pDetectSprite)
            M.disableGame()
            if self.pParent:
                self.pParent.mButtonActivated(self)

    def _finish_up(self):
        self.pLastSoundPlayed = self.pUpSound
        R().sound.puppet(1, self.pUpSound)
        M.disableGame()
        if self.pWaitForSound:
            M.addUpdateList(self)
        elif self.pParent:
            self.pParent.mButtonActivated(self)

    def mUpdate(self):
        if self._pending:
            if not R().sound.busy(1):
                self._pending = 0
                M.removeUpdateList(self)
                self._finish_up()
            return
        self.pWaitCounter += 1
        busy = R().sound.busy(1)
        ready = ((not busy) and self.pWaitForSound) or (self.pWaitCounter == 10 and not self.pWaitForSound)
        if ready:
            self.pWaitCounter = 0
            M.removeUpdateList(self)
            if self.pParent:
                self.pParent.mButtonActivated(self)

    def mouseUpOutSide(self): self.pDownFlag = 0

    def mouseEnter(self):
        lame = M.gUserHasLamePC and R().sound.busy(2)
        if not (lame or self.pSkipRolloverSoundFlag or not self.pRollSound):
            self.pLastSoundPlayed = self.pRollSound
            R().sound.puppet(1, self.pRollSound)
        self.pSkipRolloverSoundFlag = 0
        S(self.pSprite).member = self.pDownMember if self.pDownFlag else self.pRollMember

    def mouseLeave(self):
        S(self.pSprite).member = self.pNeutMember

    def mEnable(self):
        rt = R()
        if S(self.pSprite).member != M.gBlank and not is_enabled(self.pDetectSprite, self):
            if rt.will_roll_over(self.pNeutMember, self.pLoc, rt.mouse):
                self.pSkipRolloverSoundFlag = 1
            S(self.pSprite).member = self.pNeutMember
            set_behavior(self.pDetectSprite, self)

    def mDisable(self, changeAppearanceFlag=None):
        if is_enabled(self.pDetectSprite, self):
            if self.pDisMember and changeAppearanceFlag:
                S(self.pSprite).member = self.pDisMember
            remove_behavior(self.pDetectSprite, self)
            self.pDownFlag = 0

    def mMove(self, offset):
        for c in (self.pSprite, self.pDetectSprite):
            S(c).loc = S(c).loc + offset


# ============================================================================================
# text-entry widgets
# ============================================================================================

@lingo_script('BLINK')                                   # ParentScript 182
class Blink(LObject):
    def __init__(self):
        self.pParent = 0
        self.pLastUpdate = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pLastUpdate = 0
        self.pHideMem = M.getBlank()
        self.pSprite = pop_one(alloc)
        self.pLoc = Point(317, 450)
        self.pMember = get_def(self.pMember, 0)
        self.pOrigMember = self.pMember
        self.pSavedList = []
        return self

    def mDestroy(self): pass
    def mLoad(self): load_mem(self.pMember)
    def mLoadList(self, lst): lst.append(self.pMember)
    def mUnload(self): pass
    def mSetParent(self, o): self.pParent = o
    def mSetBehavior(self): set_behavior(self.pSprite, self)

    def mShow(self):
        self.pLastUpdate = R().milliseconds()
        self.mShowSprite()
        self.mChangeMem(self.pHideMem)
        M.addUpdateList(self)

    def mHide(self):
        M.removeUpdateList(self)
        self.pLastUpdate = 0
        self.mHideSprite()

    def mUpdate(self):
        if not self.pLastUpdate:
            return
        now = R().milliseconds()
        if now - self.pLastUpdate >= self.pInterval:
            self.mToggle()
            self.pLastUpdate = now

    def mToggle(self):
        if self.mGetCurMem() == self.pHideMem:
            self.mResetMem()
        else:
            self.mChangeMem(self.pHideMem)

    def mShowSprite(self):
        s = S(self.pSprite)
        s.ink, s.loc, s.member = self.pInk, self.pLoc, self.pMember

    def mHideSprite(self): blank(self.pSprite)
    def mResetMem(self): S(self.pSprite).member = self.pMember
    def mChangeMem(self, m): S(self.pSprite).member = m
    def mGetCurMem(self): return S(self.pSprite).member
    def mChangeLoc(self, p): S(self.pSprite).loc = p
    def mOffScreen(self): self.mChangeLoc(M.getOffScreenLoc())


# The sign-in text fields (typed name + saved-player list) are centre-aligned inside a field that is
# SIGNIN_FIELD_W wide.  The list box and the name underline on the SI backdrop are both centred on stage
# x = SIGNIN_CENTER_X, so the fields are positioned from that centre instead of trusting the data's pLoc.
SIGNIN_FIELD_W = 295
SIGNIN_CENTER_X = 366


def _signin_field_loc(loc):
    return Point(SIGNIN_CENTER_X - SIGNIN_FIELD_W // 2, loc[1])


def _text_width(f, text):
    rt = R()
    if rt._pg:
        return rt.get_font(f.font, f.fontSize).size(text)[0]
    return 8 * len(text)


@lingo_script('FIELD_INPUT')                             # ParentScript 183
class FieldInput(LObject):
    def __init__(self):
        self.pParent = 0
        self.pInsertMode = 0
        self.pEmpty = 1
        self.pCursorVisible = 1
        self.pCursorShow = 0
        self.pEnabled = 1
        self.pNumbersAllowed = 0
        self.pMaxChars = 20

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pcursor = get_object(self.pcursor, alloc)
        self.pcursor.mSetParent(self)
        self.pUpperCaseList = get_range_list(65, 90)
        self.pLowerCaseList = get_range_list(97, 122)
        self.pNumberList = get_range_list(48, 57)
        self.pSpaceChar = 32
        self.pInsertMode = 0
        self.pCursorVisible = 1
        self.pEmpty = 1
        self.pSprite = pop_one(alloc)
        self.pLoc = _signin_field_loc(get_def(self.pLoc, M.getRegPoint()))
        self.pLocH = self.pLoc[0]
        self.pMember = get_def(self.pMember, 0)
        self.pwidth = SIGNIN_FIELD_W
        self.pEnabled = 1
        self.pSavedList = []
        return self

    def mDestroy(self): pass
    def mSetParent(self, o): self.pParent = o
    def mDisable(self): self.pEnabled = 0
    def mEnable(self): self.pEnabled = 1
    def mIsEmpty(self): return self.pEmpty
    def mSetEmpty(self): self.pEmpty = 1
    def mSetFull(self): self.pEmpty = 0
    def mSetInsertMode(self): self.pInsertMode = 1
    def mSetCursorFlag(self): self.pCursorShow = 1
    def mUnload(self): pass

    def _f(self):
        return R().field(self.pMember)

    def mLoad(self):
        load_mem(self.pMember)
        self.pcursor.mLoad()

    def mLoadList(self, lst):
        lst.append(self.pFontMember)
        self.pcursor.mLoadList(lst)
        lst.append(self.pMember)
        lst.append(self.pFontColor)

    def mShow(self):
        s = S(self.pSprite)
        s.ink, s.loc, s.member = 36, self.pLoc, self.pMember
        set_behavior(self.pSprite, self)
        self.pcursor.mShow()
        self.mSetCursor()

    def mHide(self):
        blank(self.pSprite)
        self.pcursor.mHide()

    def mInitField(self):
        f = self._f()
        f.text = ' '
        f.font, f.fontSize = self.pFont, self.pFontSize
        f.scrollTop = 0
        f.alignment = 'center'
        f.width = self.pwidth

    def mUpdate(self):
        if self.pCursorVisible:
            self.pcursor.mUpdate()

    # -- text ---------------------------------------------------------------------------------
    def mGetText(self):
        return '' if self.pEmpty else remove_spaces(self._f().text)

    def mGetCharCount(self):
        return 0 if self.pEmpty else len(self._f().text)

    def mGetLastChar(self):
        return '' if self.pEmpty else self._f().text[-1:]

    def mSetText(self, t):
        self._f().text = t
        self.pEmpty = 0
        self.mSetCursor()

    def mErase(self):
        self._f().text = ' '
        self.pEmpty = 1

    def mAddCharField(self, ch):
        f = self._f()
        f.text = ch if self.pEmpty else f.text + ch

    def mAddChar(self, ch):
        if self.pInsertMode:
            self.mErase()
            self.mAddCharField(ch)
            self.pInsertMode = 0
        else:
            self.mAddCharField(ch)
        self.pEmpty = 0
        self.mSetCursor()

    def mDeleteLast(self):
        if not self.pEmpty:
            f = self._f()
            f.text = f.text[:-1]
            self.pEmpty = 0
            self.mSetCursor()

    # -- cursor -------------------------------------------------------------------------------
    def mSetCursor(self):
        if not isinstance(self.pcursor, LObject):
            return
        if self.mGetCharCount() < self.pMaxChars or self.pCursorShow:
            self.mPlaceCursor()
            self.pCursorVisible = 1
        else:
            self.mHideCursor()

    def mHideCursor(self):
        self.pcursor.mOffScreen()
        self.pCursorVisible = 0

    def mGetCursLoc(self):
        f = self._f()
        w = 0 if self.pEmpty else _text_width(f, f.text)
        if f.alignment == 'left':
            return Point(self.pLocH + w, self.pCursorLocV)
        return Point(self.pLocH + f.width // 2 + w // 2, self.pCursorLocV)

    def mPlaceCursor(self):
        self.pcursor.mChangeLoc(self.mGetCursLoc())

    def mCheckKey(self):
        rt = R()
        if rt.control_down or rt.option_down:
            return
        if rt.key_code in (51, 117):
            if self.mGetCharCount() == 1 or self.pInsertMode:
                self.mHideCursor()
                self.mErase()
                self.mSetCursor()
                self.pInsertMode = 0
            elif self.mGetCharCount() > 1:
                self.mHideCursor()
                self.mDeleteLast()
            return
        if self.mGetCharCount() < self.pMaxChars or self.pInsertMode:
            k = rt.key
            n = ord(k[0]) if k else 0
            if n in self.pUpperCaseList:
                self._typed(k)
            elif n == self.pSpaceChar and self.mGetText() != '' and self.mGetLastChar() != ' ' and not self.pInsertMode:
                self._typed(k)
            elif n in self.pNumberList and self.pNumbersAllowed:
                self._typed(k)
            elif n in self.pLowerCaseList:
                self._typed(chr(self.pUpperCaseList[self.pLowerCaseList.index(n)]))

    def _typed(self, ch):
        self.mHideCursor()
        self.mAddChar(ch)
        if self.pParent:
            self.pParent.mCharEntered(self)


@lingo_script('LISTFIELD_ARROWS')                        # ParentScript 184
class ListFieldArrows(LObject):
    HILITE = (150, 20, 20)

    def __init__(self):
        self.pParent = 0
        self.pCurLine = 0
        self.pCurScroll = 0
        self.pEmpty = 1
        self.pEnabled = 1

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pEmpty = 1
        self.pSprite = pop_one(alloc)
        self.pLoc = _signin_field_loc(get_def(self.pLoc, M.getRegPoint()))
        self.pMember = get_def(self.pMember, 0)
        self.pUpArrow = get_object(self.pUpArrow, alloc)
        self.pDownArrow = get_object(self.pDownArrow, alloc)
        self.pCurScroll = 0
        self.pUpArrow.mSetParent(self)
        self.pDownArrow.mSetParent(self)
        self.pEnabled = 1
        self.pSavedList = []
        self.pSpeed = 0
        self.pLastUpdate = R().milliseconds()
        self.pScrollDelta = 0
        self.pArrowsActive = 0
        return self

    def mDestroy(self): pass
    def mSetParent(self, o): self.pParent = o
    def mSetFull(self): self.pEmpty = 0
    def mSetBehavior(self): set_behavior(self.pSprite, self)
    def mUnload(self): pass
    def mGetCurLine(self): return self.pCurLine
    def _f(self): return R().field(self.pMember)

    def mLoad(self):
        load_mem(self.pMember)
        self.pUpArrow.mLoad()
        self.pDownArrow.mLoad()

    def mLoadList(self, lst):
        lst.append(self.pMember)
        self.pUpArrow.mLoadList(lst)
        self.pDownArrow.mLoadList(lst)

    def mShow(self):
        self.pCurScroll = 0
        f = self._f()
        self.pPageH = f.pageHeight
        f.lineSpace = self.pLineH
        self.pUpArrow.mShow()
        self.pDownArrow.mShow()
        s = S(self.pSprite)
        s.ink, s.loc, s.member = self.pInk, self.pLoc, self.pMember
        self.mSetBehavior()
        self.mSetArrows()
        self.pArrowsActive = 1

    def mHide(self):
        blank(self.pSprite)
        self.pUpArrow.mHide()
        self.pDownArrow.mHide()

    def mInitField(self):
        f = self._f()
        f.text = ' '
        f.font, f.fontSize = self.pFont, self.pFontSize
        f.scrollTop = 0
        f.lineColors = {}
        f.alignment = 'center'          # list sits centred under the "Pick the Player" title
        f.width = SIGNIN_FIELD_W

    # -- scrolling ----------------------------------------------------------------------------
    def mMaxScroll(self):
        lines = self.mGetLineCount() - 1
        cur_h = (lines - self.pCurScroll // self.pLineH) * self.pLineH
        return 0 if cur_h > self.pPageH else 1

    def mSetArrows(self):
        if self.mMaxScroll():
            self.pDownArrow.mDisable()
            self.mButtonDeActivated(self.pDownArrow)
        else:
            self.pDownArrow.mEnable()
        if self.pCurScroll > 0:
            self.pUpArrow.mEnable()
        else:
            self.pUpArrow.mDisable()
            self.mButtonDeActivated(self.pUpArrow)

    def mSetScroll(self, _=None):
        self._f().scrollTop = self.pCurScroll

    def mButtonActivated(self, butt):
        self.pScrollDelta = -4 if butt is self.pUpArrow else 4
        M.addUpdateList(self)

    def mButtonDeActivated(self, butt):
        self.pScrollDelta = 0
        M.removeUpdateList(self)

    def mUpdate(self):
        now = R().milliseconds()
        if now - self.pLastUpdate >= 50:
            self.pLastUpdate = now
            self.pCurScroll = max(0, self.pCurScroll + self.pScrollDelta)
            self.mSetScroll(self.pCurScroll)
            self.mSetArrows()

    # -- lines --------------------------------------------------------------------------------
    def _line_h(self):
        f = self._f()
        if f.lineSpace:
            return f.lineSpace
        rt = R()
        return rt.get_font(f.font, f.fontSize).get_linesize() if rt._pg else 16

    def mouseDown(self):
        if not self.pEnabled:
            return
        rt = R()
        f = self._f()
        line = int((rt.mouse[1] - self.pLoc[1] + f.scrollTop) // self._line_h()) + 1
        if self.mGetLineText(line) not in ('', ' '):
            self.mHiliteLine(line)
        if self.pParent:
            self.pParent.mListFieldClicked(self)

    def mGetCurLineText(self):
        return self._f().get_line(self.pCurLine) if self.pCurLine else ''

    def mGetLineText(self, n):
        return remove_spaces(self._f().get_line(n)) if n > 0 else ''

    def mHiliteLine(self, n):
        if n == self.pCurLine:
            return
        self.mUnHiliteLine()
        self.pCurLine = n
        f = self._f()
        f.lineColors[n] = self.HILITE
        f.lineColors.pop(n + 1, None)

    def mUnHiliteLine(self):
        if self.pCurLine:
            self._f().lineColors.pop(self.pCurLine, None)
            self.pCurLine = 0

    def mAddLine(self, text):
        f = self._f()
        n = self.mGetLineCount() + 1
        f.set_line(n, text)
        f.set_line(n + 1, ' ')
        self.mSetFull()

    def mDeleteLine(self):
        self.mUnHiliteLine()
        self._f().text = ' '

    def mGetLineCount(self):
        f = self._f()
        return sum(1 for i in range(1, f.line_count() + 1) if self.mGetLineText(i) not in ('', ' '))

    def mLoadFieldList(self, items):
        if items:
            f = self._f()
            f.lines = list(items) + [' ']
            f.lineColors = {}
            f.scrollTop = 0
            self.pCurScroll = 0
            self.mSetFull()

    def mGetText(self):
        return '' if self.pEmpty else self._f().text

    def mDisable(self):
        self.pEnabled = 0
        self.pUpArrow.mDisable(1)
        self.pDownArrow.mDisable(1)

    def mEnable(self):
        self.pEnabled = 1
        self.pUpArrow.mEnable()
        self.pDownArrow.mEnable()


@lingo_script('FILE_DIALOGUE')                           # ParentScript 186
class FileDialogue(LObject):
    def __init__(self):
        self.pParent = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pBackgroundObj = get_object_list(self.pBackgroundObj, alloc)
        self.pListField = get_object(self.pListField, alloc)
        self.pNameField = get_object(self.pNameField, alloc)
        self.pGoButt = get_object(self.pGoButt, alloc)
        self.pListField.mSetParent(self)
        self.pNameField.mSetParent(self)
        self.pGoButt.mSetParent(self)
        self.pSavedList = []
        return self

    def mDestroy(self): pass
    def mSetParent(self, o): self.pParent = o
    def mAnimate(self): self.pGoButt.mAnimate()
    def mUpdate(self): self.pNameField.mUpdate()
    def mGetNameText(self): return self.pNameField.mGetText()
    def mGetListText(self): return self.pListField.mGetText()
    def mGetLineCount(self): return self.pListField.mGetLineCount()
    def mDeleteFile(self): M.deleteGame(self.mGetNameText())
    def mSetFileList(self, lst): self.pListField.mLoadFieldList(lst)
    def mCheckActivity(self): self.pParent.mCheckActivity(self)

    def mShow(self):
        call_all(self.pBackgroundObj, 'mShow')
        self.pNameField.mShow()
        self.pListField.mShow()
        self.pGoButt.mShow()
        self.pGoButt.mDisable(1)

    def mHide(self):
        call_all(self.pBackgroundObj, 'mHide')
        self.pNameField.mHide()
        self.pListField.mHide()
        self.pGoButt.mHide()

    def mInitFields(self):
        self.pNameField.mInitField()
        self.pListField.mInitField()

    def mLoad(self):
        call_all(self.pBackgroundObj, 'mLoad')
        self.pListField.mLoad()
        self.pNameField.mLoad()
        self.pGoButt.mLoad()

    def mLoadList(self, lst):
        call_all(self.pBackgroundObj, 'mLoadList', lst)
        self.pListField.mLoadList(lst)
        self.pNameField.mLoadList(lst)
        self.pGoButt.mLoadList(lst)

    def mUnload(self):
        call_all(self.pBackgroundObj, 'mUnload')

    def mCheckKey(self):
        rt = R()
        if rt.control_down and rt.key in ('d', 'D', '\x04'):          # Ctrl+D deletes the selected player
            if self.mGetNameText() != '':
                self.pGoButt.mDisable(1)
                self.mDeleteFile()
                self.pListField.mDeleteLine()
                self.pNameField.mErase()
                self.pNameField.mSetCursor()
                self.mSetFileList(M.getSavedGamesList())
                self.pListField.mSetScroll(self.pListField.pCurScroll)
                self.pListField.mSetArrows()
        else:
            self.pNameField.mCheckKey()
            if self.pNameField.mGetText() == '':
                self.pGoButt.mDisable(1)

    def mListFieldClicked(self, _=None):
        cur = self.pListField.mGetCurLineText()
        if cur in ('', None, ' '):
            return
        self.pNameField.mSetText(cur)
        self.pNameField.mSetInsertMode()
        if self.mGetNameText() != '':
            self.pGoButt.mEnable()
        else:
            self.pGoButt.mDisable(1)

    def mCharEntered(self, _=None):
        if self.pListField.mGetCurLine():
            self.pListField.mUnHiliteLine()
        if self.pNameField.mIsEmpty():
            self.pGoButt.mDisable(1)
        else:
            self.pGoButt.mEnable()

    def mButtonActivated(self, butt):
        self.pParent.mButtonActivated(butt)

    def mButtonDeActivated(self, butt): pass

    def mDisable(self):
        self.pGoButt.mDisable()
        self.pListField.mDisable()
        self.pNameField.mDisable()

    def mEnable(self):
        self.pGoButt.mEnable()
        self.pListField.mEnable()
        self.pNameField.mEnable()


# ============================================================================================
# save / load  (original used the vList xtra; the port stores JSON in the same <player>\<NAME>.LST layout)
# ============================================================================================

def _enc(v):
    if isinstance(v, Sym):
        return {'$sym': str(v)}
    if isinstance(v, Rect):
        return {'$rect': list(v)}
    if isinstance(v, Point):
        return {'$point': list(v)}
    if isinstance(v, (list, tuple)):
        return [_enc(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _enc(x) for k, x in v.items()}
    return v


@lingo_script('SAVELOAD')                                # ParentScript 181
class SaveLoad(LObject):
    def __init__(self, fileDir='', theFile=None):
        self.pType = Sym('SAVELOAD')
        self.pObjectGlob = []
        self.pFileDir = fileDir
        self.pCurFile = ''
        if isinstance(theFile, str):
            self.mSetCurFile(theFile)
        self.pVersion = M.getVersion()

    def mDestroy(self): self.pObjectGlob = None
    def mGetCurFile(self): return self.pCurFile
    def mGetVersion(self): return self.pVersion
    def mGetSaveDir(self): return self.pFileDir

    def mSetCurFile(self, name):
        if '.lst' not in name.lower():
            name += '.LST'
        self.pCurFile = name

    def _path(self, name=None):
        return os.path.join(self.pFileDir or '', name or self.pCurFile)

    def mAddObjectGlob(self, obj):
        if obj not in self.pObjectGlob:
            self.pObjectGlob.append(obj)

    def mFileExists(self, name):
        return os.path.exists(self._path(name))

    def mDeleteFile(self, name=None):
        if name is not None:
            self.mSetCurFile(name)
        p = self._path()
        if os.path.exists(p):
            os.remove(p)

    @staticmethod
    def _key(o):
        """Identity of a saved object: class + pName. Restoring by position broke whenever the set of registered
        objects changed (a stale save put one object's values into another)."""
        return '%s:%s' % (type(o).__name__, getattr(o, 'pName', ''))

    def mSave(self):
        if self.pCurFile == '':
            return
        buf = [self.pVersion, 'keyed-v2']
        for o in self.pObjectGlob:
            pairs = []
            for prop in (o.pSavedList or []):
                v = getattr(o, str(prop), None)
                # objects can't be serialised; None = never set
                if v is None or isinstance(v, LObject):
                    continue
                pairs.append([str(prop), _enc(v)])
            buf.append([self._key(o), pairs])
        text = json.dumps(buf)
        if text == getattr(self, '_last_saved', None) and os.path.exists(self._path()):
            return                                   # nothing changed since the last save
        os.makedirs(self.pFileDir or '.', exist_ok=True)
        path = self._path()
        tmp = path + '.tmp'
        with open(tmp, 'w') as f:                    # write-then-rename: a crash can't leave a half file
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        self._last_saved = text

    def mRestore(self):
        p = self._path()
        if not os.path.exists(p):
            return
        try:
            buf = decode(json.load(open(p)))
        except Exception as e:
            print('[saveload] could not read', p, e)
            return
        if len(buf) < 2 or buf[1] != 'keyed-v2':
            print('[saveload] ignoring %s (old save format)' % p)
            return
        entries = {}
        for e in buf[2:]:
            if isinstance(e, (list, tuple)) and len(e) == 2:
                entries.setdefault(e[0], []).append(e[1])
        for o in self.pObjectGlob:
            pend = entries.get(self._key(o))
            if not pend:
                continue
            pairs = pend.pop(0)
            allowed = {str(x) for x in (o.pSavedList or [])}
            for pair in pairs:
                if isinstance(pair, (list, tuple)) and len(pair) == 2 and pair[0] in allowed:
                    setattr(o, pair[0], pair[1])


# ============================================================================================
# screens
# ============================================================================================

@lingo_script('SCREEN_BUMP')                             # Fantasy ParentScript 28
class ScreenBump(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pSlideList = []
        self.pSavedList = []
        self.pcursor = 0
        self.pCurBump = 0
        self.pFlushCount = 0
        self.pEnabled = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pcursor = 0
        self.pCurBump = 0
        self.pSlideList = get_object_list(self.pSlideList, alloc, 10)
        self.pSavedList = []
        call_all(self.pSlideList, 'mSetParent', self)
        self.pFlushCount = 0
        self.pEnabled = 0
        return self

    def mDestroy(self): pass
    def mInitPoolObjects(self): pass
    def mReleasePoolObjects(self): pass
    def mGetEnabled(self): return 1
    def mHide(self): pass
    def mDisable(self): pass
    def mEnable(self): pass
    def mApplicationActivated(self): pass
    def mApplicationDeactivated(self): pass
    def mGetName(self): return self.pName
    def mGetType(self): return Sym('SCREEN_BUMP')
    def mGetHelpState(self): return 0
    def mLoad(self): call_all(self.pSlideList, 'mLoad')
    def mLoadList(self, lst): call_all(self.pSlideList, 'mLoadList', lst)
    def mUnload(self): call_all(self.pSlideList, 'mUnload')

    def mShow(self):
        M.resetCursor()
        self.pFlushCount = 5
        M.addUpdateList(self)

    def mUpdate(self):
        self.pFlushCount -= 1
        if not self.pFlushCount:
            M.removeUpdateList(self)
            self.mNextBump()

    def mNextBump(self):
        if self.pcursor < len(self.pSlideList):
            self.pcursor += 1
            self.pCurBump = self.pSlideList[self.pcursor - 1]
            if self.pCurBump.pInterruptable:
                M.resetCursor()
                M.setInterruptMode(self.pCurBump)
            else:
                M.waitCursor()
                M.clearInterruptMode()
            self.pCurBump.mShow()
            self.pCurBump.mPlay()
        else:
            R().flush_input()                    # flushInputEvents()
            M.navigate(Sym('signin'))

    def mSetPalette(self): pass
    def mPlayTransSound(self): pass

    def mPlayDone(self, bump):
        M.clearInterruptMode()
        R().update_stage()                       # (set the stageColor to the stageColor; updateStage())
        R().sound.puppet(1, M.gFlushSound)
        self.pFlushCount = 5
        M.addUpdateList(self)
        R().flush_input()                        # flushInputEvents()

    def mCheckKey(self, keycode):
        if keycode == 49 and isinstance(self.pCurBump, LObject):
            self.pCurBump.mStop()


@lingo_script('SCREEN_SIGNIN')                           # Fantasy ParentScript 39
class ScreenSignin(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pDialogue = 0
        self.pTimer = 0
        self.pVOSound = 0
        self.pSavedList = []
        self.pIntroPlayed = 0
        self.pButtList = []
        self.pSpriteList = []
        self.pLoadList = []
        self.pScreenType = None
        self.pAnimObject = 0
        self.pIntroAudio = 0
        self.pRocketSound = 0
        self.pEnabled = 0
        self.pGoing = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pButtList = get_object_list(self.pButtList, alloc)
        self.pDialogue = get_object(self.pDialogue, alloc)
        self.pTimer = get_object(self.pTimer, [])
        self.pAnimObject = get_object(self.pAnimObject, alloc)
        self.pDialogue.mSetParent(self)
        self.pTimer.mSetParent(self)
        self.pAnimObject.mSetParent(self)
        self.pIntroAudio = 0
        self.pIntroPlayed = 0
        call_all(self.pButtList, 'mSetParent', self)
        self.pRocketSound = self.pAnimObject.pAnimSound
        self.pAnimObject.pAnimSound = 0
        self.pEnabled = 0
        self.pSavedList = []
        self.pGoing = 0
        return self

    def mDestroy(self): pass
    def mGetEnabled(self): return self.pEnabled
    def mGetName(self): return self.pName
    def mGetType(self): return Sym('SCREEN_SIGNIN')
    def mGetHelpState(self): return 0
    def mApplicationActivated(self): pass
    def mApplicationDeactivated(self): pass
    def mUpdate(self): pass
    def mButtonDeActivated(self, butt): pass

    def mInitPoolObjects(self):
        self.pRocketSound = M.getSoundObject(1, self.pRocketSound, self)
        self.pIntroAudio = M.getExSoundObject(2, "SI_NEW.AIF", self)

    def mReleasePoolObjects(self):
        self.pRocketSound = M.recycleSoundObject(self.pRocketSound)
        self.pIntroAudio = M.recycleSoundObject(self.pIntroAudio)

    def mShow(self):
        self.pDialogue.mInitFields()
        self.pDialogue.mSetFileList(M.getSavedGamesList())
        call_all(self.pButtList, 'mShow')
        self.pDialogue.mShow()
        if self.pDialogue.mGetListText() != '':
            self.pIntroAudio.pSound = "SI_WELCOME.AIF"
        M.setInterruptMode(self.pIntroAudio)
        self.pIntroAudio.mPlay()
        M.resetCursor()
        R().update_stage()
        self.pEnabled = 1

    def mDisable(self):
        self.pEnabled = 0
        call_all(self.pButtList, 'mDisable')
        self.pDialogue.mDisable()

    def mEnable(self):
        self.pEnabled = 1
        call_all(self.pButtList, 'mEnable')
        self.pDialogue.mEnable()

    def mHide(self):
        self.pIntroAudio.mKill()
        call_all(self.pButtList, 'mHide')
        self.pDialogue.mHide()
        self.pTimer.mStop()
        M.removeUpdateList(self.pTimer)
        self.pAnimObject.mHide()
        self.pGoing = 0
        self.pEnabled = 0

    def mLoad(self):
        self.pDialogue.mLoad()
        call_all(self.pButtList, 'mLoad')

    def mLoadList(self, lst):
        lst.append(self.pRocketSound)
        self.pAnimObject.mLoadList(lst)
        self.pDialogue.mLoadList(lst)
        call_all(self.pButtList, 'mLoadList', lst)

    def mUnload(self):
        unload_mem(self.pRocketSound)
        self.pAnimObject.mUnload()
        self.pDialogue.mUnload()
        call_all(self.pButtList, 'mUnload')

    def mSimpleButtClicked(self): pass
    def mPlayTransSound(self): pass

    def mCheckDialogue(self):
        self.mCheckKey(None)

    def mCheckKey(self, keycode):
        if self.pEnabled:
            M.QuitKeyCheck(keycode, 0)
            if R().key in ('\r', chr(3)):
                if self.pDialogue.mGetNameText() not in ('', ' '):
                    self.mAnimGoButt()
            else:
                self.pDialogue.mCheckKey()

    def mCheckActivity(self, _=None):
        M.setInterruptMode(self.pIntroAudio)
        self.pIntroAudio.mPlay()
        self.pTimer.mReset()

    def mButtonActivated(self, butt):
        if butt.pDestination == Sym('MAIN'):
            self.mAnimGoButt()

    def mAnimGoButt(self):
        self.mDisable()
        self.pIntroAudio.mKill()
        self.pDialogue.pGoButt.mHide()
        self.pAnimObject.mShow()
        self.pAnimObject.mPlay()
        self.pRocketSound.mPlay()
        M.waitCursor()

    def mFileCommitted(self):
        M.setPlayer(self.pDialogue.mGetNameText())
        M.navigate(Sym('MAIN'))

    def mPlayDone(self, obj):
        if obj is self.pAnimObject:
            if not M.isUpdating(self.pRocketSound):
                self.mFileCommitted()
        elif obj is self.pRocketSound:
            if not M.isUpdating(self.pAnimObject):
                self.mFileCommitted()
        elif obj is self.pIntroAudio:
            self.pTimer.mPlay()
        elif obj is self.pTimer:
            self.mCheckActivity()
