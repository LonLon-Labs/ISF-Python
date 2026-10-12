"""GameDaddy (ParentScript 29) and GAME (ParentScript 30) of I Spy Fantasy, ported 1:1 from the Lingo.

GameDaddy is the root object (movie.getGameDaddy()): it owns the list of "games" -- the MAIN SCREENDADDY (bump,
sign-in, main menu, credits) and the three GAME objects #S, #b, #D -- and switches between them (mGoToGame).

GAME wraps a SCREENDADDY through Lingo's `ancestor`: anything GAME doesn't define (mNavigate, mShow, mHide,
mGetScreen, ...) is delegated to the SCREENDADDY instance by LObject.__getattr__. The ancestor only exists after
mInitGameObjects (data comes from movie.getGameData(pName, pCurrentVersion)).

Method names follow the Lingo, including the case used in the .ls files where the rest of the port already has
a convention (the port uses mUnload / mUnload, the Lingo spells mUnLoad).
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list, destroy_object
from .lingo import Sym, set_properties, pop_one, random_


def _alive(o):
    """objectp(o)"""
    return isinstance(o, LObject)


def _new(ref, *a):
    from .core import new_script
    return new_script(ref, *a)


# ----------------------------------------------------------------------------------------------
@lingo_script('GameDaddy')                                # ParentScript 29 (id 131101)
class GameDaddy(LObject):
    def __init__(self):
        self.pGameList = []
        self.pCurrentGame = 0
        self.pSavedList = []
        self.pRiddlePlayed = 0
        self.pLowEndPrimerAnim = 0
        self.pLoadWaitTimer = 0
        self.pLoaderObject = 0
        self.pTimerScriptNumber = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        # getObjectList(pGameList, theSpriteAlloc, theSpriteAlloc.count): every game gets its own copy of all channels
        self.pGameList = get_object_list(self.pGameList, alloc, len(alloc))
        self.pCurrentGame = self.pGameList[0]
        self.pLowEndPrimerAnim = get_object(self.pLowEndPrimerAnim, [2, 3])
        if _alive(self.pLowEndPrimerAnim):
            self.pLowEndPrimerAnim.mSetParent(self)
        self.pLoadWaitTimer = 0
        self.pRiddlePlayed = 0
        self.pSavedList = [Sym('pRiddlePlayed')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self): pass

    def mLoad(self): self.pCurrentGame.mLoad()
    def mUnload(self): self.pCurrentGame.mUnload()

    def mShow(self):
        if M.isMac():
            self.pLowEndPrimerAnim.mShow()
            self.pLowEndPrimerAnim.mPlay()
        else:
            # hold the first screen back until the game has been up for 2 s (250 ms if loading took longer)
            self.pLoadWaitTimer = _new(self.pTimerScriptNumber)
            since = runtime.rt.milliseconds() - M.gLoadStart
            if since < 2000:
                self.pLoadWaitTimer.pTimeOutLength = 2000 - since
            else:
                self.pLoadWaitTimer.pTimeOutLength = 250
            self.pLoadWaitTimer.pParent = self
            self.pLoadWaitTimer.mPlay()

    def mHide(self): self.pCurrentGame.mHide()

    def mPlayDone(self, obj):
        if obj is self.pLowEndPrimerAnim:
            self.pLowEndPrimerAnim.mHide()
            self.pCurrentGame.mShow()
        elif obj is self.pLoadWaitTimer:
            self.pLoadWaitTimer.mKill()
            self.pCurrentGame.mShow()

    def mGoToGame(self, theGame):
        daNewGame = self.mGetGame(theGame)
        if _alive(daNewGame):
            M.waitCursor()
            if _alive(self.pCurrentGame):
                M.clearAmbientSound()
                self.pCurrentGame.mHide()
                self.pCurrentGame.mUnload()
                # (Lingo: unloadMember(); loadCursors() -- Director memory management, nothing to do)
                self.pCurrentGame.mReleasePoolObjects()
                if self.pCurrentGame.mGetType() == 'GAME':
                    self.pCurrentGame.mSave()
                    self.pCurrentGame.mDestroy()
            daGameCastExternal = M.changeGameCast(theGame)
            M.setCurrentGame(daNewGame)
            self.pCurrentGame = daNewGame
            if daNewGame.mGetType() == 'GAME':
                daNewGame.mInitGameObjects()
            self.pCurrentGame.mInitPoolObjects()
            daNewGame.mLoad()
            self.pCurrentGame.mShow()
            M.changeRiddleCast('EXTERNAL')
            if not daGameCastExternal:
                runtime.rt.update_stage()
                M.changeGameCast('EXTERNAL')

    def mSaveGames(self):
        for daGame in self.pGameList:
            if daGame.mGetType() == 'GAME':
                daGame.mSave()

    def mGetCurrentGame(self): return self.pCurrentGame

    def mGameSolvedCount(self):
        n = 0
        for daGame in self.pGameList:
            if daGame.mGetType() == 'GAME':
                n += daGame.pIsSolved
        return n

    def mGetGame(self, theName):
        for daGame in self.pGameList:
            if daGame.mGetName() == theName:
                return daGame
        return 0

    def mGetSolvedUserNotify(self):
        for daGame in self.pGameList:
            if daGame.mGetType() == 'GAME':
                if daGame.mGetSolvedUserNotify():
                    return 1
        return 0

    def mGetType(self): return Sym('GAMEDADDY')


# ----------------------------------------------------------------------------------------------
@lingo_script('GAME')                                     # ParentScript 30
class Game(LObject):
    def __init__(self):
        # the Lingo `property` list; anything else assigned in a handler is a local variable there
        self.pName = None
        self.pSaveLoadObject = 0
        self.pVersionPool = []
        self.pVersionList = []
        self.pAllVersionsPlayed = 0
        self.pCurrentVersion = None
        self.pSavedList = []
        self.pIsSolved = 0
        self.pSpriteAlloc = []
        self.pHelpButton = 0
        self.pBackButton = 0
        self.pHomeButton = 0
        self.pRiddleStripObject = 0
        self.pClueStripObject = 0
        self.pSessionCount = 0
        self.pWiggleSoundList = []
        self.pWigglePool = []
        self.pIntroList = []
        self.pTokenCollectorList = []
        self.pCurrentCollectorIndex = 1
        self.ancestor = 0
        self.pScavengerHuntManager = 0
        self.pReminderAudio = 0
        self.pEndAnim = 0
        self.pSolvedUserNotified = 0
        self.pHelpPlayer = 0
        self.pClueFound = 0
        self.pShowDSSH = 1
        self.pHackUsed = 0
        self.pSaveLoadScriptNumber = 0

    # ---- lifecycle ---------------------------------------------------------------------------
    def mInit(self, data, alloc):
        self.pShowDSSH = 1
        set_properties(data, self)
        self.pSpriteAlloc = list(alloc)
        self.pClueFound = 0
        self.pSessionCount = 0
        self.pSolvedUserNotified = 0
        self.pIsSolved = 0
        self.pCurrentCollectorIndex = 1
        self.pVersionList = [Sym('a'), Sym('b'), Sym('c')]
        self.pVersionPool = list(self.pVersionList)
        self.pAllVersionsPlayed = 0
        self.pCurrentVersion = pop_one(self.pVersionPool)
        self.pSaveLoadObject = 0
        self.ancestor = 0
        self.pReminderAudio = 0
        self.pHackUsed = 0
        self.pSavedList = [Sym(n) for n in (
            'pCurrentVersion', 'pIsSolved', 'pVersionPool', 'pCurrentCollectorIndex', 'pSessionCount',
            'pAllVersionsPlayed', 'pSolvedUserNotified', 'pClueFound', 'pHackUsed')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        if _alive(self.ancestor):
            self.ancestor.mDestroy()
            self.ancestor = 0
            for daCollector in self.pTokenCollectorList or []:
                destroy_object(daCollector, self)
            self.pTokenCollectorList = []
            for daObject in self.pIntroList or []:
                destroy_object(daObject, self)
            self.pIntroList = []
            destroy_object(self.pRiddleStripObject, self)
            self.pRiddleStripObject = 0
            destroy_object(self.pClueStripObject, self)
            self.pClueStripObject = 0
            if self.pScavengerHuntManager != 0:
                destroy_object(self.pScavengerHuntManager, self)
                self.pScavengerHuntManager = 0
            destroy_object(self.pHomeButton, self)
            self.pHomeButton = 0
            destroy_object(self.pBackButton, self)
            self.pBackButton = 0
            destroy_object(self.pHelpButton, self)
            self.pHelpButton = 0
            destroy_object(self.pEndAnim, self)
            self.pEndAnim = 0
            destroy_object(self.pHelpPlayer, self)
            self.pHelpPlayer = 0
            if _alive(self.pReminderAudio):
                destroy_object(self.pReminderAudio, self)
                self.pReminderAudio = 0
            if _alive(self.pSaveLoadObject):
                self.pSaveLoadObject.mDestroy()
                self.pSaveLoadObject = 0

    def mGetType(self): return Sym('GAME')
    def mGetName(self): return self.pName

    def mUnload(self):
        self.pHomeButton.mUnload()
        self.pBackButton.mUnload()
        self.pHelpButton.mUnload()
        if _alive(self.pScavengerHuntManager):
            self.pScavengerHuntManager.mUnload(1)
        self.pRiddleStripObject.mUnload()
        self.pClueStripObject.mUnload()
        self.ancestor.mUnload()
        if _alive(self.pReminderAudio):
            self.pReminderAudio.mClearSound()
        if _alive(self.pEndAnim):
            self.pEndAnim.mUnload()

    def mLoadList(self, *a): pass

    def mLoad(self):
        self.pHomeButton.mLoad()
        self.pBackButton.mLoad()
        self.pHelpButton.mLoad()
        self.ancestor.mLoad()
        if self.mGetLevel() == 2 and self.mRemainingTokenCount():
            self.pScavengerHuntManager.mLoad()

    def mGameInProgress(self):
        if _alive(self.ancestor):
            daScreen = self.ancestor.pScreenList[0]
            return daScreen.pIntroPlayed
        return 0

    def mInitGameObjects(self, *_):
        daPath = M.getPlayerDir()
        self.pSaveLoadObject = _new(self.pSaveLoadScriptNumber, daPath, str(self.pName))
        M.setSaveLoadObject(self.pSaveLoadObject)
        if self.pIsSolved:
            self.pSaveLoadObject.mDeleteFile()
            self.mNextVersion()
            self.pIsSolved = 0
            self.pCurrentCollectorIndex = 1
        if not _alive(self.ancestor):
            self.pSessionCount += 1
            daGameData = M.getGameData(self.pName, self.pCurrentVersion)
            set_properties(daGameData, self)
            daAlloc = list(self.pSpriteAlloc)
            self.ancestor = get_object(self.ancestor, daAlloc)
            self.pRiddleStripObject = get_object(self.pRiddleStripObject, daAlloc)
            self.pClueStripObject = get_object(self.pClueStripObject, daAlloc)
            self.pScavengerHuntManager = get_object(self.pScavengerHuntManager, daAlloc)
            if _alive(self.pScavengerHuntManager):
                self.pScavengerHuntManager.mSetParent(self)
            self.pHomeButton = get_object(self.pHomeButton, daAlloc)
            self.pBackButton = get_object(self.pBackButton, daAlloc)
            self.pHelpButton = get_object(self.pHelpButton, daAlloc)
            self.pHomeButton.mSetParent(self)
            self.pEndAnim = get_object(self.pEndAnim, daAlloc)
            self.pEndAnim.mSetParent(self)
            self.pIntroList = get_object_list(self.pIntroList, daAlloc)
            self.pReminderAudio = get_object(self.pReminderAudio, daAlloc)
            self.pTokenCollectorList = get_object_list(self.pTokenCollectorList, [])
            self.pWigglePool = list(self.pWiggleSoundList)
            self.pHelpPlayer = get_object(self.pHelpPlayer, [])
            self.pHelpPlayer.mSetParent(self)
        self.pSaveLoadObject.mRestore()

    def mInitPoolObjects(self):
        self.pHelpPlayer.mInitPoolObjects()
        self.mInitScavengerHuntPoolObjects()
        self.ancestor.mInitPoolObjects()

    def mReleasePoolObjects(self):
        self.pHelpPlayer.mReleasePoolObjects()
        self.mReleaseScavengerHuntPoolObjects()
        self.ancestor.mReleasePoolObjects()

    def mNextVersion(self):
        if self.pVersionPool:
            if not self.pAllVersionsPlayed:
                self.pCurrentVersion = pop_one(self.pVersionPool)
            else:
                idx = random_(len(self.pVersionPool))
                self.pCurrentVersion = self.pVersionPool.pop(idx - 1)
        else:
            daOldVersion = self.pCurrentVersion
            self.pAllVersionsPlayed = 1
            self.pVersionPool = list(self.pVersionList)
            self.pVersionPool.remove(daOldVersion)
            self.mNextVersion()
            self.pVersionPool.append(daOldVersion)

    # ---- tokens ---------------------------------------------------------------------------------
    def _tc(self):
        return self.pTokenCollectorList[self.pCurrentCollectorIndex - 1]

    def mAddToken(self, theToken):
        daTokenCollector = self._tc()
        daReturnVal = daTokenCollector.mAddToken(theToken)
        if daReturnVal and daTokenCollector.mIsComplete():
            pass                                  # (empty in the Lingo)
        # (the Lingo handler returns nothing)

    def mREmoveToken(self, theToken): self._tc().mREmoveToken(theToken)
    mRemoveToken = mREmoveToken

    def mNextLevel(self):
        if self.pCurrentCollectorIndex == len(self.pTokenCollectorList):
            self.pIsSolved = 1
        else:
            self.pCurrentCollectorIndex += 1

    def mLevelSolved(self): return self._tc().mIsComplete()
    def mTokenFoundCount(self): return self._tc().mTokenFoundCount()
    def mAllTokensFound(self): return self._tc().mRemainingTokenCount()     # (sic: the Lingo returns the remaining count)
    def mRemainingTokenCount(self): return self._tc().mRemainingTokenCount()
    def mGetLevel(self): return self.pCurrentCollectorIndex
    def mIsSolved(self): return self.pIsSolved
    def mTokenFound(self, theToken): return self._tc().mTokenFound(theToken)
    def mNextToken(self): return self._tc().mNextToken()

    def mShowHomeButton(self):
        if self.pIsSolved:
            self.pHomeButton.mSetParent(self)
            self.pHomeButton.mShow()

    def mHideHomeButton(self):
        if self.pIsSolved:
            self.pHomeButton.mHide()

    def mButtonActivated(self, theObject):
        if theObject is self.pHomeButton:
            M.gGameDaddy.mGoToGame(Sym('MAIN'))

    def mButtonDeActivated(self, theObject): pass

    # ---- scavenger hunt (only active on level 2) -------------------------------------------------------
    def _hunt(self):
        return self.pCurrentCollectorIndex == 2 and _alive(self.pScavengerHuntManager)

    def mLoadScavengerHunt(self):
        if self._hunt():
            if not self.pScavengerHuntManager.mAllTokensFound():
                self.pScavengerHuntManager.mLoad()
            else:
                self.pScavengerHuntManager.mLoadFoundTokens()

    def mInitScavengerHuntPoolObjects(self):
        if self._hunt():
            self.pScavengerHuntManager.mInitPoolObjects()

    def mReleaseScavengerHuntPoolObjects(self):
        if self._hunt():
            self.pScavengerHuntManager.mReleasePoolObjects()

    def mLoadScavengerHuntlist(self, theList):
        if self._hunt():
            if not self.pScavengerHuntManager.mAllTokensFound():
                self.pScavengerHuntManager.mLoadList(theList)
            else:
                self.pScavengerHuntManager.mLoadFoundTokensList(theList)

    def mUnloadScavengerHunt(self):
        if self._hunt():
            if not self.pScavengerHuntManager.mAllTokensFound():
                self.pScavengerHuntManager.mUnload(1)

    def mShowScavengerHunt(self):
        if self._hunt():
            if not self.pScavengerHuntManager.mAllTokensFound():
                self.pScavengerHuntManager.mShow()
            else:
                self.pScavengerHuntManager.mShowFoundTokens()

    def mHideScavengerHunt(self):
        if self._hunt():
            self.pScavengerHuntManager.mHide()

    def mGetCurrentHuntName(self):
        if self._hunt():
            return self.pScavengerHuntManager.mGetCurrentHuntName()
        return 0

    def mExternalSHTokenFound(self, theObject=None):
        if _alive(self.pScavengerHuntManager):
            self.pScavengerHuntManager.mExternalSHTokenFound()

    # ---- finale -------------------------------------------------------------------------------
    def mPlayFinale(self):
        self.ancestor.pCurrentScreen.mDisable()
        self.pIsSolved = 1
        M.waitCursor()
        self.mLoadFinale()
        self.pEndAnim.mPlay()

    def mPlayDone(self, theObject):
        if theObject is self.pEndAnim:
            rt = runtime.rt
            anc = self.ancestor
            newScreen = anc.pScreenList[0]
            anc.pCurrentScreen.mHide()
            rt.blank_sprite_range(1, 150)
            if newScreen is not anc.pCurrentScreen:
                anc.pCurrentScreen.mUnload()
                anc.pCurrentScreen.mReleasePoolObjects()
                anc.pPreviousScreen = anc.pCurrentScreen
                anc.pCurrentScreen = newScreen
                M.setCurScreen(anc.pCurrentScreen)
                newScreen.mInitPoolObjects()
            else:
                anc.pPreviousScreen = 0
            newScreen.mShow()
            M.resetCursor()

    def _master(self):
        return self.ancestor.pScreenList[0]

    def mLoadFinale(self):
        if _alive(self.pEndAnim):
            daMasterScreen = self._master()
            if self.ancestor.pCurrentScreen is not daMasterScreen:
                if daMasterScreen.mGetType() == 'SCREEN_MASTER':
                    daMasterScreen.mLoadFinale()
            self.pEndAnim.mLoad()

    def mLoadFinaleList(self, theList):
        if _alive(self.pEndAnim):
            daMasterScreen = self._master()
            if self.ancestor.pCurrentScreen is not daMasterScreen:
                if daMasterScreen.mGetType() == 'SCREEN_MASTER':
                    daMasterScreen.mLoadFinaleList(theList)
            self.pEndAnim.mLoadList(theList)

    def mUnloadFinale(self):
        if _alive(self.pEndAnim):
            daMasterScreen = self._master()
            if self.ancestor.pCurrentScreen is not daMasterScreen:
                if daMasterScreen.mGetType() == 'SCREEN_MASTER':
                    daMasterScreen.mUnloadFinale()
            self.pEndAnim.mUnload()

    # ---- misc ---------------------------------------------------------------------------------
    def mSave(self):
        if _alive(self.pSaveLoadObject):
            self.pSaveLoadObject.mSave()

    def mCheckStatus(self):
        if _alive(self.pReminderAudio):
            return self.pReminderAudio.mCheckStatus()

    def mEnableReminders(self):
        if _alive(self.pReminderAudio):
            return self.pReminderAudio.mEnable()

    def mClearReminderAudio(self):
        if _alive(self.pReminderAudio):
            self.pReminderAudio.mClearSound()

    def mGetIntro(self):
        if not self.pAllVersionsPlayed:
            daPos = self.pVersionList.index(self.pCurrentVersion) + 1
            return self.pIntroList[daPos - 1]
        return self.pIntroList[0]

    def mGetWiggleSound(self):
        wigCount = len(self.pWigglePool)
        if wigCount:
            sndIdx = random_(wigCount)
            sndid = self.pWigglePool.pop(sndIdx - 1)
            if wigCount == 1:
                self.pWigglePool = list(self.pWiggleSoundList)
                if sndid in self.pWigglePool:
                    self.pWigglePool.remove(sndid)
            return sndid
        return 0

    def mDisable(self):
        if _alive(self.ancestor):
            self.ancestor.pCurrentScreen.mDisable()
        if _alive(self.pScavengerHuntManager):
            self.pScavengerHuntManager.mDisable()
        if _alive(self.pReminderAudio):
            self.pReminderAudio.mDisable()

    def mEnable(self):
        if _alive(self.ancestor):
            self.ancestor.pCurrentScreen.mEnable()
        if _alive(self.pScavengerHuntManager):
            self.pScavengerHuntManager.mEnable()
        if _alive(self.pReminderAudio):
            self.pReminderAudio.mEnable()

    def mGetSolvedUserNotify(self):
        if self.pIsSolved and not self.pSolvedUserNotified:
            self.pSolvedUserNotified = 1
            return 1

    def mGetCurrentVersion(self): return self.pCurrentVersion

    def mGetClueFound(self):
        self.pClueFound = max(self.pClueFound, self.mTokenFoundCount())
        return self.pClueFound

    def mYoungersterCantFindKeys(self):
        return self.mAllRiddlesSolved() and self.mTokenFoundCount() == 0

    def mAllRiddlesSolved(self):
        daSolvedCount = 0
        daRiddleCount = 0
        for daScreen in self.ancestor.pScreenList:
            anc = daScreen.__dict__.get('ancestor')
            if isinstance(anc, LObject):          # voidp(getaProp(daScreen, #ancestor)) = false
                daScreen = anc
            if daScreen.mGetType() == 'SCREEN_RIDDLE':
                daRiddleCount += 1
                daSolvedCount += daScreen.pSolved
        return daSolvedCount == daRiddleCount

    def mShowDynamicStates(self):
        return max(self.mGetLevel() == 1, self.pShowDSSH)
