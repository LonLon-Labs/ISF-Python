"""Hand-ported parent scripts, part 6: the room screens.

    ParentScript  50  SCREEN_CREDIT      the credits slide show
    ParentScript  48  SCREEN_STUDY       the Study (book buttons / window / intro bink)

(SCREEN_KITCHEN 49, SCREEN_MM 51, SCREEN_CC 52 and SCREEN_IWORKSHOP 53 follow.)
Imported at the bottom of rooms.py so `from . import rooms` registers everything.
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object
from .lingo import Sym, set_properties, pop_one
from .ui import load_mem, unload_mem, set_behavior, remove_behavior, blank
from .screens2 import R, S, _alive
from .riddles import call_all


# ============================================================================================
# SCREEN_CREDIT  (ParentScript 50)
# ============================================================================================

@lingo_script('SCREEN_CREDIT')
class ScreenCredit(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pAmbientAudio = 0
        self.pSlideSprite = 0
        self.pSlideSet = []
        self.pSpeed = 7000
        self.pLastUpdate = 0
        self.pSavedList = []
        self.pCurrSlideSet = 1
        self.pCurrSlide = 1
        self.pFinished = 0
        self.pLastMouseDown = 0
        self.pPageSound = 0
        self.pEnabled = 0
        self.pReturnScreen = Sym('quit')
        self.pBackground = 0
        self.pBackgroundSprite = 0
        self.pAnimObject = 0

    def mInit(self, thePacketInfo, theSpriteAlloc):
        set_properties(thePacketInfo, self)
        self.pBackgroundSprite = pop_one(theSpriteAlloc)
        self.pAnimObject = get_object(self.pAnimObject, theSpriteAlloc)
        self.pSlideSprite = pop_one(theSpriteAlloc)
        self.pLastUpdate = 0
        self.pSpeed = 7000
        self.pCurrSlideSet = 1
        self.pCurrSlide = 1
        self.pFinished = 0
        self.pLastMouseDown = 0
        self.pEnabled = 0
        self.pSavedList = []
        self.pReturnScreen = Sym('quit')
        self.pAnimObject.mSetParent(self)

    def mInitPoolObjects(self):
        pass

    def mReleasePoolObjects(self):
        pass

    def mGetEnabled(self):
        return self.pEnabled

    def mDestroy(self):
        pass

    def _slide(self):
        return self.pSlideSet[self.pCurrSlideSet - 1][self.pCurrSlide - 1]

    def mLoad(self):
        for slides in self.pSlideSet:
            load_mem(slides)

    def mLoadList(self, theList):
        theList.append(self.pBackground)
        theList.append(self.pAmbientAudio)
        self.pAnimObject.mLoadList(theList)
        theList.append(self.pSlideSet[0][0])

    def mUnload(self):
        pass

    def mShow(self):
        M.FadeInAmbientSound(self.pAmbientAudio, 0)
        S(self.pBackgroundSprite).member = self.pBackground
        S(self.pSlideSprite).ink = 36
        self.mReset()
        S(self.pSlideSprite).member = self._slide()
        self.pLastUpdate = R().milliseconds()
        self.pLastMouseDown = R().milliseconds()
        M.addUpdateList(self)
        M.resetCursor()
        self.pEnabled = 1
        set_behavior(self.pBackgroundSprite, self)
        self.pAnimObject.mShow()
        self.pAnimObject.mPlay()

    def mouseDown(self):
        if R().milliseconds() > (self.pLastMouseDown + 500):
            if self.pCurrSlideSet < 2:
                self.pCurrSlide = 1
                self.pCurrSlideSet += 1
                load_mem(self._slide())
                R().sound.puppet(1, self.pPageSound)
                S(self.pSlideSprite).member = self._slide()
                self.pLastUpdate = R().milliseconds()
                self.pLastMouseDown = R().milliseconds()
            else:
                self.mFinish()

    def mUpdate(self):
        now = R().milliseconds()
        if (now - self.pLastUpdate) >= self.pSpeed:
            self.pLastUpdate = now
            if self.pFinished == 0:
                if self.pCurrSlide < len(self.pSlideSet[self.pCurrSlideSet - 1]):
                    self.pCurrSlide += 1
                    R().sound.puppet(1, self.pPageSound)
                    S(self.pSlideSprite).member = self._slide()
                else:
                    if self.pCurrSlideSet < len(self.pSlideSet):
                        self.pCurrSlide = 1
                        self.pCurrSlideSet += 1
                        R().sound.puppet(1, self.pPageSound)
                        S(self.pSlideSprite).member = self._slide()
                    else:
                        self.pFinished = 1
            else:
                self.mFinish()

    def mFinish(self):
        self.pAnimObject.mKill()
        remove_behavior(self.pBackgroundSprite, self)
        self.mReset()
        M.removeUpdateList(self)
        if self.pReturnScreen != Sym('quit'):
            M.gScreenDaddy.mNavigate(self.pReturnScreen, 1)
        else:
            M.doshutDown()

    def mReset(self):
        self.pLastUpdate = 0
        self.pCurrSlideSet = 1
        self.pCurrSlide = 1
        self.pFinished = 0
        self.pLastMouseDown = 0

    def mHide(self):
        self.pEnabled = 0
        M.removeUpdateList(self)
        self.mReset()
        blank(self.pSlideSprite)
        blank(self.pBackgroundSprite)
        self.pAnimObject.mHide()

    def mPlayLoop(self):
        M.FadeInAmbientSound(self.pAmbientAudio)

    def mGetName(self):
        return self.pName

    def mCheckKey(self, thekeycode):
        M.QuitKeyCheck(thekeycode, 1)

    def mDisable(self):
        self.pEnabled = 0
        M.removeUpdateList(self)

    def mEnable(self):
        self.pEnabled = 1
        M.addUpdateList(self)

    def mApplicationActivated(self):
        pass

    def mApplicationDeactivated(self):
        pass

    def mGetType(self):
        return Sym('SCREEN_CREDIT')

    def mGetHelpState(self):
        return 0

    def mPlayDone(self, theObject=None):
        pass


# ============================================================================================
# SCREEN_STUDY  (ParentScript 48)
# ============================================================================================

@lingo_script('SCREEN_STUDY')
class ScreenStudy(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pBGMember = 0
        self.pSprite = 0
        self.pWindowButton = 0
        self.pIntroBink = 0
        self.pBackButton = 0
        self.pHelpButton = 0
        self.pAmbientAudio = 0
        self.pEnabled = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pIntroBink = get_object(self.pIntroBink, theSpriteAlloc)
        self.pWindowButton = get_object(self.pWindowButton, theSpriteAlloc)
        self.pWindowButton.mSetParent(self)
        self.pIntroBink.mSetParent(self)
        self.pBackButton = 0
        self.pHelpButton = 0
        self.pEnabled = 0
        return self

    def mDestroy(self):
        pass

    def mInitPoolObjects(self):
        pass

    def mReleasePoolObjects(self):
        pass

    def mLoad(self):
        self.pWindowButton.mLoad()
        if not self.pIntroBink.pPlayed:
            self.pIntroBink.mLoad()
            load_mem(self.pBGMember)
        else:
            self.pIntroBink.mLoad()
        load_mem(self.pAmbientAudio)

    def mLoadList(self, theList):
        theList.append(self.pAmbientAudio)
        if not self.pIntroBink.pPlayed:
            self.pIntroBink.mLoadList(theList)
            theList.append(self.pBGMember)
        else:
            self.pIntroBink.mLoadList(theList)
        self.pWindowButton.mLoadList(theList)

    def mUnload(self):
        self.pWindowButton.mUnload()
        self.pIntroBink.mUnload()

    def mHuntObjectFound(self, theObject):
        self.mEnable()

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    def mGetEnabled(self):
        return self.pEnabled

    def mShow(self):
        self.pHelpButton = M.getGameHelpButton()
        self.pBackButton = M.getGameBackButton()
        self.pHelpButton.mSetParent(self)
        self.pBackButton.mSetParent(self)
        self.pHelpButton.mShow()
        self.pBackButton.mShow()
        M.FadeInAmbientSound(self.pAmbientAudio)
        if not self.pIntroBink.pPlayed:
            M.setMember(self.pSprite, self.pBGMember)
            R().update_stage()
            self.pHelpButton.mDisable()
            self.pBackButton.mDisable()
            self.pIntroBink.mPlay()
            return
        else:
            self.pIntroBink.mShow()
            self.pWindowButton.mShow()
        self.pEnabled = 1
        if not M.gScreenDaddy.mCheckStatus():
            M.resetCursor()

    def mHide(self):
        for o in (self.pHelpButton, self.pBackButton):
            if _alive(o):
                o.mHide()
        self.pIntroBink.mHide()
        self.pWindowButton.mHide()
        blank(self.pSprite)
        self.pEnabled = 0

    def mPlayDone(self, theObject):
        if theObject is self.pIntroBink:
            self.pWindowButton.mShow()
            if not M.gScreenDaddy.mCheckStatus():
                M.resetCursor()
            self.mEnable()

    def mButtonActivated(self, theObject):
        if theObject is self.pHelpButton:
            M.gScreenDaddy.pHelpPlayer.mStartHelp()
        elif theObject is self.pBackButton:
            M.navigateBack()
        elif theObject is self.pWindowButton:
            M.gScreenDaddy.mPlayFinale()

    def mButtonDeActivated(self, theButton):
        pass

    def mEnable(self):
        self.pEnabled = 1
        for o in (self.pHelpButton, self.pBackButton, self.pWindowButton):
            if _alive(o):
                o.mEnable()

    def mDisable(self):
        self.pEnabled = 0
        for o in (self.pHelpButton, self.pBackButton, self.pWindowButton):
            if _alive(o):
                o.mDisable()

    def mApplicationActivated(self):
        pass

    def mApplicationDeactivated(self):
        pass

    def mGetType(self):
        return Sym('SCREEN_STUDY')

    def mGetName(self):
        return self.pName

    def mGetHelpState(self):
        return 0
