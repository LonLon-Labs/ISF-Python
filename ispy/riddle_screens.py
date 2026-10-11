"""Hand-ported parent scripts, part 5: the riddle screens.

    ParentScript 45  SCREEN_RIDDLE       the riddle room: clickable objects, the riddle strip, the skeleton's reward
    ParentScript 46  SCREEN_RIDDLE_MAG   the same with a magnifying glass (`ancestor` = a SCREEN_RIDDLE)

SCREEN_RIDDLE_MAG notes (the parts Director did natively):
  * `sprite(n).ink = 9` (Mask): Director masks the sprite with the *next cast member*; here that is `pMaskMember`
    (always pMaskBackground + 1 in the data), so it is passed to the runtime as `sprite.mask_member`.
  * `member(pMaskBackground).regPoint = ...` -> runtime.set_reg_point; the parallax of the lens (pMagOffset).
  * `member(pMaskBackground).image.copyPixels(...)` -> runtime.stamp_pixels; unloadMem() -> runtime.drop_image.
  * `dosSetCursorPos(x + the stageLeft, y + the stageTop)` -> runtime.set_cursor_pos (stage coordinates).
  * `sprite(n).cursor = [25, 26] / [31, 32] / 200 / 0` -> Sprite.cursor.
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, Point, Rect, set_properties, pop_one, pop_list
from .ui import load_mem, unload_mem, set_behavior, remove_behavior, blank, _done
from .screens2 import R, S, _new, _alive, _nz, _get_pos, _inside, _sprite_rect, _symeq, _T
from .riddles import call_all, _found, _idiv


def _call_if(o, name, *a):
    """Lingo mFoo(obj, ...) on an object that may not define the handler (the call is then a no-op)."""
    fn = getattr(o, name, None) if isinstance(o, LObject) else None
    return fn(*a) if fn is not None else None


def _cursor(chan, value):
    if chan:
        S(chan).cursor = value


def _is_list(x):
    """listp(): lists and property lists."""
    return isinstance(x, (list, dict))


# ============================================================================================
# SCREEN_RIDDLE  (ParentScript 45)
# ============================================================================================

@lingo_script('SCREEN_RIDDLE')
class ScreenRiddle(LObject):
    def __init__(self):
        self._me = None
        self.pRiddleObjectList = []
        self.pRiddleWordRectList = []
        self.pSHTokenObjectList = []
        self.pNameObject = 0
        self.pSolved = 0
        self.pVisited = 0
        self.pEnabled = 0
        self.pHiddenMode = 0
        self.pParent = 0
        self.pHelpButton = 0
        self.pBackButton = 0
        self.pRiddleStripObject = 0
        self.pClueStripObject = 0
        self.pCurrRiddleObject = 0
        self.pCurrRiddleWordSound = 0
        self.pEndAniObject = 0
        self.pSkellyEndAudio = 0
        self.pCongratsAudio = 0
        self.pRiddleStripDissapearSound = 0
        self.pClueStripDissapearSound = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBGSprite = pop_one(theSpriteAlloc)
        self.pStateChangeBackAlloc = pop_list(theSpriteAlloc, 30)
        self.pRiddleObjectList = get_object_list(self.pRiddleObjectList, theSpriteAlloc)
        for daObject in self.pRiddleObjectList:
            _call_if(daObject, 'mSetBackSprite', self.pStateChangeBackAlloc)
        daMultiObjectList = []
        for daObject in self.pRiddleObjectList:
            if _T(daObject.mGetType()) == 'RIDDLE_MULTI':
                daMultiObjectList.append(daObject)
        for daObject in daMultiObjectList:
            daObject.mGrabRiddleObjects(self.pRiddleObjectList)
        daSkellySprite = pop_one(theSpriteAlloc)
        self.pSkellyAniObjectA = get_object(self.pSkellyAniObjectA, [daSkellySprite])
        self.pSkellyAniObjectB = get_object(self.pSkellyAniObjectB, [daSkellySprite])
        self.pSkellyAniObjectA.mSetParent(self._me)         # _me is still VOID here (set at the end)
        self.pSkellyAniObjectB.mSetParent(self._me)
        self.pSkellyEndAudio = 0
        self.pEndAniObject = 0
        if len(self.pSHTokenObjectList):
            self.pSHTokenObjectList = get_object_list(self.pSHTokenObjectList, theSpriteAlloc)
            call_all(self.pSHTokenObjectList, 'mSetParent', self)
            call_all(self.pSHTokenObjectList, 'mSetBackSprite', self.pStateChangeBackAlloc)
        self.pRiddleWordRectList = get_object_list(self.pRiddleWordRectList, theSpriteAlloc)
        if _is_list(self.pNameObject):
            self.pNameObject = get_object(self.pNameObject, theSpriteAlloc)
        call_all(self.pRiddleObjectList, 'mSetParent', self)
        self.pIntroRiddlesAudio = 'GL_RINTR1.AIF'
        self.pHiddenMode = 0
        self.pVisited = 0
        self.pSolved = 0
        self.pHelpButton = 0
        self.pBackButton = 0
        self.pRiddleStripObject = 0
        self.pClueStripObject = 0
        self.pCurrRiddleObject = 0
        self.pRiddleStripDissapearSound = 0
        self.pClueStripDissapearSound = 0
        self.pCongratsAudio = 0
        self.pCurrRiddleWordSound = 0
        self.pEnabled = 1
        self.pSavedList = [Sym('pSolved'), Sym('pVisited')]
        M.addObjectGlob(self)
        self._me = self
        return self

    def mDestroy(self):
        pass

    # ---- pool objects --------------------------------------------------------------------------
    def mInitPoolObjects(self):
        sd = M.gScreenDaddy
        self.pHelpButton = M.getGameHelpButton()
        self.pBackButton = M.getGameBackButton()
        self.pHelpButton.mSetParent(self)
        self.pBackButton.mSetParent(self)
        self.pRiddleStripObject = M.getGameRiddleStrip()
        self.pRiddleStripObject.mSetWordList(self.pRiddleWordRectList)
        self.pRiddleStripObject.pRiddleStripMember = self.pRiddleStripMember
        self.pRiddleStripObject.mSetParent(self._me)
        self.pRiddleStripDissapearSound = M.getSoundObject(1, self.pRiddleStripObject.pPaperSound, self._me)
        self.pFullRiddleAudio = M.getExSoundObject(2, self.pFullRiddleAudio, self._me)
        self.pClueAudio = M.getExSoundObject(2, self.pClueAudio, self._me)
        self.pIntroRiddlesAudio = M.getExSoundObject(2, self.pIntroRiddlesAudio, self._me)
        self.pSkellyEndAudio = sd.mGetEndRiddleAudio()
        self.pSkellyEndAudio = M.getExSoundObject(2, self.pSkellyEndAudio, self._me)
        self.pCongratsAudio = M.getGameCongratsAudio()
        self.pCongratsAudio = M.getSoundObject(1, self.pCongratsAudio, self._me)
        sd.mInitScavengerHuntPoolObjects()

    def mReleasePoolObjects(self):
        self.pRiddleStripDissapearSound = M.recycleSoundObject(self.pRiddleStripDissapearSound)
        self.pRiddleStripDissapearSound = 0
        self.pClueStripDissapearSound = 0
        self.pFullRiddleAudio = M.recycleSoundObject(self.pFullRiddleAudio)
        self.pClueAudio = M.recycleSoundObject(self.pClueAudio)
        self.pIntroRiddlesAudio = M.recycleSoundObject(self.pIntroRiddlesAudio)
        self.pCongratsAudio = M.recycleSoundObject(self.pCongratsAudio)
        self.pSkellyEndAudio = M.recycleSoundObject(self.pSkellyEndAudio)
        M.gScreenDaddy.mReleaseScavengerHuntPoolObjects()

    # ---- load / unload ---------------------------------------------------------------------------
    def mLoad(self):
        pass

    def mLoadList(self, theList):
        sd = M.gScreenDaddy
        self.pSkellyEndAudio = sd.mGetEndRiddleAudio()
        theList.append(self.pAmbientAudio)
        theList.append(self.pBGMember)
        sd.mLoadScavengerHuntlist(theList)
        if _alive(self.pNameObject):
            self.pNameObject.mLoadList(theList)
        if not self.pSolved:
            if not self.pHiddenMode:
                call_all(self.pRiddleObjectList, 'mLoadList', theList)
            call_all(self.pRiddleWordRectList, 'mLoadList', theList)
            theList.append(self.pRiddleStripMember)
            sd.pRiddleStripObject.mLoadList(theList)
            theList.append(self.pSkellyEndAudio)
            theList.append(self.pCongratsAudio)
        self.pSkellyAniObjectA.mLoadList(theList)
        self.pSkellyAniObjectB.mLoadList(theList)
        if len(self.pSHTokenObjectList):
            call_all(self.pSHTokenObjectList, 'mLoadList', theList)

    def mUnload(self):
        sd = M.gScreenDaddy
        sd.mUnloadScavengerHunt()
        unload_mem(self.pBGMember)
        unload_mem(self.pSkellyEndAudio)
        self.pSkellyAniObjectA.mUnload()
        self.pSkellyAniObjectB.mUnload()
        call_all(self.pSHTokenObjectList, 'mUnload')
        if _alive(self.pNameObject):
            self.pNameObject.mUnload()
        call_all(self.pRiddleObjectList, 'mUnload')
        call_all(self.pRiddleWordRectList, 'mUnload')
        unload_mem(self.pRiddleStripMember)
        unload_mem(self.pClueStripMember)
        sd.pRiddleStripObject.mUnload()
        unload_mem(self.pCongratsAudio)

    def mHuntObjectFound(self, theObject):
        M.gScreenDaddy.mEnable()

    def mGetEnabled(self):
        return self.pEnabled

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    # ---- show / hide -----------------------------------------------------------------------------
    def mShow(self):
        sd = M.gScreenDaddy
        self.pEnabled = 1
        M.FadeInAmbientSound(self.pAmbientAudio)
        sd.mShowScavengerHunt()
        self.pHelpButton.mShow()
        self.pBackButton.mShow()
        daResetCursorFlag = 0
        S(self.pBGSprite).member = self.pBGMember
        if not self.pHiddenMode:
            for daObject in self.pSHTokenObjectList:
                daObject.mShow()
            for daObject in self.pRiddleObjectList:
                daObject.mShow()
            if _alive(self.pNameObject):
                self.pNameObject.mShow()
        if not self.pSolved:
            self.pRiddleStripObject.mShow()
            if not M.riddlePlayed():
                self.pVisited = 1
                self._me.mDisable()
                self.pIntroRiddlesAudio.mPlay()
            else:
                self.pVisited = 1
                M.setInterruptMode(self.pFullRiddleAudio)
                self.pFullRiddleAudio.mPlay()
                call_all(self.pRiddleWordRectList, 'mShow')
                daResetCursorFlag = 1
        else:
            call_all(self.pRiddleObjectList, 'mDisable')
            daResetCursorFlag = 1
        if not sd.mEnableReminders() and daResetCursorFlag:
            M.resetCursor()

    def mHide(self):
        blank(self.pBGSprite)
        if _alive(self.pBackButton):
            self.pBackButton.mHide()
        if _alive(self.pHelpButton):
            self.pHelpButton.mHide()
        if _alive(self.pRiddleStripObject):
            self.pRiddleStripObject.mHide()
        call_all(self.pRiddleObjectList, 'mHide')
        if _alive(self.pNameObject):
            self.pNameObject.mHide()
        call_all(self.pSHTokenObjectList, 'mHide')
        M.gScreenDaddy.mHideScavengerHunt()
        self.pEnabled = 0

    def mGetName(self):
        return self.pName

    def mGetType(self):
        return Sym('SCREEN_RIDDLE')

    def mEnable(self):
        self.pEnabled = 1
        if _alive(self.pBackButton):
            self.pBackButton.mEnable()
        if _alive(self.pHelpButton):
            self.pHelpButton.mEnable()
        if self.pSolved:
            call_all(self.pSHTokenObjectList, 'mEnable')
        else:
            if _alive(self.pRiddleStripObject):
                self.pRiddleStripObject.mEnable()
            call_all(self.pRiddleObjectList, 'mEnable')

    def mDisable(self):
        self.pEnabled = 0
        if _alive(self.pBackButton):
            self.pBackButton.mDisable()
        if _alive(self.pHelpButton):
            self.pHelpButton.mDisable()
        if self.pSolved:
            call_all(self.pSHTokenObjectList, 'mDisable')
        else:
            call_all(self.pRiddleObjectList, 'mDisable')
            if _alive(self.pRiddleStripObject):
                self.pRiddleStripObject.mDisable()

    def mApplicationActivated(self):
        pass

    def mApplicationDeactivated(self):
        pass

    # ---- buttons ---------------------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        sd = M.gScreenDaddy
        if theObject is self.pHelpButton:
            sd.pHelpPlayer.mStartHelp()
        else:
            if theObject is self.pBackButton:
                if (sd.mGetLevel() == 1) and _alive(sd.pReminderAudio):
                    if sd.mLevelSolved():
                        sd.pReminderAudio.mSetSound(Sym('allkeys'), 0)
                    else:
                        if sd.mYoungersterCantFindKeys():
                            sd.pReminderAudio.mSetSound(Sym('allriddles'), 0)
                M.navigateBack()
            else:
                if theObject is self.pRiddleStripObject:
                    sd.mEnable()
                    M.setInterruptMode(self.pFullRiddleAudio)
                    self.pFullRiddleAudio.mPlay()
                else:
                    if theObject is self.pClueStripObject:
                        M.setInterruptMode(self.pClueAudio)
                        self.pClueAudio.mPlay()

    def mRiddleButtonClicked(self, theObject):
        if _get_pos(self.pRiddleObjectList, theObject):
            self.pCurrRiddleObject = theObject
            self._me.mDisable()
            daSound = theObject.mGetWordSound()
            daWordObject = self.mFindWordObject(theObject.pName)
            if _T(theObject.mGetType()) == 'RIDDLE_MULTI':
                if not _alive(daWordObject) or daSound != daWordObject.pClickSound:
                    daWordObject = 0
            self.pCurrRiddleWordSound = M.getSoundObject(1, daSound, self)
            load_mem(daSound)
            daQueue = M.getPlayQueueObject(self._me)
            daQueue.mAddItem(theObject)
            if _alive(daWordObject):
                daQueue.mAddItem(daWordObject)
            daQueue.mAddItem(self.pCurrRiddleWordSound)
            daQueue.mPlay()
        else:
            self.pCurrRiddleObject = theObject
            theObject.mPlay()
            M.gScreenDaddy.mDisable()

    def mWordClicked(self, theWordObj):
        theObject = self.mFindRiddleObject(theWordObj.mGetName())
        if _alive(theObject):
            daSound = theObject.mGetWordClickedSound()
        else:
            daSound = theWordObj.pClickSound
        if daSound:
            load_mem(daSound)
            self.pCurrRiddleWordSound = M.getSoundObject(1, daSound, self._me)
            self._me.mDisable()
            self.pCurrRiddleWordSound.mPlay()

    # ---- play-done dispatch ----------------------------------------------------------------------
    def mPlayDone(self, theObject):
        daType = _T(theObject.mGetType())
        if daType in ('INTERNALSOUND', 'EXTERNALSOUND'):
            self.mSoundDone(theObject)
        elif daType in ('RIDDLEWORD', 'RIDDLEWORD_RECT'):
            self.mSoundDone(theObject)
        elif daType in ('RIDDLE_SC', 'RIDDLE_LIN', 'RIDDLE_WIG', 'RIDDLE_MULTI', 'RIDDLE_DRAG', 'RIDDLE_NAME'):
            self.mRiddleAnimationDone(theObject)
        elif daType == 'PLAY_QUEUE':
            self.mHandlePlayQueue(theObject)
        elif daType == 'RIDDLETOKENOBJECT':
            M.gScreenDaddy.mExternalSHTokenFound(theObject)

    def mHandlePlayQueue(self, theObject):
        if theObject.mContainsObject(self.pCurrRiddleObject):
            theObject.mRecycle()
            if _alive(self.pCurrRiddleWordSound):
                unload_mem(self.pCurrRiddleWordSound.pSound)
                M.recycleSoundObject(self.pCurrRiddleWordSound)
            self.pCurrRiddleWordSound = 0
            self.pCurrRiddleObject = 0
            if self.mTestForRiddleDone():
                M.waitCursor()
                self.pCongratsAudio.mPlay()
            else:
                self._me.mEnable()
        else:
            if self.pEndAniObject is theObject:
                self.pRiddleStripObject.mHide()
                self.pRiddleStripObject.mUnload()
                self.pSkellyAniObjectA.mHide()
                self.pSkellyAniObjectB.mHide()
                theObject.mRecycle()
                self.pEndAniObject = 0
                self.pRiddleStripDissapearSound.mPlay()

    def mRiddleAnimationDone(self, theObject):
        if _get_pos(self.pSHTokenObjectList, theObject):
            if self.pHiddenMode:
                theObject.mHide()
                theObject.mUnload()
            theObject.mDisable()
            M.gScreenDaddy.mExternalSHTokenFound(theObject)
            self.pCurrRiddleObject = 0
        else:
            daWordObjct = self.mFindWordObject(theObject.mGetName())
            if _alive(daWordObjct):
                if theObject.mGetFound():
                    daWordObjct.mSetSelected()
                daSound = theObject.mGetWordSound()
                self.pCurrRiddleWordSound = M.getSoundObject(1, daSound, self._me)
                self.pCurrRiddleWordSound.mPlay()
            else:
                self._me.mEnable()

    def mSoundDone(self, theObject):
        if theObject is self.pCurrRiddleWordSound:
            unload_mem(self.pCurrRiddleWordSound.pSound)
            if _T(theObject.mGetType()) == 'INTERNALSOUND':
                M.recycleSoundObject(theObject)
            self._me.mEnable()
        else:
            if theObject is self.pCongratsAudio:
                self._me.mPlayEndAnim()
                return
            else:
                if theObject is self.pClueAudio:
                    M.clearInterruptMode()
                    self._me.mEnable()
                    M.resetCursor()
                else:
                    if self.pIntroRiddlesAudio is theObject:
                        M.setRiddlePlayed()
                        self._me.mEnable()
                        M.setInterruptMode(self.pFullRiddleAudio)
                        call_all(self.pRiddleWordRectList, 'mShow')
                        self.pFullRiddleAudio.mPlay()
                        M.resetCursor()
                    else:
                        if self.pRiddleStripDissapearSound is theObject:
                            M.resetCursor()
                        else:
                            if theObject is self.pFullRiddleAudio:
                                return
        self._me.mEnable()

    def mShowKeyClue(self):
        pass

    def mPlayEndAnim(self):
        M.gScreenDaddy.mAddToken(self.pName)
        self.pEndAniObject = M.getPlayQueueObject(self._me)
        self.pEndAniObject.mAddItem(self.pSkellyAniObjectA)
        self.pEndAniObject.mAddItem(self.pSkellyEndAudio)
        self.pEndAniObject.mAddItem(self.pSkellyAniObjectB)
        self.pEndAniObject.mPlay()

    def mTestForRiddleDone(self):
        self.pSolved = 1
        for daAnimObject in self.pRiddleObjectList:
            self.pSolved = min(self.pSolved, _found(daAnimObject))
        return self.pSolved

    def mFindWordObject(self, theName):
        for daObj in self.pRiddleWordRectList:
            if daObj.mGetName() == theName:
                return daObj
        return 0

    def mFindRiddleObject(self, theName):
        for daObj in self.pRiddleObjectList:
            if daObj.mGetName() == theName:
                return daObj
        return 0

    def mUpdate(self):
        pass

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetRiddleObjClicked(self):
        found = 0
        for daAnimObject in self.pRiddleObjectList:
            if daAnimObject.mGetFound():
                found = 1
        return found

    def mIsSolved(self):
        return self.pSolved

    def mGetHelpState(self):
        return 0


# ============================================================================================
# SCREEN_RIDDLE_MAG  (ParentScript 46)
# ============================================================================================

@lingo_script('SCREEN_RIDDLE_MAG')
class ScreenRiddleMag(LObject):
    def __init__(self):
        self.ancestor = None
        # these are properties of both scripts: keep them local so writes do not fall through to the ancestor
        self.pName = None
        self.pType = None
        self.pSavedList = []
        self.pParent = 0
        self.pMagCurRiddleObject = 0
        self.pSavedSprite = 0
        self.pSavedBackSprite = 0
        self.pClickLoc = 0
        self.pCursorDisabled = 0
        self.pStateChangeList = []
        self.pPrevMagGlassLoc = Point(320, 240)

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.ancestor = get_object(self.ancestor, theSpriteAlloc)
        if self.pMagOffset > 1:
            self.ancestor.pHiddenMode = 1
        self.ancestor._me = self
        call_all(self.ancestor.pRiddleObjectList, 'mSetParent', self)
        if len(self.ancestor.pSHTokenObjectList):
            call_all(self.ancestor.pSHTokenObjectList, 'mSetParent', self)
        self.ancestor.pBGSprite = pop_one(theSpriteAlloc)
        self.pMaskSprite = pop_one(theSpriteAlloc)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pAnimSprite = pop_one(theSpriteAlloc)
        self.pTestSprite = pop_one(theSpriteAlloc)
        self.pHandleSprite = pop_one(theSpriteAlloc)
        self.pCrossHairsSprite = pop_one(theSpriteAlloc)
        pSkellySprite = pop_one(theSpriteAlloc)
        self.ancestor.pSkellyAniObjectA.pSprite = pSkellySprite
        self.ancestor.pSkellyAniObjectB.pSprite = pSkellySprite
        self.pPrevMagGlassLoc = Point(320, 240)
        self.pSavedSprite = 0
        self.pSavedBackSprite = 0
        self.pClickLoc = 0
        self.pStateChangeList = []
        self.pMagCurRiddleObject = 0
        self.pMagMoveObj = _new(self.pAnimSlideObjectScriptNumber, self.pMaskSprite, self)
        self.pMagMoveObj.mSetMoveObject(self)
        self.pMagMoveObj.mSetParent(self)
        self.pCursorDisabled = 0
        return self

    def mGetEnabled(self):
        return self.ancestor.mGetEnabled()

    def mCheckKey(self, daKeyCode):
        if self.ancestor.pEnabled:
            if M.QuitKeyCheck(daKeyCode, 1):
                self.pCursorDisabled = 1
                M.removeUpdateList(self)

    def mDestroy(self):
        pass

    # ---- cursors -----------------------------------------------------------------------------------
    def mInitMagCursorUtils(self):
        sd = M.gScreenDaddy
        _cursor(sd.pRiddleStripObject.pBackSprite, [25, 26])
        _cursor(self.pMaskSprite, 200)
        _cursor(self.pHandleSprite, 200)
        _cursor(sd.pBackButton.pSprite, [25, 26])
        _cursor(sd.pHomeButton.pSprite, [25, 26])
        _cursor(sd.pHelpButton.pSprite, [25, 26])

    def mRemoveCursors(self):
        sd = M.gScreenDaddy
        _cursor(sd.pRiddleStripObject.pBackSprite, 0)
        _cursor(self.pMaskSprite, 0)
        _cursor(self.pHandleSprite, 0)
        _cursor(sd.pBackButton.pSprite, 0)
        _cursor(sd.pHomeButton.pSprite, 0)
        _cursor(sd.pHelpButton.pSprite, 0)

    def mSetWaitCursor(self):
        self.mRemoveCursors()
        S(self.pCrossHairsSprite).member = 1
        S(self.pMaskSprite).cursor = [31, 32]

    def mResetCursor(self):
        self.mInitMagCursorUtils()
        S(self.pCrossHairsSprite).member = self.pCrossHairsMember
        S(self.pMaskSprite).cursor = 200

    # ---- load / unload ---------------------------------------------------------------------------
    def mLoad(self):
        load_mem(self.pMaskMember)
        load_mem(self.pCrossHairsMember)
        load_mem(self.pMaskBackground)
        self.ancestor.mLoad()

    def mLoadList(self, theList):
        theList.append(self.pMaskBackground)
        # (original: if the freeBlock < member(pMaskBackground).size then unloadMember() and load the buttons first)
        theList.append(self.pMaskMember)
        theList.append(self.pCrossHairsMember)
        self.ancestor.mLoadList(theList)

    def mUnload(self):
        unload_mem(self.pMaskMember)
        unload_mem(self.pCrossHairsMember)
        R().drop_image(self.pMaskBackground)        # unloadMem(pMaskBackground): forgets the stamped state changes
        self.ancestor.mUnload()

    # ---- show / hide ------------------------------------------------------------------------------
    def mShow(self):
        rt = R()
        daRiddlePlayed = M.gScreenDaddy.pRiddlePlayed
        self.ancestor.mShow()
        S(self.pAnimSprite).member = 1
        self.pPrevMagGlassLoc = Point(320, 240)
        img = rt.image(self.pMaskBackground)
        if img is not None:
            daLeft = img.get_width() // 2
            daTop = img.get_height() // 2
            rt.set_reg_point(self.pMaskBackground, Point(daLeft, daTop))
        S(self.pMaskSprite).ink = 9
        S(self.pMaskSprite).mask_member = self.pMaskMember        # port-only: Director uses the next cast member
        S(self.pMaskSprite).member = self.pMaskBackground
        S(self.pCrossHairsSprite).member = self.pCrossHairsMember
        S(self.pCrossHairsSprite).ink = 8
        S(self.pHandleSprite).member = self.pHandleMember
        S(self.pHandleSprite).ink = 36
        S(self.pBackSprite).ink = 8
        for daObject in self.ancestor.pRiddleObjectList:
            self.mCheckStampStateChange(daObject)
        if len(self.ancestor.pSHTokenObjectList):
            for daObject in self.ancestor.pSHTokenObjectList:
                self.mCheckStampStateChange(daObject)
        if daRiddlePlayed:
            self.mInitMagCursorUtils()
            M.addUpdateList(self)
            if self.pMagOffset > 1:
                set_behavior(self.ancestor.pBGSprite, self)
        else:
            self.mSetWaitCursor()
            M.addUpdateList(self)

    def mHide(self):
        self.ancestor.mHide()
        blank(self.pMaskSprite)
        blank(self.pCrossHairsSprite)
        blank(self.pHandleSprite)
        blank(self.pAnimSprite)
        blank(self.pBackSprite)
        M.removeUpdateList(self)

    # ---- the lens -------------------------------------------------------------------------------
    def mUpdate(self):
        mouse = R().mouse
        mLoc = Point(min(max(mouse[0], 10), 630), min(max(mouse[1], 10), 415))
        self.mSetLoc(mLoc)

    def mSetLoc(self, mLoc):
        rt = R()
        S(self.pHandleSprite).loc = mLoc
        S(self.pCrossHairsSprite).loc = mLoc
        S(self.pMaskSprite).loc = mLoc
        deltaPoint = mLoc - self.pPrevMagGlassLoc
        cur = rt.reg_point(self.pMaskBackground)
        rt.set_reg_point(self.pMaskBackground, Point(cur[0] + self.pMagOffset * deltaPoint[0],
                                                     cur[1] + self.pMagOffset * deltaPoint[1]))
        self.pPrevMagGlassLoc = mLoc

    def mGetLoc(self):
        return S(self.pMaskSprite).loc

    def mGetName(self):
        return self.pName

    def mGetType(self):
        return Sym('SCREEN_RIDDLE_MAG')

    # ---- clicking -----------------------------------------------------------------------------------
    def mouseDown(self):
        theObject = 0
        theMouseLoc = R().mouse
        anc = self.ancestor
        if not anc.pSolved:
            for daObject in anc.pRiddleObjectList:
                theObject = self.mGetClickedObjectMag(daObject, theMouseLoc)
                if _alive(theObject):
                    break
        else:
            if len(anc.pSHTokenObjectList):
                theCurrentHunt = M.gScreenDaddy.mGetCurrentHuntName()
                for daObject in anc.pSHTokenObjectList:
                    if not daObject.pFound and (theCurrentHunt == daObject.pName):
                        theObject = self.mGetClickedObjectMag(daObject, theMouseLoc)
        if _alive(theObject):
            theObject.mouseDown()

    def mGetClickedObjectMag(self, theObject, theLoc):
        daType = _T(theObject.mGetType())
        if daType in ('RIDDLE_WIG', 'RIDDLE_SC', 'RIDDLE_LIN'):
            rc = theObject.pMagClickRect
            if isinstance(rc, (tuple, list)) and len(rc) == 4:
                if _inside(theLoc, Rect(rc[0] // 2, rc[1] // 2, rc[2] // 2, rc[3] // 2)):     # pMagClickRect / 2
                    return theObject
        else:
            if daType == 'RIDDLE_MULTI':
                for daMObject in theObject.pClickAnimObjList:
                    daObject = self.mGetClickedObjectMag(daMObject, theLoc)
                    if _alive(daObject):
                        return daMObject
        return 0

    def mCheckStampStateChange(self, theObject):
        daType = _T(theObject.mGetType())
        if daType == 'RIDDLE_SC':
            if theObject.pFound:
                self.mStampStateChange(theObject)
        else:
            if daType == 'RIDDLETOKENOBJECT':
                if theObject.mObjectVisible():
                    self.mStampStateChange(theObject)
            else:
                if daType == 'RIDDLE_MULTI':
                    for daMObject in theObject.pClickAnimObjList:
                        self.mCheckStampStateChange(daMObject)

    def mStampStateChange(self, theRiddleObject):
        daStampRect = theRiddleObject.pMagStampRect
        if isinstance(daStampRect, (tuple, list)) and len(daStampRect) == 4:
            R().stamp_pixels(self.pMaskBackground, theRiddleObject.pCurMember, daStampRect, 36)

    def mEnable(self):
        if self.pMagOffset > 1:
            set_behavior(self.ancestor.pBGSprite, self)
        M.addUpdateList(self)
        self.mResetCursor()
        self.ancestor.mEnable()

    def mDisable(self):
        anc = self.ancestor
        if self.pMagOffset > 1:
            remove_behavior(anc.pBGSprite)
        if _alive(anc.pCurrRiddleObject):
            M.removeUpdateList(self)
        else:
            if not _alive(anc.pCurrRiddleWordSound):
                self.mRemoveCursors()
        anc.mDisable()

    def mButtonActivated(self, theObject):
        if theObject is self.ancestor.pHelpButton:
            M.gScreenDaddy.pHelpPlayer.mStartHelp()
        self.ancestor.mButtonActivated(theObject)

    def mRiddleButtonClicked(self, theObject):
        anc = self.ancestor
        if _T(theObject.mGetType()) == 'RIDDLE_MULTI':
            daRidObject = theObject.pCurrentRiddleObject
            theObject.pPlayAllFound = 0
        else:
            daRidObject = theObject
        mp = daRidObject.pMagPoint
        if not isinstance(mp, (tuple, list)) or len(mp) != 2:
            mp = Point(320, 240)
        self.pClickLoc = Point(_idiv(mp[0], self.pMagOffset), _idiv(mp[1], self.pMagOffset))      # pMagPoint / pMagOffset
        if not ((_T(daRidObject.mGetType()) == 'RIDDLE_SC') and daRidObject.pFound):
            theObject.mDisable()
            self.pSavedSprite = daRidObject.pSprite
            self.pSavedBackSprite = daRidObject.pBackSprite
            S(self.pAnimSprite).ink = daRidObject.pInk
            daRidObject.pSprite = self.pAnimSprite
            daRidObject.pBackSprite = self.pBackSprite
            if self.pMagOffset > 1:
                S(self.pAnimSprite).loc = self.pClickLoc
                S(self.pBackSprite).loc = self.pClickLoc
        anc.pCurrRiddleObject = theObject
        self.pMagCurRiddleObject = theObject
        self.pMagMoveObj.mSetReturnLoc(self.pClickLoc)
        self.mDisable()
        self.pMagMoveObj.mPlay()

    # ---- play-done dispatch ----------------------------------------------------------------------
    def mPlayDone(self, theObject):
        daType = _T(theObject.mGetType())
        if daType in ('INTERNALSOUND', 'EXTERNALSOUND'):
            self.mSoundDone(theObject)
        elif daType in ('RIDDLETOKENOBJECT', 'BINK_TOKEN', 'RIDDLE_SC', 'RIDDLE_LIN', 'RIDDLE_WIG',
                        'RIDDLE_MULTI', 'RIDDLE_DRAG', 'RIDDLE_NAME'):
            self.mRiddleAnimationDone(theObject)
        elif daType == 'PLAY_QUEUE':
            self.mHandlePlayQueue(theObject)
        elif daType == 'ANIM_MOVE':
            self.mMagMoveDone(theObject)

    def mMagMoveDone(self, theObject):
        if _alive(self.pMagCurRiddleObject):
            self.mSetLoc(self.pClickLoc)
            if self.pMagOffset > 1:
                S(self.pAnimSprite).loc = self.pClickLoc
                S(self.pBackSprite).loc = self.pClickLoc
            R().update_stage()
            daCurObject = self.pMagCurRiddleObject
            self.pMagCurRiddleObject = 0
            self.ancestor.mRiddleButtonClicked(daCurObject)
        else:
            self.mPlayEndAnim()

    def mHandlePlayQueue(self, theObject):
        anc = self.ancestor
        if theObject.mContainsObject(anc.pCurrRiddleObject):
            self.mPostProcessMagAnim(anc.pCurrRiddleObject)
            anc.mHandlePlayQueue(theObject)
            if anc.mTestForRiddleDone():
                M.resetCursor()
                self.mSetWaitCursor()
        else:
            if theObject is anc.pEndAniObject:
                R().set_cursor_pos(Point(self.pSkellyAnimPoint[0], self.pSkellyAnimPoint[1]))
                anc.mHandlePlayQueue(theObject)

    def mSoundDone(self, theObject):
        anc = self.ancestor
        if theObject is anc.pClueAudio:
            if not anc.pEnabled:
                self.mResetCursor()
            anc.mSoundDone(theObject)
        else:
            if anc.pIntroRiddlesAudio is theObject:
                M.setRiddlePlayed()
                self.mInitMagCursorUtils()
                self.mResetCursor()
                self.mEnable()
                M.setInterruptMode(anc.pFullRiddleAudio)
                call_all(anc.pRiddleWordRectList, 'mShow')
                anc.pFullRiddleAudio.mPlay()
            else:
                if anc.pCongratsAudio is theObject:
                    self.pMagCurRiddleObject = 0
                    self.pMagMoveObj.mSetReturnLoc(self.pSkellyAnimPoint)
                    self.pMagMoveObj.mPlay()
                else:
                    anc.mSoundDone(theObject)

    def mRiddleAnimationDone(self, theObject):
        self.mPostProcessMagAnim(theObject)
        self.ancestor.mRiddleAnimationDone(theObject)

    def mPostProcessMagAnim(self, theObject):
        pc = self.pClickLoc
        if isinstance(pc, (tuple, list)) and len(pc) == 2:
            R().set_cursor_pos(Point(pc[0], pc[1]))
        daRidObject = theObject
        if _T(theObject.mGetType()) == 'RIDDLE_MULTI':
            daRidObject = theObject.pCurrentRiddleObject
        if _alive(daRidObject) and _T(daRidObject.mGetType()) in ('RIDDLE_SC', 'RIDDLETOKENOBJECT'):
            if (daRidObject.pMagStampRect == 0) and (self.pMagOffset == 1):
                daRidObject.pMagStampRect = Rect(*_sprite_rect(self.pAnimSprite))
            self.mStampStateChange(daRidObject)
        if self.pSavedSprite:
            daRidObject.pSprite = self.pSavedSprite
            daRidObject.pBackSprite = self.pSavedBackSprite
            if self.pMagOffset == 1:
                S(daRidObject.pSprite).member = S(self.pAnimSprite).member
            S(self.pAnimSprite).member = 1
            self.pSavedSprite = 0
            self.pSavedBackSprite = 0

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetHelpState(self):
        return 0


# registered here so a bare `from . import riddle_screens` is enough
_ = (Sym, _done, _nz, _symeq, _call_if, runtime)
