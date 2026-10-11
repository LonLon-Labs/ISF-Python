"""Hand-ported parent scripts, part 3: animation mover, opening animation, skeleton/main buttons,
TokenCollector, quit dialogue and the MAIN / DOOR / NAV screens.

Direct translations of ParentScripts 104, 111, 79, 74, 26, 185, 43, 47 and 44.
"""
import math

from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, Point, set_properties, pop_one, random_, ease
from .ui import R, S, load_mem, call_all, set_behavior, remove_behavior, blank


def _alive(o):
    return isinstance(o, LObject)


def _ver():
    return str(M.gScreenDaddy.mGetCurrentVersion()).lower()


def _get_dist(p):
    return math.sqrt(p[0] * p[0] + p[1] * p[1])


def _call_if(o, name, *a):
    fn = getattr(o, name, None) if _alive(o) else None
    return fn(*a) if fn else None


def _new(ref, *a):
    from .core import new_script
    return new_script(ref, *a)


# ============================================================================================
# ANIM_MOVE (104): slides a sprite from where it is to pStopLoc at pPixelsPerSecond
# ============================================================================================

@lingo_script('ANIM_MOVE')
class AnimMove(LObject):
    def __init__(self, theSprite=None, theParent=None):
        self.pParent = theParent
        self.pSprite = theSprite
        self.pPixelsPerSecond = 100
        self.pLastUpdate = R().milliseconds()
        self.pSpeed = 1000 // 30
        self.pStartTime = 0
        self.pEaseFlag = 0
        self.pMoveObject = 0
        self.pNewLoc = Point(0, 0)
        self.pInk = None
        self.mSetMinimumDistance()

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pSprite = pop_one(alloc)
        self.mSetMinimumDistance()

    def mSetMinimumDistance(self):
        v = self.pPixelsPerSecond / (self.pSpeed * 1.0)
        self.pMinimumDist = _get_dist(Point(v, v))

    def mDestroy(self): pass
    def mSetReturnLoc(self, p): self.pStopLoc = p
    def mSetMember(self, m): self.pMember = m
    def mSetStartLoc(self, p): self.pStartLoc = p
    def mSetMoveObject(self, o): self.pMoveObject = o
    def mClearMoveObject(self): self.pMoveObject = 0
    def mSetParent(self, o): self.pParent = o
    def mGetType(self): return Sym('ANIM_MOVE')
    def mGetName(self): return self.pName
    def mSetEventTag(self, t): self.pEventTag = t
    def mGetEventTag(self): return self.pEventTag
    def mLoad(self): load_mem(self.pSound); load_mem(self.pMember)
    def mLoadList(self, lst): lst.append(self.pSound); lst.append(self.pMember)
    def mUnload(self): pass

    def mShow(self):
        s = S(self.pSprite)
        s.member = self.pMember
        s.loc = self.pStartLoc
        # The data carries #pInk (36 for the gates/letters) but the Lingo never applies it here; the
        # ripped PNGs keep their white background, so honour the data.
        if self.pInk is not None:
            s.ink = self.pInk

    def mHide(self):
        S(self.pSprite).member = 1

    def mPlay(self):
        rt = R()
        if self.pSound:
            rt.sound.puppet(self.pSoundChannel, self.pSound)
        s = S(self.pSprite)
        self.pStartLoc = s.loc
        self.pStartH, self.pStartV = s.loc[0], s.loc[1]
        self.pCurrH, self.pCurrV = self.pStartH, self.pStartV
        self.pHDist = self.pStopLoc[0] - s.loc[0]
        self.pVDist = self.pStopLoc[1] - s.loc[1]
        d = _get_dist(Point(s.loc[0] - self.pStopLoc[0], s.loc[1] - self.pStopLoc[1])) * 1.0
        if d <= self.pMinimumDist:
            s.loc = self.pStopLoc
            if self.pParent:
                self.pParent.mPlayDone(self)
            return
        self.pTotalMilliSeconds = d / self.pPixelsPerSecond * 1000
        self.pStartTime = rt.milliseconds() * 1.0
        self.pLastUpdate = rt.milliseconds() - self.pSpeed
        M.addUpdateList(self)

    def mStop(self):
        M.removeUpdateList(self)

    def mUpdate(self):
        rt = R()
        now = rt.milliseconds()
        if now - self.pLastUpdate >= self.pSpeed:
            self.pLastUpdate = now
            pct = (now - self.pStartTime) / self.pTotalMilliSeconds
            s = S(self.pSprite)
            d = _get_dist(Point(s.loc[0] - self.pStopLoc[0], s.loc[1] - self.pStopLoc[1]))
            if d <= self.pMinimumDist or pct > 1:
                if _alive(self.pMoveObject):
                    self.pMoveObject.mSetLoc(self.pStopLoc)
                else:
                    s.loc = self.pStopLoc
                M.removeUpdateList(self)
                if self.pParent:
                    self.pParent.mPlayDone(self)
            else:
                if self.pEaseFlag:
                    pct = ease(pct)
                self.pCurrH = self.pStartH + self.pHDist * pct
                self.pCurrV = self.pStartV + self.pVDist * pct
                self.pNewLoc = Point(self.pCurrH, self.pCurrV)
                if _alive(self.pMoveObject):
                    self.pParent.mSetLoc(Point(int(self.pCurrH), int(self.pCurrV)))
                else:
                    s.loc = self.pNewLoc


