"""Hand-ported parent scripts: scavenger-hunt managers.

    ParentScript 162  HUNT_FINALE   the level-2 "soup card" clue strip shown in every room (type #HUNT_FINALE)

Clicking the soup card on the finale screen (pFinaleScreen, the DOOR) plays the finale and beats the game;
anywhere else it plays the "wrong" sound + the KT_NO.AIF voice-over.  Imported from INIT_MAIN (movie.py).
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object
from .lingo import Sym, Point, set_properties, pop_one
from .ui import blank, load_mem, unload_mem
from .screens2 import S


@lingo_script('HUNT_FINALE')
class HuntFinale(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pClueButton = 0
        self.pWrongSound = 0
        self.pFinaleScreen = None
        self.pClueTextMember = 0
        self.pClueTExtSprite = 0
        self.pClueAudio = 0
        self.pClueStripMember = 0
        self.pClueStripSprite = 0
        self.pClueTextButton = 0
        self.pShown = 0
        self.pWrongVO = 0
        self.pParent = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        self.pShown = 0
        set_properties(theObjectData, self)
        self.pClueStripSprite = pop_one(theSpriteAlloc)
        self.pClueTExtSprite = pop_one(theSpriteAlloc)
        self.pClueButton = get_object(self.pClueButton, theSpriteAlloc)
        self.pClueButton.mSetParent(self)
        self.pClueTextButton = 0
        self.pWrongVO = "KT_NO.AIF"
        return self

    def mInitPoolObjects(self):
        if not isinstance(self.pClueAudio, LObject):
            self.pClueAudio = M.getExSoundObject(2, self.pClueAudio, self)
        if not isinstance(self.pClueTextButton, LObject):
            self.pClueTextButton = M.getSimpleButt(self.pClueTExtSprite, self.pClueTextMember, self, 8)
            if self.pClueTextButton.pLoc is None:
                self.pClueTextButton.pLoc = M.getRegPoint()
        if not isinstance(self.pWrongSound, LObject):
            self.pWrongSound = M.getSoundObject(1, self.pWrongSound, self)
        if not isinstance(self.pWrongVO, LObject):
            self.pWrongVO = M.getExSoundObject(1, self.pWrongVO, self)

    def mReleasePoolObjects(self):
        if isinstance(self.pClueAudio, LObject):
            self.pClueAudio = M.recycleSoundObject(self.pClueAudio)
        if isinstance(self.pWrongSound, LObject):
            self.pWrongSound = M.recycleSoundObject(self.pWrongSound)
        if isinstance(self.pWrongVO, LObject):
            self.pWrongVO = M.recycleSoundObject(self.pWrongVO)
        if isinstance(self.pClueTextButton, LObject):
            M.recycleSimpleButt(self.pClueTextButton)
            self.pClueTextButton = 0

    def mDestroy(self):
        pass

    def mDisable(self):
        if self.pShown:
            S(self.pClueTExtSprite).cursor = 0
            self.pClueTextButton.mDisable()
            self.pClueButton.mDisable()

    def mEnable(self):
        if self.pShown:
            S(self.pClueTExtSprite).cursor = [33, 34]
            self.pClueTextButton.mEnable()
            self.pClueButton.mEnable()

    def mShow(self):
        S(self.pClueStripSprite).member = self.pClueStripMember
        S(self.pClueTExtSprite).cursor = [33, 34]
        self.pClueTextButton.mShow()
        self.pClueButton.mShow()
        self.pShown = 1

    def mHide(self):
        S(self.pClueTExtSprite).cursor = 0
        blank(self.pClueStripSprite)
        if isinstance(self.pClueTextButton, LObject):
            self.pClueTextButton.mHide()
        self.pClueButton.mHide()
        self.pShown = 0

    def mLoad(self):
        load_mem(self.pClueTextMember)
        load_mem(self.pClueStripMember)

    def mLoadList(self, theList):
        theList.append(self.pClueTextMember)
        theList.append(self.pClueStripMember)
        theList.append(self.pWrongSound)

    def mUnload(self, forceFlag=0):
        pass

    # ---- buttons / sounds -----------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        sd = M.gScreenDaddy
        if theObject is self.pClueButton:
            if self.pFinaleScreen == M.gCurScreen.pName:
                M.waitCursor()
                sd.mDisable()
                sd.mPlayFinale()
            else:
                self.pWrongSound.mPlay()
        elif theObject is self.pClueTextButton:
            M.setInterruptMode(self.pClueAudio)
            self.pClueAudio.mPlay()

    def mPlayDone(self, theObject):
        if theObject is self.pWrongSound:
            M.setInterruptMode(self.pWrongVO)
            self.pWrongVO.mPlay()
        elif theObject is self.pWrongVO:
            M.clearInterruptMode()
            M.resetCursor()
            M.gScreenDaddy.mEnable()

    # ---- manager interface used by GAME ---------------------------------------------------------
    def mGetName(self):
        return self.pName

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('HUNT_FINALE')

    def mSetHuntIndex(self, theIndex):
        pass

    def mGetHuntIndex(self):
        return 1

    def mExternalSHTokenFound(self, theObject=None):
        M.waitCursor()
        M.gScreenDaddy.mDisable()
        M.gScreenDaddy.mPlayFinale()

    def mGetCurrentHuntObject(self):
        return None

    def mAllTokensFound(self):
        return 0

    def mLoadFoundTokens(self):
        pass

    def mLoadFoundTokensList(self, theList=None):
        pass

    def mUnloadFoundTokens(self):
        pass

    def mShowFoundTokens(self):
        pass

    def mHideFoundTokens(self):
        pass

    def mGetCurrentHuntName(self):
        return self.pFinaleScreen
