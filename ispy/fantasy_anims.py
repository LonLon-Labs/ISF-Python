"""Hand-ported Fantasy parent scripts, part 2: helper animations and utility objects.

    ParentScript  62  DROP              sine-eased "ease out" move of the drag sprite (pSinCounter 0..90)
    ParentScript  98  ANIM_MOVE_OBJECT  linear move; the *parent* places the sprite (mSetLoc)
    ParentScript 103  ANIM_MULTI        plays a list of animation objects one after another
    ParentScript 109  FADE_SOUND        plays a sound (the transition fade is OS X only, so it is a plain sound here)
    ParentScript  71  OBJECT_GROUP      a list of objects handed out one at a time (mNextObject)
    ParentScript  31  REG_MAP           Windows registry map (dosReadReg ...): nothing to read in the port
    ParentScript  25  ALERT_HOOK        the movie's alertHook

Same conventions as scavenger.py (one class per script, names unchanged, both mUnLoad / mUnload).
"""
import math

from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, Point, set_properties, pop_one
from .ui import R, S, load_mem, unload_mem, call_all, blank, _done
from .screens2 import _alive, _get_pos, _get_dist, _integer
from .scavenger import _unload, _stringp


def _unload_all(lst, *a):
    """call(#mUnLoad, list)"""
    for o in list(lst or []):
        _unload(o, *a)


# ============================================================================================
# DROP  (ParentScript 62)
# ============================================================================================