# ============================================================================================
# OPENING_ANIM (111): the gates opening on the main screen
# ============================================================================================

@lingo_script('OPENING_ANIM')
class OpeningAnim(LObject):
    def __init__(self):
        self.pParent = 0
        self.pEnabled = 1

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pBackAnimObj = get_object(self.pBackAnimObj, alloc)
        self.pLeftGateAnimObj = get_object(self.pLeftGateAnimObj, alloc)
        self.pRightGateAnimObj = get_object(self.pRightGateAnimObj, alloc)
        self.pLetterObjectList = get_object_list(self.pLetterObjectList, alloc)
        self.pPostsSprite = pop_one(alloc)
        self.pSpiderAnimObj = get_object(self.pSpiderAnimObj, alloc)
        self.pSkeletonEmergeAnim = get_object(self.pSkeletonEmergeAnim, alloc)
        self.pGateOpenTimer = get_object(self.pGateOpenTimer, [])
        self.pGoDoorTimer = get_object(self.pGoDoorTimer, [])
        for o in (self.pBackAnimObj, self.pSpiderAnimObj, self.pLeftGateAnimObj, self.pRightGateAnimObj,
                  self.pSkeletonEmergeAnim, self.pGateOpenTimer, self.pGoDoorTimer):
            o.mSetParent(self)
        call_all(self.pLetterObjectList, 'mSetParent', self)
        self.pEnterVO = 'ENTERV.AIF'
        self.pEnabled = 1
        return self

    def mSetLetters(self):
        name = M.gPlayer
        n = len(name)
        start = (10 - n) // 2 + 1
        for ctr in range(1, n + 1):
            m = self.pLetterLookupList.get(name[ctr - 1].upper(), 305)
            idx = start + ctr - 2
            if 0 <= idx < len(self.pLetterObjectList):
                self.pLetterObjectList[idx].mSetMember(m)

    def mDestroy(self): pass
    def mGetEnabled(self): return self.pEnabled
    def mEnable(self): self.pEnabled = 1
    def mDisable(self): self.pEnabled = 0
    def mGetType(self): return Sym('OPENING_ANIM')
    def mGetName(self): return self.pName
    def mSetParent(self, o): self.pParent = o

    def mInitPoolObjects(self):
        self.pSound = M.getSoundObject(2, self.pSound, self)
        self.pEnterVO = M.getExSoundObject(2, self.pEnterVO, self)

    def mReleasePoolObjects(self):
        self.pEnterVO = M.recycleSoundObject(self.pEnterVO)
        self.pSound = M.recycleSoundObject(self.pSound)

    def mLoad(self):
        load_mem(self.pSound)
        load_mem(self.pPostsMember)
        self.pSpiderAnimObj.mLoad()

    def mLoadList(self, lst):
        lst.append(self.pSound)
        lst.append(self.pPostsMember)
        for o in (self.pSpiderAnimObj, self.pBackAnimObj, self.pLeftGateAnimObj,
                  self.pRightGateAnimObj, self.pSkeletonEmergeAnim):
            o.mLoadList(lst)

    def mUnload(self):
        for o in (self.pSpiderAnimObj, self.pBackAnimObj, self.pLeftGateAnimObj,
                  self.pRightGateAnimObj, self.pSkeletonEmergeAnim):
            o.mUnload()

    def mShow(self):
        self.mSetLetters()
        M.setMember(self.pPostsSprite, self.pPostsMember)
        S(self.pPostsSprite).ink = 36
        self.pBackAnimObj.mShow()
        self.pSpiderAnimObj.mShow()
        self.pLeftGateAnimObj.mShow()
        self.pRightGateAnimObj.mShow()
        call_all(self.pLetterObjectList, 'mShow')
        self.pEnabled = 1

    def mPlay(self):
        self.pSpiderAnimObj.mPlay()

    def mPlayDone(self, o):
        if o is self.pSpiderAnimObj:
            self.pBackAnimObj.mPlay()
        elif o is self.pBackAnimObj:
            self.pSound.mPlay()
            self.pGateOpenTimer.mPlay()
            self.pGoDoorTimer.mPlay()
        elif o is self.pGateOpenTimer:
            self.pGateOpenTimer.mDisable()
            self.pLeftGateAnimObj.mPlay()
            self.pRightGateAnimObj.mPlay()
            call_all(self.pLetterObjectList, 'mPlay')
        elif o is self.pGoDoorTimer:
            self.pGoDoorTimer.mDisable()
            blank(self.pPostsSprite)
            self.pBackAnimObj.mHide()
            self.pSpiderAnimObj.mHide()
            self.pLeftGateAnimObj.mHide()
            self.pRightGateAnimObj.mHide()
            call_all(self.pLetterObjectList, 'mHide')
        elif o is self.pSound:
            self.pEnterVO.mPlay()
            self.pSkeletonEmergeAnim.mPlay()
        elif o is self.pEnterVO:
            pass
        elif o is self.pSkeletonEmergeAnim:
            self.pSkeletonEmergeAnim.mHide()
            if self.pParent:
                self.pParent.mPlayDone(self)

    def mHide(self):
        self.pGateOpenTimer.mStop()
        M.removeUpdateList(self.pGateOpenTimer)
        self.pGoDoorTimer.mStop()
        M.removeUpdateList(self.pGoDoorTimer)
        blank(self.pPostsSprite)
        for o in (self.pBackAnimObj, self.pSpiderAnimObj, self.pLeftGateAnimObj,
                  self.pRightGateAnimObj, self.pSkeletonEmergeAnim):
            o.mHide()
        call_all(self.pLetterObjectList, 'mHide')
        self.pEnabled = 0


