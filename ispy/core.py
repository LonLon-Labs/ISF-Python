"""Hand-ported parent scripts (1:1 with the Lingo, method names kept so they can be diffed).

Ported so far:  LOADER (28), TIMER (112), SCREENDADDY (29), GAME (25)  +  the movie-script helpers
that they call (MAIN_MOVIE 23 / General Handlers 24) in movie.py.
Everything else resolves to stubs.MissingScript until ported.
"""
from . import runtime
from .runtime import (LObject, lingo_script, get_object, get_object_list, destroy_object,
                      REGISTRY, SCRIPT_IDS)
from .lingo import (set_properties, pop_one, pop_last, pop_list, random_, get_range_list, Sym)
from . import movie as M
from .stubs import MissingScript


def new_script(ref, *args):
    name = SCRIPT_IDS.get(ref, ref)
    cls = REGISTRY.get(str(name).lower())
    return cls(*args) if cls else MissingScript(name)


def _rt():
    return runtime.rt


def _screen_desc(s):
    """'SCREEN_RIDDLE_MAG <name>' for a ported screen, 'UNPORTED SCREEN_ROCKET <name>' for a MissingScript stub."""
    if isinstance(s, MissingScript):
        return 'UNPORTED %s %s' % (s._name, s.__dict__.get('pName'))
    if not s:
        return '(none)'
    return '%s %s' % (type(s).__name__, getattr(s, 'pName', None))


# ------------------------------------------------------------------------------------------
@lingo_script('LOADER')                                   # ParentScript 28
class Loader(LObject):
    def __init__(self):
        self.pLoadList = 0
        self.pParent = 0
        self.pCurIndex = 0
        self.pMinTime = 0
        self.pFlushCount = 0

    def mInit(self, *a): pass
    def mDestroy(self): pass
    def mSetParent(self, obj): self.pParent = obj
    def mSetLoadList(self, lst): self.pLoadList = lst
    def mGetType(self): return Sym('LOADER')

    def mPlay(self, dontFlush=None):
        rt = _rt()
        self.pCurIndex = 0
        self.pMinTime = rt.milliseconds() + 700
        for m in self.pLoadList:
            self.mLoadItem(m)
        self.pCurIndex = len(self.pLoadList)
        if not dontFlush:
            self.pFlushCount = 2
            M.addUpdateList(self)
        else:
            self.pParent.mPlayDone(self)

    def mStop(self):
        M.removeUpdateList(self)
        self.pParent.mPlayDone(self)

    def mLoadItem(self, m):
        if isinstance(m, (list, tuple)):
            for i in m:
                self.mLoadItem(i)
        elif isinstance(m, int):
            if m:
                _rt().image(m)               # preloadMember -> warm the image cache
        elif isinstance(m, LObject) or hasattr(m, 'mLoad'):
            m.mLoad()

    def mUpdate(self):
        self.pCurIndex += 1
        if self.pCurIndex <= len(self.pLoadList):
            self.mLoadItem(self.pLoadList[self.pCurIndex - 1])
        elif _rt().milliseconds() > self.pMinTime:
            M.removeUpdateList(self)
            self.pParent.mPlayDone(self)
        else:
            self.pFlushCount -= 1


