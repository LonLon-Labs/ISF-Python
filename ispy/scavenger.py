"""Hand-ported Fantasy parent scripts, part 1: scavenger hunt, reminders, dynamic states, drag-and-drop.

Translated one-to-one from the Fantasy .ls files (method / property names unchanged so each class can be diffed
against its script).  Imported from INIT_MAIN (movie.py) so the classes register.

    ParentScript 107  ANIM_SLIDE_OBJECT          slide of a sprite to a point; the *parent* moves it (mSetLoc)
    ParentScript 110  DYNAMIC_STATE              a sprite that shows a random member of a list (idle "state")
    ParentScript  66  DRAG_N_DROP                drag a piece, drop it into pDropRect or slide it back
    ParentScript  72  SCAVENGER_HUNT             one clue of the hunt (clue text + token animation)
    ParentScript  73  SH_DADDY                   the hunt manager (list of SCAVENGER_HUNT, level 2 only)
    ParentScript 102  SH_DADDY_ANIM              SH_DADDY (ancestor) that plays an intro / outro animation
    ParentScript  78  REMINDER_AUDIO             idle-timer voice-over reminders
    ParentScript 111, 113-117, 120, 121, 123     the REMINDER_* condition objects REMINDER_AUDIO polls

Port notes:
  * `call(#mFoo, list, me)` ignores extra arguments in Lingo; here they are simply not passed.
  * `mUnLoad` and `mUnload` are both defined (the Lingo spells it mUnLoad, the older Python callers say mUnload).
  * Spelling quirks of the originals (pClueTExtSprite elsewhere, pRiddleStripDissapearSound) are kept.
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, Point, Rect, set_properties, pop_one, pop_list, random_
from .ui import (R, S, load_mem, unload_mem, call_all, blank, set_behavior, remove_behavior, is_enabled,
                 _done)
from .screens2 import (_new, _alive, _get_pos, _inside, _get_dist, _integer, _loc_from_rect, _sprite_rect,
                       _rollover)


# ---- small helpers ----------------------------------------------------------------------------
def _eq(a, b):
    """Lingo `=` on symbols / strings: case-insensitive."""
    if a is None or b is None:
        return a is b
    if isinstance(a, (str, Sym)) and isinstance(b, (str, Sym)):
        return str(a).lower() == str(b).lower()
    return a == b


def _typ(o):
    if not _alive(o):
        return ''
    try:
        return str(o.mGetType()).upper().lstrip('#')
    except Exception:
        return ''


def _stringp(x):
    """Lingo stringp(): a string, not a symbol."""
    return isinstance(x, str) and not isinstance(x, Sym)


def _unload(o, *a):
    """mUnLoad(o, ...) -- either spelling."""
    if _alive(o):
        fn = getattr(o, 'mUnLoad', None) or getattr(o, 'mUnload', None)
        if fn:
            fn(*a)


def _call_if(o, name, *a):
    fn = getattr(o, name, None) if _alive(o) else None
    return fn(*a) if fn else None


def _wait_ms(ms):
    """repeat while daTicks > the milliSeconds / updateStage() / end repeat"""
    import time
    rt = R()
    end = rt.milliseconds() + ms
    while rt.milliseconds() < end:
        rt.pump()
        rt.update_stage()
        time.sleep(0.004)


# ============================================================================================
# ANIM_SLIDE_OBJECT  (ParentScript 107)
# ============================================================================================

@lingo_script('ANIM_SLIDE_OBJECT')
class AnimSlideObject(LObject):
    """Unlike ANIM_SLIDE this does not move the sprite itself: every step calls parent.mSetLoc(point).
    The original's throttle `pLastUpdate < (the milliSeconds + (1000 / pFPS))` is always true, so it steps on
    every update-list tick; that is kept."""

    def __init__(self, theSprite=0, theParent=0):
        self.pType = None
        self.pName = None
        self.pSprite = theSprite
        self.pReturnLoc = 0
        self.pPixelsPerSecond = 50
        self.pLastUpdate = 0
        self.pFPS = 10
        self.pHDist = 0
        self.pVDist = 0
        self.pStepHDist = 0
        self.pStepVDist = 0
        self.pCurrH = 0
        self.pCurrV = 0
        self.pStopLoc = 0
        self.pSrcH = 0
        self.pSrcV = 0
        self.pIncrement = 0
        self.pStepDist = 0
        self.pSinCounter = 0
        self.pDistanceTimer = 200
        self.pParent = theParent

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        return self

    def mDestroy(self): pass
    def mSetReturnLoc(self, theReturnLoc): self.pReturnLoc = theReturnLoc
    def mShow(self): pass
    def mHide(self): pass
    def mGetType(self): return Sym('ANIM_SLIDE_OBJECT')
    def mSetParent(self, theObject): self.pParent = theObject
    def mGetName(self): return self.pName

    def mPlay(self):
        loc = S(self.pSprite).loc
        ret = self.pReturnLoc
        self.pSrcH = loc[0]
        self.pSrcV = loc[1]
        self.pCurrH = loc[0]
        self.pCurrV = loc[1]
        self.pHDist = ret[0] - loc[0]
        self.pVDist = ret[1] - loc[1]
        daDist = _get_dist(Point(loc[0] - ret[0], loc[1] - ret[1])) * 1.0
        if daDist < 2:
            self.pParent.mSetLoc(ret)
            _done(self.pParent, self)
            return
        self.pIncrement = self.pDistanceTimer / daDist
        daTotalUpdates = daDist / self.pPixelsPerSecond * self.pFPS
        self.pStepHDist = self.pHDist / daTotalUpdates * 1.0
        self.pStepVDist = self.pVDist / daTotalUpdates * 1.0
        self.pStepDist = _get_dist(Point(self.pStepHDist, self.pStepVDist))
        self.pSinCounter = -90
        self.pLastUpdate = R().milliseconds()
        M.addUpdateList(self)

    def mStop(self):
        M.removeUpdateList(self)

    def mUpdate(self):
        import math
        if self.pLastUpdate < (R().milliseconds() + (1000 // self.pFPS)):
            if self.pSinCounter >= 90:
                self.pParent.mSetLoc(self.pReturnLoc)
                M.removeUpdateList(self)
                _done(self.pParent, self)
            else:
                radians = math.pi / 180 * self.pSinCounter
                ratio = 1 + math.sin(radians)
                ratio = ratio * 0.5
                self.pCurrH = self.pSrcH + (ratio * self.pHDist)
                self.pCurrV = self.pSrcV + (ratio * self.pVDist)
                self.pParent.mSetLoc(Point(_integer(self.pCurrH), _integer(self.pCurrV)))
                self.pLastUpdate = R().milliseconds()
            self.pSinCounter = self.pSinCounter + self.pIncrement


# ============================================================================================
# DYNAMIC_STATE  (ParentScript 110)
# ============================================================================================

@lingo_script('DYNAMIC_STATE')
class DynamicState(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pMemberList = []
        self.pMember = 0
        self.pSprite = 0
        self.pParent = 0
        self.pGrabList = []

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pGrabList = list(self.pMemberList)
        self.mGrabMember()
        return self

    def mDestroy(self): pass

    def mLoad(self):
        self.mGrabMember()
        load_mem(self.pMember)

    def mLoadList(self, theList):
        self.mGrabMember()
        theList.append(self.pMember)

    def mUnLoad(self): unload_mem(self.pMember)
    mUnload = mUnLoad

    def mShow(self):
        S(self.pSprite).member = self.pMember
        S(self.pSprite).ink = 8

    def mGrabMember(self):
        if self.pGrabList == []:
            self.pGrabList = list(self.pMemberList)
        thisOne = random_(len(self.pGrabList))
        self.pMember = self.pGrabList[thisOne - 1]
        del self.pGrabList[thisOne - 1]

    def mHide(self): blank(self.pSprite)
    def mGetType(self): return Sym('DYNAMIC_STATE')
    def mGetName(self): return self.pName
    def mSetParent(self, theObject): self.pParent = theObject


# ============================================================================================
# DRAG_N_DROP  (ParentScript 66)
# ============================================================================================

@lingo_script('DRAG_N_DROP')
class DragNDrop(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pSprite = 0
        self.pTokenName = None
        self.pDropRect = 0
        self.pMember = 0
        self.pDragMember = 0
        self.pDropped = 0
        self.pStateChangeAnim = 0
        self.pPickupSound = 0
        self.pDropSound = 0
        self.pDragObject = 0
        self.pDropObject = 0
        self.pDownTime = 0
        self.pSavedList = []
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pDragReturnLoc = 0
        self.pParent = 0
        self.pInk = 0
        self.pDragScriptNumber = 0
        self.pAnimSlideScriptNumber = 0
        self.pLoc = Point(320, 240)
        self.pStartLoc = Point(320, 240)

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pLoc = Point(320, 240)
        self.pStartLoc = Point(320, 240)
        self.pDropped = 0
        self.pDownTime = 0
        self.pStateChangeAnim = get_object(self.pStateChangeAnim, theSpriteAlloc)
        _call_if(self.pStateChangeAnim, 'mSetParent', self)
        self.pDragObject = _new(self.pDragScriptNumber, self.pDragMember, self)
        # The DRAG parent hard-codes ink 36 (every white pixel transparent), which punched holes in the white
        # highlights of gems / crystals while carried. Carry the piece with the same ink it has at rest
        # (pInk; 0 lets Runtime._guess_ink treat it as Matte, so only the outside white is keyed out).
        if _alive(self.pDragObject):
            self.pDragObject.pInk = self.pInk
        self.pDropObject = _new(self.pAnimSlideScriptNumber, self)
        self.pDragReturnLoc = 0
        self.pSavedList = [Sym('pDropped')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self): pass

    def mLoad(self):
        load_mem(self.pBackMember)
        if not self.pDropped:
            load_mem(self.pPickupSound)
            load_mem(self.pDropSound)
            load_mem(self.pDragMember)
            load_mem(self.pMember)
        if _alive(self.pStateChangeAnim):
            self.pStateChangeAnim.mLoad()

    def mLoadList(self, theList):
        theList.append(self.pBackMember)
        if not self.pDropped:
            theList.append(self.pPickupSound)
            theList.append(self.pDropSound)
            theList.append(self.pDragMember)
            theList.append(self.pMember)
        if _alive(self.pStateChangeAnim):
            self.pStateChangeAnim.mLoadList(theList)

    def mUnLoad(self):
        unload_mem(self.pPickupSound)
        unload_mem(self.pDropSound)
        unload_mem(self.pBackMember)
        unload_mem(self.pDragMember)
        unload_mem(self.pMember)
        _unload(self.pStateChangeAnim)
    mUnload = mUnLoad

    def mSetBackSprite(self, theSpriteAlloc): self.pBackSprite = pop_one(theSpriteAlloc)
    def mGetType(self): return Sym('DRAG_N_DROP')
    def mGetName(self): return self.pName
    def mSetParent(self, theObject): self.pParent = theObject

    def mShow(self):
        if not self.pDropped:
            S(self.pBackSprite).member = self.pBackMember
            S(self.pBackSprite).ink = self.pInk
            S(self.pSprite).member = self.pMember
            S(self.pSprite).ink = self.pInk
            _call_if(self.pStateChangeAnim, 'mDisable')
            set_behavior(self.pSprite, self)
        else:
            if _alive(self.pStateChangeAnim):
                self.pStateChangeAnim.mShow()

    def mHide(self):
        if _alive(self.pStateChangeAnim):
            self.pStateChangeAnim.mHide()
        blank(self.pBackSprite)
        blank(self.pSprite)
        remove_behavior(self.pSprite, self)

    def mEnable(self):
        if not is_enabled(self.pSprite, self) and not self.pDropped:
            if _rollover(self.pSprite):
                M.setOpenhandCursor()
            set_behavior(self.pSprite, self)

    def mDisable(self):
        if is_enabled(self.pSprite, self):
            remove_behavior(self.pSprite, self)

    def mouseEnter(self):
        M.setOpenhandCursor()

    def mouseLeave(self):
        if S(self.pSprite).member == self.pMember:
            M.resetCursor()

    def mouseDown(self):
        if _rollover(self.pSprite):
            daMouseLoc = R().mouse
            self.pDragReturnLoc = _loc_from_rect(_sprite_rect(self.pSprite))
            daDragOffset = self.pDragReturnLoc - daMouseLoc
            S(self.pBackSprite).member = 1
            S(self.pSprite).member = 1
            self.pDragObject.pDragOffset = daDragOffset
            self.pDragObject.mShow()
            R().sound.puppet(1, self.pPickupSound)
            self.pDragObject.mPlay()
            M.disableGame()

    def mPlay(self):
        if not self.pDropped:
            pass
        else:
            if _alive(self.pStateChangeAnim):
                self.pStateChangeAnim.mShow()
                self.pStateChangeAnim.mPlay()
            else:
                _done(self.pParent, self)

    def mouseUp(self):
        # Lingo: empty.  The port's mouse dispatcher can deliver the release to the pressed (now blank)
        # sprite instead of the drag sprite; hand it on so a drag always ends (same as DRAG_N_DROP_SIMPLE).
        self._release_drag()

    def mouseUpOutSide(self):
        self._release_drag()

    def _release_drag(self):
        d = self.pDragObject
        if _alive(d) and is_enabled(d.pSprite, d):
            d.mouseUp()

    def mPlayDone(self, theObject):
        if theObject is self.pStateChangeAnim:
            _done(self.pParent, self)
        elif theObject is self.pDropObject:
            self.pDropObject.mHide()
            S(self.pBackSprite).member = self.pBackMember
            S(self.pSprite).member = self.pMember
            M.enableGame()
        else:
            rect = self.pDropRect
            if isinstance(rect, (tuple, list)) and len(rect) == 4 and _inside(S(theObject.pSprite).loc, rect):
                self.pDropped = 1
                self.pDragObject.mHide()
                if _alive(self.pStateChangeAnim):
                    self.pStateChangeAnim.mShow()
                    self.pStateChangeAnim.mPlay()
                    M.resetCursor()
                else:
                    _done(self.pParent, self)
            else:
                R().sound.puppet(1, self.pDropSound)
                self.pDropObject.mSetReturnLoc(self.pDragReturnLoc)
                self.pDropObject.mPlay()
                M.resetCursor()


# ============================================================================================
# SCAVENGER_HUNT  (ParentScript 72)
# ============================================================================================

@lingo_script('SCAVENGER_HUNT')
class ScavengerHunt(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pTextSprite = 0
        self.pTextMember = 0
        self.pTokenAnim = 0
        self.pClueSound = 0
        self.pTransAnim = 0
        self.pTokenButton = 0
        self.pClickMember = 0
        self.pClickBlend = 0
        self.pClickSprite = 0
        self.pShown = 0
        self.pDragObject = 0
        self.pScreenDropRect = 0
        self.pParent = 0
        self.pSavedList = []
        self.pHuntScreen = None
        self.pFound = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pClickSprite = pop_one(theSpriteAlloc)
        self.pTokenAnim = get_object(self.pTokenAnim, theSpriteAlloc)
        self.pTextSprite = pop_one(theSpriteAlloc)
        self.pTransAnim = get_object(self.pTransAnim, theSpriteAlloc)
        self.pDragObject = get_object(self.pDragObject, theSpriteAlloc)
        _call_if(self.pTokenAnim, 'mSetParent', self)
        _call_if(self.pTransAnim, 'mSetParent', self)
        _call_if(self.pDragObject, 'mSetParent', self)
        self.pTokenButton = 0
        self.pShown = 0
        self.pFound = 0
        self.pSavedList = [Sym('pShown'), Sym('pFound')]
        M.addObjectGlob(self)
        if _alive(self.pDragObject):
            self.pScreenDropRect = self.pDragObject.pDropRect
        if isinstance(self.pClueSound, dict):                      # listp(pClueSound): an ANIM_WIGGLE propList
            self.pClueSound = get_object(self.pClueSound, theSpriteAlloc)
            _call_if(self.pClueSound, 'mSetParent', self)
        return self

    def mInitPoolObjects(self):
        if _stringp(self.pClueSound):
            self.pClueSound = M.getExSoundObject(2, self.pClueSound, self)
        if (self.pClickMember or 0) > 0:
            self.pTokenButton = M.getSimpleButt(self.pClickSprite, self.pClickMember, self, 8)
            if self.pTokenButton.pLoc is None:
                self.pTokenButton.pLoc = M.getRegPoint()

    def mReleasePoolObjects(self):
        if _typ(self.pClueSound) == 'EXTERNALSOUND':
            self.pClueSound = M.recycleSoundObject(self.pClueSound)
        if _alive(self.pTokenButton):
            M.recycleSimpleButt(self.pTokenButton)
            self.pTokenButton = 0

    def mDestroy(self): pass

    def _here(self):
        return _eq(M.gCurScreen.mGetName(), self.pHuntScreen)

    def mLoad(self):
        load_mem(self.pTextMember)
        if _alive(self.pClueSound):
            self.pClueSound.mLoad()
        if self._here():
            load_mem(self.pClickMember)
            if _alive(self.pTokenAnim):
                self.pTokenAnim.mLoad()
            if _alive(self.pTransAnim):
                self.pTransAnim.mLoad()
            if _alive(self.pDragObject):
                self.pDragObject.mLoad()

    def mLoadList(self, theList):
        theList.append(self.pTextMember)
        if _alive(self.pClueSound):
            self.pClueSound.mLoadList(theList)
        if _alive(self.pDragObject):
            self.pDragObject.mLoadList(theList)
        if self._here():
            theList.append(self.pClickMember)
            if _alive(self.pTokenAnim):
                self.pTokenAnim.mLoadList(theList)
            if _alive(self.pTransAnim):
                self.pTransAnim.mLoadList(theList)

    def mUnLoad(self, forceFlag=None):
        if self.pFound or forceFlag:
            unload_mem(self.pTextMember)
            _unload(self.pClueSound)
            _unload(self.pDragObject)
        unload_mem(self.pClickMember)
        _unload(self.pTokenAnim)
        _unload(self.pTransAnim)
    mUnload = mUnLoad

    def mouseDown(self):
        if _rollover(self.pTextSprite):
            M.setInterruptMode(self.pClueSound)
            self.pClueSound.mPlay()

    def mButtonActivated(self, theObject):
        if theObject is self.pTokenAnim:
            self.pFound = 1
            self.mDisable()
            M.gCurScreen.mDisable()
            self.pTokenAnim.mPlay()
        elif theObject is self.pTokenButton:
            if _alive(self.pTokenAnim):
                self.mButtonActivated(self.pTokenAnim)
            else:
                self.pParent.mTokenFound(self)

    def mDisable(self):
        if _alive(self.pTokenButton):
            self.pTokenButton.mDisable()
        if _alive(self.pTokenAnim):
            self.pTokenAnim.mDisable()
        if _alive(self.pDragObject):
            self.pDragObject.mDisable()
        remove_behavior(self.pClickSprite, self)
        S(self.pTextSprite).cursor = 0
        remove_behavior(self.pTextSprite, self)

    def mEnable(self):
        if self._here():
            if _alive(self.pTokenAnim):
                self.pTokenAnim.mEnable()
            if _alive(self.pTokenButton):
                self.pTokenButton.mEnable()
        if _alive(self.pDragObject):
            self.pDragObject.mEnable()
        S(self.pTextSprite).cursor = [22, 23]
        set_behavior(self.pTextSprite, self)

    def mShow(self):
        if self.pTextMember:
            S(self.pTextSprite).member = self.pTextMember
            S(self.pTextSprite).ink = 36
            S(self.pTextSprite).cursor = [22, 23]
            set_behavior(self.pTextSprite, self)
        if _alive(self.pDragObject):
            self.pDragObject.mShow()
            if self._here():
                self.pDragObject.pDropRect = self.pScreenDropRect
            else:
                self.pDragObject.pDropRect = Rect(0, 0, 0, 0)
        if self._here():
            if _alive(self.pTokenButton):
                self.pTokenButton.mShow()
            if _alive(self.pTokenAnim):
                self.pTokenAnim.mShow()
                self.pTokenAnim.mEnable()
        if not self.pShown and _alive(self.pClueSound):
            M.setInterruptMode(self.pClueSound)
            self.pClueSound.mPlay()
            self.pShown = 1

    def mHide(self):
        blank(self.pClickSprite)
        if _alive(self.pDragObject):
            self.pDragObject.mHide()
        if _alive(self.pTokenAnim):
            self.pTokenAnim.mHide()
        if _alive(self.pTransAnim):
            self.pTransAnim.mHide()
        blank(self.pTextSprite)
        if _alive(self.pTokenButton):
            self.pTokenButton.mHide()

    def mPlayClueAudio(self):
        M.setInterruptMode(self.pClueSound)
        self.pClueSound.mPlay()

    def mSetFound(self): self.pFound = 1
    def mFound(self): return self.pFound
    def mLoadFoundToken(self): pass

    def mLoadFoundTokenList(self, theList):
        if _alive(self.pTokenAnim):
            if self.pTokenAnim.pPlayed and _eq(self.mGetName(), M.gCurScreen.mGetName()):
                self.pTokenAnim.mLoadList(theList)

    def mUnloadFoundToken(self):
        _unload(self.pTokenAnim)

    def mShowFoundToken(self):
        if _alive(self.pTokenAnim):
            if self.pTokenAnim.pPlayed and _eq(self.mGetName(), M.gCurScreen.mGetName()):
                self.pTokenAnim.mShow()

    def mHideFoundToken(self):
        if _alive(self.pTokenAnim):
            self.pTokenAnim.mHide()

    def mPlayDone(self, theObject):
        if theObject is self.pTokenAnim:
            if _alive(self.pTransAnim):
                self.pTransAnim.mPlay()
            else:
                self.pParent.mTokenFound(self)
        elif theObject is self.pTransAnim:
            _unload(self.pTransAnim)
            self.pParent.mTokenFound(self)
        elif theObject is self.pDragObject:
            self.pFound = 1
            self.pParent.mTokenFound(self)
        elif theObject is self.pClueSound:
            if _typ(theObject) == 'ANIM_WIGGLE':
                theObject.mHide()

    def mGetName(self): return self.pName
    def mGetHuntScreen(self): return self.pHuntScreen
    def mSetParent(self, theObject): self.pParent = theObject
    def mGetType(self): return Sym('SCAVENGER_HUNT')

    def mExternalSHTokenFound(self, theObject=None):
        self.pFound = 1
        self.mNextToken()

    def mNextToken(self):
        if _alive(self.pTransAnim):
            blank(self.pTextSprite)
            self.pTransAnim.mPlay()
        else:
            self.pParent.mTokenFound(self)


# ============================================================================================
# SH_DADDY  (ParentScript 73)
# ============================================================================================

@lingo_script('SH_DADDY')
class ShDaddy(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pHuntList = []
        self.pHuntIndex = 1
        self.pClueStripSprite = 0
        self.pClueStripMember = 0
        self.pDragObject = 0
        self.pDropRect = 0
        self.pDragShown = 0
        self.pAutoFinale = 0
        self.pGameScreen = None
        self.pParent = 0
        self.pSavedList = []
        self.pAnimQueue = 0
        self.pFoundCount = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        daTokenAnimSprite = pop_one(theSpriteAlloc)
        self.pClueStripSprite = pop_one(theSpriteAlloc)
        self.pHuntList = get_object_list(self.pHuntList, theSpriteAlloc, 10)
        call_all(self.pHuntList, 'mSetParent', self)
        for daHunt in self.pHuntList:
            if _alive(daHunt.pTokenAnim):
                if getattr(daHunt.pTokenAnim, 'pSprite', None) is not None:      # not voidp(getaProp(..., #pSprite))
                    daHunt.pTokenAnim.pSprite = daTokenAnimSprite
        self.pGameScreen = Sym('S_SH')
        self.pHuntIndex = 1
        self.pFoundCount = 0
        self.pSavedList = [Sym('pHuntIndex')]
        M.addObjectGlob(self)
        return self

    def mInitPoolObjects(self):
        for daHunt in self.pHuntList:
            daHunt.mInitPoolObjects()

    def mReleasePoolObjects(self):
        for daHunt in self.pHuntList:
            daHunt.mReleasePoolObjects()

    def mDestroy(self): pass

    def _cur(self):
        return self.pHuntList[self.pHuntIndex - 1]

    def _not_game_screen(self):
        return not _eq(M.gCurScreen.mGetName(), self.pGameScreen)

    def mNextHunt(self):
        self._cur().mSetFound()
        self._cur().mHide()
        self.pHuntIndex = self.pHuntIndex + 1
        self._cur().mLoad()
        self._cur().mShow()
        _unload(self.pHuntList[self.pHuntIndex - 2])

    def mAllTokensFound(self):
        daFound = 1
        for daObject in self.pHuntList:
            daFound = min(daFound, daObject.mFound() or 0)
        return daFound

    def mLoadFoundTokens(self): pass
    def mLoadFoundTokensList(self, theList=None): pass
    def mUnloadFoundTokens(self): pass

    def mShowFoundTokens(self):
        for daObject in self.pHuntList:
            if self._not_game_screen():
                daObject.mShowFoundToken()

    def mHideFoundTokens(self):
        for daObject in self.pHuntList:
            if self._not_game_screen():
                daObject.mHideFoundToken()

    def mTokenFound(self, theObject):
        sd = M.gScreenDaddy
        self.pFoundCount = self.pFoundCount + 1
        sd.mAddToken(theObject.pName)
        if self.pHuntIndex < len(self.pHuntList):
            theObject.mHide()
            if self._not_game_screen():
                theObject.mShowFoundToken()
            self.pHuntIndex = self.pHuntIndex + 1
            self.mShow()
        else:
            if self.pAutoFinale:
                theObject.mHide()
                blank(self.pClueStripSprite)
                R().update_stage()
                sd.mDisable()
                sd.mPlayFinale()
                return
        _call_if(M.gCurScreen, 'mHuntObjectFound', theObject)

    def mDisable(self):
        if self.pHuntIndex and len(self.pHuntList):
            self._cur().mDisable()

    def mEnable(self):
        if self.pHuntIndex and len(self.pHuntList):
            self._cur().mEnable()

    def mGetCurrentHuntName(self):
        if len(self.pHuntList):
            return self._cur().mGetHuntScreen()
        return Sym('none')

    def mShow(self):
        daHunt = self._cur()
        if daHunt.pTextMember:
            S(self.pClueStripSprite).member = self.pClueStripMember
        else:
            blank(self.pClueStripSprite)
        if self._not_game_screen():
            self.mShowFoundTokens()
        if self.pAutoFinale and (self.pHuntIndex == len(self.pHuntList)) and not getattr(M, 'gAppInBackground', 0):
            M.gScreenDaddy.mLoadFinale()
        self._cur().mShow()
        self.pFoundCount = 0

    def mHide(self):
        blank(self.pClueStripSprite)
        self.mHideFoundTokens()
        self._cur().mHide()

    def mLoad(self):
        load_mem(self.pClueStripMember)
        if self.pHuntIndex and len(self.pHuntList):
            self._cur().mLoad()
        if self.pAutoFinale and (self.pHuntIndex == len(self.pHuntList)) and not getattr(M, 'gAppInBackground', 0):
            self.pParent.mLoadFinale()

    def mLoadList(self, theList):
        theList.append(self.pClueStripMember)
        if self.pHuntIndex and len(self.pHuntList):
            self._cur().mLoadList(theList)
            if _eq(M.gCurScreen.mGetName(), self._cur().mGetHuntScreen()) and (self.pHuntIndex < len(self.pHuntList)):
                self.pHuntList[self.pHuntIndex].mLoadList(theList)
        for daHunt in self.pHuntList:
            daHunt.mLoadFoundTokenList(theList)
        if self.pAutoFinale and (self.pHuntIndex == len(self.pHuntList)):
            M.gScreenDaddy.mLoadFinaleList(theList)

    def mUnLoad(self, forceFlag=None):
        if self.mAllTokensFound() or forceFlag:
            unload_mem(self.pClueStripMember)
        if self.pHuntIndex and len(self.pHuntList):
            _unload(self._cur(), forceFlag)
            if self.pHuntIndex < len(self.pHuntList):
                _unload(self.pHuntList[self.pHuntIndex], 1)
            if (self.pHuntIndex > 1) and self.pFoundCount:
                _unload(self.pHuntList[self.pHuntIndex - 2])
        for daHunt in self.pHuntList:
            daHunt.mUnloadFoundToken()
        if self.pAutoFinale:
            M.gScreenDaddy.mUnloadFinale()
    mUnload = mUnLoad

    def mExternalSHTokenFound(self, theObject=None):
        if self.pHuntIndex and len(self.pHuntList):
            self._cur().mExternalSHTokenFound()

    def mGetCurrentHuntObject(self):
        if self.pHuntIndex and len(self.pHuntList):
            return self._cur()

    def mGetName(self): return self.pName
    def mSetParent(self, theObject): self.pParent = theObject
    def mGetType(self): return Sym('SH_DADDY')


# ============================================================================================
# SH_DADDY_ANIM  (ParentScript 102): an SH_DADDY that plays an intro when first shown and an outro on the last token
# ============================================================================================

@lingo_script('SH_DADDY_ANIM')
class ShDaddyAnim(LObject):
    def __init__(self):
        self.ancestor = None
        self.pType = None
        self.pName = None
        self.pShowAnim = 0
        self.pHideAnim = 0
        self.pTimesShown = 0
        self.pSavedList = []

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.ancestor = get_object(self.ancestor, theSpriteAlloc)
        anc = self.ancestor
        call_all(anc.pHuntList, 'mSetParent', self)
        daAlloc = pop_list(theSpriteAlloc, 5)
        self.pShowAnim = get_object(self.pShowAnim, list(daAlloc))
        self.pShowAnim.mSetParent(self)
        self.pHideAnim = get_object(self.pHideAnim, list(daAlloc))
        self.pHideAnim.mSetParent(self)
        self.pTimesShown = 0
        self.pSavedList = [Sym('pTimesShown')]
        M.addObjectGlob(self)
        return self

    def mDisable(self):
        anc = self.ancestor
        if anc.pHuntIndex and len(anc.pHuntList):
            anc.pHuntList[anc.pHuntIndex - 1].mDisable()

    def mEnable(self):
        anc = self.ancestor
        if anc.pHuntIndex and len(anc.pHuntList):
            anc.pHuntList[anc.pHuntIndex - 1].mEnable()

    def mDestroy(self): pass

    def mShow(self):
        if not self.pTimesShown:
            self.pTimesShown = self.pTimesShown + 1
            self.pShowAnim.mShow()
            self.pShowAnim.mPlay()
        else:
            self.ancestor.mShow()

    def mHide(self):
        self.ancestor.mHide()

    def _last_hunt_here(self):
        anc = self.ancestor
        return (len(anc.pHuntList) == anc.pHuntIndex) and \
            _eq(M.gCurScreen.mGetName(), anc.pHuntList[len(anc.pHuntList) - 1].pName)

    def mLoad(self):
        if not self.pTimesShown:
            self.pShowAnim.mLoad()
        elif self._last_hunt_here():
            self.pHideAnim.mLoad()
        self.ancestor.mLoad()

    def mLoadList(self, theList, theForceFlag=None):
        if not self.pTimesShown:
            self.pShowAnim.mLoadList(theList)
        elif self._last_hunt_here():
            self.pHideAnim.mLoadList(theList)
        self.ancestor.mLoadList(theList)

    def mUnLoad(self, theForceFlag=None):
        _unload(self.pShowAnim)
        _unload(self.pHideAnim)
        self.ancestor.mUnLoad(theForceFlag)
    mUnload = mUnLoad

    def mTokenFound(self, theObject):
        anc = self.ancestor
        if anc.pHuntIndex == len(anc.pHuntList):
            theObject.mHide()
            blank(anc.pClueStripSprite)
            theObject.mShowFoundToken()
            self.pHideAnim.mShow()
            self.pHideAnim.mPlay()
            return
        else:
            anc.mTokenFound(theObject)

    def mPlayDone(self, theObject):
        anc = self.ancestor
        if theObject is self.pShowAnim:
            self.pShowAnim.mHide()
            anc.mShow()
        elif theObject is self.pHideAnim:
            self.pHideAnim.mHide()
            _unload(self.pHideAnim)
            daCurrentHuntObject = anc.pHuntList[anc.pHuntIndex - 1]
            anc.mTokenFound(daCurrentHuntObject)

    def mGetName(self): return self.pName
    def mSetParent(self, theObject): self.pParent = theObject
    def mGetType(self): return Sym('SH_DADDY_ANIM')


# ============================================================================================
# REMINDER_*  (ParentScripts 111, 113-117, 120, 121, 123): the conditions REMINDER_AUDIO polls
# ============================================================================================

class _Reminder(LObject):
    _NAME = None

    def __init__(self):
        self.pName = Sym(self._NAME)
        self.pAccessCount = 0
        self.pSound = 0
        self.pSkipFirst = 0
        self.pExcludeList = []
        self.pTimeOutLength = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        return self

    def mConditionTrue(self):
        return 0

    @staticmethod
    def _min(conds):
        return min(1 if c else 0 for c in conds)


@lingo_script('REMINDER_CHUTE')
class ReminderChute(_Reminder):
    _NAME = 'CHUTE'

    def mConditionTrue(self):
        sd = M.gScreenDaddy
        c = [sd.mAllRiddlesSolved(), sd.mTokenFoundCount() > 0, sd.mGetLevel() == 1, _eq(sd.pName, Sym('b'))]
        daScreen = sd.mGetScreen(Sym('B_RK'))
        if _alive(daScreen):
            c.append(not daScreen.mAllFuelCrystalsDropped())
        else:
            c.append(0)
        return self._min(c)


@lingo_script('REMINDER_ALLRIDDLES_NOKEYS')
class ReminderAllRiddlesNoKeys(_Reminder):
    _NAME = 'ALLRIDDLES_NOKEYS'

    def mConditionTrue(self):
        sd = M.gScreenDaddy
        return self._min([sd.mAllRiddlesSolved(), sd.mTokenFoundCount() == 0, sd.mGetLevel() == 1])


@lingo_script('REMINDER_ALLRIDDLES_DU')
class ReminderAllRiddlesDU(_Reminder):
    _NAME = 'REMINDER_ALLRIDDLES_DU'

    def mConditionTrue(self):
        sd = M.gScreenDaddy
        c = [sd.mRemainingTokenCount() == 0, sd.mGetLevel() == 1]
        daScreen = sd.mGetScreen(Sym('S_DU'))
        c.append((daScreen.mAllKeysDropped() if _alive(daScreen) else 1) == 0)
        return self._min(c)


@lingo_script('REMINDER_SCROLL_DU')
class ReminderScrollDU(_Reminder):
    _NAME = 'REMINDER_SCROLL_DU'

    def mConditionTrue(self):
        sd = M.gScreenDaddy
        daDungeonScreen = sd.mGetScreen(Sym('S_DU'))
        daWizLabScreen = sd.mGetScreen(Sym('S_SH'))
        c = [daDungeonScreen.pDragonEmergeAnim.pPlayed if _alive(daDungeonScreen) else 0,
             (daWizLabScreen.pMagicScrollAnimation.pPlayed == 0) if _alive(daWizLabScreen) else 0]
        return self._min(c)


@lingo_script('REMINDER_ALLRIDDLES_BK')
class ReminderAllRiddlesBK(_Reminder):
    _NAME = 'REMINDER_ALLRIDDLES_BK'

    def mConditionTrue(self):
        sd = M.gScreenDaddy
        c = [sd.mRemainingTokenCount() == 0, sd.mGetLevel() == 1]
        daBookScreen = sd.mGetScreen(Sym('D_BK'))
        c.append((daBookScreen.pAllFoundBink.pPlayed == 0) if _alive(daBookScreen) else 0)
        return self._min(c)


@lingo_script('REMINDER_FIRSTCLUE_BK')
class ReminderFirstClueBK(_Reminder):
    _NAME = 'REMINDER_FIRSTCLUE_BK'

    def mConditionTrue(self):
        sd = M.gScreenDaddy
        c = [sd.mGetLevel() == 2, sd.mTokenFoundCount() == 0]
        daBookScreen = sd.mGetScreen(Sym('D_BK'))
        c.append((daBookScreen.pAllFoundBink.pPlayed == 1) if _alive(daBookScreen) else 0)
        return self._min(c)


@lingo_script('REMINDER_ALLRIDDLES_NOKEYS_RK')
class ReminderAllRiddlesNoKeysRK(_Reminder):
    _NAME = 'ALLRIDDLES_NOKEYS_RK'

    def mConditionTrue(self):
        sd = M.gScreenDaddy
        c = [sd.mAllRiddlesSolved(), sd.mTokenFoundCount() == 0, sd.mGetLevel() == 1]
        daRocketScreen = sd.mGetScreen(Sym('B_RK'))
        c.append(daRocketScreen.pAttemptedLaunch if _alive(daRocketScreen) else 0)
        return self._min(c)


@lingo_script('REMINDER_ALLRIDDLES_RK')
class ReminderAllRiddlesRK(_Reminder):
    _NAME = 'REMINDER_ALLRIDDLES_RK'

    def mConditionTrue(self):
        sd = M.gScreenDaddy
        c = [sd.mRemainingTokenCount() == 0, sd.mGetLevel() == 1]
        daRocketScreen = sd.mGetScreen(Sym('B_RK'))
        c.append((daRocketScreen.mAllFuelCrystalsDropped() == 0) if _alive(daRocketScreen) else 0)
        return self._min(c)


@lingo_script('REMINDER_ALLRIDDLES_NOKEYS_BK')
class ReminderAllRiddlesNoKeysBK(_Reminder):
    _NAME = 'ALLRIDDLES_NOKEYS_RK'            # (sic: the Lingo names this one #ALLRIDDLES_NOKEYS_RK too)

    def mConditionTrue(self):
        sd = M.gScreenDaddy
        c = [sd.mAllRiddlesSolved(), sd.mTokenFoundCount() == 0, sd.mGetLevel() == 1]
        daBookScreen = sd.mGetScreen(Sym('D_BK'))
        c.append(daBookScreen.pVisited if _alive(daBookScreen) else 0)
        return self._min(c)


# ============================================================================================
# REMINDER_AUDIO  (ParentScript 78)
# ============================================================================================

@lingo_script('REMINDER_AUDIO')
class ReminderAudio(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pTimer = 0
        self.pSoundObj = 0
        self.pCurReminder = 0
        self.pReminderList = []
        self.pTimerScriptNumber = 0
        self.pEnabled = 0
        self.pPlayCount = 0
        self.pSavedList = []

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pTimerScriptNumber = 'TIMER'                     # getMemNum("Timer")
        self.pTimer = _new(self.pTimerScriptNumber)
        self.pTimer.pCheckForMouseActivity = 0
        self.pTimer.mSetParent(self)
        self.pSoundObj = 0
        self.pCurReminder = 0
        self.pPlayCount = 0
        self.pReminderList = get_object_list(self.pReminderList, theSpriteAlloc)
        # (author-mode only: shorten every pTimeOutLength to 5 s)
        self.pSavedList = [Sym('pPlayCount')]
        M.addObjectGlob(self)
        return self

    def _dont_play(self, *extra):
        daDontPlayList = list(extra)
        daDontPlayList.append(1 if ((self.pPlayCount == 1) and self.pCurReminder.pSkipFirst) else 0)
        daDontPlayList.append(_get_pos_eq(self.pCurReminder.pExcludeList, M.gCurScreen.pName))
        return max(daDontPlayList)

    def mEnable(self):
        self.pTimer.mEnable()
        if _alive(self.pCurReminder):
            return 1 if (self.pTimer.mTimeUp() and self._dont_play() == 0) else 0
        return 0

    def mDisable(self):
        self.pTimer.mDisable()

    def mCheckStatus(self):
        if not _alive(self.pCurReminder):
            for daReminder in self.pReminderList:
                if daReminder.mConditionTrue():
                    self.pCurReminder = daReminder
                    if _stringp(self.pCurReminder.pSound):
                        self.pSoundObj = M.getExSoundObject(2, self.pCurReminder.pSound, self)
                    else:
                        self.pSoundObj = M.getSoundObject(2, self.pCurReminder.pSound, self)
                    return self.mPlaySound()
        else:
            self.pTimer.mEnable()
        return 0

    def mPlaySound(self):
        self.pPlayCount = self.pPlayCount + 1
        if not self._dont_play(0 if M.gCurScreen.mGetEnabled() else 1):
            if not R().sound.busy(self.pSoundObj.pChannel):
                M.disableGame()
                M.waitCursor()
                self.pSoundObj.mPlay()
                return 1
            else:
                self.pTimer.pTimeOutLength = 10 * 1000
                self.pTimer.mPlay()
        else:
            self.pTimer.pTimeOutLength = self.pCurReminder.pTimeOutLength
            self.pTimer.mPlay()
        return 0

    def mDestroy(self): pass

    def mPlayDone(self, theObject):
        if theObject is self.pSoundObj:
            self.pTimer.pTimeOutLength = self.pCurReminder.pTimeOutLength
            self.pTimer.mPlay()
            M.enableGame()
            M.resetCursor()
        elif theObject is self.pTimer:
            if self.pCurReminder.mConditionTrue():
                self.mPlaySound()
            else:
                self.mClearSound()

    def mSetSound(self, thesound=None, theInterrupt=None): pass

    def mClearSound(self):
        self.pCurReminder = 0
        if _alive(self.pSoundObj):
            M.recycleSoundObject(self.pSoundObj)
            self.pSoundObj = 0
        self.pPlayCount = 0
        self.pTimer.mKill()

    def mGetCurSound(self): return self.pCurReminder.pSound
    def mGetType(self): return Sym('REMINDER_AUDIO')


def _get_pos_eq(lst, item):
    """getPos(list, item) with Lingo equality: 1-based index, 0 when absent."""
    for i, x in enumerate(lst or []):
        if _eq(x, item):
            return i + 1
    return 0