# ============================================================================================
# buttons
# ============================================================================================

@lingo_script('BUTT_SKELLY')                             # ParentScript 79
class ButtSkelly(LObject):
    def __init__(self):
        self.pParent = 0
        self.pCurrentAnimObject = 0
        self.pDownFlag = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pAnimSprite = pop_one(alloc)
        self.pIdleAnimationObject = get_object(self.pIdleAnimationObject, [self.pAnimSprite])
        self.pDownAnimObject = get_object(self.pDownAnimObject, [self.pAnimSprite])
        self.pIdleAnimationObject.mSetParent(self)
        self.pDownAnimObject.mSetParent(self)
        self.pTimerObject = _new(self.pTimerScriptNumber)
        self.pTimerObject.mSetParent(self)
        self.pTimerObject.pTimeOutLength = 4000
        self.pCurrentAnimObject = 0
        self.pEnabled = 1
        self.pSavedList = []
        self.pDebug = 0
        return self

    def mInitPoolObjects(self):
        if self.pScareVO != 0:
            self.pScareVO = M.getExSoundObject(2, self.pScareVO, self)

    def mReleasePoolObjects(self):
        if self.pScareVO != 0:
            self.pScareVO = M.recycleSoundObject(self.pScareVO)

    def mShow(self):
        set_behavior(self.pAnimSprite, self)
        self.pIdleAnimationObject.mShow()

    def mPlay(self):
        self.pCurrentAnimObject = self.pTimerObject
        self.pTimerObject.mPlay()

    def mHide(self):
        if _alive(self.pCurrentAnimObject):
            self.pCurrentAnimObject.mKill()
            if self.pCurrentAnimObject is not self.pTimerObject:
                self.pCurrentAnimObject.mHide()
            self.pCurrentAnimObject = 0

    def mDestroy(self): pass
    def mSetParent(self, o): self.pParent = o
    def mGetType(self): return Sym('BUTT_SKELLY')
    def mGetName(self): return self.pName
    def mLoad(self): self.pIdleAnimationObject.mLoad(); self.pDownAnimObject.mLoad()
    def mLoadList(self, lst): self.pIdleAnimationObject.mLoadList(lst); self.pDownAnimObject.mLoadList(lst)
    def mUnload(self): self.pIdleAnimationObject.mUnload(); self.pDownAnimObject.mUnload()

    def mouseDown(self):
        self.pDownFlag = 1
        if _alive(self.pCurrentAnimObject):
            self.pCurrentAnimObject.mKill()
            if self.pCurrentAnimObject is not self.pTimerObject:
                self.pCurrentAnimObject.mHide()
        M.waitCursor()
        self.pTimerObject.mKill()
        self.pCurrentAnimObject = self.pDownAnimObject
        self.pCurrentAnimObject.mShow()
        self.pCurrentAnimObject.mPlay()
        if self.pScareVO != 0:
            self.pScareVO.mPlay()
        M.disableGame()

    def mPlayDone(self, o):
        if o is self.pIdleAnimationObject:
            self.pCurrentAnimObject = self.pTimerObject
            self.pTimerObject.mReset()
            self.pTimerObject.mPlay()
        elif o is self.pTimerObject:
            self.pCurrentAnimObject = self.pIdleAnimationObject
            self.pCurrentAnimObject.mShow()
            self.pCurrentAnimObject.mPlay()
        elif o is self.pScareVO:
            self.pParent.mButtonActivated(self)
        elif o is self.pDownAnimObject:
            if self.pScareVO == 0:
                self.pParent.mButtonActivated(self)

    def mEnable(self):
        self.pCurrentAnimObject = self.pTimerObject
        self.pTimerObject.mReset()
        self.pTimerObject.mPlay()
        set_behavior(self.pAnimSprite, self)

    def mDisable(self):
        if self.pCurrentAnimObject is self.pIdleAnimationObject:
            self.pCurrentAnimObject.mKill()
        elif self.pCurrentAnimObject == 0:
            self.pTimerObject.mKill()
        remove_behavior(self.pAnimSprite, self)