# ------------------------------------------------------------------------------------------
@lingo_script('TIMER')                                    # ParentScript 112
class Timer(LObject):
    def __init__(self):
        self.pPlaying = 0
        self.pEnabled = 0
        self.pLastUpdate = 0
        self.pLastClick = 0
        self.pCheckForMouseActivity = 0
        self.pParent = None
        self.pName = None
        self.pEventTag = None
        self.pTimeOutLength = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pMouseTimeOut = int(self.pTimeOutLength * 0.06)   # ticks (1/60 s) in the original
        return self

    def mDestroy(self): pass
    def mSetName(self, n): self.pName = n
    def mGetName(self): return self.pName
    def mGetType(self): return Sym('timer')
    def mSetTimeOutLength(self, ms): self.pTimeOutLength = ms
    def mSetParent(self, o): self.pParent = o
    def mSetEventTag(self, t): self.pEventTag = t
    def mGetEventTag(self): return self.pEventTag
    def mIsActive(self): return self.pEnabled

    def mPlay(self):
        rt = _rt()
        self.pPlaying = 1
        self.pEnabled = 1
        self.pLastUpdate = rt.milliseconds()
        self.pLastClick = rt.last_click
        M.addUpdateList(self)

    def mKill(self):
        self.pPlaying = 0
        self.pLastUpdate = 0
        M.removeUpdateList(self)
        self.mDisable()

    mStop = mKill

    def mTimeUp(self):
        return (_rt().milliseconds() - self.pLastUpdate) >= self.pTimeOutLength and self.pPlaying

    def mTimeRemaining(self):
        return self.pTimeOutLength - (_rt().milliseconds() - self.pLastUpdate)

    def mEnable(self):
        self.pEnabled = 1
        if self.pPlaying:
            M.addUpdateList(self)

    def mDisable(self):
        self.pEnabled = 0
        M.removeUpdateList(self)

    def mReset(self):
        rt = _rt()
        self.pLastUpdate = rt.milliseconds()
        self.pLastClick = rt.last_click

    def mUpdate(self):
        if not self.pEnabled:
            return
        rt = _rt()
        now = rt.milliseconds()
        if self.pCheckForMouseActivity:
            # `the lastClick` is in ticks in Director; we track ms, so compare in ms
            if now > self.pLastUpdate + self.pTimeOutLength or \
               rt.last_click > self.pLastClick + self.pMouseTimeOut * 1000 // 60:
                self.pLastUpdate = now
                self.pParent.mPlayDone(self)
        elif now > self.pLastUpdate + self.pTimeOutLength:
            self.pLastUpdate = now
            self.mDisable()
            if self.pParent is not None:
                self.pParent.mPlayDone(self)
            else:
                M.GlobalPlayDone(self)


