"""GAME (ParentScript 25), ported 1:1. Replaces the first-draft Game class in core.py.

GAME wraps SCREENDADDY through Lingo's `ancestor`: anything GAME doesn't define (mNavigate, mShow,
mHide, mGetScreen, ...) is delegated to the SCREENDADDY instance by LObject.__getattr__.
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list, destroy_object
from .lingo import Sym, set_properties, pop_one, random_
from .stubs import MissingScript


def _alive(o):
    return isinstance(o, LObject)


def _new(ref, *a):
    from .core import new_script
    return new_script(ref, *a)


@lingo_script('GAME')
class Game(LObject):
    def __init__(self):
        self.ancestor = None
        self.pSaveLoadObject = 0

    # ---- lifecycle ---------------------------------------------------------------------------
    def mInit(self, data, alloc):
        self.pRiddlePlayed = 0
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
        object.__setattr__(self, 'ancestor', get_object(self.ancestor, alloc))
        self.pHelpPlayer = get_object(self.pHelpPlayer, [])
        if _alive(self.pHelpPlayer):
            self.pHelpPlayer.mInitPoolObjects()
            self.pHelpPlayer.mSetParent(self)
        self.pReminderAudio = 0
        self.pHackUsed = 0
        self.pOpenAnimPlayed = 0
        self.pSavedList = [Sym(n) for n in (
            'pRiddlePlayed', 'pCurrentVersion', 'pIsSolved', 'pVersionPool', 'pCurrentCollectorIndex',
            'pSessionCount', 'pAllVersionsPlayed', 'pSolvedUserNotified', 'pClueFound', 'pHackUsed',
            'pOpenAnimPlayed')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        for scr in list(self.pLevelScreenList or []):
            lst = self.ancestor.pScreenList
            if scr in lst:
                lst.remove(scr)
                destroy_object(scr)
        self.pLevelScreenList = []
        for c in self.pTokenCollectorList or []:
            destroy_object(c, self)
        self.pTokenCollectorList = []
        for attr in ('pRiddleStripObject',):
            destroy_object(getattr(self, attr), self)
            setattr(self, attr, 0)
        if self.pScavengerHuntManager != 0:
            destroy_object(self.pScavengerHuntManager, self)
            self.pScavengerHuntManager = 0
        for attr in ('pHomeButton', 'pBackButton', 'pHelpButton', 'pEndAnim', 'pLipsButton'):
            destroy_object(getattr(self, attr), self)
            setattr(self, attr, 0)
        if _alive(self.pReminderAudio):
            destroy_object(self.pReminderAudio, self)
            self.pReminderAudio = 0
        if _alive(self.pSaveLoadObject):
            self.pSaveLoadObject.mDestroy()
            self.pSaveLoadObject = 0

    def mGetType(self): return Sym('GAME')
    def mGetName(self): return self.pName
    def mGetCurrentVersion(self): return self.pCurrentVersion
    def mGetSessionCount(self): return self.pSessionCount
    def mLoadList(self, *a): pass
    def mLoad(self): self.ancestor.mLoad()
    def mButtonActivated(self, o): pass
    def mButtonDeActivated(self, o): pass

    def mUnload(self):
        for attr in ('pHomeButton', 'pBackButton', 'pHelpButton'):
            if _alive(getattr(self, attr)):
                getattr(self, attr).mUnload()
        if _alive(self.pScavengerHuntManager):
            self.pScavengerHuntManager.mUnload(1)
        if _alive(self.pRiddleStripObject):
            self.pRiddleStripObject.mUnload()
        if _alive(self.ancestor):
            self.ancestor.mUnload()
        if _alive(self.pReminderAudio):
            self.pReminderAudio.mClearSound()
        if _alive(self.pEndAnim):
            self.pEndAnim.mUnload()

    def mGameInProgress(self):
        if _alive(self.ancestor):
            return self.ancestor.pScreenList[0].pIntroPlayed
        return 0

    def mInitGameObjects(self, noRestore=None):
        stashed = self.ancestor
        object.__setattr__(self, 'ancestor', None)
        self.pSaveLoadObject = _new(self.pSaveLoadScriptNumber, M.getPlayerDir(), str(self.pName))
        M.setSaveLoadObject(self.pSaveLoadObject)
        if self.pIsSolved:
            self.pSaveLoadObject.mDeleteFile()
            self.mNextVersion()
            self.pIsSolved = 0
            self.pCurrentCollectorIndex = 1
        self.pSessionCount += 1
        set_properties(M.getGameData(self.pCurrentVersion), self)
        alloc = list(self.pSpriteAlloc)
        self.pLevelScreenList = get_object_list(self.pLevelScreenList, alloc, 100)
        for scr in self.pLevelScreenList:
            stashed.pScreenList.append(scr)
        self.pRiddleStripObject = get_object(self.pRiddleStripObject, alloc)
        self.pClueStripObject = get_object(self.pClueStripObject, alloc)
        self.pScavengerHuntManager = get_object(self.pScavengerHuntManager, alloc)
        if _alive(self.pScavengerHuntManager):
            self.pScavengerHuntManager.mSetParent(self)
        for attr in ('pHomeButton', 'pBackButton', 'pHelpButton', 'pLipsButton'):
            setattr(self, attr, get_object(getattr(self, attr), alloc))
        for attr in ('pHomeButton', 'pBackButton', 'pHelpButton', 'pLipsButton'):
            getattr(self, attr).mLoad()
        self.pHomeButton.mSetParent(self)
        self.pEndAnim = get_object(self.pEndAnim, alloc)
        self.pEndAnim.mSetParent(self)
        self.pReminderAudio = get_object(self.pReminderAudio, alloc)
        self.pTokenCollectorList = get_object_list(self.pTokenCollectorList, [])
        self.pWigglePool = list(self.pWiggleSoundList)
        if noRestore != 1:
            self.pSaveLoadObject.mRestore()
        object.__setattr__(self, 'ancestor', stashed)

    def mInitPoolObjects(self):
        self.pHelpPlayer.mInitPoolObjects()
        self.mInitScavengerHuntPoolObjects()
        self.ancestor.mInitPoolObjects()

    def mReleasePoolObjects(self):
        if _alive(self.pHelpPlayer):
            self.pHelpPlayer.mReleasePoolObjects()
        self.mReleaseScavengerHuntPoolObjects()
        if _alive(self.ancestor):
            self.ancestor.mReleasePoolObjects()

    def mSetVersion(self, v):
        """Choose the game version (a / b / c) outright -- used by the 'Choose an Ending' screen. The pool keeps the
        other two so mNextVersion() still rotates through them afterwards."""
        v = Sym(str(v).lower())
        self.pCurrentVersion = v
        self.pVersionPool = [x for x in self.pVersionList if str(x).lower() != str(v).lower()]

    def _remember_version(self):
        """Write '<save name>.VER' so the next sign-in loads the game data of this version."""
        try:
            from . import version_picker
            if M.getPlayerDir():
                version_picker.write_version(M.getPlayerDir(), self.pName, self.pCurrentVersion)
        except Exception as e:
            print('[game] could not remember the version:', e)

    def mNextVersion(self):
        if self.pVersionPool:
            self.pCurrentVersion = pop_one(self.pVersionPool)
            self._remember_version()
        else:
            self.pVersionPool = list(self.pVersionList)
            self.mNextVersion()

    # ---- tokens ---------------------------------------------------------------------------------
    def _tc(self):
        return self.pTokenCollectorList[self.pCurrentCollectorIndex - 1]

    def mAddToken(self, t): return self._tc().mAddToken(t)
    def mREmoveToken(self, t): self._tc().mREmoveToken(t)
    mRemoveToken = mREmoveToken
    def mLevelSolved(self): return self._tc().mIsComplete()
    def mTokenFoundCount(self): return self._tc().mTokenFoundCount()
    def mRemainingTokenCount(self): return self._tc().mRemainingTokenCount()
    def mAllTokensFound(self): return self.mRemainingTokenCount() == 0
    def mTokenFound(self, t): return self._tc().mTokenFound(t)
    def mNextToken(self): return self._tc().mNextToken()
    def mGetLevel(self): return self.pCurrentCollectorIndex
    def mIsSolved(self): return self.pIsSolved

    def mNextLevel(self):
        self.pCurrentCollectorIndex = min(self.pCurrentCollectorIndex + 1, len(self.pTokenCollectorList))

    def mShowHomeButton(self):
        if self.pIsSolved:
            self.pHomeButton.mSetParent(self)
            self.pHomeButton.mShow()

    def mHideHomeButton(self):
        if self.pIsSolved:
            self.pHomeButton.mHide()

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

    def mLoadScavengerHuntlist(self, lst):
        if self._hunt():
            if not self.pScavengerHuntManager.mAllTokensFound():
                self.pScavengerHuntManager.mLoadList(lst)
            else:
                self.pScavengerHuntManager.mLoadFoundTokensList(lst)

    def mEnableScavengerHunt(self):
        if self._hunt():
            self.pScavengerHuntManager.mEnable()

    def mDisableScavengerHunt(self):
        if self._hunt():
            self.pScavengerHuntManager.mDisable()

    def mUnloadScavengerHunt(self):
        if self._hunt() and not self.pScavengerHuntManager.mAllTokensFound():
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
        return self.pScavengerHuntManager.mGetCurrentHuntName() if self._hunt() else 0

    def mSetHuntIndex(self, i):
        if self._hunt():
            self.pScavengerHuntManager.mSetHuntIndex(i)

    def mGetHuntIndex(self):
        return self.pScavengerHuntManager.mGetHuntIndex() if _alive(self.pScavengerHuntManager) else 0

    def mExternalSHTokenFound(self, _=None):
        if _alive(self.pScavengerHuntManager):
            self.pScavengerHuntManager.mExternalSHTokenFound()

    # ---- finale -------------------------------------------------------------------------------
    def mPlayFinale(self):
        M.clearAmbientSound()
        self.ancestor.pCurrentScreen.mDisable()
        self.pIsSolved = 1
        M.waitCursor()
        self.mLoadFinale()
        self.pEndAnim.mPlay()

    def mPlayDone(self, obj):
        if obj is self.pEndAnim:
            cs = self.ancestor.pCurrentScreen
            cs.mUnload()
            cs.mHide()
            cs.mReleasePoolObjects()
            self.ancestor.pCurrentScreen = 0
            if self.pCurrentVersion != Sym('c'):
                self.mDestroy()
                self.mInitGameObjects(1)
                self.mSetDisableUpdateMode()
                self.mNavigate(Sym('MAIN'))
                M.resetCursor()
            else:
                self.pOpenAnimPlayed = 0
                self.mSetCreditReturn(Sym('quit'))
                self.mSetDisableUpdateMode()
                self.mNavigate(Sym('credit'))

    def _master(self):
        return self.ancestor.pScreenList[0]

    def mLoadFinale(self):
        if _alive(self.pEndAnim):
            m = self._master()
            if self.ancestor.pCurrentScreen is not m and str(m.mGetType()).upper() == 'SCREEN_MASTER':
                m.mLoadFinale()
            self.pEndAnim.mLoad()

    def mLoadFinaleList(self, lst):
        if _alive(self.pEndAnim):
            m = self._master()
            if self.ancestor.pCurrentScreen is not m and str(m.mGetType()).upper() == 'SCREEN_MASTER':
                m.mLoadFinaleList(lst)
            self.pEndAnim.mLoadList(lst)

    def mUnloadFinale(self):
        if _alive(self.pEndAnim):
            m = self._master()
            if self.ancestor.pCurrentScreen is not m and str(m.mGetType()).upper() == 'SCREEN_MASTER':
                m.mUnloadFinale()
            self.pEndAnim.mUnload()

    def mSetCreditReturn(self, screen):
        c = self.ancestor.mGetScreen(Sym('credit'))
        if _alive(c):
            c.pReturnScreen = screen

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

    def mGetWiggleSound(self):
        n = len(self.pWigglePool)
        if not n:
            return 0
        idx = random_(n)
        snd = self.pWigglePool.pop(idx - 1)
        if n == 1:
            self.pWigglePool = list(self.pWiggleSoundList)
            if snd in self.pWigglePool:
                self.pWigglePool.remove(snd)
        return snd

    def mDisable(self):
        if _alive(self.ancestor.pCurrentScreen):
            self.ancestor.pCurrentScreen.mDisable()
        self.mDisableScavengerHunt()
        if _alive(self.pReminderAudio):
            self.pReminderAudio.mDisable()

    def mEnable(self):
        if _alive(self.ancestor):
            self.ancestor.pCurrentScreen.mEnable()
        self.mEnableScavengerHunt()
        if _alive(self.pReminderAudio):
            self.pReminderAudio.mEnable()

    def mGetSolvedUserNotify(self):
        if self.pIsSolved and not self.pSolvedUserNotified:
            self.pSolvedUserNotified = 1
            return 1

    def mGetClueFound(self):
        self.pClueFound = max(self.pClueFound, self.mTokenFoundCount())
        return self.pClueFound

    def _riddles(self):
        for scr in self.ancestor.pScreenList:
            anc = scr.__dict__.get('ancestor')
            if isinstance(anc, dict):
                continue                     # unported ancestor, not a translated screen
            if anc is not None:
                scr = anc
            if str(scr.mGetType()).upper() == 'SCREEN_RIDDLE':
                yield scr

    def mAllRiddlesSolved(self):
        rs = list(self._riddles())
        return sum(1 for r in rs if r.pSolved) == len(rs)

    def mYoungersterCantFindKeys(self):
        return self.mAllRiddlesSolved() and self.mTokenFoundCount() == 0

    def mGetSolvedRiddleCount(self):
        return sum(1 for r in self._riddles() if r.pSolved)

    def mGetEndRiddleAudio(self):
        c = min(self.mTokenFoundCount() + 1, len(self.pRewardAudioList))
        return self.pRewardAudioList[c - 1]

    def mShowDynamicStates(self):
        return max(self.mGetLevel() == 1, self.pShowDSSH)