@lingo_script('BUTT_MAIN')                               # ParentScript 74
class ButtMain(LObject):
    def __init__(self):
        self.pParent = 0
        self.pCurrentAnimObject = 0
        self.pDownFlag = 0
        self.pActivateFlag = 0
        self.pRollOn = 0
        self.pHasRolledOn = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pSprite = pop_one(alloc)
        self.pAnimSprite = pop_one(alloc)
        self.pRollOnAnimObject = get_object(self.pRollOnAnimObject, [self.pAnimSprite])
        self.pRollOffAnimObject = get_object(self.pRollOffAnimObject, [self.pAnimSprite])
        self.pDownAnimObject = get_object(self.pDownAnimObject, [self.pAnimSprite])
        self.pRollOnAnimObject.mSetParent(self)
        self.pRollOffAnimObject.mSetParent(self)
        self.pDownAnimObject.mSetParent(self)
        self.pRollOnSound = self.pRollOnAnimObject.pAnimSound
        self.pCurrentAnimObject = 0
        self.pDownFlag = 0
        self.pActivateFlag = 0
        self.pRollOn = 0
        self.pEnabled = 1
        self.pSavedList = []
        self.pHasRolledOn = 0
        self.pDebug = 0
        return self

    def mDestroy(self): pass
    def mSetParent(self, o): self.pParent = o
    def mGetType(self): return Sym('BUTT_MAIN')
    def mGetName(self): return self.pName

    def mLoad(self):
        load_mem(self.pNeutMember)
        for o in (self.pRollOnAnimObject, self.pRollOffAnimObject, self.pDownAnimObject):
            o.mLoad()

    def mLoadList(self, lst):
        lst.append(self.pNeutMember)
        for o in (self.pRollOnAnimObject, self.pRollOffAnimObject, self.pDownAnimObject):
            o.mLoadList(lst)

    def mUnload(self):
        for o in (self.pRollOnAnimObject, self.pRollOffAnimObject, self.pDownAnimObject):
            o.mUnload()

    def _drop_current(self):
        if _alive(self.pCurrentAnimObject):
            self.pCurrentAnimObject.mStop()
            self.pCurrentAnimObject.mHide()

    def mouseDown(self):
        self.pDownFlag = 1
        self._drop_current()
        self.pCurrentAnimObject = self.pDownAnimObject
        self.pCurrentAnimObject.mShow()
        self.pCurrentAnimObject.mPlay()
        M.disableGame()
        self.mEnable()

    def mouseUp(self):
        if self.pDownFlag:
            self.pDownFlag = 0
            M.waitCursor()
            self.mDisable()
            if M.isUpdating(self.pDownAnimObject):
                self.pActivateFlag = 1
            else:
                self.pParent.mButtonActivated(self)

    def mouseUpOutSide(self):
        if self.pDownFlag:
            self.pDownFlag = 0
            self.pActivateFlag = 0
            M.enableGame()
            self._drop_current()
            self.pCurrentAnimObject = 0

    def mouseEnter(self):
        self.pRollOn = 1
        if not self.pDownFlag and not self.pCurrentAnimObject:
            self.pHasRolledOn = 1
            lame = M.gUserHasLamePC and R().sound.busy(2)
            self.pRollOnAnimObject.pAnimSound = 0 if lame else self.pRollOnSound
            self.pCurrentAnimObject = self.pRollOnAnimObject
            self.pCurrentAnimObject.mShow()
            self.pCurrentAnimObject.mPlay()

    def mouseLeave(self):
        self.pRollOn = 0
        if self.pHasRolledOn and not self.pDownFlag and not self.pCurrentAnimObject:
            self.pCurrentAnimObject = self.pRollOffAnimObject
            self.pCurrentAnimObject.mShow()
            self.pCurrentAnimObject.mPlay()

    def mPlayDone(self, o):
        if o is self.pRollOffAnimObject:
            self.pCurrentAnimObject.mHide()
            S(self.pSprite).ink = self.pInk
            self.pCurrentAnimObject = 0
            if self.pRollOn:
                self.mouseEnter()
        elif o is self.pRollOnAnimObject:
            self.pRollOnAnimObject.mStop()
            self.pCurrentAnimObject = 0
            if not self.pRollOn:
                self.mouseLeave()
        elif o is self.pDownAnimObject:
            if self.pActivateFlag:
                self.pActivateFlag = 0
                self.pParent.mButtonActivated(self)

    def mEnable(self): set_behavior(self.pSprite, self)
    def mDisable(self): remove_behavior(self.pSprite, self)

    def mShow(self):
        s = S(self.pSprite)
        s.ink, s.loc, s.member = self.pInk, self.pLoc, self.pNeutMember
        set_behavior(self.pSprite, self)
        self.pHasRolledOn = 0

    def mHide(self):
        if _alive(self.pCurrentAnimObject):
            self.pCurrentAnimObject.mStop()
            self.pCurrentAnimObject.mHide()
            self.pCurrentAnimObject = 0
        self.pRollOffAnimObject.mHide()
        self.pDownFlag = 0
        blank(self.pSprite)


# ============================================================================================
# TokenCollector (26)
# ============================================================================================

@lingo_script('TokenCollector')
class TokenCollector(LObject):
    def __init__(self):
        self.pCollectedTokenList = []

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pCollectedTokenList = []
        self.pSavedList = [Sym('pCollectedTokenList')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self): pass
    def mGetName(self): return self.pName
    def mGetType(self): return Sym('TokenCollector')

    def mAddToken(self, t):
        if t in self.pAcceptedTokenList:
            if t not in self.pCollectedTokenList:
                self.pCollectedTokenList.append(t)
                return 1
        else:
            print('attempting to add illegal token (%s) to token collection %s' % (t, self.pName))
        return 0

    def mNextToken(self):
        n = len(self.pCollectedTokenList) + 1
        if n < len(self.pAcceptedTokenList):
            return self.pAcceptedTokenList[n - 1]
        return self.pAcceptedTokenList[-1]

    def mREmoveToken(self, t):
        if t in self.pCollectedTokenList:
            self.pCollectedTokenList.remove(t)

    mRemoveToken = mREmoveToken

    def mTokenFoundCount(self): return len(self.pCollectedTokenList)

    def mTokenFound(self, t):
        return (self.pCollectedTokenList.index(t) + 1) if t in self.pCollectedTokenList else 0

    def mIsComplete(self):
        return len(self.pAcceptedTokenList) == len(self.pCollectedTokenList)

    def mRemainingTokenCount(self):
        return len(self.pAcceptedTokenList) - len(self.pCollectedTokenList)