@lingo_script('DROP')
class Drop(LObject):
    def __init__(self, theParent=0):
        self.pType = None
        self.pName = None
        self.pSound = 0
        self.pSoundChannel = 1
        self.pMember = 0
        self.pStartLoc = Point(320, 240)
        self.pStopLoc = Point(320, 240)
        self.pSprite = M.getDragSprite()
        self.pPixelsPerSecond = 10
        self.pLastUpdate = 0
        self.pFPS = 10
        self.pHDist = 0
        self.pVDist = 0
        self.pStepHDist = 0
        self.pStepVDist = 0
        self.pCurrH = 0
        self.pCurrV = 0
        self.pSrcH = 0
        self.pSrcV = 0
        self.pIncrement = 0
        self.pStepDist = 0
        self.pSinCounter = 0
        self.pDistanceTimer = 170
        self.pParent = theParent

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        return self

    def mDestroy(self): pass
    def mSetReturnLoc(self, theReturnLoc): self.pStopLoc = theReturnLoc
    def mSetMember(self, theMember): self.pMember = theMember
    def mSetStartLoc(self, theLoc): self.pStartLoc = theLoc

    def mShow(self):
        S(self.pSprite).member = self.pMember
        S(self.pSprite).loc = self.pStartLoc

    def mHide(self):
        S(self.pSprite).member = 1

    def mPlay(self):
        if self.pSound:
            R().sound.puppet(self.pSoundChannel, self.pSound)
        loc = S(self.pSprite).loc
        stop = self.pStopLoc
        self.pSrcH = loc[0]
        self.pSrcV = loc[1]
        self.pCurrH = loc[0]
        self.pCurrV = loc[1]
        self.pHDist = stop[0] - loc[0]
        self.pVDist = stop[1] - loc[1]
        daDist = _get_dist(Point(loc[0] - stop[0], loc[1] - stop[1])) * 1.0
        if daDist == 0:
            return                                   # (the Lingo `exit`s without telling the parent)
        self.pIncrement = self.pDistanceTimer / daDist
        daTotalUpdates = daDist / self.pPixelsPerSecond * self.pFPS
        self.pStepHDist = self.pHDist / daTotalUpdates * 1.0
        self.pStepVDist = self.pVDist / daTotalUpdates * 1.0
        self.pStepDist = _get_dist(Point(self.pStepHDist, self.pStepVDist))
        self.pSinCounter = 0
        M.addUpdateList(self)

    def mStop(self):
        M.removeUpdateList(self)

    def mUpdate(self):
        # (`pLastUpdate < (the milliSeconds + (1000 / pFPS))` is always true: one step per update-list tick)
        if self.pLastUpdate < (R().milliseconds() + (1000 // self.pFPS)):
            if self.pSinCounter >= 90:
                S(self.pSprite).loc = self.pStopLoc
                M.removeUpdateList(self)
                _done(self.pParent, self)
            else:
                radians = math.pi / 180 * self.pSinCounter
                ratio = math.sin(radians)
                self.pCurrH = self.pSrcH + (ratio * self.pHDist)
                self.pCurrV = self.pSrcV + (ratio * self.pVDist)
                S(self.pSprite).loc = Point(_integer(self.pCurrH), _integer(self.pCurrV))
            self.pSinCounter = self.pSinCounter + self.pIncrement

    def mLoad(self):
        load_mem(self.pSound)
        load_mem(self.pMember)

    def mLoadList(self, theList):
        theList.append(self.pSound)
        theList.append(self.pMember)

    def mUnLoad(self):
        unload_mem(self.pSound)
        unload_mem(self.pMember)
    mUnload = mUnLoad

    def mGetType(self): return Sym('ANIM_MOVE')
    def mSetParent(self, theObject): self.pParent = theObject
    def mGetName(self): return self.pName


# ============================================================================================
# ANIM_MOVE_OBJECT  (ParentScript 98)
# ============================================================================================

@lingo_script('ANIM_MOVE_OBJECT')
class AnimMoveObject(LObject):
    def __init__(self, theSprite=0, theParent=0):
        self.pType = None
        self.pName = None
        self.pSprite = theSprite
        self.pReturnLoc = Point(320, 240)
        self.pPixelsPerSecond = 50
        self.pLastUpdate = 0
        self.pSpeed = 10
        self.pHDist = 0
        self.pVDist = 0
        self.pStepHDist = 0
        self.pStepVDist = 0
        self.pCurrH = 0
        self.pCurrV = 0
        self.pStepDist = 0
        self.pParent = theParent

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        return self

    def mDestroy(self): pass
    def mSetReturnLoc(self, theReturnLoc): self.pReturnLoc = theReturnLoc
    def mShow(self): pass
    def mHide(self): pass

    def mPlay(self):
        loc = S(self.pSprite).loc
        ret = self.pReturnLoc
        self.pCurrH = loc[0]
        self.pCurrV = loc[1]
        self.pHDist = ret[0] - loc[0]
        self.pVDist = ret[1] - loc[1]
        daDist = _get_dist(Point(loc[0] - ret[0], loc[1] - ret[1])) * 1.0
        if daDist < 10:
            self.pParent.mSetLoc(ret)
            _done(self.pParent, self)
            return
        daTotalUpdates = daDist / self.pPixelsPerSecond * self.pSpeed
        self.pStepHDist = self.pHDist / daTotalUpdates * 1.0
        self.pStepVDist = self.pVDist / daTotalUpdates * 1.0
        self.pStepDist = _get_dist(Point(self.pStepHDist, self.pStepVDist))
        M.addUpdateList(self)

    def mStop(self):
        M.removeUpdateList(self)

    def mUpdate(self):
        if self.pLastUpdate < (R().milliseconds() + (1000 // self.pSpeed)):
            loc = S(self.pSprite).loc
            ret = self.pReturnLoc
            daDist = _get_dist(Point(loc[0] - ret[0], loc[1] - ret[1]))
            if daDist < self.pStepDist:
                M.removeUpdateList(self)
                _done(self.pParent, self)
            else:
                self.pCurrH = self.pCurrH + self.pStepHDist
                self.pCurrV = self.pCurrV + self.pStepVDist
                self.pParent.mSetLoc(Point(_integer(self.pCurrH), _integer(self.pCurrV)))

    def mGetType(self): return Sym('ANIM_MOV')                # (sic)
    def mSetParent(self, theObject): self.pParent = theObject
    def mGetName(self): return self.pName


# ============================================================================================
# ANIM_MULTI  (ParentScript 103)
# ============================================================================================

@lingo_script('ANIM_MULTI')
class AnimMulti(LObject):
    def __init__(self):
        self.pType = None
        self.pObjectList = []
        self.pCurrentObject = 0
        self.pParent = 0
        self.pIndex = 1
        self.pHidePrevious = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pObjectList = get_object_list(self.pObjectList, theSpriteAlloc)
        call_all(self.pObjectList, 'mSetParent', self)
        self.pParent = 0
        self.pIndex = 1
        self.pCurrentObject = self.pObjectList[self.pIndex - 1]
        return self

    def mLoad(self): call_all(self.pObjectList, 'mLoad')
    def mLoadList(self, theList): call_all(self.pObjectList, 'mLoadList', theList)

    def mUnLoad(self): _unload_all(self.pObjectList)
    mUnload = mUnLoad

    def mDestroy(self): pass
    def mSetParent(self, theParent): self.pParent = theParent
    def mShow(self): self.pCurrentObject.mShow()

    def mHide(self):
        if self.pHidePrevious:
            self.pCurrentObject.mHide()
        else:
            call_all(self.pObjectList, 'mHide')

    def mPlay(self): self.pCurrentObject.mPlay()

    def mPlayDone(self, theObject):
        if self.pIndex < len(self.pObjectList):
            if self.pHidePrevious:
                theObject.mHide()
            self.pIndex = self.pIndex + 1
            self.pCurrentObject = self.pObjectList[self.pIndex - 1]
            self.pCurrentObject.mShow()
            self.pCurrentObject.mPlay()
        else:
            self.pIndex = 0
            _done(self.pParent, self)

    def mStop(self):
        if _alive(self.pCurrentObject):
            self.pCurrentObject.mStop()

    def mGetType(self): return Sym('ANIM_MULTI')


# ============================================================================================
# FADE_SOUND  (ParentScript 109)
# ============================================================================================

@lingo_script('FADE_SOUND')
class FadeSound(LObject):
    """pFadeActive = isOSX(), which is always 0 in the port: the black-cover + puppetTransition path is skipped
    and this is a plain sound (a string is an AIFF file name, a number is a main-cast sound member)."""

    def __init__(self, theName=None):
        self.pName = theName
        self.pSound = 0
        self.pParent = 0
        self.pChannel = 1
        self.pInterrupt = 0
        self.pPlaying = 0
        self.pFadeMember = 0
        self.pBlackMember = 0
        self.pSprite = 0
        self.pFadeActive = M.isOSX()
        self.pFlushCount = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        return self

    def mDestroy(self): pass
    def mSetParent(self, theObject): self.pParent = theObject

    def mLoad(self):
        if isinstance(self.pSound, int):
            load_mem(self.pSound)

    def mLoadList(self, theList):
        if isinstance(self.pSound, int):
            theList.append(self.pSound)

    def mUnLoad(self):
        if isinstance(self.pSound, int):
            unload_mem(self.pSound)
    mUnload = mUnLoad

    def mGetType(self): return Sym('FADE_SOUND')
    def mGetName(self): return self.pName

    def mPlay(self):
        if self.pFadeActive:
            if self.pBlackMember:
                S(self.pSprite).member = self.pBlackMember
                R().update_stage()
            blank(self.pSprite)
        if _stringp(self.pSound):
            R().sound.play_file(self.pChannel, self.pSound)
        else:
            R().sound.puppet(self.pChannel, self.pSound)
        M.addUpdateList(self)

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


# ============================================================================================
# OBJECT_GROUP  (ParentScript 71)
# ============================================================================================

@lingo_script('OBJECT_GROUP')
class ObjectGroup(LObject):
    def __init__(self):
        self.pName = None
        self.pObjectList = []
        self.pCount = 0
        self.pParent = 0
        self.pSavedList = []
        self.pSpriteDepth = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        # Lingo (as decompiled): `if pSpriteDepth then getObjectList(list, alloc) else getObjectList(list, alloc, pSpriteDepth)`
        # -- either way the depth is 0/void, so every object takes its own sprites from the allocation.
        self.pObjectList = get_object_list(self.pObjectList, theSpriteAlloc)
        self.pCount = 0
        self.pSavedList = [Sym('pCount')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self): pass

    def mSetParent(self, theObject):
        call_all(self.pObjectList, 'mSetParent', None)       # (the Lingo `call(#mSetParent, pObjectList)` passes no parent)

    def mLoad(self): call_all(self.pObjectList, 'mLoad')
    def mLoadList(self, theList): call_all(self.pObjectList, 'mLoadList', theList)

    def mUnLoad(self): _unload_all(self.pObjectList)
    mUnload = mUnLoad

    def mGetType(self): return Sym('OBJECT_GROUP')
    def mGetName(self): return self.pName

    def mLoadNextObject(self):
        daIndex = (self.pCount % len(self.pObjectList)) + 1
        self.pObjectList[daIndex - 1].mLoad()

    def mNextObject(self):
        daIndex = (self.pCount % len(self.pObjectList)) + 1
        self.pCount = self.pCount + 1
        return self.pObjectList[daIndex - 1]

    def mBelongsToGroup(self, theObject):
        return _get_pos(self.pObjectList, theObject)

    def mGetObjectAt(self, theIndex):
        # (decompiled as `theIndex > (0 && theIndex) <= count`: the bounds check 0 < theIndex <= count)
        if 0 < theIndex <= len(self.pObjectList):
            return self.pObjectList[theIndex - 1]
        return 0


# ============================================================================================
# REG_MAP  (ParentScript 31) / ALERT_HOOK  (ParentScript 25)
# ============================================================================================

@lingo_script('REG_MAP')
class RegMap(LObject):
    """dosReadReg / dosWriteReg / dosDeleteReg (the Windows registry xtra) have no use in the port: reads give EMPTY."""

    def __init__(self, theBranch=None, thePath=None):
        self.pRegBranch = theBranch
        self.pRegPath = thePath
        self._vals = {}

    def mDestroy(self): pass
    def mGetRegVal(self, theKey): return self._vals.get(theKey, '')
    def mSetRegVal(self, theKey, theVal): self._vals[theKey] = theVal
    def mDeleteRegKey(self, theKey): self._vals.pop(theKey, None)


@lingo_script('ALERT_HOOK')
class AlertHook(LObject):
    def alertHook(self, err, Msg, thirdParam=None):
        daMessage = 'err = %s , message =  %s' % (err, Msg)
        if thirdParam is not None:
            daMessage = '%s %s' % (daMessage, thirdParam)
        print('[alert]', daMessage, flush=True)
        return 1
