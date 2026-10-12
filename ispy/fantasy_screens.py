"""Hand-ported Fantasy parent scripts, part 3: the screens that were still missing.

    ParentScript  65  SCREEN_DUNGEON        castle dungeon (#S_DU): key rack, gate, princess, dragon
    ParentScript  70  SCREEN_WIZLAB         wizard's lab (#S_SH): magic scroll, cauldron, ingredient drag-and-drop
    ParentScript 101  SCREEN_CP             rocket circuit board (#B_CP): the keys are dropped onto the board
    ParentScript 118  SCREEN_RIDDLE_MICRO   a SCREEN_RIDDLE (ancestor) with three magnification views (#B_LK style)

Translated one-to-one from the Fantasy .ls; method and property names unchanged.  Conventions as in
master_screens.py (`M.gScreenDaddy` is the Lingo global gScreenDaddy, `S(chan)` is sprite(chan)).

Port notes:
  * `repeat while soundBusy(1) ... end repeat` busy loops go through Runtime.wait_sound (keeps the window alive).
  * `repeat while daTicks > the milliSeconds ... updateStage()` goes through scavenger._wait_ms.
  * `call(#mHide, list, me)`: the extra argument is not passed (Lingo ignores it).
  * `set the stageColor to the stageColor` (a redraw nudge) is dropped; updateStage() stays.
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, Point, set_properties, pop_one, pop_list
from .ui import R, S, load_mem, unload_mem, call_all, blank
from .screens2 import _alive, _get_pos
from .scavenger import _eq, _typ, _unload, _call_if, _wait_ms
from .fantasy_anims import _unload_all


def _sd():
    return M.gScreenDaddy


# ============================================================================================
# SCREEN_DUNGEON  (ParentScript 65)
# ============================================================================================

@lingo_script('SCREEN_DUNGEON')
class ScreenDungeon(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pBackMember = 0
        self.pBackMemberSH = 0
        self.pBackSprite = 0
        self.pKeyObjectList = []
        self.pKeyRackButton = 0
        self.pGateButton = 0
        self.pWizardNavButton = 0
        self.pAmbientAudio = 0
        self.pAmbientAudioDragon = 0
        self.pAmbientAudioNoDragon = 0
        self.pPrincessDoorButton = 0
        self.pDragonWatchButton = 0
        self.pDragonWatchButtonBottle = 0
        self.pCurrDragonWatchButton = 0
        self.pPrincessHelpAnimGroup = 0
        self.pDragonEmergeAnim = 0
        self.pDragonWatchAnimSH = 0
        self.pDragonWatchAnim = 0
        self.pDragonGoAwayAnim = 0
        self.pGateOpenAnimObj = 0
        self.pEndAnimObj = 0
        self.pHomeButton = 0
        self.pHelpButton = 0
        self.pBackButton = 0
        self.pGateRattleSound = 0
        self.pVisited = 0
        self.pGateOpen = 0
        self.pDoorOpenMember = 0
        self.pDoorOpenSprite = 0
        self.pSavedList = []
        self.pParent = 0
        self.pPrincessNoKeyAnimObjList = []
        self.pPrincessGateAnimObj = 0
        self.pHuntObjectFound = 0
        self.pPrincessAllRiddlesNoKeysAnim = 0
        self.pPrincessUseKeysAnim = 0
        self.pEnabled = 0

    def mGetEnabled(self): return self.pEnabled

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackSprite = pop_one(theSpriteAlloc)
        pop_list(theSpriteAlloc, 10)                         # pStateChangeBackAlloc (a local in the Lingo, never used)
        self.pKeyRackButton = get_object(self.pKeyRackButton, theSpriteAlloc)
        self.pGateButton = get_object(self.pGateButton, theSpriteAlloc)
        self.pWizardNavButton = get_object(self.pWizardNavButton, theSpriteAlloc)
        self.pKeyRackButton.mSetParent(self)
        self.pGateButton.mSetParent(self)
        self.pWizardNavButton.mSetParent(self)
        self.pKeyObjectList = get_object_list(self.pKeyObjectList, theSpriteAlloc)
        call_all(self.pKeyObjectList, 'mSetParent', self)
        self.pGateOpenAnimObj = get_object(self.pGateOpenAnimObj, theSpriteAlloc)
        self.pGateOpenAnimObj.mSetParent(self)
        self.pPrincessNoKeyAnimObjList = get_object_list(self.pPrincessNoKeyAnimObjList, theSpriteAlloc, 1)
        call_all(self.pPrincessNoKeyAnimObjList, 'mSetParent', self)
        self.pPrincessUseKeysAnim = get_object(self.pPrincessUseKeysAnim, theSpriteAlloc)
        self.pPrincessUseKeysAnim.mSetParent(self)
        self.pPrincessGateAnimObj = get_object(self.pPrincessGateAnimObj, theSpriteAlloc)
        self.pPrincessGateAnimObj.mSetParent(self)
        self.pDragonEmergeAnim = get_object(self.pDragonEmergeAnim, theSpriteAlloc)
        self.pPrincessAllRiddlesNoKeysAnim = get_object(self.pPrincessAllRiddlesNoKeysAnim, theSpriteAlloc)
        self.pDragonWatchButton = get_object(self.pDragonWatchButton, theSpriteAlloc)
        self.pDragonWatchButtonBottle = get_object(self.pDragonWatchButtonBottle, theSpriteAlloc)
        self.pCurrDragonWatchButton = self.pDragonWatchButton
        self.pDragonWatchAnimSH = get_object(self.pDragonWatchAnimSH, theSpriteAlloc)
        self.pDragonWatchAnim = get_object(self.pDragonWatchAnim, theSpriteAlloc)
        self.pPrincessHelpAnimGroup = get_object(self.pPrincessHelpAnimGroup, theSpriteAlloc)
        self.pDragonGoAwayAnim = get_object(self.pDragonGoAwayAnim, theSpriteAlloc)
        self.pPrincessDoorButton = get_object(self.pPrincessDoorButton, theSpriteAlloc)
        self.pDoorOpenSprite = pop_one(theSpriteAlloc)
        self.pPrincessAllRiddlesNoKeysAnim.mSetParent(self)
        self.pPrincessDoorButton.mSetParent(self)
        self.pDragonWatchButton.mSetParent(self)
        self.pDragonWatchButtonBottle.mSetParent(self)
        self.pPrincessHelpAnimGroup.mSetParent(self)
        self.pDragonEmergeAnim.mSetParent(self)
        self.pDragonWatchAnimSH.mSetParent(self)
        self.pDragonWatchAnim.mSetParent(self)
        self.pDragonGoAwayAnim.mSetParent(self)
        self.pHuntObjectFound = 0
        self.pEnabled = 1
        self.pGateOpen = 0
        self.pAmbientAudioNoDragon = self.pAmbientAudio
        self.pSavedList = [Sym('pGateOpen'), Sym('pAmbientAudio')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self): pass

    def mInitPoolObjects(self):
        self.pGateRattleSound = M.getSoundObject(1, self.pGateRattleSound, self)

    def mReleasePoolObjects(self):
        self.pGateRattleSound = M.recycleSoundObject(self.pGateRattleSound)

    def mLoad(self): pass

    # ---- load / unload -------------------------------------------------------------------------
    def mLoadList(self, theList):
        sd = _sd()
        theList.append(self.pAmbientAudio)
        self.pWizardNavButton.mLoadList(theList)
        if not self.pDragonEmergeAnim.pPlayed:
            theList.append(self.pBackMember)
            if not self.pGateOpenAnimObj.pPlayed:
                theList.append(self.pGateRattleSound)
                self.pGateButton.mLoadList(theList)
                for daKey in self.pKeyObjectList:
                    if sd.mTokenFound(daKey.pTokenName):
                        daKey.mLoadList(theList)
                if sd.mLevelSolved():
                    self.pGateOpenAnimObj.mLoadList(theList)
                else:
                    self.pPrincessGateAnimObj.mLoadList(theList)
                    self.pPrincessAllRiddlesNoKeysAnim.mLoadList(theList)
                    if self.pPrincessNoKeyAnimObjList[0].pPlayed:
                        self.pPrincessNoKeyAnimObjList[0].mLoadList(theList)
                    else:
                        self.pPrincessNoKeyAnimObjList[0].mLoadList(theList)
                        self.pPrincessNoKeyAnimObjList[1].mLoadList(theList)
            else:
                if not self.pDragonEmergeAnim.pPlayed:
                    self.pDragonEmergeAnim.mLoadList(theList)
                    self.pGateOpenAnimObj.mLoadList(theList)
                    self.pPrincessDoorButton.mLoadList(theList)
                else:
                    self.pPrincessHelpAnimGroup.mLoadList(theList)
                    self.pDragonEmergeAnim.mLoadList(theList)
                    self.pGateOpenAnimObj.mLoadList(theList)
                    self.pDragonWatchAnim.mLoadList(theList)
        else:
            sd.mLoadScavengerHuntlist(theList)
            theList.append(self.pBackMemberSH)
            if not self.pDragonGoAwayAnim.pPlayed:
                self.pDragonWatchButton.mLoadList(theList)
                self.pDragonWatchAnimSH.mLoadList(theList)
                if _eq(sd.mGetCurrentHuntName(), self.pName):
                    self.pDragonGoAwayAnim.mLoadList(theList)
                    self.pPrincessDoorButton.mLoadList(theList)
                    self.pDragonWatchButtonBottle.mLoadList(theList)
            else:
                if not sd.pIsSolved:
                    self.pPrincessDoorButton.mLoadList(theList)
                    sd.mLoadFinaleList(theList)
                else:
                    self.pGateOpenAnimObj.mLoadList(theList)
                    self.pDragonEmergeAnim.mLoadList(theList)
                    self.pDragonGoAwayAnim.mLoadList(theList)
                    theList.append(self.pDoorOpenMember)

    def mUnLoad(self):
        sd = _sd()
        sd.mUnloadScavengerHunt()
        unload_mem(self.pAmbientAudioDragon)
        unload_mem(self.pAmbientAudioNoDragon)
        _unload(self.pWizardNavButton)
        unload_mem(self.pBackMember)
        unload_mem(self.pGateRattleSound)
        _unload(self.pGateButton)
        for daKey in self.pKeyObjectList:
            _unload(daKey)
        _unload(self.pGateOpenAnimObj)
        _unload(self.pPrincessDoorButton)
        _unload(self.pDragonEmergeAnim)
        _unload(self.pDragonWatchButton)
        _unload(self.pPrincessHelpAnimGroup)
        _unload(self.pDragonGoAwayAnim)
        unload_mem(self.pDoorOpenMember)
        _unload(self.pDragonWatchAnim)
        _unload(self.pDragonWatchAnimSH)
        _unload(self.pPrincessUseKeysAnim)
        _unload(self.pPrincessAllRiddlesNoKeysAnim)
        _unload_all(self.pPrincessNoKeyAnimObjList)
        _unload(self.pPrincessGateAnimObj)
        _unload(self.pDragonWatchButtonBottle)
        sd.mUnloadFinale()
    mUnload = mUnLoad

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    # ---- hunt ----------------------------------------------------------------------------------
    def mHuntObjectFound(self, theObject):
        sd = _sd()
        self.pHuntObjectFound = 1
        sd.mHideScavengerHunt()
        self.pCurrDragonWatchButton.mDisableUpdateMode()
        self.pCurrDragonWatchButton.mDisable()
        M.clearUpDateList()
        self.pAmbientAudio = self.pAmbientAudioNoDragon
        M.FadeInAmbientSound(self.pAmbientAudio)
        M.waitCursor()
        self.pDragonGoAwayAnim.mPlay()

    # ---- show / hide ---------------------------------------------------------------------------
    def mShow(self):
        sd = _sd()
        self.pHelpButton = M.getGameHelpButton()
        self.pBackButton = M.getGameBackButton()
        self.pHelpButton.mSetParent(self)
        self.pBackButton.mSetParent(self)
        self.pHelpButton.mShow()
        self.pBackButton.mShow()
        self.pWizardNavButton.mShow()
        if not self.pDragonEmergeAnim.pPlayed:
            S(self.pBackSprite).member = self.pBackMember
            if not self.pGateOpenAnimObj.pPlayed:
                self.pGateButton.mShow()
                if sd.mGetLevel() == 1:
                    for daKey in self.pKeyObjectList:
                        if M.tokenFound(daKey.pTokenName):
                            daKey.mShow()
            else:
                if not self.pDragonEmergeAnim.pPlayed:
                    self.pGateOpenAnimObj.mShow()
                    self.pPrincessDoorButton.mShow()
        else:
            S(self.pBackSprite).member = self.pBackMemberSH
            if not self.pDragonGoAwayAnim.pPlayed:
                self.pWizardNavButton.pDestination = Sym('S_SH')
                sd.mShowScavengerHunt()
                self.pCurrDragonWatchButton.mShow()
            else:
                if not sd.pIsSolved:
                    self.pPrincessDoorButton.mShow()
                else:
                    self.pGateOpenAnimObj.mShow()
                    self.pDragonEmergeAnim.mShow()
                    self.pDragonGoAwayAnim.mShow()
                    M.setMember(self.pDoorOpenSprite, self.pDoorOpenMember)
        self.pEnabled = 1
        M.FadeInAmbientSound(self.pAmbientAudio)
        if not sd.mCheckStatus():
            M.resetCursor()

    def mHide(self):
        blank(self.pBackSprite)
        blank(self.pDoorOpenSprite)
        _sd().mHideScavengerHunt()
        self.pGateButton.mHide()
        self.pWizardNavButton.mHide()
        _call_if(self.pBackButton, 'mHide')
        _call_if(self.pHelpButton, 'mHide')
        call_all(self.pKeyObjectList, 'mHide')
        self.pGateOpenAnimObj.mHide()
        self.pPrincessDoorButton.mHide()
        self.pCurrDragonWatchButton.mHide()
        self.pDragonEmergeAnim.mHide()
        self.pDragonWatchAnim.mHide()
        self.pDragonGoAwayAnim.mHide()
        call_all(self.pPrincessNoKeyAnimObjList, 'mHide')
        self.pPrincessGateAnimObj.mHide()
        self.pEnabled = 0

    def mGetName(self): return self.pName
    def mGetType(self): return Sym('SCREEN_DUNGEON')

    def _hunt_here(self):
        mgr = _sd().pScavengerHuntManager
        return _alive(mgr) and _eq(mgr.mGetCurrentHuntName(), self.pName)

    # ---- enable / disable ----------------------------------------------------------------------
    def mEnable(self):
        self.pEnabled = 1
        _call_if(self.pBackButton, 'mEnable')
        _call_if(self.pHelpButton, 'mEnable')
        self.pWizardNavButton.mEnable()
        if not self.pGateOpenAnimObj.pPlayed:
            call_all(self.pKeyObjectList, 'mEnable')
            self.pGateButton.mEnable()
            self.pKeyRackButton.mEnable()
        else:
            if not self.pDragonEmergeAnim.pPlayed:
                self.pPrincessDoorButton.mEnable()
            else:
                if not self.pDragonGoAwayAnim.pPlayed:
                    if self._hunt_here():
                        self.mSetDragonNormalMode()
                    else:
                        self.pCurrDragonWatchButton.mEnable()
                else:
                    self.pPrincessDoorButton.mEnable()

    def mSetDragonBottleMode(self):
        self.pDragonWatchButton.mHide()
        self.pDragonWatchButtonBottle.mShow()
        self.pDragonWatchButtonBottle.mEnableUpdateMode()
        self.pCurrDragonWatchButton = self.pDragonWatchButtonBottle

    def mSetDragonNormalMode(self):
        self.pDragonWatchButton.mShow()
        self.pDragonWatchButtonBottle.mDisableUpdateMode()
        self.pDragonWatchButtonBottle.mHide()
        self.pCurrDragonWatchButton = self.pDragonWatchButton

    def mDisable(self):
        self.pEnabled = 0
        _call_if(self.pBackButton, 'mDisable')
        _call_if(self.pHelpButton, 'mDisable')
        self.pWizardNavButton.mDisable()
        if not self.pGateOpenAnimObj.pPlayed:
            call_all(self.pKeyObjectList, 'mDisable')
            self.pGateButton.mDisable()
        else:
            if not self.pDragonEmergeAnim.pPlayed:
                self.pPrincessDoorButton.mDisable()
            else:
                if not self.pDragonGoAwayAnim.pPlayed:
                    if self._hunt_here():
                        self.mSetDragonBottleMode()
                    else:
                        self.pCurrDragonWatchButton.mDisable()
                else:
                    self.pCurrDragonWatchButton.mDisable()
                    self.pPrincessDoorButton.mDisable()

    # ---- buttons -------------------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        sd = _sd()
        if theObject is self.pHelpButton:
            M.gGameDaddy.pCurrentGame.pHelpPlayer.mStartHelp()
        elif theObject is self.pBackButton:
            M.navigateBack()
        elif theObject is self.pGateButton:
            M.waitCursor()
            self.mDisable()
            if not sd.mLevelSolved():
                daKeyOnGateCount = self.mKeysOnGateCount()
                if daKeyOnGateCount:
                    self.pPrincessUseKeysAnim.mPlay()
                else:
                    if sd.mAllRiddlesSolved():
                        self.pPrincessAllRiddlesNoKeysAnim.mPlay()
                    else:
                        daObject = self.pPrincessNoKeyAnimObjList[0]
                        if daObject.pPlayed:
                            daObject = self.pPrincessNoKeyAnimObjList[1]
                        daObject.mPlay()
            else:
                self.pPrincessGateAnimObj.mPlay()
        elif theObject is self.pWizardNavButton:
            if not self.pDragonEmergeAnim.pPlayed:
                sd.mNavigate(Sym('S_WL'))
            else:
                sd.mNavigate(Sym('S_SH'))
        elif theObject is self.pPrincessDoorButton:
            if sd.mGetLevel() < 2:
                self.mDisable()
                self.pPrincessDoorButton.mHide()
                _unload(self.pPrincessDoorButton)
                self.pDragonEmergeAnim.mLoad()
                self.pDragonEmergeAnim.mPlay()
                M.waitCursor()
            else:
                self.mDisable()
                self.pPrincessDoorButton.mHide()
                sd.mPlayFinale()
        elif theObject is self.pCurrDragonWatchButton:
            sd.mDisable()
            self.pCurrDragonWatchButton.mDisable()
            if sd.mGetLevel() < 2:
                self.pDragonWatchAnim.mLoad()
                self.pDragonWatchAnim.mPlay()
            else:
                self.pDragonWatchAnimSH.mLoad()
                self.pDragonWatchAnimSH.mPlay()
            M.waitCursor()

    def mButtonDeActivated(self, theObject=None): pass

    # ---- play done -----------------------------------------------------------------------------
    def mPlayDone(self, theObject):
        daType = _typ(theObject)
        if daType in ('INTERNALSOUND', 'EXTERNALSOUND'):
            self.mSoundDone(theObject)
        elif daType == 'DRAG_N_DROP':
            self.mHandleDroppedObject(theObject)
        elif daType == 'PLAY_QUEUE':
            self.mHandlePlayQueue(theObject)
        elif daType == 'BINK':
            self.mHandleBinkDone(theObject)
        elif daType in ('ANIM_SC', 'ANIM_WIGGLE'):
            self.mHandleAnimDone(theObject)

    def mHandleAnimDone(self, theObject):
        daHelpList = [self.pPrincessUseKeysAnim, self.pPrincessAllRiddlesNoKeysAnim, self.pPrincessGateAnimObj]
        if _get_pos(self.pPrincessNoKeyAnimObjList, theObject) or _get_pos(daHelpList, theObject):
            theObject.mHide()
            M.resetCursor()
        else:
            if self.pPrincessHelpAnimGroup.mBelongsToGroup(theObject):
                theObject.mHide()
                M.resetCursor()
                if _sd().mGetLevel() == 2:
                    _sd().mEnable()
                    return
        self.mEnable()

    def mHandleBinkDone(self, theObject):
        sd = _sd()
        if theObject is self.pGateOpenAnimObj:
            self.pGateButton.mHide()
            self.pPrincessDoorButton.mShow()
            if not getattr(M, 'gAppInBackground', 0):
                self.pDragonEmergeAnim.mLoad()
            sd.mClearReminderAudio()
            self.pPrincessDoorButton.mLoad()
            self.pPrincessDoorButton.mShow()
            M.resetCursor()
        else:
            if theObject is self.pDragonEmergeAnim:
                _unload(theObject)
                self.pAmbientAudio = self.pAmbientAudioDragon
                load_mem(self.pAmbientAudio)
                self.pPrincessHelpAnimGroup.mLoad()
                if not getattr(M, 'gAppInBackground', 0):
                    self.pDragonWatchAnim.mLoad()
                self.pCurrDragonWatchButton.mLoad()
                M.FadeInAmbientSound(self.pAmbientAudio)
                self.pCurrDragonWatchButton.mShow()
                self.pWizardNavButton.pDestination = Sym('S_SH')
                if not sd.mCheckStatus():
                    M.resetCursor()
            else:
                if theObject is self.pDragonGoAwayAnim:
                    _unload(theObject)
                    R().flush_input()
                    S(self.pCurrDragonWatchButton.pSprite).loc = Point(-1000, -1000)
                    self.pCurrDragonWatchButton.mHide()
                    self.pPrincessDoorButton.mShow()
                    _unload(self.pDragonWatchAnimSH)
                    if not getattr(M, 'gAppInBackground', 0):
                        sd.mLoadFinale()
                    M.resetCursor()
                else:
                    if (theObject is self.pDragonWatchAnim) or (theObject is self.pDragonWatchAnimSH):
                        self.pCurrDragonWatchButton.mHide()
                        self.pCurrDragonWatchButton.mShow()
                        self.pCurrDragonWatchButton.mDisable()
                        R().update_stage()
                        if theObject is self.pDragonWatchAnimSH:
                            daHelpAnim = self.pPrincessHelpAnimGroup.mGetObjectAt(1)
                        else:
                            daHelpAnim = self.pPrincessHelpAnimGroup.mNextObject()
                        daHelpAnim.mLoad()
                        daHelpAnim.mSetParent(self)
                        daHelpAnim.mPlay()
                        return
        sd.mEnable()

    def mGetDroppedCount(self):
        daCount = 0
        for daKey in self.pKeyObjectList:
            daCount = daCount + (daKey.pDropped or 0)
        return daCount

    def mHandleDroppedObject(self, theObject):
        sd = _sd()
        if self.mAllKeysDropped():
            self.pGateOpen = 1
            sd.mClearReminderAudio()
            M.waitCursor()
            self.mDisable()
            self.pGateOpenAnimObj.mPlay()
        else:
            sd.mEnable()

    def mHandlePlayQueue(self, theObject):
        if theObject.mContainsObject(self.pDragonEmergeAnim):
            theObject.mRecycle()
            self.pAmbientAudio = self.pAmbientAudioDragon
            M.FadeInAmbientSound(self.pAmbientAudio)
            self.pCurrDragonWatchButton.mShow()
            self.mEnable()

    def mSoundDone(self, theObject):
        M.resetCursor()
        _sd().mEnable()

    def mAllKeysDropped(self):
        daReturnVal = 1
        for daKey in self.pKeyObjectList:
            daReturnVal = min(daReturnVal, daKey.pDropped or 0)
        return daReturnVal

    def mKeysOnGateCount(self):
        daActiveCount = 0
        if _sd().mGetLevel() == 1:
            for daKey in self.pKeyObjectList:
                if M.tokenFound(daKey.pTokenName) and not daKey.pDropped:
                    daActiveCount = daActiveCount + 1
        return daActiveCount

    def mYoungsterCantFindKeys(self):
        return self.mKeysOnGateCount()

    def mUpdate(self): pass
    def mSetParent(self, theObject): self.pParent = theObject
    def mGetHelpState(self): return 0


# ============================================================================================
# SCREEN_WIZLAB  (ParentScript 70)
# ============================================================================================

@lingo_script('SCREEN_WIZLAB')
class ScreenWizLab(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pIngredientObjectList = []
        self.pMagicScrollButton = 0
        self.pMagicScrollAnimation = 0
        self.pDungeonNavButton = 0
        self.pAmbientAudio = 0
        self.pTokenAnimation = 0
        self.pScrollOpenAnimObj = 0
        self.pCaldronPourAnimObj = 0
        self.pCaldronAnimObj = 0
        self.pCaldronAnimObjBig = 0
        self.pSplashSound = 0
        self.pShellCoverSprite = 0
        self.pShellCoverMember = 0
        self.pHomeButton = 0
        self.pHelpButton = 0
        self.pBackButton = 0
        self.pSavedList = []
        self.pParent = 0
        self.pStashedCauldronSprite = 0
        self.pLameNameObj = 0
        self.pSpecialStateChangeMember = 0
        self.pSpecialStateChangeSprite = 0
        self.pEnabled = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pShellCoverSprite = pop_one(theSpriteAlloc)
        self.pSpecialStateChangeSprite = pop_one(theSpriteAlloc)
        self.pLameNameObj = get_object(self.pLameNameObj, theSpriteAlloc)
        self.pMagicScrollAnimation = get_object(self.pMagicScrollAnimation, theSpriteAlloc)
        self.pMagicScrollButton = get_object(self.pMagicScrollButton, theSpriteAlloc)
        self.pDungeonNavButton = get_object(self.pDungeonNavButton, theSpriteAlloc)
        self.pCaldronPourAnimObj = get_object(self.pCaldronPourAnimObj, theSpriteAlloc)
        self.pCaldronAnimObjBig = get_object(self.pCaldronAnimObjBig, theSpriteAlloc)
        self.pCaldronAnimObj = get_object(self.pCaldronAnimObj, theSpriteAlloc)
        self.pLameNameObj.mSetParent(self)
        self.pMagicScrollButton.mSetParent(self)
        self.pMagicScrollAnimation.mSetParent(self)
        # the S_SH data has no #pDungeonNavButton, so it is VOID here; mSetParent(VOID, me) is a silent no-op in Director
        _call_if(self.pDungeonNavButton, 'mSetParent', self)
        self.pCaldronAnimObj.mSetParent(self)
        self.pCaldronAnimObjBig.mSetParent(self)
        self.pCaldronPourAnimObj.mSetParent(self)
        self.pIngredientObjectList = get_object_list(self.pIngredientObjectList, theSpriteAlloc)
        call_all(self.pIngredientObjectList, 'mSetParent', self)
        # (pGateInstructionAudio / pKeyRackInstructionAudio / pDragonAnimationNextDoor are locals in the Lingo)
        self.pStashedCauldronSprite = 0
        self.pEnabled = 1
        self.pSavedList = []
        return self

    def mInitPoolObjects(self): pass
    def mReleasePoolObjects(self): pass
    def mDestroy(self): pass
    def mGetEnabled(self): return self.pEnabled
    def mLoad(self): pass

    # ---- load / unload -------------------------------------------------------------------------
    def mLoadList(self, theList):
        sd = _sd()
        sd.mLoadScavengerHuntlist(theList)
        theList.append(self.pAmbientAudio)
        self.pLameNameObj.mLoadList(theList)
        theList.append(self.pBackMember)
        if not self.pMagicScrollAnimation.pPlayed:
            self.pMagicScrollButton.mLoadList(theList)
            self.pMagicScrollAnimation.mLoadList(theList)
            theList.append(self.pShellCoverMember)
            theList.append(self.pSpecialStateChangeMember)
            sd.pScavengerHuntManager.mLoadList(theList)
        else:
            if not self.pCaldronPourAnimObj.pPlayed:
                if sd.mTokenFoundCount():
                    theList.append(self.pSplashSound)
                    daDroppedCount = self.mGetDroppedCount()
                    daRemainingDropped = len(self.pIngredientObjectList) - daDroppedCount
                    if daDroppedCount == 0:
                        self.pCaldronAnimObj.mLoadList(theList)
                    else:
                        if daRemainingDropped > 1:
                            self.pCaldronAnimObjBig.mLoadList(theList)
                        else:
                            self.pCaldronPourAnimObj.mLoadList(theList)
                    if sd.mGetLevel() == 2:
                        for daKey in self.pIngredientObjectList:
                            if sd.mTokenFound(daKey.pTokenName):
                                if not daKey.pDropped:
                                    daKey.mLoadList(theList)
                    if sd.mRemainingTokenCount() < 2:
                        self.pCaldronPourAnimObj.mLoadList(theList)

    def mUnLoad(self):
        sd = _sd()
        sd.mUnloadScavengerHunt()
        unload_mem(self.pSplashSound)
        unload_mem(self.pAmbientAudio)
        _unload(self.pLameNameObj)
        unload_mem(self.pBackMember)
        unload_mem(self.pShellCoverMember)
        unload_mem(self.pSpecialStateChangeMember)
        _unload_all(self.pIngredientObjectList)
        _unload(self.pCaldronAnimObj)
        _unload(self.pCaldronAnimObjBig)
        _unload(self.pCaldronPourAnimObj)
        _unload(self.pMagicScrollAnimation)
        _unload(self.pMagicScrollButton)
        if not self.pMagicScrollAnimation.pPlayed:
            _unload(sd.pScavengerHuntManager)
    mUnload = mUnLoad

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    def mHuntObjectFound(self, theObject):
        if _eq(theObject.pName, self.pName):
            self.mShowShellCover()
            self.mShowIngredients()
            self.mEnable()
        else:
            _sd().mEnable()

    # ---- show / hide ---------------------------------------------------------------------------
    def mShow(self):
        sd = _sd()
        M.FadeInAmbientSound(self.pAmbientAudio)
        self.pHelpButton = M.getGameHelpButton()
        self.pBackButton = M.getGameBackButton()
        self.pHelpButton.mSetParent(self)
        self.pBackButton.mSetParent(self)
        self.pHelpButton.mShow()
        self.pBackButton.mShow()
        self.pLameNameObj.mShow()
        S(self.pBackSprite).member = self.pBackMember
        if not self.pMagicScrollAnimation.pPlayed:
            self.pMagicScrollButton.mShow()
            self.pMagicScrollAnimation.mEnable()
            self.mShowSpecialStateChange()
        else:
            if not self.pCaldronPourAnimObj.pPlayed:
                if sd.mTokenFound(self.pName):
                    self.mHideSpecialStateChange()
                    self.mShowShellCover()
                else:
                    self.mShowSpecialStateChange()
                sd.mShowScavengerHunt()
                self.mShowIngredients()
            else:
                self.mHideSpecialStateChange()
                self.mShowShellCover()
                sd.mShowScavengerHunt()
                self.pCaldronPourAnimObj.mShow()
        self.pEnabled = 1
        if not sd.mEnableReminders():
            M.resetCursor()

    def mShowShellCover(self):
        S(self.pShellCoverSprite).member = self.pShellCoverMember
        S(self.pShellCoverSprite).ink = 8
        self.mHideSpecialStateChange()

    def mShowSpecialStateChange(self):
        if self.pSpecialStateChangeMember:
            S(self.pSpecialStateChangeSprite).member = self.pSpecialStateChangeMember
            S(self.pSpecialStateChangeSprite).ink = 8

    def mHideSpecialStateChange(self):
        if self.pSpecialStateChangeMember:
            blank(self.pSpecialStateChangeSprite)

    def mHide(self):
        blank(self.pBackSprite)
        blank(self.pShellCoverSprite)
        self.mHideSpecialStateChange()
        self.pMagicScrollButton.mHide()
        self.pCaldronPourAnimObj.mHide()
        self.pCaldronAnimObj.mHide()
        self.pCaldronAnimObjBig.mHide()
        self.pMagicScrollAnimation.mHide()
        _call_if(self.pBackButton, 'mHide')
        _call_if(self.pHelpButton, 'mHide')
        self.pLameNameObj.mHide()
        call_all(self.pIngredientObjectList, 'mHide')
        _sd().mHideScavengerHunt()
        self.pEnabled = 0

    def mLoadIngredients(self):
        sd = _sd()
        if sd.mGetLevel() == 2:
            for daKey in self.pIngredientObjectList:
                if sd.mTokenFound(daKey.pTokenName):
                    if not daKey.pDropped:
                        daKey.mLoad()

    def mGetDroppedCount(self):
        daCount = 0
        for daKey in self.pIngredientObjectList:
            daCount = daCount + (daKey.pDropped or 0)
        return daCount

    def mShowIngredients(self):
        sd = _sd()
        if sd.mGetLevel() == 2:
            for daKey in self.pIngredientObjectList:
                if sd.mTokenFound(daKey.pTokenName):
                    daKey.mShow()

    def mGetName(self): return self.pName
    def mGetType(self): return Sym('SCREEN_WIZLAB')

    def mEnable(self):
        call_all(self.pIngredientObjectList, 'mEnable')
        _call_if(self.pBackButton, 'mEnable')
        _call_if(self.pHelpButton, 'mEnable')
        if not self.pMagicScrollAnimation.pPlayed:
            self.pMagicScrollButton.mEnable()
        self.pEnabled = 1

    def mDisable(self):
        self.pEnabled = 0
        call_all(self.pIngredientObjectList, 'mDisable')
        _call_if(self.pBackButton, 'mDisable')
        _call_if(self.pHelpButton, 'mDisable')
        self.pMagicScrollButton.mDisable()

    def mButtonActivated(self, theObject):
        if theObject is self.pHelpButton:
            M.gGameDaddy.pCurrentGame.pHelpPlayer.mStartHelp()
        elif theObject is self.pBackButton:
            M.navigateBack()
        elif theObject is self.pMagicScrollButton:
            M.waitCursor()
            self.mDisable()
            self.pMagicScrollAnimation.mPlay()

    def mButtonDeActivated(self, theObject=None): pass

    # ---- play done -----------------------------------------------------------------------------
    def mPlayDone(self, theObject):
        daType = _typ(theObject)
        if daType in ('INTERNALSOUND', 'EXTERNALSOUND'):
            self.mSoundDone(theObject)
        elif daType == 'DRAG_N_DROP':
            self.mHandleDroppedObject(theObject)
        elif daType == 'PLAY_QUEUE':
            self.mHandlePlayQueue(theObject)
        elif daType in ('ANIM_SC', 'ANIM_LIN'):
            self.mHandleAnimDone(theObject)
        elif daType == 'BINK':
            self.mHandleBinkDone(theObject)

    def mHandleAnimDone(self, theObject):
        if theObject is self.pCaldronAnimObj:
            theObject.mHide()
            _unload(theObject)
            self.pCaldronAnimObjBig.mLoad()
        else:
            if theObject is self.pCaldronAnimObjBig:
                theObject.mHide()
                daDroppedCount = self.mGetDroppedCount()
                daRemainingDropped = len(self.pIngredientObjectList) - daDroppedCount
                if daRemainingDropped == 1:
                    _unload(theObject)
                    self.pCaldronPourAnimObj.mLoad()
        _sd().mEnable()

    def mHandleBinkDone(self, theObject):
        sd = _sd()
        if theObject is self.pMagicScrollAnimation:
            self.pMagicScrollAnimation.mHide()
            sd.mNextLevel()
            sd.mInitScavengerHuntPoolObjects()
            sd.mLoadScavengerHunt()
            sd.mShowScavengerHunt()
            self.pMagicScrollButton.mHide()
            self.mEnable()
            M.resetCursor()
            R().flush_input()
        else:
            if theObject is self.pCaldronPourAnimObj:
                sd.pScavengerHuntManager.mNextHunt()
        self.mEnable()

    def mHandleDroppedObject(self, theObject):
        rt = R()
        if _get_pos(self.pIngredientObjectList, theObject):
            _sd().mDisable()
            M.resetCursor()
            rt.sound.puppet(1, self.pSplashSound)
            rt.update_stage()
            if not self.mAllIngredientsDropped():
                if not self.pCaldronAnimObj.pPlayed:
                    rt.wait_sound(1)
                    self.pCaldronAnimObj.mShow()
                    self.pCaldronAnimObj.mPlay()
                else:
                    rt.wait_sound(1)
                    self.pCaldronAnimObjBig.mShow()
                    self.pCaldronAnimObjBig.mPlay()
            else:
                M.resetCursor()
                theObject.mHide()
                rt.update_stage()
                self.pCaldronPourAnimObj.mLoad()
                rt.wait_sound(1)
                self.pCaldronPourAnimObj.mPlay()

    def mHandlePlayQueue(self, theObject): pass

    def mSoundDone(self, theObject):
        M.resetCursor()
        self.mEnable()

    def mAllIngredientsDropped(self):
        daReturnVal = 1
        for daKey in self.pIngredientObjectList:
            daReturnVal = min(daReturnVal, daKey.pDropped or 0)
        return daReturnVal

    def mRiddleStripAdvanced(self): pass
    def mUpdate(self): pass
    def mSetParent(self, theObject): self.pParent = theObject
    def mGetHelpState(self): return 0


# ============================================================================================
# SCREEN_CP  (ParentScript 101)
# ============================================================================================

@lingo_script('SCREEN_CP')
class ScreenCP(LObject):
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
        self.pPDAOnGraphic = 0
        self.pPDAOffGraphic = 0
        self.pPDASlideUpSound = 0
        self.pPDASlideDownSound = 0
        self.pPDASprite = 0
        self.pKeyObjectList = []
        self.pIntroAudio = 0
        self.pCompleteAudio = 0
        self.pIntroPlayed = 0
        self.pTransAnim = 0
        self.pEnabled = 0
        self.pFinaleSound = 0
        self.pFinaleAnimList = []

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pKeyObjectList = get_object_list(self.pKeyObjectList, theSpriteAlloc)
        call_all(self.pKeyObjectList, 'mSetParent', self)
        self.pFinaleAnimList = get_object_list(self.pFinaleAnimList, theSpriteAlloc)
        call_all(self.pFinaleAnimList, 'mSetParent', self)
        self.pPDASprite = pop_one(theSpriteAlloc)
        self.pTransAnim = get_object(self.pTransAnim, theSpriteAlloc)
        self.pTransAnim.mSetParent(self)
        self.pEnabled = 1
        self.pIntroPlayed = 0
        self.pSavedList = [Sym('pIntroPlayed')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self): pass

    def mInitPoolObjects(self):
        self.pIntroAudio = M.getExSoundObject(1, self.pIntroAudio, self)
        self.pCompleteAudio = M.getExSoundObject(1, self.pCompleteAudio, self)
        self.pFinaleSound = M.getSoundObject(2, self.pFinaleSound, self)

    def mReleasePoolObjects(self):
        self.pIntroAudio = M.recycleSoundObject(self.pIntroAudio)
        self.pCompleteAudio = M.recycleSoundObject(self.pCompleteAudio)
        self.pFinaleSound = M.recycleSoundObject(self.pFinaleSound)

    def mLoad(self):
        sd = _sd()
        sd.mLoadScavengerHunt()
        load_mem(self.pAmbientAudio)
        load_mem(self.pBackMember)
        self.mAllKeysDropped()
        self.mLoadKeys()

    def mLoadList(self, theList):
        sd = _sd()
        sd.mLoadScavengerHuntlist(theList)
        theList.append(self.pAmbientAudio)
        theList.append(self.pBackMember)
        theList.append(self.pFinaleSound)
        self.mAllKeysDropped()
        for daKey in self.pKeyObjectList:
            if sd.mTokenFound(daKey.pTokenName):
                if not daKey.pDropped:
                    daKey.mLoadList(theList)

    def mUnLoad(self):
        _sd().mUnloadScavengerHunt()
        unload_mem(self.pAmbientAudio)
        unload_mem(self.pBackMember)
        unload_mem(self.pFinaleSound)
        _unload_all(self.pKeyObjectList)
    mUnload = mUnLoad

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    def mHuntObjectFound(self, theObject):
        M.waitCursor()
        self.pCompleteAudio.mPlay()

    def mShow(self):
        sd = _sd()
        theResetCursorFlag = 0
        M.FadeInAmbientSound(self.pAmbientAudio)
        self.pHelpButton = M.getGameHelpButton()
        self.pBackButton = M.getGameBackButton()
        self.pHelpButton.mSetParent(self)
        self.pBackButton.mSetParent(self)
        self.pHelpButton.mShow()
        self.pBackButton.mShow()
        S(self.pBackSprite).member = self.pBackMember
        self.mShowKeys()
        if self.pIntroPlayed:
            sd.mShowScavengerHunt()
            theResetCursorFlag = 1
        else:
            self.pIntroPlayed = 1
            self.mDisable()
            self.pIntroAudio.mPlay()
        self.pEnabled = 1
        if not sd.mEnableReminders() and theResetCursorFlag:
            M.resetCursor()

    def mHide(self):
        blank(self.pBackSprite)
        _call_if(self.pHelpButton, 'mHide')
        _call_if(self.pBackButton, 'mHide')
        call_all(self.pKeyObjectList, 'mHide')
        _sd().mHideScavengerHunt()
        self.pEnabled = 0

    def mButtonActivated(self, theObject):
        if theObject is self.pHelpButton:
            M.gGameDaddy.pCurrentGame.pHelpPlayer.mStartHelp()
        elif theObject is self.pBackButton:
            M.navigateBack()

    def mButtonDeActivated(self, theObject=None): pass

    def mPlayDone(self, theObject):
        sd = _sd()
        if _get_pos(self.pKeyObjectList, theObject):
            if self.mAllKeysDropped():
                self.pFinaleSound.mPlay()
                call_all(self.pFinaleAnimList, 'mShow')
                call_all(self.pFinaleAnimList, 'mPlay')
            else:
                sd.mEnable()
        else:
            if theObject is self.pIntroAudio:
                M.resetCursor()
                self.mEnable()
                sd.mShowScavengerHunt()
            else:
                if theObject is self.pFinaleSound:
                    call_all(self.pFinaleAnimList, 'mStop')
                    sd.mExternalSHTokenFound(self)
                else:
                    if theObject is self.pCompleteAudio:
                        M.resetCursor()
                        self.mEnable()
                    else:
                        if _get_pos(self.pFinaleAnimList, theObject):
                            pass

    def mLoadKeys(self):
        sd = _sd()
        for daKey in self.pKeyObjectList:
            if sd.mTokenFound(daKey.pTokenName):
                if not daKey.pDropped:
                    daKey.mLoad()

    def mShowKeys(self):
        sd = _sd()
        for daKey in self.pKeyObjectList:
            if sd.mTokenFound(daKey.pTokenName):
                daKey.mShow()

    def mGetDroppedCount(self):
        daCount = 0
        for daKey in self.pKeyObjectList:
            daCount = daCount + (daKey.pDropped or 0)
        return daCount

    def mAllKeysDropped(self):
        daReturnVal = 1
        for daKey in self.pKeyObjectList:
            daReturnVal = min(daReturnVal, daKey.pDropped or 0)
        return daReturnVal

    def mGetName(self): return self.pName
    def mGetType(self): return Sym('SCREEN_CP')
    def mGetEnabled(self): return self.pEnabled

    def mEnable(self):
        self.pEnabled = 1
        call_all(self.pKeyObjectList, 'mEnable')
        _call_if(self.pBackButton, 'mEnable')
        _call_if(self.pHelpButton, 'mEnable')

    def mDisable(self):
        self.pEnabled = 0
        call_all(self.pKeyObjectList, 'mDisable')
        _call_if(self.pBackButton, 'mDisable')
        _call_if(self.pHelpButton, 'mDisable')

    def mUpdate(self): pass
    def mSetParent(self, theObject): self.pParent = theObject

    def mGetHelpState(self):
        if _sd().mLevelSolved() == 0:
            return Sym('CIRCUIT_BOARD')
        return Sym('ALL_FIXED')


# ============================================================================================
# SCREEN_RIDDLE_MICRO  (ParentScript 118): a SCREEN_RIDDLE (ancestor) seen at 1x / 5x / 10x magnification
# ============================================================================================

@lingo_script('SCREEN_RIDDLE_MICRO')
class ScreenRiddleMicro(LObject):
    def __init__(self):
        self.ancestor = None
        self.pBGMemberList = []
        self.pCurrView = Sym('_01X')
        self.pViewButtList = []
        self.pViewList = [Sym('_01X'), Sym('_05X'), Sym('_10X')]
        self.pTransList = []
        self.pTransSound = 0
        self.pTransSprite = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.ancestor = get_object(self.ancestor, theSpriteAlloc)
        self.ancestor._me = self
        self.pTransSprite = pop_one(theSpriteAlloc)
        self.pViewButtList = get_object_list(self.pViewButtList, theSpriteAlloc)
        call_all(self.pViewButtList, 'mSetParent', self)
        return self

    def mLoad(self):
        self.ancestor.mLoad()

    def mLoadList(self, theList):
        self.ancestor.mLoadList(theList)
        theList.extend(self.pBGMemberList)
        call_all(self.pViewButtList, 'mLoadList', theList)
        theList.extend(self.pTransList)
        theList.append(self.pTransSound)

    def mUnLoad(self):
        self.ancestor.mUnload()
        unload_mem(self.pBGMemberList)
        _unload_all(self.pViewButtList)
        unload_mem(self.pTransList)
        unload_mem(self.pTransSound)
    mUnload = mUnLoad

    def mShow(self):
        anc = self.ancestor
        daStashedRiddles = anc.pRiddleObjectList
        anc.pRiddleObjectList = []
        anc.mShow()
        anc.pRiddleObjectList = daStashedRiddles
        self.mSetView()
        if not M.riddlePlayed():
            self.mDisable()

    def mHide(self):
        for daButt in self.pViewButtList:
            daButt.mHide()
        self.ancestor.mHide()

    def mSetView(self, theTransFlag=None):
        anc = self.ancestor
        rt = R()
        if theTransFlag is None:
            theTransFlag = 0
        daIndex = _get_pos_eq(self.pViewList, self.pCurrView)
        call_all(self.pViewButtList, 'mShow')
        self.pViewButtList[daIndex - 1].mDisable(1)
        daBackMember = self.pBGMemberList[daIndex - 1]
        if theTransFlag:
            rt.sound.puppet(1, self.pTransSound)
            S(self.pTransSprite).member = self.pTransList[0]
            _wait_ms(150)
            S(self.pTransSprite).member = self.pTransList[1]
        S(anc.pBGSprite).member = daBackMember
        call_all(anc.pRiddleObjectList, 'mHide')
        call_all(anc.pRiddleObjectList, 'mShowMicro', self.pCurrView)
        if anc.pSolved:
            call_all(anc.pRiddleObjectList, 'mDisable')
            if _eq(self.pCurrView, anc.pEndAniObject.pMicroView):
                anc.pEndAniObject.mShow()
                if anc.pClueFound:
                    anc.pEndAniObject.mDisable()
            else:
                anc.pEndAniObject.mHide()
            if anc.pClueFound and _alive(anc.pSHTokenObject):
                if S(anc.pSHTokenObject.pSprite).member > 1:
                    loc = S(anc.pSHTokenObject.pSprite).loc
                    if not _eq(self.pCurrView, anc.pSHTokenObject.pMicroView):
                        S(anc.pSHTokenObject.pSprite).loc = Point(-600, loc[1])
                    else:
                        S(anc.pSHTokenObject.pSprite).loc = Point(320, loc[1])
        if theTransFlag:
            _wait_ms(150)
            S(self.pTransSprite).member = self.pTransList[2]
            _wait_ms(150)
            S(self.pTransSprite).member = 1
        rt.flush_input()

    def mHandlePlayQueue(self, theObject):
        anc = self.ancestor
        if theObject.mContainsObject(anc.pCurrRiddleObject):
            for daRiddleObject in anc.pRiddleObjectList:
                if (anc.pCurrRiddleObject is not daRiddleObject) and \
                        _eq(anc.pCurrRiddleObject.pName, daRiddleObject.pName):
                    daRiddleObject.mSetFound()
        anc.mHandlePlayQueue(theObject)

    def mSoundDone(self, theObject):
        anc = self.ancestor
        if theObject is anc.pRiddleStripDissapearSound:
            anc.mSoundDone(theObject)
            if not _eq(anc.pEndAniObject.pMicroView, self.pCurrView):
                anc.pEndAniObject.mHide()
        else:
            anc.mSoundDone(theObject)

    def mShowKeyClue(self):
        anc = self.ancestor
        anc.mShowKeyClue()
        if not _eq(anc.pEndAniObject.pMicroView, self.pCurrView):
            anc.pEndAniObject.mHide()

    def mButtonActivated(self, theObject):
        daViewPos = _get_pos(self.pViewButtList, theObject)
        if daViewPos:
            self.pCurrView = self.pViewList[daViewPos - 1]
            self.mSetView(1)
            self.mEnable()
        else:
            self.ancestor.mButtonActivated(theObject)

    def mDisable(self):
        call_all(self.pViewButtList, 'mDisable')
        self.ancestor.mDisable()

    def mEnable(self):
        call_all(self.pViewButtList, 'mEnable')
        self.pViewButtList[_get_pos_eq(self.pViewList, self.pCurrView) - 1].mDisable(1)
        self.ancestor.mEnable()

    def mPlayDone(self, theObject):
        # Not defined in SCREEN_RIDDLE_MICRO's Lingo: it is inherited from the ancestor SCREEN_RIDDLE, and in Lingo `me` inside an
        # inherited handler is still the child. Calling SCREEN_RIDDLE.mPlayDone with the micro screen as self makes
        # self.mHandlePlayQueue / self.mSoundDone reach the micro overrides (twin objects in the other views are marked found,
        # the end-ani object is hidden in the wrong view); the ancestor's own bound method would skip them.
        from .riddle_screens import ScreenRiddle
        ScreenRiddle.mPlayDone(self, theObject)

    def mGetType(self): return Sym('SCREEN_RIDDLE_MICRO')
    def mGetHelpState(self): return 0


def _get_pos_eq(lst, item):
    for i, x in enumerate(lst or []):
        if _eq(x, item):
            return i + 1
    return 0