# ============================================================================================
# QUIT_DIALOGUE (185)
# ============================================================================================

@lingo_script('QUIT_DIALOGUE')
class QuitDialogue(LObject):
    def __init__(self):
        self.pStashedYesRollSound = self.pStashedNoRollSound = self.pStashedCreditRollSound = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pBGSprite = pop_one(alloc)
        self.pYesButton = get_object(self.pYesButton, alloc)
        self.pNoButton = get_object(self.pNoButton, alloc)
        self.pCreditsButton = get_object(self.pCreditsButton, alloc)
        self.pYesButton.mSetParent(self)
        self.pNoButton.mSetParent(self)
        if _alive(self.pCreditsButton):
            self.pCreditsButton.mSetParent(self)
        self.pStashedYesRollSound = self.pStashedNoRollSound = self.pStashedCreditRollSound = 0
        return self

    def mDestroy(self): pass

    def _buttons(self):
        b = [self.pYesButton, self.pNoButton]
        if _alive(self.pCreditsButton):
            b.append(self.pCreditsButton)
        return b

    def mLoad(self):
        for b in self._buttons():
            b.mLoad()
        load_mem(self.pBGMember)

    def mLoadList(self, lst):
        for b in self._buttons():
            b.mLoadList(lst)
        lst.append(self.pBGMember)

    def mUnload(self):
        for b in self._buttons():
            b.mUnload()

    def mShow(self):
        M.resetCursor()
        self.pPromptSound = M.getSoundObject(2, self.pPromptSound, self)
        M.setMember(self.pBGSprite, self.pBGMember)
        self.pStashedYesRollSound = self.pYesButton.pRollSound
        self.pStashedNoRollSound = self.pNoButton.pRollSound
        self.pYesButton.pRollSound = 0
        self.pNoButton.pRollSound = 0
        if _alive(self.pCreditsButton):
            self.pStashedCreditRollSound = self.pCreditsButton.pRollSound
            self.pCreditsButton.pRollSound = 0
        for b in self._buttons():
            b.mShow()
        M.setInterruptMode(self.pPromptSound)
        self.pPromptSound.mPlay()

    def mPlayDone(self, o):
        self.pPromptSound = M.recycleSoundObject(self.pPromptSound)
        self.pYesButton.pRollSound = self.pStashedYesRollSound
        self.pNoButton.pRollSound = self.pStashedNoRollSound
        if _alive(self.pCreditsButton):
            self.pCreditsButton.pRollSound = self.pStashedCreditRollSound
        M.clearInterruptMode()

    def mButtonActivated(self, o):
        if o is self.pYesButton:
            self.mHide()
            M.doshutDown()
        elif o is self.pNoButton:
            self.mHide()
            M.enableGame()
        elif o is self.pCreditsButton:
            self.mHide()
            M.gScreenDaddy.mSetCreditReturn(M.gCurScreen.pName)
            M.gScreenDaddy.mNavigate(Sym('credit'), 1)

    def mHide(self):
        for b in self._buttons():
            b.mHide()
        blank(self.pBGSprite)


# ============================================================================================
# screens
# ============================================================================================

