"""Hand-ported parent scripts, part 8: the two timed matching-game room screens.

    ParentScript  51  SCREEN_MM     "MT" memory-match room game (type #SCREEN_MM, awards token #MT, VO = MT_*.AIF)
    ParentScript  52  SCREEN_CC     Creepy Crawlies: tiles creep in and decay; click the good ones (token #CC)

(BUTT_MM 75 / BUTT_CC 76 live in riddles.py; VisibleTimer, WIN_COUNTER, SKELLY_TALK_ANIM in rooms.py;
DISSOLVE_BLEND / PLAY_QUEUE in screens2.py.)  Imported at the bottom of rooms.py.

Same conventions as the other room screens: one class per Lingo parent script, method and property
names unchanged, `S(chan)` is `sprite(chan)`, `R()` is the runtime, Lingo lists are 1-based so every
`list[i]` is written `list[i - 1]`, Lingo `=` between two objects is `is`.
"""
import copy

from . import movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, set_properties, pop_one, pop_list, random_
from .ui import load_mem, unload_mem, blank
from .screens2 import R, S, _get_pos, _integer
from .riddles import call_all, _pos
from .room_screens2 import _tag, _get_prop


def _ver_is_a(v):
    """`pVersion = "A"` (Lingo string compare is case-insensitive)."""
    return str(v).upper() == 'A'


def _symeq(a, b):
    return str(a).lower() == str(b).lower()


def _pop_at(lst, idx):
    """popAt(list, index): remove and return the item at 1-based idx, 0 when out of range."""
    if len(lst) >= idx:
        return lst.pop(idx - 1)
    return 0


# ============================================================================================
# SCREEN_MM  (ParentScript 51)
# ============================================================================================