# ------------------------------------------------------------------------------------------
@lingo_script('SCREENDADDY')                              # ParentScript 29
class ScreenDaddy(LObject):
    def __init__(self):
        self.pName = self.pType = None
        self.pScreenList = []
        self.pCurrentScreen = 0
        self.pPreviousScreen = 0
        self.pHistory = []
        self.pLoaderObject = None
        self.pCastChanged = 0
        self.pLoaderScriptNumber = 0

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pScreenList = get_object_list(self.pScreenList, alloc, 70)
        self.pHistory = []
        self.pCurrentScreen = self.pScreenList[0]
        self.pLoaderObject = new_script(self.pLoaderScriptNumber)
        self.pLoaderObject.mSetParent(self)
        return self

    def mDestroy(self):
        for o in self.pScreenList or []:
            destroy_object(o)
        destroy_object(self.pLoaderObject)
        self.pScreenList = None
        self.pCurrentScreen = None
        self.pHistory = None

    def mGetName(self): return self.pName
    def mGetType(self): return Sym('ScreenDaddy')
    def mGetHelpState(self): return 0

    def _cur(self, name, *a):
        s = self.pCurrentScreen
        if s:
            return getattr(s, name)(*a)

    def mInitPoolObjects(self): self._cur('mInitPoolObjects')
    def mReleasePoolObjects(self): self._cur('mReleasePoolObjects')
    def mLoad(self): self._cur('mLoad')
    def mLoadList(self, lst): self._cur('mLoadList', lst)
    def mUnload(self): self._cur('mUnload')
    def mDisable(self): self._cur('mDisable')
    def mEnable(self): self._cur('mEnable')

    def mShow(self):
        if not self.pCurrentScreen:
            self.pCurrentScreen = self.pScreenList[0]
        M.setCurScreen(self.pCurrentScreen)
        self.pCurrentScreen.mShow()
        self.pHistory.append(self.pCurrentScreen.pName)

    def mHide(self):
        self.pCurrentScreen.mHide()
        self.pHistory = []

    def mNavigateBack(self):
        sect = pop_last(self.pHistory)
        self.mNavigate(sect, 1)

    def mGetScreen(self, name):
        for s in self.pScreenList:
            if str(s.mGetName()).lower() == str(name).lower():
                return s
        return 0

    def mGetScreenType(self, t):
        for s in self.pScreenList:
            if s.mGetType() == t:
                return s
        return 0

    def mNavigateNext(self):
        i = self.pScreenList.index(self.pCurrentScreen)
        if i < len(self.pScreenList) - 1:
            self.mNavigate(self.pScreenList[i + 1])

    def mNavigate(self, section, backFlag=None, dontFlush=None):
        if section is None:
            return
        M.waitCursor()
        if isinstance(section, LObject):
            new = section
            section = new.mGetName()
        else:
            new = self.mGetScreen(section)
        if not new:
            print('could not locate screen', section)
            M.resetCursor()
            self.pCurrentScreen.mEnable()
            return
        print('[nav] %s  ->  %s' % (_screen_desc(self.pCurrentScreen), _screen_desc(new)), flush=True)
        if self.pCurrentScreen:
            M.clearInterruptMode()
            self.pCurrentScreen.mDisable()
            self.pCurrentScreen.mUnload()
            if not backFlag:
                self.pHistory.append(self.pCurrentScreen.mGetName())
            self.pPreviousScreen = self.pCurrentScreen
        self.pCastChanged = M.changeRiddleCast(str(section))
        self.pCurrentScreen = new
        M.setCurScreen(new)
        self.pCurrentScreen.mInitPoolObjects()
        lst = []
        new.mLoadList(lst)
        self.pLoaderObject.mSetLoadList(lst)
        self.pLoaderObject.mPlay(dontFlush)

    def mPlayDone(self, obj):
        if obj is self.pLoaderObject:
            rt = _rt()
            print('[screen] showing %s' % _screen_desc(self.pCurrentScreen), flush=True)
            if self.pPreviousScreen:
                self.pPreviousScreen.mHide()
                self.pPreviousScreen.mReleasePoolObjects()
                rt.blank_sprite_range(1, 150)
                self.pPreviousScreen = 0
            # (Lingo: `if the frame <> 5 then go(5)`)
            theManualUpdate = self.pCurrentScreen.mShow()
            rt._save_due = True                 # port: autosave after every screen change
            if not self.pCastChanged and not theManualUpdate:
                rt.update_stage()
                M.changeRiddleCast('EXTERNAL')
            rt.flush_input()