@lingo_script('SCREEN_MAIN')                             # ParentScript 43
class ScreenMain(LObject):
    def __init__(self):
        self.pEnabled = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pSprite = pop_one(alloc)
        self.pButtList = get_object_list(self.pButtList, alloc)
        call_all(self.pButtList, 'mSetParent', self)
        self.pOpenAnim = get_object(self.pOpenAnim, alloc)
        _call_if(self.pOpenAnim, 'mSetParent', self)
        self.pOpenAnimPlayed = 0
        self.pSavedList = []
        self.pEnabled = 0
        self.pCurrentSkellyButton = 0
        self.pStopButt = get_object(self.pStopButt, alloc)
        _call_if(self.pStopButt, 'mSetParent', self)
        return self

    def mInitPoolObjects(self):
        self.pOpenAnim.mInitPoolObjects()
        for b in self.pButtList:
            _call_if(b, 'mInitPoolObjects')

    def mReleasePoolObjects(self):
        self.pOpenAnim.mReleasePoolObjects()
        for b in self.pButtList:
            _call_if(b, 'mReleasePoolObjects')

    def mDestroy(self): pass
    def mGetEnabled(self): return self.pEnabled
    def mGetType(self): return Sym('SCREEN_MAIN')
    def mGetName(self): return self.pName
    def mGetHelpState(self): return 0
    def mApplicationActivated(self): pass
    def mApplicationDeactivated(self): pass
    def mUpdate(self): pass
    def mShowSkellyButt(self): pass
    def mButtonDeActivated(self, o): pass

    def mShow(self):
        gd = M.gScreenDaddy
        if not gd.pOpenAnimPlayed:
            M.setMember(self.pSprite, self.pBGMember)
            self.pOpenAnim.mShow()
            gd.mSetDisableUpdateMode()
            M.FadeInAmbientSound(self.pAmbientAudio, 3000)
            self.pOpenAnim.mPlay()
            gd.pOpenAnimPlayed = 1
            return 1
        self.mShowGraphics()
        self.mShowSkellyButt()
        if _ver() != 'a':
            self.pStopButt.mShow()
        return 0

    def mShowGraphics(self):
        M.setMember(self.pSprite, self.pBGMember)
        call_all(self.pButtList, 'mShow')
        call_all(self.pButtList, 'mPlay')
        self.pEnabled = 1
        M.resetCursor()
        if _ver() != 'a':
            M.FadeInAmbientSound(self.pAmbientAudio, 1000)
        else:
            M.FadeInAmbientSound(self.pAmbientAudio, 0)

    def mHide(self):
        call_all(self.pButtList, 'mHide')
        blank(self.pSprite)
        self.pEnabled = 0
        _call_if(self.pStopButt, 'mHide')

    def mLoad(self):
        load_mem(self.pBGMember)
        if not self.pOpenAnimPlayed:
            self.pOpenAnim.mLoad()
        load_mem(self.pAmbientAudio)
        _call_if(self.pStopButt, 'mLoad')

    def mLoadList(self, lst):
        _call_if(self.pStopButt, 'mLoadList', lst)
        lst.append(self.pBGMember)
        if not self.pOpenAnimPlayed:
            self.pOpenAnim.mLoadList(lst)
        lst.append(self.pAmbientAudio)

    def mUnload(self):
        _call_if(self.pStopButt, 'mUnload')
        call_all(self.pButtList, 'mUnload')
        _call_if(self.pOpenAnim, 'mUnload')

    def mCheckKey(self, keycode):
        if self.pEnabled:
            M.QuitKeyCheck(keycode, 1)

    def mButtonActivated(self, o):
        if o is self.pStopButt:
            M.quitDialogue()
        else:
            M.gScreenDaddy.mNavigate(Sym('DOOR'))

    def mDisable(self):
        _call_if(self.pStopButt, 'mDisable')
        call_all(self.pButtList, 'mDisable')
        self.pEnabled = 0

    def mEnable(self):
        _call_if(self.pStopButt, 'mEnable')
        call_all(self.pButtList, 'mEnable')
        self.pEnabled = 1

    def mPlayDone(self, o):
        if o is self.pOpenAnim:
            self.pOpenAnim.mHide()
            self.pOpenAnim.mUnload()
            self.mShowGraphics()
            self.mShowSkellyButt()
            M.resetCursor()


@lingo_script('SCREEN_NAV')                              # ParentScript 44
class ScreenNav(LObject):
    def __init__(self):
        self.pEnabled = 1
        self.pHelpButton = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pSprite = pop_one(alloc)
        self.pButtList = get_object_list(self.pButtList, alloc)
        self.pSHTokenObjectList = get_object_list(self.pSHTokenObjectList, alloc)
        call_all(self.pButtList, 'mSetParent', self)
        call_all(self.pSHTokenObjectList, 'mSetParent', self)
        self.pBackButton = get_object(self.pBackButton, alloc)
        if _alive(self.pBackButton):
            self.pBackButton.mSetParent(self)
        self.pHelpButton = 0
        self.pEnabled = 1
        return self

    def mDestroy(self): pass
    def mGetEnabled(self): return self.pEnabled
    def mGetType(self): return Sym('SCREEN_NAV')
    def mGetName(self): return self.pName
    def mGetHelpState(self): return 0
    def mApplicationActivated(self): pass
    def mApplicationDeactivated(self): pass
    def mButtonDeActivated(self, o): pass
    def mHuntObjectFound(self, o): self.mEnable()

    def mInitPoolObjects(self):
        M.gScreenDaddy.mInitScavengerHuntPoolObjects()
        self.pHelpButton = M.getGameHelpButton()
        self.pHelpButton.mSetParent(self)
        if not _alive(self.pBackButton):
            self.pBackButton = M.getGameBackButton()
            self.pBackButton.mSetParent(self)

    def mReleasePoolObjects(self):
        M.gScreenDaddy.mReleaseScavengerHuntPoolObjects()

    def mLoad(self):
        call_all(self.pSHTokenObjectList, 'mLoad')
        M.gScreenDaddy.mLoadScavengerHunt()
        load_mem(self.pAmbientAudio)
        call_all(self.pButtList, 'mLoad')
        load_mem(self.pBGMember)

    def mLoadList(self, lst):
        call_all(self.pSHTokenObjectList, 'mLoadList', lst)
        M.gScreenDaddy.mLoadScavengerHuntlist(lst)
        lst.append(self.pAmbientAudio)
        call_all(self.pButtList, 'mLoadList', lst)
        lst.append(self.pBGMember)

    def mUnload(self):
        M.gScreenDaddy.mUnloadScavengerHunt()
        call_all(self.pSHTokenObjectList, 'mUnload')
        call_all(self.pButtList, 'mUnload')

    def mCheckKey(self, keycode):
        if self.pEnabled:
            M.QuitKeyCheck(keycode, 1)

    def mShow(self):
        M.gScreenDaddy.mShowScavengerHunt()
        _call_if(self.pHelpButton, 'mShow')
        _call_if(self.pBackButton, 'mShow')
        M.setMember(self.pSprite, self.pBGMember)
        call_all(self.pButtList, 'mShow')
        call_all(self.pSHTokenObjectList, 'mShow')
        M.FadeInAmbientSound(self.pAmbientAudio)
        self.pEnabled = 1
        if not M.gScreenDaddy.mCheckStatus():
            M.resetCursor()

    def mHide(self):
        _call_if(self.pHelpButton, 'mHide')
        _call_if(self.pBackButton, 'mHide')
        call_all(self.pButtList, 'mHide')
        call_all(self.pSHTokenObjectList, 'mHide')
        blank(self.pSprite)
        M.gScreenDaddy.mHideScavengerHunt()
        self.pEnabled = 0

    def mButtonActivated(self, o):
        gd = M.gScreenDaddy
        if o is self.pHelpButton:
            gd.pHelpPlayer.mStartHelp()
        elif o is self.pBackButton:
            M.navigateBack()
        elif o in self.pSHTokenObjectList:
            gd.mExternalSHTokenFound(o)
        else:
            M.navigate(o.pDestination)

    def mEnable(self):
        self.pEnabled = 1
        _call_if(self.pHelpButton, 'mEnable')
        _call_if(self.pBackButton, 'mEnable')
        call_all(self.pButtList, 'mEnable')
        call_all(self.pSHTokenObjectList, 'mEnable')

    def mDisable(self):
        self.pEnabled = 0
        _call_if(self.pHelpButton, 'mDisable')
        _call_if(self.pBackButton, 'mDisable')
        call_all(self.pButtList, 'mDisable')
        call_all(self.pSHTokenObjectList, 'mDisable')


