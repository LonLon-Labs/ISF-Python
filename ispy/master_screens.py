"""Hand-ported parent scripts, part 6: the game's home screen.

    ParentScript 119  DISSOLVE       the fade used by SCREEN_MASTER's intro (a frame counter; Director's puppetTransition
                                     has no port equivalent, so the "transition" is just the ~10 frame wait)
    ParentScript 44   SCREEN_MASTER  the home screen of a game world (spaceship / castle / aquarium): buttons, dynamic
                                     states, intro animation and fanfare. Translated one-to-one from the Fantasy .ls.

Port notes:
  * isOSX() is always 0 here, so the Windows path is taken: fade out, show the graphics, fade in over the fanfare.
  * mDisableTaskSwitching(gScreenMgr) / mEnableTaskSwitching(gScreenMgr) (SCREENMGR_WIN) do nothing in the port.
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object_list, get_object
from .lingo import Sym, set_properties, pop_one
from .ui import R, S, load_mem, unload_mem, call_all, blank, set_behavior, remove_behavior


def _alive(o):
    return isinstance(o, LObject)


def _call_if(o, name, *a):
    fn = getattr(o, name, None) if _alive(o) else None
    return fn(*a) if fn else None


def _typ(o):
    """mGetType(o) as an upper-case string, '' for anything that is not an object (Lingo: VOID/0)."""
    if not _alive(o):
        return ''
    try:
        return str(o.mGetType()).upper().lstrip('#')
    except Exception:
        return ''


def _listp(x):
    return isinstance(x, (list, dict))


# ============================================================================================
# DISSOLVE  (ParentScript 119)
# ============================================================================================

@lingo_script('DISSOLVE')
class Dissolve(LObject):
    def __init__(self, theName=None, theMember=0, theParent=0):
        self.pName = theName
        self.pFadeMember = theMember
        self.pParent = theParent
        self.pFlushCount = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        return self

    def mDestroy(self): pass
    def mSetParent(self, o): self.pParent = o
    def mLoad(self): pass
    def mLoadList(self, lst=None): pass
    def mUnload(self): pass
    mUnLoad = mUnload
    def mGetType(self): return Sym('DISSOLVE')
    def mGetName(self): return self.pName

    def mPlay(self):
        # Lingo: puppetTransition(member(pFadeMember)) -- no transition support in the port; the frame wait remains
        self.pFlushCount = 0
        M.addUpdateList(self)

    def mStop(self):
        M.removeUpdateList(self)
        if self.pParent:
            self.pParent.mPlayDone(self)

    def mUpdate(self):
        self.pFlushCount += 1
        if self.pFlushCount > 10:
            self.mStop()


# ============================================================================================
# SCREEN_MASTER  (ParentScript 44)
# ============================================================================================

@lingo_script('SCREEN_MASTER')
class ScreenMaster(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pButtList = []
        self.pSprite = 0
        self.pBGMember = 0
        self.pSolvedBGMember = 0
        self.pFanFareAudio = 0
        self.pFadeObject = 0
        self.pFadeInMember = 0
        self.pFadeOutMember = 0
        self.pIntroAnim = 0
        self.pSolvedAudio = 0
        self.pHelpButton = 0
        self.pHomeButton = 0
        self.pSavedList = []
        self.pAmbientAudio = 0
        self.pIntroPlayed = 0
        self.pEndVoPlayed = 0
        self.pHomeButtonAnim = 0
        self.pHelpObject = 0
        self.pTimer = 0
        self.pDynamicStateList = 0
        self.pIntroStateChangeMember = 0
        self.pIntroStateChangeSprite = 0
        self.pEnabled = 0
        self.pTaskSwitchDisabled = 0
        self.pSolvedAmbientAudio = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pTaskSwitchDisabled = 0
        self.pHelpButton = 0
        self.pHomeButton = 0
        self.pFadeInMember = R().member_number_by_name('END')
        self.pFadeOutMember = R().member_number_by_name('FADE_500MS')
        self.pFadeObject = Dissolve(Sym('MASTER'), self.pFadeOutMember, self)
        self.pEnabled = 1
        if self.pIntroStateChangeMember:
            self.pIntroStateChangeSprite = pop_one(theSpriteAlloc)
        self.pButtList = get_object_list(self.pButtList, theSpriteAlloc)
        if _listp(self.pDynamicStateList):
            self.pDynamicStateList = get_object_list(self.pDynamicStateList, theSpriteAlloc)
            call_all(self.pDynamicStateList, 'mSetParent', self)
        if _listp(self.pHomeButtonAnim):
            self.pHomeButtonAnim = get_object(self.pHomeButtonAnim, theSpriteAlloc)
            _call_if(self.pHomeButtonAnim, 'mSetParent', self)
        self.pIntroPlayed = 0
        self.pEndVoPlayed = 0
        call_all(self.pButtList, 'mSetParent', self)
        self.pSavedList = [Sym('pEndVoPlayed'), Sym('pIntroPlayed')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self): pass

    # ---- pool objects --------------------------------------------------------------------------
    def mInitPoolObjects(self):
        self.pIntroAnim = M.gScreenDaddy.mGetIntro()
        if _alive(self.pIntroAnim):
            self.pIntroAnim.mSetParent(self)
        elif isinstance(self.pIntroAnim, str):
            self.pIntroAnim = M.getExSoundObject(2, self.pIntroAnim, self)
        if isinstance(self.pFanFareAudio, str):
            self.pFanFareAudio = M.getExSoundObject(2, self.pFanFareAudio, self)
        self.pSolvedAudio = M.getExSoundObject(2, self.pSolvedAudio, self)

    def mReleasePoolObjects(self):
        self.pSolvedAudio = M.recycleSoundObject(self.pSolvedAudio)
        self.pFanFareAudio = M.recycleSoundObject(self.pFanFareAudio)
        if _typ(self.pIntroAnim) == 'EXTERNALSOUND':
            self.pIntroAnim = M.recycleSoundObject(self.pIntroAnim)

    # ---- load / unload -------------------------------------------------------------------------
    def mLoad(self):
        sd = M.gScreenDaddy
        call_all(self._dyn(), 'mLoad')
        if _alive(self.pIntroAnim):
            self.pIntroAnim.mSetParent(self)
        load_mem(self.pAmbientAudio)
        sd.mLoadScavengerHunt()
        call_all(self.pButtList, 'mLoad')
        if not sd.pIsSolved:
            load_mem(self.pBGMember)
        else:
            load_mem(self.pSolvedBGMember)
            if _alive(self.pHomeButtonAnim):
                self.pHomeButtonAnim.mLoad()

    def mLoadList(self, theList):
        sd = M.gScreenDaddy
        call_all(self._dyn(), 'mLoadList', theList)
        theList.append(self.pAmbientAudio)
        sd.mLoadScavengerHuntlist(theList)
        if self.pIntroStateChangeMember:
            theList.append(self.pIntroStateChangeMember)
        call_all(self.pButtList, 'mLoadList', theList)
        if not sd.pIsSolved:
            theList.append(self.pBGMember)
        else:
            theList.append(self.pSolvedBGMember)

    def mLoadFinale(self):
        load_mem(self.pSolvedAmbientAudio)
        load_mem(self.pSolvedBGMember)
        _call_if(self.pHomeButton, 'mLoad')
        _call_if(self.pHelpButton, 'mLoad')

    def mLoadFinaleList(self, theList):
        theList.append(self.pAmbientAudio)
        theList.append(self.pSolvedBGMember)
        _call_if(self.pHomeButton, 'mLoadList', theList)
        _call_if(self.pHelpButton, 'mLoadList', theList)

    def mUnloadFinale(self):
        unload_mem(self.pSolvedAmbientAudio)
        unload_mem(self.pSolvedBGMember)
        _call_if(self.pHomeButton, 'mUnload')
        _call_if(self.pHelpButton, 'mUnload')

    def mGetEnabled(self): return self.pEnabled

    def mUnLoad(self):
        M.gScreenDaddy.mUnloadScavengerHunt()
        call_all(self._dyn(), 'mUnload')
        if _alive(self.pIntroAnim):
            self.pIntroAnim.mUnload()
        call_all(self.pButtList, 'mUnload')
        unload_mem(self.pBGMember)
        if _alive(self.pHomeButtonAnim):
            self.pHomeButtonAnim.mUnload()
        unload_mem(self.pIntroStateChangeMember)

    mUnload = mUnLoad

    def _dyn(self):
        return self.pDynamicStateList if _listp(self.pDynamicStateList) else []

    def mHuntObjectFound(self, theObject):
        self.mEnable()

    # ---- show / hide ---------------------------------------------------------------------------
    def mShow(self):
        theResetCursorFlag = 0
        if not self.pIntroPlayed:
            if M.isOSX():
                _call_if(self.pFanFareAudio, 'mPlay')
                self.mShowGraphics()
                self.pIntroPlayed = 1
                self.mDisable()
            else:
                self.pTaskSwitchDisabled = 0           # mDisableTaskSwitching(gScreenMgr): not needed in the port
                self.pFadeObject.mPlay()
        else:
            self.mShowGraphics()
            theResetCursorFlag = 1
        self.pEnabled = 1
        if not M.gScreenDaddy.mCheckStatus() and theResetCursorFlag:
            M.resetCursor()

    def mShowGraphics(self, theDontShowStates=None):
        sd = M.gScreenDaddy
        self.pHelpButton = M.getGameHelpButton()
        self.pHomeButton = M.getGameHomeButton()
        self.pHelpButton.mSetParent(self)
        self.pHomeButton.mSetParent(self)
        self.pHelpButton.mShow()
        self.pHomeButton.mShow()
        if not sd.pIsSolved:
            daDisabledFlag = 0
            if _listp(M.gDisabledGamesList):
                if sd.pName in M.gDisabledGamesList:
                    daDisabledFlag = 1
            if sd.mGetLevel() == 1:
                daList = [self.pIntroPlayed, sd.pShowDSSH]
                if max(daList) > 0:
                    call_all(self._dyn(), 'mShow')
                if self.pIntroStateChangeMember and not self.pIntroPlayed:
                    S(self.pIntroStateChangeSprite).member = self.pIntroStateChangeMember
            else:
                if sd.mShowDynamicStates():
                    call_all(self._dyn(), 'mShow')
            if not daDisabledFlag:
                call_all(self.pButtList, 'mShow')
            sd.mShowScavengerHunt()
            M.setMember(self.pSprite, self.pBGMember)
            if not self.pIntroPlayed:
                M.FadeInAmbientSound(self.pAmbientAudio, 200)
            else:
                M.FadeInAmbientSound(self.pAmbientAudio)
        else:
            M.FadeInAmbientSound(self.pSolvedAmbientAudio)
            M.setMember(self.pSprite, self.pSolvedBGMember)
            M.resetCursor()
        self.pEnabled = 1

    def mHide(self):
        sd = M.gScreenDaddy
        if _typ(self.pIntroAnim) == 'BINK':
            self.pIntroAnim.mHide()
        sd.mHideScavengerHunt()
        call_all(self.pButtList, 'mHide')
        if _listp(self.pDynamicStateList):
            call_all(self.pDynamicStateList, 'mHide')
        _call_if(self.pHomeButton, 'mHide')
        _call_if(self.pHelpButton, 'mHide')
        blank(self.pSprite)
        self.pEnabled = 0

    def mUpdate(self):
        if self.pTimer < R().milliseconds():
            M.removeUpdateList(self)
            self.mShowGraphics()

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    # ---- buttons -------------------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        if theObject is self.pHelpButton:
            M.gGameDaddy.pCurrentGame.pHelpPlayer.mStartHelp()
        elif theObject is self.pHomeButton:
            M.gGameDaddy.mGoToGame(Sym('MAIN'))
        else:
            M.navigate(theObject.pDestination)

    def mButtonDeActivated(self, theObject): pass

    def mGetType(self): return Sym('SCREEN_MASTER')
    def mGetName(self): return self.pName

    def mDisable(self):
        self.pEnabled = 0
        call_all(self.pButtList, 'mDisable')
        _call_if(self.pHelpButton, 'mDisable')
        _call_if(self.pHomeButton, 'mDisable')

    def mEnable(self):
        self.pEnabled = 1
        call_all(self.pButtList, 'mEnable')
        _call_if(self.pHelpButton, 'mEnable')
        _call_if(self.pHomeButton, 'mEnable')

    # ---- play-done dispatch --------------------------------------------------------------------
    def mPlayDone(self, theObject):
        if theObject is self.pIntroAnim:
            if self.pIntroStateChangeMember:
                blank(self.pIntroStateChangeSprite)
            self.pIntroAnim.mUnload()
            self.pTaskSwitchDisabled = 0               # mEnableTaskSwitching(gScreenMgr)
            self.mEnable()
            M.resetCursor()
            M.FadeInAmbientSound(self.pAmbientAudio)
        elif theObject is self.pSolvedAudio:
            if _alive(self.pHomeButtonAnim):
                self.pHomeButton.mHide()
                self.pHomeButtonAnim.mPlay()
            else:
                M.resetCursor()
        elif theObject is self.pHomeButtonAnim:
            self.pHomeButton.mShow()
            self.mEnable()
            M.resetCursor()
            M.FadeInAmbientSound(self.pAmbientAudio)
        elif theObject is self.pFadeObject:
            if self.pFadeObject.pFadeMember == self.pFadeOutMember:
                self.mShowGraphics()
                self.pIntroPlayed = 1
                self.mDisable()
                self.pFadeObject.pFadeMember = self.pFadeInMember
                self.pFadeObject.mPlay()
                _call_if(self.pFanFareAudio, 'mPlay')
            else:
                if not M.isUpdating(self.pFanFareAudio):
                    _call_if(self.pIntroAnim, 'mLoad')
                    _call_if(self.pIntroAnim, 'mPlay')
        elif theObject is self.pFanFareAudio:
            if M.isOSX():
                _call_if(self.pIntroAnim, 'mLoad')
                _call_if(self.pIntroAnim, 'mPlay')
            else:
                if not M.isUpdating(self.pFadeObject):
                    _call_if(self.pIntroAnim, 'mLoad')
                    _call_if(self.pIntroAnim, 'mPlay')

    def mGetHelpState(self): return 0


# ============================================================================================
# SIMPLESTRIP  (ParentScript 57): the clue strip (getGameClueStrip); its mGetType is #RIDDLESTRIP
# ============================================================================================

@lingo_script('SIMPLESTRIP')
class SimpleStrip(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pWordMember = 0
        self.pWordSprite = 0
        self.pParent = 0
        self.pClueSound = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pWordSprite = pop_one(theSpriteAlloc)
        return self

    def mDestroy(self): pass

    def mouseDown(self):
        self.pParent.mButtonActivated(self)

    def mDisable(self):
        S(self.pWordSprite).cursor = 0
        remove_behavior(self.pWordSprite)

    def mEnable(self):
        S(self.pWordSprite).cursor = [22, 23]
        set_behavior(self.pWordSprite, self)

    def mShow(self):
        M.setMember(self.pBackSprite, self.pBackMember)
        M.setMember(self.pWordSprite, self.pWordMember)
        S(self.pWordSprite).cursor = [22, 23]
        S(self.pBackSprite).ink = 8
        S(self.pWordSprite).ink = 36
        set_behavior(self.pWordSprite, self)

    def mPlaySound(self):
        R().sound.puppet(1, self.pClueSound)

    def mHide(self):
        blank(self.pBackSprite)
        blank(self.pWordSprite)

    def mLoad(self):
        load_mem(self.pBackMember)
        load_mem(self.pWordMember)
        load_mem(self.pClueSound)

    def mLoadList(self, theList):
        theList.append(self.pBackMember)
        theList.append(self.pWordMember)
        theList.append(self.pClueSound)

    def mUnLoad(self): pass                               # unloadMem of three members
    mUnload = mUnLoad
    def mGetName(self): return self.pName
    def mSetParent(self, o): self.pParent = o
    def mGetType(self): return Sym('RIDDLESTRIP')


# ============================================================================================
# SCREEN_ROCKET  (ParentScript 99): the spaceship's rocket room (fuel crystals, launch button, circuit board)
# ============================================================================================

@lingo_script('SCREEN_ROCKET')
class ScreenRocket(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pAmbientAudio = 0
        self.pHomeButton = 0
        self.pHelpButton = 0
        self.pBackButton = 0
        self.pSavedList = []
        self.pParent = 0
        self.pFuelCrystalObjectList = []
        self.pFuelCrystalAnimList = []
        self.pControlPanelButton = 0
        self.pLaunchButtonInactive = 0
        self.pLaunchButtonActive = 0
        self.pLaunchActiveMember = 0
        self.pLaunchActiveSprite = 0
        self.pLockerButton = 0
        self.pFuelGaugeMemberList = []
        self.pFuelGaugeSprite = 0
        self.pAttemptedLaunch = 0
        self.pHighFuelSound = 0
        self.pLowFuelSound = 0
        self.pCircuitBoardPopUpSound = 0
        self.pCircuitBoardFixedClosed = 0
        self.pCircuitBoardCloseAnim = 0
        self.pChuteAudio = 0
        self.pGetFuelAudio = 0
        self.pNotFueledAudio = 0
        self.pFueledAudio = 0
        self.pCountdownErrorBink = 0
        self.pCountdownFinalAudio = 0
        self.pFixCircuitAudio = 0
        self.pReadyToLaunchAudio = 0
        self.pFuelGaugeFullAnim = 0
        self.pEnabled = 0
        self.pCrystalCorrectDropSoundObj = 0
        self.pCurrCrystalObj = 0
        self.pBlastOffButtonONSound = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pLaunchActiveSprite = pop_one(theSpriteAlloc)
        self.pFuelGaugeSprite = pop_one(theSpriteAlloc)
        self.pFuelCrystalObjectList = get_object_list(self.pFuelCrystalObjectList, theSpriteAlloc)
        call_all(self.pFuelCrystalObjectList, 'mSetParent', self)
        self.pFuelCrystalAnimList = get_object_list(self.pFuelCrystalAnimList, theSpriteAlloc)
        call_all(self.pFuelCrystalAnimList, 'mSetParent', self)
        self.pControlPanelButton = get_object(self.pControlPanelButton, theSpriteAlloc)
        self.pControlPanelButton.mSetParent(self)
        self.pLaunchButtonInactive = get_object(self.pLaunchButtonInactive, theSpriteAlloc)
        self.pLaunchButtonInactive.mSetParent(self)
        self.pLaunchButtonActive = get_object(self.pLaunchButtonActive, theSpriteAlloc)
        self.pLaunchButtonActive.mSetParent(self)
        self.pLockerButton = get_object(self.pLockerButton, theSpriteAlloc)
        self.pLockerButton.mSetParent(self)
        self.pAttemptedLaunch = 0
        self.pEnabled = 1
        self.pSavedList = [Sym('pAttemptedLaunch')]
        self.pCircuitBoardFixedClosed = 0
        self.pCountdownErrorBink = get_object(self.pCountdownErrorBink, theSpriteAlloc)
        self.pCountdownErrorBink.mSetParent(self)
        self.pCircuitBoardCloseAnim = get_object(self.pCircuitBoardCloseAnim, theSpriteAlloc)
        self.pCircuitBoardCloseAnim.mSetParent(self)
        self.pFuelGaugeFullAnim = get_object(self.pFuelGaugeFullAnim, theSpriteAlloc)
        self.pFuelGaugeFullAnim.mSetParent(self)
        M.addObjectGlob(self)
        return self                                    # (the Lingo mInit has no return; get_object ignores it)

    # ---- pool objects --------------------------------------------------------------------------
    def mInitPoolObjects(self):
        self.pHighFuelSound = M.getSoundObject(1, self.pHighFuelSound, self)
        self.pLowFuelSound = M.getSoundObject(1, self.pLowFuelSound, self)
        self.pFueledAudio = M.getExSoundObject(1, self.pFueledAudio, self)
        self.pNotFueledAudio = M.getExSoundObject(1, self.pNotFueledAudio, self)
        self.pGetFuelAudio = M.getExSoundObject(1, self.pGetFuelAudio, self)
        self.pChuteAudio = M.getExSoundObject(1, self.pChuteAudio, self)
        self.pCrystalCorrectDropSoundObj = M.getSoundObject(1, self.pCrystalCorrectDropSoundObj, self)
        self.pCountdownFinalAudio = M.getExSoundObject(1, self.pCountdownFinalAudio, self)
        self.pFixCircuitAudio = M.getExSoundObject(1, self.pFixCircuitAudio, self)
        self.pReadyToLaunchAudio = M.getExSoundObject(1, self.pReadyToLaunchAudio, self)
        self.pCircuitBoardPopUpSound = M.getSoundObject(1, self.pCircuitBoardPopUpSound, self)

    def mReleasePoolObjects(self):
        self.pHighFuelSound = M.recycleSoundObject(self.pHighFuelSound)
        self.pLowFuelSound = M.recycleSoundObject(self.pLowFuelSound)
        self.pChuteAudio = M.recycleSoundObject(self.pChuteAudio)
        self.pGetFuelAudio = M.recycleSoundObject(self.pGetFuelAudio)
        self.pNotFueledAudio = M.recycleSoundObject(self.pNotFueledAudio)
        self.pFueledAudio = M.recycleSoundObject(self.pFueledAudio)
        self.pCountdownFinalAudio = M.recycleSoundObject(self.pCountdownFinalAudio)
        self.pFixCircuitAudio = M.recycleSoundObject(self.pFixCircuitAudio)
        self.pReadyToLaunchAudio = M.recycleSoundObject(self.pReadyToLaunchAudio)
        self.pCircuitBoardPopUpSound = M.recycleSoundObject(self.pCircuitBoardPopUpSound)
        self.pCrystalCorrectDropSoundObj = M.recycleSoundObject(self.pCrystalCorrectDropSoundObj)

    def mDestroy(self): pass
    def mGetEnabled(self): return self.pEnabled
    def mLoad(self): pass

    # ---- load / unload -------------------------------------------------------------------------
    def mLoadList(self, theList):
        sd = M.gScreenDaddy
        sd.mLoadScavengerHuntlist(theList)
        theList.append(self.pAmbientAudio)
        theList.append(self.pBackMember)
        if sd.mGetLevel() < 2:
            for daMember in self.pFuelGaugeMemberList:
                theList.append(daMember)
            theList.append(self.pControlPanelButton)
            theList.append(self.pCircuitBoardPopUpSound)
            theList.append(self.pHighFuelSound)
            theList.append(self.pLowFuelSound)
            theList.append(self.pLaunchActiveMember)
            theList.append(self.pBlastOffButtonONSound)
            self.pLaunchButtonActive.mLoadList(theList)
            self.pLaunchButtonInactive.mLoadList(theList)
        else:
            theList.append(self.pFuelGaugeMemberList[len(self.pFuelGaugeMemberList) - 1])
            if sd.mLevelSolved():
                self.pLaunchButtonActive.mLoadList(theList)
                sd.mLoadFinaleList(theList)
                if not self.pCircuitBoardCloseAnim.pPlayed:
                    self.pCircuitBoardCloseAnim.mLoadList(theList)
            else:
                self.pLaunchButtonActive.mLoadList(theList)
                self.pLaunchButtonInactive.mLoadList(theList)
                self.pControlPanelButton.mLoadList(theList)
        self.pLockerButton.mLoadList(theList)
        self.pCountdownErrorBink.mLoadList(theList)
        if sd.mGetLevel() == 1:
            for daKey in self.pFuelCrystalObjectList:
                if sd.mTokenFound(daKey.pTokenName):
                    if not daKey.pDropped:
                        daKey.mLoadList(theList)
                        daPos = self.pFuelCrystalObjectList.index(daKey) + 1
                        self.pFuelCrystalAnimList[daPos - 1].mLoadList(theList)

    def mUnLoad(self):
        sd = M.gScreenDaddy
        sd.mUnloadScavengerHunt()
        call_all(self.pFuelCrystalObjectList, 'mUnload')
        call_all(self.pFuelCrystalAnimList, 'mUnload')
        self.pControlPanelButton.mUnload()
        self.pLaunchButtonInactive.mUnload()
        self.pLaunchButtonActive.mUnload()
        self.pLaunchButtonActive.mUnload()
        self.pLockerButton.mUnload()
        sd.mUnloadFinale()
        self.pCountdownErrorBink.mUnload()
        self.pCircuitBoardCloseAnim.mUnload()

    mUnload = mUnLoad

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    def mHuntObjectFound(self, theObject):
        self.mEnable()

    # ---- show / hide ---------------------------------------------------------------------------
    def mShow(self):
        sd = M.gScreenDaddy
        M.FadeInAmbientSound(self.pAmbientAudio)
        self.pHelpButton = M.getGameHelpButton()
        self.pBackButton = M.getGameBackButton()
        self.pHelpButton.mSetParent(self)
        self.pBackButton.mSetParent(self)
        self.pHelpButton.mShow()
        self.pBackButton.mShow()
        S(self.pBackSprite).member = self.pBackMember
        self.mShowFuelCrystals()
        self.mShowFuelGuage()
        self.pLockerButton.mShow()
        if sd.mGetLevel() < 2:
            daAllDropped = self.mAllFuelCrystalsDropped()
            if daAllDropped:
                if not self.pAttemptedLaunch:
                    self.pLaunchButtonActive.mShow()
                else:
                    self.pLaunchButtonInactive.mShow()
                    self.pControlPanelButton.mShow()
            else:
                self.pLaunchButtonInactive.mShow()
        else:
            if sd.mLevelSolved():
                if not self.pCircuitBoardCloseAnim.pPlayed:
                    self.mDisable()
                    self.pCircuitBoardCloseAnim.mShow()
                    self.pCircuitBoardCloseAnim.mPlay()
                    self.pControlPanelButton.mHide()
                    self.pCircuitBoardFixedClosed = 1
                else:
                    self.pLaunchButtonActive.mShow()
            else:
                self.pControlPanelButton.mShow()
                self.pLaunchButtonInactive.mShow()
        if not ((sd.mGetLevel() == 2) and sd.mLevelSolved()):
            sd.mShowScavengerHunt()
        self.pEnabled = 1
        if not sd.mCheckStatus():
            M.resetCursor()

    def mHide(self):
        _call_if(self.pHelpButton, 'mHide')
        _call_if(self.pBackButton, 'mHide')
        blank(self.pBackSprite)
        blank(self.pFuelGaugeSprite)
        call_all(self.pFuelCrystalObjectList, 'mHide')
        self.pLockerButton.mHide()
        self.pControlPanelButton.mHide()
        self.pLaunchButtonInactive.mHide()
        self.pLaunchButtonActive.mHide()
        M.gScreenDaddy.mHideScavengerHunt()
        self.pCountdownErrorBink.mHide()
        self.pEnabled = 0

    def mShowFuelGuage(self):
        if M.gScreenDaddy.mGetLevel() == 1:
            daIndex = self.mGetDroppedCount()
        else:
            daIndex = len(self.pFuelGaugeMemberList)
        if daIndex:
            S(self.pFuelGaugeSprite).member = self.pFuelGaugeMemberList[daIndex - 1]

    def mLoadFuelCrystals(self):
        sd = M.gScreenDaddy
        if sd.mGetLevel() == 1:
            for daKey in self.pFuelCrystalObjectList:
                if sd.mTokenFound(daKey.pTokenName):
                    if not daKey.pDropped:
                        daKey.mLoad()
                        daPos = self.pFuelCrystalObjectList.index(daKey) + 1
                        self.pFuelCrystalAnimList[daPos - 1].mLoad()

    def mShowFuelCrystals(self):
        sd = M.gScreenDaddy
        if sd.mGetLevel() == 1:
            for daKey in self.pFuelCrystalObjectList:
                if sd.mTokenFound(daKey.pTokenName):
                    daKey.mShow()

    def mGetDroppedCount(self):
        daCount = 0
        for daKey in self.pFuelCrystalObjectList:
            daCount = daCount + (daKey.pDropped or 0)
        return daCount

    def mAllFuelCrystalsDropped(self):
        daReturnVal = 1
        for daKey in self.pFuelCrystalObjectList:
            daReturnVal = min(daReturnVal, daKey.pDropped or 0)
        return daReturnVal

    def mGetName(self): return self.pName
    def mGetType(self): return Sym('SCREEN_ROCKET')

    # ---- enable / disable ----------------------------------------------------------------------
    def mEnable(self):
        sd = M.gScreenDaddy
        self.pEnabled = 1
        _call_if(self.pBackButton, 'mEnable')
        _call_if(self.pHelpButton, 'mEnable')
        self.pLockerButton.mEnable()
        if sd.mGetLevel() < 2:
            daAllDropped = self.mAllFuelCrystalsDropped()
            if daAllDropped:
                if not self.pAttemptedLaunch:
                    self.pLaunchButtonActive.mEnable()
                else:
                    self.pControlPanelButton.mEnable()
                    self.pLaunchButtonInactive.mEnable()
            else:
                call_all(self.pFuelCrystalObjectList, 'mEnable')
                self.pLaunchButtonInactive.mEnable()
        else:
            if sd.mLevelSolved():
                self.pLaunchButtonActive.mEnable()
            else:
                self.pLaunchButtonInactive.mEnable()
                self.pControlPanelButton.mEnable()

    def mDisable(self):
        self.pEnabled = 0
        call_all(self.pFuelCrystalObjectList, 'mDisable')
        self.pLaunchButtonActive.mDisable()
        self.pControlPanelButton.mDisable()
        self.pLaunchButtonInactive.mDisable()
        self.pLockerButton.mDisable()
        _call_if(self.pBackButton, 'mDisable')
        _call_if(self.pHelpButton, 'mDisable')

    # ---- buttons -------------------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        sd = M.gScreenDaddy
        if theObject is self.pHelpButton:
            M.gGameDaddy.pCurrentGame.pHelpPlayer.mStartHelp()
        elif theObject is self.pBackButton:
            M.navigateBack()
        elif theObject is self.pLockerButton:
            sd.mNavigate(Sym('B_LK'))
        elif theObject is self.pControlPanelButton:
            if sd.mGetLevel() < 2:
                sd.mNextLevel()
                sd.mInitScavengerHuntPoolObjects()
            sd.mNavigate(Sym('B_CP'))
        elif theObject is self.pLaunchButtonInactive:
            # Lingo: repeat while soundBusy(1) / updateStage() -- a blocking wait; the port does not block,
            # the next sound simply replaces the one playing
            self.pLaunchButtonInactive.mHide()
            self.pLaunchButtonInactive.mShow()
            _call_if(self.pLaunchButtonInactive, 'mouseEnter')
            sd.mDisable()
            M.waitCursor()
            if not self.pCountdownErrorBink.pPlayed:
                if sd.mYoungersterCantFindKeys():
                    self.pGetFuelAudio.mPlay()
                else:
                    if sd.mAllRiddlesSolved() and not self.mAllFuelCrystalsDropped():
                        self.pChuteAudio.mPlay()
                    else:
                        self.pNotFueledAudio.mPlay()
            else:
                self.pFixCircuitAudio.mPlay()
        elif theObject is self.pLaunchButtonActive:
            if (sd.mGetLevel() < 2) or not sd.mLevelSolved():
                M.waitCursor()
                self.mDisable()
                self.pCountdownErrorBink.mPlay()
                self.pAttemptedLaunch = 1
            else:
                self.mDisable()
                M.waitCursor()
                sd.mPlayFinale()

    def mButtonDeActivated(self, theObject): pass

    # ---- play-done dispatch --------------------------------------------------------------------
    def mPlayDone(self, theObject):
        sd = M.gScreenDaddy
        if theObject in self.pFuelCrystalObjectList:
            self.mDisable()
            M.resetCursor()
            daPos = self.pFuelCrystalObjectList.index(theObject) + 1
            self.pFuelCrystalAnimList[daPos - 1].mPlay()
        elif theObject in self.pFuelCrystalAnimList:
            self.mShowFuelGuage()
            theObject.mHide()
            theObject.mUnload()
            if self.mAllFuelCrystalsDropped():
                sd.mClearReminderAudio()
                self.pFuelGaugeFullAnim.mPlay()
            else:
                self.pLowFuelSound.mPlay()
        elif any(theObject is o for o in (self.pChuteAudio, self.pGetFuelAudio, self.pNotFueledAudio,
                                           self.pFixCircuitAudio)):
            _call_if(self.pLaunchButtonInactive, 'mouseLeave')
            self.pLaunchButtonInactive.mEnable()
            M.resetCursor()
            sd.mEnable()
            if theObject is self.pGetFuelAudio:
                _call_if(sd.pReminderAudio, 'mSetSound', Sym('RK_allRiddles'))
        elif theObject is self.pCountdownErrorBink:
            self.pCountdownErrorBink.mUnload()
            self.pLaunchButtonActive.mHide()
            self.pLaunchButtonInactive.mShow()
            self.pControlPanelButton.mShow()
            M.resetCursor()
            self.mEnable()
        elif theObject is self.pCountdownFinalAudio:
            sd.mPlayFinale()
        elif theObject is self.pFuelGaugeFullAnim:
            # Lingo: daTimeUP = the milliSeconds + 500 / repeat while daTimeUP < the milliSeconds -- the condition is
            # false from the start, so the loop never ran and there was no delay
            R().flush_input()
            R().sound.puppet(2, self.pBlastOffButtonONSound)
            self.pLaunchButtonInactive.mHide()
            self.pLaunchButtonActive.mShow()
            sd.mEnable()
        elif theObject is self.pLowFuelSound:
            sd.mEnable()
        elif theObject is self.pCircuitBoardCloseAnim:
            R().sound.puppet(2, self.pBlastOffButtonONSound)
            self.pLaunchButtonActive.mShow()
            self.mEnable()

    def mHandleDroppedObject(self, theObject): pass

    def mSoundDone(self, theObject):
        M.resetCursor()
        self.mEnable()

    def mUpdate(self): pass
    def mSetParent(self, theObject): self.pParent = theObject

    def mCrystalsOnShelfCount(self):
        daActiveCount = 0
        if M.gScreenDaddy.mGetLevel() == 1:
            for daCrystal in self.pFuelCrystalObjectList:
                if M.tokenFound(daCrystal.pTokenName) and not daCrystal.pDropped:
                    daActiveCount += 1
        return daActiveCount

    def mGetHelpState(self):
        sd = M.gScreenDaddy
        if sd.mGetLevel() == 1:
            if not self.mAllFuelCrystalsDropped():
                if sd.mAllRiddlesSolved() == 0:
                    if self.mCrystalsOnShelfCount() > 0:
                        return Sym('ROCKET_CRYSTALS')
                    return Sym('ROCKET_NOCRYSTAL')
                if self.mCrystalsOnShelfCount() > 0:
                    return Sym('ROCKET_CRYSTALS')
                return Sym('ROCKET_GETCRYSTALS')
            if not self.pAttemptedLaunch:
                return Sym('ROCKET_BLASTOFF')
            return Sym('ROCKET_FIX')
        if sd.mLevelSolved() and not sd.mIsSolved():
            return Sym('ROCKET_FIXED')
        if sd.mIsSolved():
            return Sym('ENDGAME_COMPLETE')
        return Sym('SCAV_HUNT')