# ------------------------------------------------------------------------------------------
@lingo_script('GAME_DRAFT')                               # superseded by game.py
class _GameDraft(LObject):
    def __init__(self):
        self.pRiddlePlayed = 0
        self.pShowDSSH = 1
        self.pVersionList = []
        self.pVersionPool = []
        self.pCurrentVersion = None
        self.pAllVersionsPlayed = 0
        self.pIsSolved = 0
        self.pSessionCount = 0
        self.pCurrentCollectorIndex = 1
        self.pTokenCollectorList = []
        self.pLevelScreenList = []
        self.pSolvedUserNotified = 0
        self.pClueFound = 0
        self.pHackUsed = 0
        self.pOpenAnimPlayed = 0
        self.pReminderAudio = 0
        self.pSaveLoadObject = 0
        self.ancestor = None
        self.pName = None

    def mInit(self, data, alloc):
        set_properties(data, self)
        self.pSpriteAlloc = list(alloc)
        self.pVersionList = ['a', 'b', 'c']
        self.pVersionPool = list(self.pVersionList)
        self.pCurrentVersion = pop_one(self.pVersionPool)
        anc = self.ancestor
        object.__setattr__(self, 'ancestor', get_object(anc, alloc))
        self.pHelpPlayer = get_object(self.pHelpPlayer, [])
        if hasattr(self.pHelpPlayer, 'mInitPoolObjects'):
            self.pHelpPlayer.mInitPoolObjects()
            self.pHelpPlayer.mSetParent(self)
        self.pSavedList = ['pRiddlePlayed', 'pCurrentVersion', 'pIsSolved', 'pVersionPool',
                           'pCurrentCollectorIndex', 'pSessionCount', 'pAllVersionsPlayed',
                           'pSolvedUserNotified', 'pClueFound', 'pHackUsed', 'pOpenAnimPlayed']
        M.addObjectGlob(self)
        return self

    def mGetType(self): return Sym('GAME')
    def mGetName(self): return self.pName
    def mLoad(self): self.ancestor.mLoad()
    def mIsSolved(self): return self.pIsSolved
    def mGetLevel(self): return self.pCurrentCollectorIndex
    def mGetCurrentVersion(self): return self.pCurrentVersion
    def mGetSessionCount(self): return self.pSessionCount

    def mNextVersion(self):
        if self.pVersionPool:
            self.pCurrentVersion = pop_one(self.pVersionPool)
        else:
            self.pVersionPool = list(self.pVersionList)
            self.mNextVersion()

    # -- tokens --------------------------------------------------------------------------
    def _collector(self):
        return self.pTokenCollectorList[self.pCurrentCollectorIndex - 1]

    def mAddToken(self, t): return self._collector().mAddToken(t)
    def mRemoveToken(self, t): return self._collector().mRemoveToken(t)
    def mTokenFound(self, t): return self._collector().mTokenFound(t)
    def mTokenFoundCount(self): return self._collector().mTokenFoundCount()
    def mNextToken(self): return self._collector().mNextToken()
    def mLevelSolved(self): return self._collector().mIsComplete()

    def mNextLevel(self):
        self.pCurrentCollectorIndex = min(self.pCurrentCollectorIndex + 1, len(self.pTokenCollectorList))

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

    def mGetEndRiddleAudio(self):
        c = min(self.mTokenFoundCount() + 1, len(self.pRewardAudioList))
        return self.pRewardAudioList[c - 1]

    def mShowDynamicStates(self):
        return max([self.mGetLevel() == 1, self.pShowDSSH])

    # -- (re)build the per-version game objects (mInitGameObjects) -----------------------------
    def mInitGameObjects(self, theNoRestore=None):
        rt = _rt()
        stashed = self.ancestor
        object.__setattr__(self, 'ancestor', None)
        self.pSaveLoadObject = new_script(self.pSaveLoadScriptNumber, M.getPlayerDir(), str(self.pName))
        M.setSaveLoadObject(self.pSaveLoadObject)
        if self.pIsSolved:
            self.pSaveLoadObject.mDeleteFile()
            self.mNextVersion()
            self.pIsSolved = 0
            self.pCurrentCollectorIndex = 1
        self.pSessionCount += 1
        data = M.getGameData(self.pCurrentVersion)
        set_properties(data, self)
        alloc = list(self.pSpriteAlloc)
        self.pLevelScreenList = get_object_list(self.pLevelScreenList, alloc, 100)
        for s in self.pLevelScreenList:
            stashed.pScreenList.append(s)
        for attr in ('pRiddleStripObject', 'pClueStripObject', 'pScavengerHuntManager',
                     'pHomeButton', 'pBackButton', 'pHelpButton', 'pLipsButton'):
            setattr(self, attr, get_object(getattr(self, attr), alloc))
        for attr in ('pHomeButton', 'pBackButton', 'pHelpButton', 'pLipsButton'):
            getattr(self, attr).mLoad()
        self.pHomeButton.mSetParent(self)
        self.pEndAnim = get_object(self.pEndAnim, alloc)
        self.pEndAnim.mSetParent(self)
        self.pReminderAudio = get_object(self.pReminderAudio, alloc)
        self.pTokenCollectorList = get_object_list(self.pTokenCollectorList, [])
        self.pWigglePool = list(self.pWiggleSoundList)
        if theNoRestore != 1:
            self.pSaveLoadObject.mRestore()
        object.__setattr__(self, 'ancestor', stashed)