@lingo_script('SCREEN_DOOR')                             # ParentScript 47
class ScreenDoor(LObject):
    def __init__(self):
        self.pEnabled = 1
        self.pHouseEntered = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pSprite = pop_one(alloc)
        self.pSHTokenObjectList = get_object_list(self.pSHTokenObjectList, alloc)
        self.pDoorAnim = get_object(self.pDoorAnim, alloc)
        self.pButtList = get_object_list(self.pButtList, alloc)
        self.pTurnAroundButton = get_object(self.pTurnAroundButton, alloc)
        self.pSecretAnim = get_object(self.pSecretAnim, alloc)
        self.pKnobButt = get_object(self.pKnobButt, alloc)
        self.pStopButt = get_object(self.pStopButt, alloc)
        call_all(self.pButtList, 'mSetParent', self)
        call_all(self.pSHTokenObjectList, 'mSetParent', self)
        for o in (self.pTurnAroundButton, self.pDoorAnim, self.pSecretAnim, self.pKnobButt, self.pStopButt):
            o.mSetParent(self)
        self.pHelpButton = get_object(M.getGameHelpButton(), alloc)
        self.pHelpButton.mSetParent(self)
        self.pEnabled = 1
        self.pHouseEntered = 0
        self.pSavedList = [Sym('pHouseEntered')]
        M.addObjectGlob(self)
        self.pAudio1 = self.pAudio2 = self.pKnobVO = self.pNavAudio = 0
        self.pReturnVOplayed = 0
        self.pReturnVO = 0
        return self

    def mDestroy(self): pass
    def mGetEnabled(self): return self.pEnabled
    def mGetType(self): return Sym('SCREEN_DOOR')
    def mGetName(self): return self.pName
    def mGetHelpState(self): return 0
    def mApplicationActivated(self): pass
    def mApplicationDeactivated(self): pass
    def mButtonDeActivated(self, o): pass
    def mHuntObjectFound(self, o): self.mEnable()

    def mInitPoolObjects(self):
        M.gScreenDaddy.mInitScavengerHuntPoolObjects()
        self.pAudio1 = M.getExSoundObject(2, self.pAudioList[0], self)
        self.pAudio2 = M.getExSoundObject(2, self.pAudioList[1], self)
        self.pKnobVO = M.getExSoundObject(2, self.pAudioList[2], self)
        self.pNavAudio = M.getSoundObject(2, self.pAudioList[3], self)
        self.pReturnVO = M.getExSoundObject(2, self.pReturnVOlist[random_(len(self.pReturnVOlist)) - 1], self)

    def mReleasePoolObjects(self):
        self.pAudio1 = M.recycleSoundObject(self.pAudio1)
        self.pAudio2 = M.recycleSoundObject(self.pAudio2)
        self.pKnobVO = M.recycleSoundObject(self.pKnobVO)
        self.pNavAudio = M.recycleSoundObject(self.pNavAudio)
        self.pReturnVO = M.recycleSoundObject(self.pReturnVO)
        M.gScreenDaddy.mReleaseScavengerHuntPoolObjects()

    def mLoad(self):
        call_all(self.pButtList, 'mLoad')
        call_all(self.pSHTokenObjectList, 'mLoad')
        M.gScreenDaddy.mLoadScavengerHunt()
        load_mem(self.pAmbientAudio)
        load_mem(self.pBGMember)

    def mLoadList(self, lst):
        call_all(self.pSHTokenObjectList, 'mLoadList', lst)
        call_all(self.pButtList, 'mLoadList', lst)
        M.gScreenDaddy.mLoadScavengerHuntlist(lst)
        lst.append(self.pTurnAroundButton)
        lst.append(self.pAmbientAudio)
        lst.append(self.pBGMember)
        lst.append(self.pKnobVO)
        lst.append(self.pKnobButt)
        if self.pHouseEntered == 0:
            for x in (self.pFoyerMember, self.pAudio1, self.pAudio2, self.pDoorAnim, self.pSecretAnim, self.pNavAudio):
                lst.append(x)
        if self.pReturnVOplayed == 0:
            lst.append(self.pReturnVO)

    def mUnload(self):
        call_all(self.pSHTokenObjectList, 'mUnload')
        call_all(self.pButtList, 'mUnload')
        M.gScreenDaddy.mUnloadScavengerHunt()
        self.pDoorAnim.mUnload()
        self.pSecretAnim.mUnload()

    def mCheckKey(self, keycode):
        if self.pEnabled:
            M.QuitKeyCheck(keycode, 1)

    def mShow(self):
        gd = M.gScreenDaddy
        if self.pHouseEntered == 1:
            self.mShowGraphics()
            self.pKnobButt.mShow()
            self.pEnabled = 1
            if not gd.mCheckStatus():
                M.resetCursor()
            if gd.mAllRiddlesSolved() == 0:
                if self.pReturnVOplayed == 0:
                    self.pReturnVO.mPlay()
                    M.setInterruptMode(self.pReturnVO)
                    self.pReturnVOplayed = 1
        else:
            self.mHouseEnter()
        M.FadeInAmbientSound(self.pAmbientAudio)

    def mShowDoorAnim(self):
        self.mShowGraphics()
        self.mDisable()
        self.pDoorAnim.mShow()

    def mShowGraphics(self):
        M.gScreenDaddy.mShowScavengerHunt()
        call_all(self.pButtList, 'mShow')
        call_all(self.pSHTokenObjectList, 'mShow')
        self.pHelpButton.mShow()
        self.pTurnAroundButton.mShow()
        M.setMember(self.pSprite, self.pBGMember)
        M.FadeInAmbientSound(self.pAmbientAudio)
        self.pStopButt.mShow()

    def mHouseEnter(self):
        self.pHouseEntered = 1
        M.setMember(self.pSprite, self.pFoyerMember)
        self.pNavAudio.mPlay()
        self.pReturnVOplayed = 1

    def _revealKnob(self):
        if not M.gScreenDaddy.mCheckStatus():
            M.resetCursor()
        self.pKnobButt.mShow()
        self.mEnable()

    def mPlayDone(self, o):
        v = _ver()
        if o is self.pKnobVO:
            M.resetCursor()
            self.mEnable()
        elif o is self.pNavAudio:
            self.mShowDoorAnim()
            if v == 'a':
                self.pAudio1.mPlay()
            elif v in ('b', 'c'):
                self.pDoorAnim.mPlay()
        elif o is self.pAudio1:
            if v == 'a':
                self.pDoorAnim.mPlay()
            elif v == 'b':
                self.pSecretAnim.mPlay()
            elif v == 'c':
                self._revealKnob()
        elif o is self.pDoorAnim:
            if v == 'a':
                self.pDoorAnim.mHide()
                self.pDoorAnim.mUnload()
                self.pAudio2.mPlay()
            elif v in ('b', 'c'):
                self.pAudio1.mPlay()
        elif o is self.pAudio2:
            if v in ('a', 'b'):
                self._revealKnob()
        elif o is self.pSecretAnim:
            if v == 'b':
                self.pAudio2.mPlay()

    def mHide(self):
        call_all(self.pSHTokenObjectList, 'mHide')
        call_all(self.pButtList, 'mHide')
        self.pHelpButton.mHide()
        self.pTurnAroundButton.mHide()
        blank(self.pSprite)
        M.gScreenDaddy.mHideScavengerHunt()
        self.pStopButt.mHide()
        self.pKnobButt.mHide()
        self.pDoorAnim.mHide()
        self.pSecretAnim.mHide()
        self.pEnabled = 0

    def mButtonActivated(self, o):
        gd = M.gScreenDaddy
        if o is self.pHelpButton:
            gd.pHelpPlayer.mStartHelp()
        elif o is self.pStopButt:
            M.quitDialogue()
        elif o is self.pKnobButt:
            M.waitCursor()
            self.mDisable()
            self.pKnobVO.mPlay()
        elif o is self.pTurnAroundButton:
            M.navigate(o.pDestination)
        elif o in self.pButtList:
            M.navigate(o.pDestination)
        elif o in self.pSHTokenObjectList:
            gd.mExternalSHTokenFound(o)

    def mEnable(self):
        self.pEnabled = 1
        call_all(self.pSHTokenObjectList, 'mEnable')
        call_all(self.pButtList, 'mEnable')
        for o in (self.pHelpButton, self.pTurnAroundButton, self.pStopButt, self.pKnobButt):
            o.mEnable()

    def mDisable(self):
        self.pEnabled = 0
        call_all(self.pSHTokenObjectList, 'mDisable')
        call_all(self.pButtList, 'mDisable')
        for o in (self.pHelpButton, self.pTurnAroundButton, self.pStopButt, self.pKnobButt):
            o.mDisable()