@lingo_script('SCREEN_MM')
class ScreenMM(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pEnabled = 0
        self.pBackButton = 0
        self.pHelpButton = 0
        self.pAmbientAudio = 0
        self.pResetButton = 0
        self.pIntroAudio = 0
        self.pHintAudio = 0
        self.pFirstFinishAudio = 0
        self.pCompleteAudio = 0
        self.pPlayMoreAudio = 0
        self.pBGMember = 0
        self.pBGSprite = 0
        self.pAppearSound = 0
        self.pPickSound = 0
        self.pUnPickSound = 0
        self.pCorrectSound = 0
        self.pWrongSound = 0
        self.pNewBestSound = 0
        self.pCategoryList = []
        self.pGameList = {}
        self.pMatchList = []
        self.pItemCount = 0
        self.pElementList = []
        self.pLastCategory = 0
        self.pIntroVOPlayed = 0
        self.pFirstFinishVOPlayed = 0
        self.pFirstTimeCat = 0
        self.pPlayMoreVOPlayed = 0
        self.pVersion = None
        self.pButtonList = []
        self.pCurrentButton = 0
        self.pVisibleTimer = 0
        self.pBestTimer = 0
        self.pNewBest = 0
        self.pFirstSelectInBinFlag = 1
        self.pHasAnythingBeenMatched = 0
        self.pWinCounter = 0
        self.pMatchSolved = 0
        self.pEndAudio = 0
        self.pSkellyAnims = []
        self.pQueObject = 0
        self.pHintButtonList = []
        self.pFinishCount = 0
        self.pSavedList = []

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBGSprite = pop_one(theSpriteAlloc)
        self.pResetButton = get_object(self.pResetButton, theSpriteAlloc)
        self.pResetButton.mSetParent(self)
        self.pVisibleTimer = get_object(self.pVisibleTimer, theSpriteAlloc)
        self.pVisibleTimer.mReset()
        self.pBestTimer = get_object(self.pBestTimer, theSpriteAlloc)
        self.pBestTimer.mReset()
        self.pWinCounter = get_object(self.pWinCounter, theSpriteAlloc)
        self.pWinCounter.mReset()
        self.pFirstTwoTimes = 0
        self.pFinishCount = 0
        self.pFirstTimeCat = 0
        self.pIntroVOPlayed = 0
        self.pFirstFinishVOPlayed = 0
        self.pPlayMoreVOPlayed = 0
        self.pGameList = {}
        self.pCurrentPuzzle = 0
        self.pCurrentButton = 0
        self.pMatchSolved = 0
        self.pNewBest = 0
        self.pQueObject = 0
        self.pHasAnythingBeenMatched = 0
        self.pFirstSelectInBinFlag = 1
        self.pHintButtonList = []
        self.pIntroAudio = 'MT_INT1.AIF'
        self.pHintAudio = 'MT_Hint02.AIF'
        self.pFirstFinishAudio = 'MT_ONE.AIF'
        self.pPlayMoreAudio = 'MT_MORE.AIF'
        self.pButtonList = get_object_list(self.pButtonList, theSpriteAlloc)
        call_all(self.pButtonList, 'mSetParent', self)
        daSkellySprite = pop_one(theSpriteAlloc)
        self.pSkellyAnims = get_object_list(self.pSkellyAnims, [daSkellySprite], 1)
        call_all(self.pSkellyAnims, 'mSetParent', self)
        self.pSavedList = [Sym(n) for n in ('pIntroVOPlayed', 'pFinishCount', 'pFirstFinishVOPlayed',
                                            'pFirstTimeCat', 'pPlayMoreVOPlayed', 'pHasAnythingBeenMatched')]
        self.pCurrentSets = []
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    # ---- pool objects ---------------------------------------------------------------------------
    def mInitPoolObjects(self):
        self.pIntroAudio = M.getExSoundObject(2, self.pIntroAudio, self)
        self.pHintAudio = M.getExSoundObject(2, self.pHintAudio, self)
        self.pFirstFinishAudio = M.getExSoundObject(2, self.pFirstFinishAudio, self)
        self.pPlayMoreAudio = M.getExSoundObject(2, self.pPlayMoreAudio, self)
        self.pEndAudio = M.gScreenDaddy.mGetEndRiddleAudio()
        self.pEndAudio = M.getExSoundObject(2, self.pEndAudio, self)
        self.pCompleteAudio = M.getSoundObject(1, self.pCompleteAudio, self)
        self.pNewBestSound = M.getSoundObject(1, self.pNewBestSound, self)
        self.pCorrectSound = M.getSoundObject(1, self.pCorrectSound, self)
        M.gScreenDaddy.mInitScavengerHuntPoolObjects()

    def mReleasePoolObjects(self):
        self.pIntroAudio = M.recycleSoundObject(self.pIntroAudio)
        self.pHintAudio = M.recycleSoundObject(self.pHintAudio)
        self.pFirstFinishAudio = M.recycleSoundObject(self.pFirstFinishAudio)
        self.pPlayMoreAudio = M.recycleSoundObject(self.pPlayMoreAudio)
        self.pEndAudio = M.recycleSoundObject(self.pEndAudio)
        self.pCompleteAudio = M.recycleSoundObject(self.pCompleteAudio)
        self.pNewBestSound = M.recycleSoundObject(self.pNewBestSound)
        self.pCorrectSound = M.recycleSoundObject(self.pCorrectSound)
        M.gScreenDaddy.mReleaseScavengerHuntPoolObjects()
        self.pQueObject = 0

    # ---- load / unload --------------------------------------------------------------------------
    def mLoad(self):
        pass

    def mLoadList(self, theList):
        if not self.pGameList:
            self.mFillGameList()
        self.mLoadGameObjectsList(theList)
        for m in (self.pAmbientAudio, self.pBGMember, self.pAppearSound, self.pPickSound, self.pUnPickSound,
                  self.pWrongSound, self.pCompleteAudio, self.pNewBestSound, self.pCorrectSound):
            theList.append(m)
        self.pResetButton.mLoadList(theList)
        call_all(self.pButtonList, 'mLoadList', theList)
        self.pVisibleTimer.mLoadList(theList)
        self.pWinCounter.mLoadList(theList)
        call_all(self.pSkellyAnims, 'mLoadList', theList)

    def mUnload(self):
        for m in (self.pBGMember, self.pAppearSound, self.pPickSound, self.pUnPickSound, self.pWrongSound):
            unload_mem(m)
        self.mUnLoadGameObjects()
        unload_mem(self.pResetButton)
        unload_mem(self.pCompleteAudio)
        unload_mem(self.pCorrectSound)
        unload_mem(self.pNewBestSound)
        # call(#unload, pButtonList) / call(#unload, pSkellyAnims): there is no `unload` handler (the real one
        # is mUnload) -> a no-op in the original
        unload_mem(self.pVisibleTimer)
        unload_mem(self.pWinCounter)

    def mLoadGameObjects(self, theList=None):
        for daSubList in self.pGameList.values():
            for daObject in daSubList:
                load_mem(daObject)

    def mLoadGameObjectsList(self, theList):
        for daSubList in self.pGameList.values():
            theList.extend(daSubList)

    def mUnLoadGameObjects(self):
        for daSubList in self.pGameList.values():
            for daObject in daSubList:
                unload_mem(daObject)

    def mHuntObjectFound(self, theObject):
        pass

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    def mGetEnabled(self):
        return self.pEnabled

    # ---- show / hide ----------------------------------------------------------------------------
    def mShow(self):
        sd = M.gScreenDaddy
        S(self.pBGSprite).member = self.pBGMember
        self.pBackButton = M.getGameBackButton()
        self.pBackButton.mSetParent(self)
        self.pHelpButton = M.getGameHelpButton()
        self.pHelpButton.mSetParent(self)
        self.pResetButton.mShow()
        self.pHelpButton.mShow()
        self.pBackButton.mShow()
        self.pVisibleTimer.mShow()
        self.pVisibleTimer.mStop()
        self.pFirstSelectInBinFlag = 1
        self.pBestTimer.mShow()
        self.pWinCounter.mShow()
        M.FadeInAmbientSound(self.pAmbientAudio)
        self.pEnabled = 1
        if (sd.mGetLevel() == 2) and not _ver_is_a(self.pVersion):
            sd.mShowScavengerHunt()
            self.pResetButton.mHide()
            M.resetCursor()
        else:
            self.mFillBin()

    def mHide(self):
        call_all(self.pButtonList, 'mHide')
        self.pResetButton.mHide()
        self.pHelpButton.mHide()
        self.pBackButton.mHide()
        self.pVisibleTimer.mStop()
        self.pVisibleTimer.mHide()
        self.pBestTimer.mHide()
        blank(self.pBGSprite)
        self.pCurrentButton = 0
        self.pEnabled = 0
        self.pFirstSelectInBinFlag = 1

    # ---- the bin --------------------------------------------------------------------------------
    def mFillBin(self):
        sd = M.gScreenDaddy
        sd.mDisable()
        M.waitCursor()
        if self.mMatchSolved():
            self.pVisibleTimer.mStop()
            self.pVisibleTimer.mReset()
            self.pVisibleTimer.mDraw()
            daTempButtonList = list(self.pButtonList)
            buttonOne = buttonTwo = None
            for i in range(1, len(self.pGameList) + 1):
                daBinDef = self.pGameList[i]
                buttonOne = daTempButtonList.pop(random_(len(daTempButtonList)) - 1)
                buttonTwo = daTempButtonList.pop(random_(len(daTempButtonList)) - 1)
                buttonOne.pMember = daBinDef[0]
                buttonOne.pMatch = i
                buttonTwo.pMember = daBinDef[1]
                buttonTwo.pMatch = i
            # (outside the loop in the original: only the LAST pair becomes the hint)
            self.pHintButtonList.append(buttonOne)
            self.pHintButtonList.append(buttonTwo)
            for daButton in self.pButtonList:
                daButton.mShow()
                R().sound.puppet(1, self.pAppearSound)
                R().update_stage()
                R().wait_ticks(5)
            self.pHasAnythingBeenMatched = 0
            self.pFirstSelectInBinFlag = 1
        else:
            call_all(self.pButtonList, 'mShow')
            if not self.pHasAnythingBeenMatched:
                daHighestMatch = len(self.pButtonList) // 2
                self.pHintButtonList = []
                for daButton in self.pButtonList:
                    if daButton.pMatch == daHighestMatch:
                        self.pHintButtonList.append(daButton)
                self.mGiveHint()
                R().update_stage()
                M.waitCursor()
                return
            M.resetCursor()
            sd.mEnable()
            return
        if not self.pIntroVOPlayed:
            if _ver_is_a(self.pVersion):
                self.pIntroVOPlayed = 1
                M.waitCursor()
                sd.mDisable()
                self.pIntroAudio.mPlay()
            else:
                self.pIntroVOPlayed = 1
                self.mGiveHint()
        else:
            if (self.pFinishCount == 3) and not self.pPlayMoreVOPlayed:
                self.pPlayMoreVOPlayed = 1
                M.waitCursor()
                sd.mDisable()
                self.pPlayMoreAudio.mPlay()
            else:
                self.mGiveHint()

    def mMatchSolved(self):
        daReturnVal = 0
        for daButton in self.pButtonList:
            daReturnVal = max(daReturnVal, daButton.pMatch)
        return 0 if daReturnVal else 1

    def mGiveHint(self):
        M.gScreenDaddy.mDisable()
        R().wait_sound(1)                      # repeat while soundBusy(1) / end repeat
        self.pHintAudio.mPlay()
        call_all(self.pHintButtonList, 'mPlay')

    def mReset(self):
        M.gScreenDaddy.mDisable()
        call_all(self.pButtonList, 'mClearMatch')
        self.mUnLoadGameObjects()
        self.mFillGameList()
        self.mLoadGameObjects()
        self.mFillBin()

    # ---- play-done dispatch ---------------------------------------------------------------------
    def mPlayDone(self, theObject):
        sd = M.gScreenDaddy
        if (theObject is self.pIntroAudio) or (theObject is self.pPlayMoreAudio):
            self.mGiveHint()
        elif theObject is self.pHintAudio:
            call_all(self.pHintButtonList, 'mStop')
            self.pHintButtonList = []
            sd.mEnable()
            M.resetCursor()
        elif (theObject is self.pCorrectSound) and self.pMatchSolved:
            self.pFinishCount += 1
            M.waitCursor()
            self.mDisable()
            self.pCompleteAudio.mPlay()
            self.pMatchSolved = 0
            if self.mTestForBest():
                self.pVisibleTimer.mFlashOn()
                self.pVisibleTimer.mPlay()
                self.pNewBest = 1
        elif theObject is self.pCompleteAudio:
            if self.pNewBest:
                self.pVisibleTimer.mFlashOff()
                self.pBestTimer.mSetTime(self.pVisibleTimer.mGetTime())
                self.pBestTimer.mDraw()
                self.pNewBestSound.mPlay()
            else:
                self.pWinCounter.mIncrementCount()
                if (self.pFinishCount == 1) and not self.pFirstFinishVOPlayed:
                    self.pFirstFinishVOPlayed = 1
                    M.waitCursor()
                    sd.mDisable()
                    self.pFirstFinishAudio.mPlay()
                else:
                    if self.pWinCounter.mGetWinCount() == 3:
                        self.mWon3()
                    else:
                        self.mReset()
        elif theObject is self.pNewBestSound:
            self.pWinCounter.mIncrementCount()
            if self.pWinCounter.mGetWinCount() == 3:
                self.mWon3()
            else:
                self.mReset()
            self.pNewBest = 0
        elif theObject is self.pQueObject:
            self.pQueObject.mRecycle()
            self.pQueObject = 0
            self.mReset()
        elif theObject is self.pFirstFinishAudio:
            self.mReset()

    def mWon3(self):
        M.gScreenDaddy.mAddToken(Sym('MT'))
        self.pQueObject = M.getPlayQueueObject(self)
        self.pQueObject.mAddItem(self.pSkellyAnims[0])
        self.pQueObject.mAddItem(self.pEndAudio)
        self.pQueObject.mAddItem(self.pSkellyAnims[1])
        self.pQueObject.mPlay()

    # ---- buttons --------------------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        if theObject is self.pHelpButton:
            M.gScreenDaddy.pHelpPlayer.mStartHelp()
        elif theObject is self.pBackButton:
            M.navigateBack()
        elif theObject is self.pResetButton:
            if self.pCurrentButton != 0:
                self.pCurrentButton.mDeSelect()
                self.pCurrentButton = 0
            if len(self.pHintButtonList) != 0:
                self.pHintAudio.mKill()        # mKill(pHintAudio, 1): EXTERNALSOUND.mKill takes no argument
                call_all(self.pHintButtonList, 'mStop')
                self.pHintButtonList = []
            self.mReset()
        elif _get_pos(self.pButtonList, theObject):
            self.mHandleMMObject(theObject)
        R().flush_input()                      # flush() -> flushInputEvents()

    def mHandleMMObject(self, theObject):
        if theObject.mGetSelected():
            self.pCurrentButton = 0
            theObject.mDeSelect()
            R().sound.puppet(1, self.pUnPickSound)
            return
        if not self.pCurrentButton:
            self.pCurrentButton = theObject
            R().sound.puppet(1, self.pPickSound)
            theObject.mSelect()
            if self.pFirstSelectInBinFlag:
                self.pFirstSelectInBinFlag = 0
                self.pVisibleTimer.mPlay()
        else:
            if self.pCurrentButton.pMatch == theObject.pMatch:
                self.pCorrectSound.mPlay()
                theObject.mSelect()
                R().update_stage()
                R().wait_ticks(5)
                self.pHasAnythingBeenMatched = 1
                self.pCurrentButton.mDeSelect()
                theObject.mDeSelect()
                self.pCurrentButton.mClearMatch()
                theObject.mClearMatch()
                self.pCurrentButton.mShow()
                theObject.mShow()
                self.pCurrentButton = 0
                if self.mMatchSolved():
                    self.pVisibleTimer.mStop()
                    M.gScreenDaddy.mDisable()
                    self.pMatchSolved = 1
            else:
                R().sound.puppet(1, self.pWrongSound)
                theObject.mSelect()
                R().update_stage()
                R().wait_ticks(5)
                theObject.mDeSelect()
                self.pCurrentButton.mDeSelect()
                self.pCurrentButton = 0

    def mButtonDeActivated(self, theButton):
        pass

    # ---- enable / disable -----------------------------------------------------------------------
    def mEnable(self):
        self.pEnabled = 1
        self.pHelpButton.mEnable()
        self.pBackButton.mEnable()
        self.pResetButton.mEnable()
        call_all(self.pButtonList, 'mEnable')
        self.pVisibleTimer.mEnable()

    def mDisable(self):
        self.pEnabled = 0
        self.pHelpButton.mDisable()
        self.pBackButton.mDisable()
        self.pResetButton.mDisable()
        call_all(self.pButtonList, 'mDisable')
        self.pVisibleTimer.mDisable()

    def mApplicationActivated(self):
        self.pVisibleTimer.mEnable()

    def mApplicationDeactivated(self):
        self.pVisibleTimer.mDisable()

    def mGetType(self):
        return Sym('SCREEN_MM')

    def mGetName(self):
        return self.pName

    def mGetHelpState(self):
        return 0

    def mUpdate(self):
        pass

    # ---- picking the tiles ----------------------------------------------------------------------
    def mFillGameList(self):
        self.mPickCategory()
        total = self.pItemCount // 2
        self.pGameList = {}
        for myPairNum in range(1, total + 1):
            self.pGameList[myPairNum] = self.mPickPair()

    def mPickCategory(self):
        if self.pFirstTimeCat == 0:
            thisOne = 1
            self.pLastCategory = thisOne
            self.pCategoryList = copy.deepcopy(self.pElementList[thisOne - 1])
            self.pFirstTimeCat = 1
            return
        thisOne = random_(len(self.pElementList))
        while thisOne == self.pLastCategory:
            thisOne = random_(len(self.pElementList))
        self.pLastCategory = thisOne
        self.pCategoryList = copy.deepcopy(self.pElementList[thisOne - 1])

    def mPickPair(self):
        thisPosInCatList = random_(len(self.pCategoryList))
        myPairList = self.pCategoryList[thisPosInCatList - 1]
        firstPos = random_(len(myPairList))
        first = myPairList[firstPos - 1]
        if isinstance(first, list):
            first = first[random_(len(first)) - 1]
        del myPairList[firstPos - 1]
        secondPos = random_(len(myPairList))
        second = myPairList[secondPos - 1]
        if isinstance(second, list):
            second = second[random_(len(second)) - 1]
        del myPairList[secondPos - 1]
        myPair = [first, second]
        del self.pCategoryList[thisPosInCatList - 1]
        return myPair

    def mTestForBest(self):
        if self.pBestTimer.mGetTime() == 0:
            self.pBestTimer.mSetTime(self.pVisibleTimer.mGetTime())
            self.pBestTimer.mDraw()
            return 0
        if self.pVisibleTimer.mGetTime() < self.pBestTimer.mGetTime():
            return 1
        return 0

    def mGetFinishCount(self):
        return self.pFinishCount


# ============================================================================================
# SCREEN_CC  (ParentScript 52)
# ============================================================================================

#: mAdjustTimerInterval lookup tables, indexed by found-count (1..14)
_CC_INSERT = {
    'easy': [1, 1, 1, 1, 1, 0.9327, 0.8654, 0.7981, 0.7308, 0.6636, 0.5963, 0.529, 0.4617, 0.76471],
    'medium': [1, 1, 1, 0.9462, 0.8923, 0.8385, 0.7847, 0.7308, 0.677, 0.6232, 0.5694, 0.5155, 0.4617, 0.65],
    'hard': [1, 0.9596, 0.9192, 0.8789, 0.8385, 0.7981, 0.7577, 0.7173, 0.6769, 0.6365, 0.5962, 0.5558, 0.54,
             0.76471],
}
_CC_DECAY = {
    'easy': [2, 2, 2, 2, 2, 2, 2, 2, 2.3, 2.5, 1.7, 2, 2, 2],
    'medium': [2, 2, 2, 2, 2, 2, 2.3, 2.5, 2.5, 2.5, 1.7, 2, 2, 2],
    'hard': [2, 2.1, 2.2, 2.3, 2.4, 2.5, 3, 3.5, 3, 2.5, 1.7, 2, 2, 2],
}


@lingo_script('SCREEN_CC')
class ScreenCC(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pEnabled = 0
        self.pBackButton = 0
        self.pHelpButton = 0
        self.pAmbientAudio = 0
        self.pResetButton = 0
        self.pIntroAudio = 0
        self.pFirstFinishAudio = 0
        self.pPlayMoreAudio = 0
        self.pCompleteAudio = 0
        self.pNewBestSound = 0
        self.pStartSound = 0
        self.pFinishSound = 0
        self.pAppearSound = 0
        self.pDisapearSound = 0
        self.pCorrectSound = 0
        self.pWrongSound = 0
        self.pLevel = None
        self.pMaxFlux = 0
        self.pStartGiveAway = 0
        self.pInsertInterval = 0
        self.pDecayTime = 0
        self.pFavorProb = 0
        self.pStartCategory = None
        self.pUsedCategories = []
        self.pCurrentCategory = None
        self.pGiveAwayCount = 0
        self.pCurrentDecayTime = 0
        self.pCurrentFavorProb = 0
        self.pCurrentInsertInterval = 0
        self.pGoodList = []
        self.pFakeList = []
        self.pUsedGoodList = []
        self.pUsedFakeList = []
        self.pBGMember = 0
        self.pBGSprite = 0
        self.pGameList = {}
        self.pButtonList = []
        self.pButtonSpriteList = []
        self.pVisibleTimer = 0
        self.pBestTimer = 0
        self.pWinCounter = 0
        self.pEndAudio = 0
        self.pSkellyAnims = []
        self.pIntroVOPlayed = 0
        self.pWinCount = 0
        self.pFirstFinishVOPlayed = 0
        self.pNewBest = 0
        self.pVersion = None
        self.pQueObject = 0
        self.pDissolveBlendObject = 0
        self.pLastUpdate = 0
        self.pUnLoadGoodList = []
        self.pUnLoadFakeList = []
        self.pLoadFlag = 0
        self.pHolddaButton = 0
        self.pSavedList = []

    def _lvl(self):
        return str(self.pLevel).lower()

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBGSprite = pop_one(theSpriteAlloc)
        self.pResetButton = get_object(self.pResetButton, theSpriteAlloc)
        self.pResetButton.mSetParent(self)
        self.pVisibleTimer = get_object(self.pVisibleTimer, theSpriteAlloc)
        self.pVisibleTimer.mReset()
        self.pBestTimer = get_object(self.pBestTimer, theSpriteAlloc)
        self.pBestTimer.mReset()
        self.pWinCounter = get_object(self.pWinCounter, theSpriteAlloc)
        self.pWinCount = 0
        self.pLoadFlag = 0
        self.pWinCounter.mReset()
        self.pGiveAwayCount = self.pStartGiveAway
        self.pCurrentCategory = self.pStartCategory
        self.pCurrentDecayTime = self.pDecayTime
        self.pCurrentFavorProb = self.pFavorProb
        self.pCurrentInsertInterval = self.pInsertInterval
        self.pUsedCategories = []
        self.pLastUpdate = 0
        self.pIntroVOPlayed = 0
        self.pFirstFinishVOPlayed = 0
        self.pNewBest = 0
        self.pIntroAudio = 'CC_INT1.AIF'
        self.pFirstFinishAudio = 'CC_ONE.AIF'
        self.pPlayMoreAudio = 'CC_MORE.AIF'
        self.pButtonSpriteList = pop_list(theSpriteAlloc, 30)
        self.pButtonList = get_object_list(self.pButtonList, list(self.pButtonSpriteList))
        call_all(self.pButtonList, 'mSetParent', self)
        daSkellySprite = pop_one(theSpriteAlloc)
        self.pSkellyAnims = get_object_list(self.pSkellyAnims, [daSkellySprite], 1)
        call_all(self.pSkellyAnims, 'mSetParent', self)
        self.pGoodList = []
        self.pFakeList = []
        self.pUsedGoodList = []
        self.pUsedFakeList = []
        self.pUnLoadGoodList = []
        self.pUnLoadFakeList = []
        self.pSavedList = [Sym(n) for n in ('pNewBest', 'pGoodList', 'pFakeList', 'pUsedGoodList', 'pUsedFakeList',
                                            'pCurrentDecayTime', 'pGiveAwayCount', 'pCurrentCategory',
                                            'pCurrentFavorProb', 'pCurrentInsertInterval', 'pUsedCategories',
                                            'pWinCount', 'pFirstFinishVOPlayed', 'pIntroVOPlayed')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    # ---- pool objects ---------------------------------------------------------------------------
    def mInitPoolObjects(self):
        sd = M.gScreenDaddy
        sd.mInitScavengerHuntPoolObjects()
        self.pIntroAudio = M.getExSoundObject(2, self.pIntroAudio, self)
        self.pFirstFinishAudio = M.getExSoundObject(2, self.pFirstFinishAudio, self)
        self.pPlayMoreAudio = M.getExSoundObject(2, self.pPlayMoreAudio, self)
        self.pEndAudio = sd.mGetEndRiddleAudio()
        self.pEndAudio = M.getExSoundObject(2, self.pEndAudio, self)
        self.pCompleteAudio = M.getSoundObject(1, self.pCompleteAudio, self)
        self.pNewBestSound = M.getSoundObject(1, self.pNewBestSound, self)
        self.pStartSound = M.getSoundObject(1, self.pStartSound, self)

    def mReleasePoolObjects(self):
        M.gScreenDaddy.mReleaseScavengerHuntPoolObjects()
        self.pIntroAudio = M.recycleSoundObject(self.pIntroAudio)
        self.pFirstFinishAudio = M.recycleSoundObject(self.pFirstFinishAudio)
        self.pPlayMoreAudio = M.recycleSoundObject(self.pPlayMoreAudio)
        self.pEndAudio = M.recycleSoundObject(self.pEndAudio)
        self.pCompleteAudio = M.recycleSoundObject(self.pCompleteAudio)
        self.pNewBestSound = M.recycleSoundObject(self.pNewBestSound)
        M.recycleBlendDissolve()
        self.pDissolveBlendObject = 0
        self.pQueObject = 0
        self.pStartSound = M.recycleSoundObject(self.pStartSound)

    # ---- load / unload --------------------------------------------------------------------------
    def mLoad(self):
        pass

    def mLoadList(self, theList):
        self.pLoadFlag = 1
        if self.mGameSolved():
            self.mInitgame()
        self.pLoadFlag = 0
        theList.extend(self.pGoodList)
        theList.extend(self.pFakeList)
        for m in (self.pAmbientAudio, self.pBGMember, self.pFinishSound, self.pAppearSound, self.pDisapearSound,
                  self.pCorrectSound, self.pWrongSound, self.pCompleteAudio, self.pNewBestSound, self.pStartSound):
            theList.append(m)
        call_all(self.pButtonList, 'mLoadList', theList)
        self.pVisibleTimer.mLoadList(theList)
        self.pWinCounter.mLoadList(theList)
        call_all(self.pSkellyAnims, 'mLoadList', theList)

    def mUnload(self):
        # call(#unload, pButtonList) / call(#unload, pSkellyAnims): no `unload` handler exists -> no-op
        for m in (self.pUnLoadGoodList, self.pUnLoadFakeList, self.pBGMember, self.pFinishSound, self.pAppearSound,
                  self.pDisapearSound, self.pCorrectSound, self.pWrongSound, self.pCompleteAudio,
                  self.pNewBestSound, self.pStartSound):
            unload_mem(m)
        unload_mem(self.pVisibleTimer)
        self.pWinCounter.mUnload()

    def mHuntObjectFound(self, theObject):
        pass

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    def mGetEnabled(self):
        return self.pEnabled

    # ---- show / hide ----------------------------------------------------------------------------
    def _plays_here(self):
        """(mGetLevel(gScreenDaddy) <> 2) or (pVersion = "A")"""
        return (M.gScreenDaddy.mGetLevel() != 2) or _ver_is_a(self.pVersion)

    def mShow(self):
        sd = M.gScreenDaddy
        self.pLastUpdate = R().milliseconds()
        S(self.pBGSprite).member = self.pBGMember
        self.pBackButton = M.getGameBackButton()
        self.pBackButton.mSetParent(self)
        self.pHelpButton = M.getGameHelpButton()
        self.pHelpButton.mSetParent(self)
        if self._plays_here():
            self.pResetButton.mShow()
        self.pHelpButton.mShow()
        self.pBackButton.mShow()
        self.pVisibleTimer.mShow()
        self.pBestTimer.mShow()
        self.pWinCounter.mShow()
        if self._plays_here():
            call_all(self.pButtonList, 'mShow')
            for daButton in self.pButtonList:
                if daButton.pFound:
                    daButton.mDisable()
                    continue
                if daButton.mGetSelected():
                    if daButton.pMatch == 0:
                        self.pFakeList.append(daButton.pMember)
                    else:
                        self.pGoodList.append(daButton.pMember)
                    daButton.mHide()
                    daButton.mReset()
        M.FadeInAmbientSound(self.pAmbientAudio)
        self.pEnabled = 1
        R().update_stage()
        if self._plays_here():
            M.addUpdateList(self)
            if not self.pIntroVOPlayed:
                if _ver_is_a(self.pVersion):
                    self.pIntroVOPlayed = 1
                    M.waitCursor()
                    sd.mDisable()
                    self.pIntroAudio.mSetEventTag(Sym('INTROAUDIO'))
                    self.pIntroAudio.mPlay()
                else:
                    self.pIntroVOPlayed = 1
                    sd.mEnable()
                    M.resetCursor()
                    self.pVisibleTimer.mPlay()
            else:
                self.pVisibleTimer.mPlay()
                if not sd.mCheckStatus():
                    M.resetCursor()
        else:
            sd.mShowScavengerHunt()
            M.resetCursor()

    def mHide(self):
        for daButton in self.pButtonList:
            if daButton.mGetSelected():
                if daButton.pMatch == 0:
                    self.pFakeList.append(daButton.pMember)
                else:
                    self.pGoodList.append(daButton.pMember)
                daButton.mReset()
        call_all(self.pButtonList, 'mHide')
        self.pResetButton.mHide()
        self.pHelpButton.mHide()
        self.pBackButton.mHide()
        self.pVisibleTimer.mStop()
        self.pVisibleTimer.mHide()
        self.pBestTimer.mHide()
        blank(self.pBGSprite)
        self.pEnabled = 0

    # ---- play-done dispatch ---------------------------------------------------------------------
    def mPlayDone(self, theObject):
        t = _tag(theObject)
        fn = {'punishment': self.mHandlePunishmentDone,
              'winround': self.mHandleWINROUNDDone,
              'introaudio': self.mHandleIntroAudioDone,
              'mreset': self.mHandleMRESETDone,
              'buttondone': self.mHandleExpiredObject}.get(t)
        if fn:
            fn(theObject)

    def mHandleIntroAudioDone(self, theObject):
        M.gScreenDaddy.mEnable()
        M.resetCursor()
        self.pVisibleTimer.mPlay()

    def mHandlePunishmentDone(self, theObject):
        M.recycleBlendDissolve()
        daButton = self.pHolddaButton
        daButton.mKill()
        daButton.mHide()
        daButton.mReset()
        self.mAdjustTimerInterval()
        self.mEnable()

    def mHandleWINROUNDDone(self, theObject):
        if theObject is self.pCompleteAudio:
            if self.pNewBest:
                self.pVisibleTimer.mFlashOff()
                self.pBestTimer.mSetTime(self.pVisibleTimer.mGetTime())
                self.pBestTimer.mDraw()
                self.pNewBestSound.mSetEventTag(Sym('WINROUND'))
                self.pNewBestSound.mPlay()
            else:
                self.pWinCounter.mIncrementCount()
                if (self.pWinCount == 1) and not self.pFirstFinishVOPlayed:
                    self.pFirstFinishVOPlayed = 1
                    self.pFirstFinishAudio.mSetEventTag(Sym('WINROUND'))
                    self.pFirstFinishAudio.mPlay()
                else:
                    if self.pWinCounter.mGetWinCount() == 3:
                        self.mWon3()
                    else:
                        self.mReset()
        elif theObject is self.pNewBestSound:
            self.pWinCounter.mIncrementCount()
            self.pNewBest = 0
            if self.pWinCounter.mGetWinCount() == 3:
                self.mWon3()
            else:
                self.mReset()
        elif theObject is self.pQueObject:
            self.pQueObject.mRecycle()
            self.pQueObject = 0
            self.pPlayMoreAudio.mSetEventTag(Sym('WINROUND'))
            self.pPlayMoreAudio.mPlay()
        elif theObject is self.pPlayMoreAudio:
            self.mReset()
        elif theObject is self.pFirstFinishAudio:
            self.mReset()

    def mReset(self):
        self.pUsedCategories.append(self.pCurrentCategory)
        if len(self.pUsedCategories) == len(self.pGameList):
            self.pUsedCategories = []
        daUnusedList = []
        for daProp in self.pGameList.keys():
            if not _pos(self.pUsedCategories, daProp) and not _symeq(daProp, self.pCurrentCategory):
                daUnusedList.append(daProp)
        if daUnusedList:                      # (random(0) is an error in Lingo; keep the category instead)
            self.pCurrentCategory = daUnusedList[random_(len(daUnusedList)) - 1]
        R().sound.puppet(1, self.pFinishSound)
        self.pDissolveBlendObject = M.getBlendDissolveObject(self)
        self.pDissolveBlendObject.mSetBlendDissolve(self.pButtonSpriteList, 1.4, 20, 0)
        self.pDissolveBlendObject.mSetEventTag(Sym('mReset'))
        self.pDissolveBlendObject.mPlay()

    def mHandleMRESETDone(self, theObject):
        if theObject is self.pDissolveBlendObject:
            M.recycleBlendDissolve()
            call_all(self.pButtonList, 'mHide')
            call_all(self.pButtonList, 'mReset')
            R().update_stage()
            self.pGiveAwayCount = self.pStartGiveAway
            self.pCurrentDecayTime = self.pDecayTime
            self.pCurrentFavorProb = self.pFavorProb
            self.pCurrentInsertInterval = self.pInsertInterval
            self.mInitgame()
            call_all(self.pButtonList, 'mShow')
            for daButton in self.pButtonList:
                if daButton.pFound:
                    daButton.mDisable()
            self.pVisibleTimer.mReset()
            self.pVisibleTimer.mDraw()
            self.pStartSound.mSetEventTag(Sym('mReset'))
            self.pStartSound.mPlay()
            M.recycleBlendDissolve()
            self.pDissolveBlendObject = 0
        elif theObject is self.pStartSound:
            M.addUpdateList(self)
            M.resetCursor()
            M.gScreenDaddy.mEnable()
            self.pVisibleTimer.mPlay()

    # ---- buttons --------------------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        sd = M.gScreenDaddy
        if theObject is self.pHelpButton:
            sd.mDisable()
            sd.pHelpPlayer.mStartHelp()
        elif theObject is self.pBackButton:
            sd.mDisable()
            M.navigateBack()
        elif theObject is self.pResetButton:
            sd.mDisable()
            M.waitCursor()
            self.pVisibleTimer.mStop()
            self.pVisibleTimer.mReset()
            self.pVisibleTimer.mDraw()
            self.mReset()
        elif _get_pos(self.pButtonList, theObject):
            self.mHandleCCObject(theObject)

    def mButtonDeActivated(self, theButton):
        pass

    def mEnable(self):
        if self._plays_here():
            M.addUpdateList(self)
            for daButton in self.pButtonList:
                if daButton.mGetSelected():
                    daButton.mEnable()
                    daButton.mPlay()
            self.pResetButton.mEnable()
            self.pVisibleTimer.mEnable()
        self.pEnabled = 1
        self.pHelpButton.mEnable()
        self.pBackButton.mEnable()

    def mDisable(self):
        M.removeUpdateList(self)
        call_all(self.pButtonList, 'mKill')
        call_all(self.pButtonList, 'mDisable')
        self.pEnabled = 0
        self.pHelpButton.mDisable()
        self.pBackButton.mDisable()
        self.pResetButton.mDisable()
        self.pVisibleTimer.mDisable()

    def mApplicationActivated(self):
        self.pVisibleTimer.mEnable()

    def mApplicationDeactivated(self):
        self.pVisibleTimer.mDisable()

    def mGetType(self):
        return Sym('SCREEN_CC')

    def mGetName(self):
        return self.pName

    def mGetHelpState(self):
        return 0

    # ---- the game -------------------------------------------------------------------------------
    def mInitgame(self):
        unload_mem(self.pUnLoadGoodList)
        unload_mem(self.pUnLoadFakeList)
        daGameDef = _get_prop(self.pGameList, self.pCurrentCategory)
        self.pGoodList = list(_get_prop(daGameDef, 'goodpieces'))
        self.pFakeList = list(_get_prop(daGameDef, 'piecePool'))
        self.pUnLoadGoodList = self.pGoodList
        self.pUnLoadFakeList = self.pFakeList
        if not self.pLoadFlag:
            load_mem(self.pGoodList)
            load_mem(self.pFakeList)
        self.pUsedGoodList = []
        self.pUsedFakeList = []
        daTempButtons = list(self.pButtonList)
        for i in range(1, self.pGiveAwayCount + 1):
            daButton = daTempButtons.pop(random_(len(daTempButtons)) - 1)
            daButton.pMember = self.mPopGoodObject()
            daButton.pMatch = 1
            daButton.mSetFound()
            # (the original deletes by index from the temp list; pop() above does exactly that)
        self.pVisibleTimer.mReset()

    def mPopGoodObject(self):
        daUnusedList = [o for o in self.pGoodList if not _pos(self.pUsedGoodList, o)]
        if daUnusedList:
            daUsedObject = daUnusedList[random_(len(daUnusedList)) - 1]
            daObject = _pop_at(self.pGoodList, _pos(self.pGoodList, daUsedObject))
        else:
            daObject = _pop_at(self.pGoodList, random_(len(self.pGoodList)))
            self.pUsedGoodList = []
        self.pUsedGoodList.append(daObject)
        return daObject

    def mPopFakeObject(self):
        daUnusedList = [o for o in self.pFakeList if not _pos(self.pUsedFakeList, o)]
        if daUnusedList:
            daUsedObject = daUnusedList[random_(len(daUnusedList)) - 1]
            daObject = _pop_at(self.pFakeList, _pos(self.pFakeList, daUsedObject))
        else:
            daObject = _pop_at(self.pFakeList, random_(len(self.pFakeList)))
            self.pUsedFakeList = []
        self.pUsedFakeList.append(daObject)
        return daObject

    def mUpdate(self):
        interval = max(1, _integer(self.pCurrentInsertInterval))
        daAddTime = (0.5 * self.pCurrentInsertInterval) + random_(interval)
        now = R().milliseconds()
        if (now - self.pLastUpdate) >= daAddTime:
            self.pLastUpdate = now
            if self.mGetFluxCount() < self.pMaxFlux:
                self.mAddItem()

    def mAdjustTimerInterval(self):
        pFoundNum = self.mGetFoundCount()
        if pFoundNum == 0:
            pFoundNum = 1
        lvl = self._lvl()
        idx = min(pFoundNum, 14) - 1          # the tables have 14 entries (the original never asks for more)
        if lvl in _CC_INSERT:
            self.pCurrentInsertInterval = self.pInsertInterval * _CC_INSERT[lvl][idx]
            self.pCurrentDecayTime = self.pCurrentInsertInterval * _CC_DECAY[lvl][idx]
        self.pCurrentFavorProb = _integer(1.5 * self.pFavorProb)
        if pFoundNum == 14:
            self.pCurrentFavorProb = 2 * self.pFavorProb

    def mGetPlacedCount(self):
        daCount = 0
        for daButton in self.pButtonList:
            if daButton.pMember > 0:
                daCount += 1
        return daCount

    def mGetFoundCount(self):
        daCount = 0
        for daButton in self.pButtonList:
            if daButton.mGetFound():
                daCount += 1
        return daCount

    def mGetFluxCount(self):
        daCount = 0
        for daButton in self.pButtonList:
            daCount += int(daButton.mGetSelected() or 0)
        return daCount

    def mGameSolved(self):
        return 0 if self.pGoodList else 1

    def mAddItem(self):
        daUnusedButtonList = [b for b in self.pButtonList if b.pMember == 1]
        daHoldStolenButton = 0
        if (self.mGetFoundCount() >= 12) and (len(daUnusedButtonList) == 0):
            # every tile is busy: steal the oldest selected one
            daStartTimeLookUp = []
            daIndexLookUp = []
            for i in range(1, len(self.pButtonList) + 1):
                daButton = self.pButtonList[i - 1]
                if daButton.mGetSelected():
                    daIndexLookUp.append(i)
                    daStartTimeLookUp.append(daButton.pStartTime)
            if daStartTimeLookUp:
                daOldestIndex = daIndexLookUp[_pos(daStartTimeLookUp, min(daStartTimeLookUp)) - 1]
                oldest = self.pButtonList[daOldestIndex - 1]
                daUnusedButtonList.append(oldest)
                daHoldStolenButton = oldest.pMember
                self.mHandleExpiredObject(oldest)
        if daUnusedButtonList:
            daGoodFlag = 0
            if random_(100) < self.pCurrentFavorProb:
                daCreep = self.mPopGoodObject()
                daGoodFlag = 1
            else:
                daCreep = self.mPopFakeObject()
            if daHoldStolenButton != 0:
                while daCreep == daHoldStolenButton:
                    if daGoodFlag:
                        self.pGoodList.append(daHoldStolenButton)
                    else:
                        self.pFakeList.append(daHoldStolenButton)
                    daGoodFlag = 0
                    if random_(100) < self.pCurrentFavorProb:
                        daCreep = self.mPopGoodObject()
                        daGoodFlag = 1
                        continue
                    daCreep = self.mPopFakeObject()
            daButton = daUnusedButtonList[random_(len(daUnusedButtonList)) - 1]
            daButton.pDecayTime = self.pCurrentDecayTime
            if daGoodFlag:
                daButton.mSetMatch(daCreep, 1)
            else:
                daButton.pMember = daCreep
            daButton.mShow()
            daButton.mSelect()
            daButton.mPlay()
            R().sound.puppet(1, self.pAppearSound)

    def mRemoveFoundItem(self):
        daResolvedList = [b for b in self.pButtonList if b.pFound]
        daButton = 0
        if daResolvedList:
            daButton = daResolvedList[random_(len(daResolvedList)) - 1]
            self.pGoodList.append(daButton.pMember)
            self.pDissolveBlendObject = M.getBlendDissolveObject(self)
            self.pDissolveBlendObject.mSetBlendDissolve([daButton.pSprite], 1.25, 20, 0)
            self.pDissolveBlendObject.mSetEventTag(Sym('PUNISHMENT'))
            self.pDissolveBlendObject.mPlay()
            R().sound.puppet(1, self.pDisapearSound)
            self.mDisable()
        return daButton

    def mHandleExpiredObject(self, theObject):
        if theObject.pMatch:
            self.pGoodList.append(theObject.pMember)
        else:
            self.pFakeList.append(theObject.pMember)
        theObject.mHide()
        theObject.mReset()

    def mHandleCCObject(self, theObject):
        sd = M.gScreenDaddy
        if not theObject.mGetSelected():
            return
        theObject.mKill()
        theObject.mDisable()
        if theObject.pMatch:
            theObject.mDeSelect()
            theObject.mSetFound()
            R().sound.puppet(1, self.pCorrectSound)
            R().update_stage()
            R().wait_sound(1)
            R().flush_input()
            if self.mGetFoundCount() < 15:
                self.mAdjustTimerInterval()
            else:
                M.waitCursor()
                self.pWinCount += 1
                M.removeUpdateList(self)
                sd.mDisable()
                self.pVisibleTimer.mStop()
                if self.mTestForBest():
                    self.pVisibleTimer.mFlashOn()
                    self.pVisibleTimer.mPlay()
                    self.pNewBest = 1
                self.pCompleteAudio.mSetEventTag(Sym('WINROUND'))
                self.pCompleteAudio.mPlay()
        else:
            self.pFakeList.append(theObject.pMember)
            theObject.mHide()
            theObject.mReset()
            R().sound.puppet(1, self.pWrongSound)
            R().update_stage()
            R().wait_sound(1)
            if self._lvl() != 'easy':
                self.pHolddaButton = self.mRemoveFoundItem()
            R().flush_input()

    def mTestForBest(self):
        if self.pBestTimer.mGetTime() == 0:
            self.pBestTimer.mSetTime(self.pVisibleTimer.mGetTime())
            self.pBestTimer.mDraw()
            return 0
        if self.pVisibleTimer.mGetTime() < self.pBestTimer.mGetTime():
            return 1
        return 0

    def mWon3(self):
        M.gScreenDaddy.mAddToken(Sym('CC'))
        self.pQueObject = M.getPlayQueueObject(self)
        self.pQueObject.mSetEventTag(Sym('WINROUND'))
        self.pQueObject.mAddItem(self.pSkellyAnims[0])
        self.pQueObject.mAddItem(self.pEndAudio)
        self.pQueObject.mAddItem(self.pSkellyAnims[1])
        self.pQueObject.mPlay()

    def mGetWinCount(self):
        return self.pWinCounter.mGetWinCount()
