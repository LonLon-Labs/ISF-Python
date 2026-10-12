"""Hand-ported Fantasy parent scripts, part 4: the book (cast #D_BK) and the pieces it is built from.

    ParentScript 100  BINK_MODAL     a BINK whose video blocks until it has finished (binkPlay is modal in the xtra)
    ParentScript  94  BOOK_PAGE      one page of the book: curled-edge button, centre art, optional text button + audio
    ParentScript  83  BUTT_DRAGON    a button made of three animation objects (roll on / roll off / down)
    ParentScript  93  SCREEN_BOOK    the book itself: right-hand page list, left-hand page list, "missing pages" audio

Translated one-to-one from the Fantasy .ls; method and property names unchanged.  Conventions as in
fantasy_screens.py (`M.gScreenDaddy` is the Lingo global gScreenDaddy, `S(chan)` is sprite(chan)).

Port notes:
  * BINK_MODAL.mPlay: the Lingo calls binkPlay(), which returns only when the video has ended, and then
    waits ~10 update-list ticks before telling its parent.  Here the clip (video.VideoClip, ffmpeg) is run in a
    pump loop with the same effect.  With no ffmpeg / no .bik file the Lingo's own `not objectp(pBinkObject)`
    branch is taken (show the still, tell the parent at once).
  * BOOK_PAGE.mInit: `pEdgeButton = getObject(pEdgeButton, theSpriteAlloc)` -- pEdgeButton is not a property of the
    script, so in Lingo it is a VOID local and getObject() hands it straight back; it takes no sprites.  Kept as a no-op.
  * SCREEN_BOOK.mHide: `if objectp(pCurrentLeftPageObj) then mHide(...) pCurrentRightPageObj = 0` (sic, the left
    object stays set).  Kept.
  * SCREEN_BOOK.mSoundDone's `daList = [pCurrentPageSound, pLoaderObject]` is an unused local in the Lingo.
  * SCREEN_BOOK has no mHandleDroppedObject; the #DRAG_N_DROP case of mPlayDone is dead code in the original
    (no DRAG_N_DROP object is ever created for this screen).
"""
import os
import time

from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, Point, set_properties, pop_one, pop_list
from .ui import R, S, load_mem, unload_mem, call_all, blank, set_behavior, remove_behavior
from .screens2 import _alive, _get_pos, _new, _rollover
from .scavenger import _eq, _typ, _unload, _call_if, _stringp
from .video import VideoClip, find_ffmpeg


def _sd():
    return M.gScreenDaddy


def _rollover_chan(chan):
    """rollover(chan) -- screens2._rollover (matte / bg-transparent pixels do not count, as in Director)."""
    return _rollover(chan)


# ============================================================================================
# BINK_MODAL  (ParentScript 100)
# ============================================================================================

@lingo_script('BINK_MODAL')
class BinkModal(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pFileName = ''
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pPlayed = 0
        self.pLoc = Point(0, 0)
        self.pButtonMember = 0
        self.pButtonSprite = 0
        self.pAnimPos = 0
        self.pSound = 0
        self.pLastUpdate = 0
        self.pSpeed = 0
        self.pParent = 0
        self.pSavedList = []
        self.pRepeatable = 0
        self.pBinkObject = 0
        self.pFlushCount = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pButtonSprite = pop_one(theSpriteAlloc)
        self.pBackSprite = pop_one(theSpriteAlloc)
        # getPath(the moviePath, ["BINK"], pFileName): <game>\DATA\BINK\<file> (as video.Bink does)
        self.pFileName = os.path.join(R().game_root or '', 'DATA', 'BINK', str(self.pFileName))
        self.pPlayed = 0
        self.pAnimPos = 0
        self.pLastUpdate = 0
        self.pFlushCount = 0
        self.pSavedList = [Sym('pPlayed')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self): pass

    def mLoad(self):
        if max(self.pRepeatable or 0, 0 if self.pPlayed else 1):
            if not self.pBinkObject:
                # xtraLoaded("binkXTRA"): ffmpeg + the .bik file
                if find_ffmpeg() and os.path.exists(self.pFileName):
                    self.pBinkObject = VideoClip(R(), self.pFileName, self.pLoc)
        load_mem(self.pBackMember)

    def mLoadList(self, theList):
        theList.append(self)

    def mUnLoad(self):
        if isinstance(self.pBinkObject, VideoClip):
            self.pBinkObject.stop()                      # binkClose
            self.pBinkObject = 0
        unload_mem(self.pSound)
        unload_mem(self.pBackMember)
    mUnload = mUnLoad

    def mSetParent(self, theObject): self.pParent = theObject
    def mGetType(self): return Sym('Bink')
    def mGetName(self): return self.pName

    def mShow(self):
        if self.pPlayed and self.pBackMember and not self.pRepeatable:
            S(self.pBackSprite).member = self.pBackMember
        else:
            if self.pButtonMember:
                S(self.pButtonSprite).member = self.pButtonMember

    def mHide(self):
        blank(self.pButtonSprite)
        blank(self.pBackSprite)

    def mouseDown(self):
        self.mPlay()

    def mPlay(self):
        self.pPlayed = self.pPlayed + 1
        if isinstance(self.pBinkObject, VideoClip):
            rt = R()
            clip = self.pBinkObject
            # binkGoto(1) on a replay is implied: VideoClip.start() always begins at the first frame
            clip.start()                                  # binkPlay (modal: returns when the video is over)
            try:
                while True:
                    rt.pump()
                    if clip.update():
                        break
                    rt.update_stage()
                    time.sleep(0.004)
            finally:
                clip.stop()
            if self.pBackMember:
                S(self.pBackSprite).member = self.pBackMember
            rt.flush_input()
            # (the Lingo sets `the updateLock` = 1 here)
            M.addUpdateList(self)
        else:
            S(self.pBackSprite).member = self.pBackMember
            if self.pParent:
                self.pParent.mPlayDone(self)

    def mEnable(self): set_behavior(self.pButtonSprite, self)
    def mDisable(self): remove_behavior(self.pButtonSprite, self)

    def mUpdate(self):
        self.pFlushCount = self.pFlushCount + 1
        if self.pFlushCount > 10:
            self.pFlushCount = 0
            M.removeUpdateList(self)
            if self.pParent:
                self.pParent.mPlayDone(self)
            # (the Lingo sets `the updateLock` = 0 here)

    def mStop(self):
        S(self.pBackSprite).member = self.pBackMember
        if self.pParent:
            self.pParent.mPlayDone(self)


# ============================================================================================
# BOOK_PAGE  (ParentScript 94)
# ============================================================================================

@lingo_script('BOOK_PAGE')
class BookPage(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pEdgeNeutral = 0
        self.pEdgeRoll = 0
        self.pEdgeSprite = 0
        self.pCenterMember = 0
        self.pCenterSprite = 0
        self.pBottomMember = 0
        self.pBottomSprite = 0
        self.pDetectSprite = 0
        self.pSavedList = []
        self.pParent = 0
        self.pPageAudio = 0
        self.pRollSound = 0
        self.pPageButton = 0
        self.pRollOn = 0
        self.pMouseDown = 0
        self.pDontClick = 0
        self.pTextMember = 0
        self.pTextSprite = 0
        self.pShown = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        # pEdgeButton = getObject(pEdgeButton, theSpriteAlloc): a VOID local in the Lingo -> no-op (see module note)
        self.pTextSprite = pop_one(theSpriteAlloc)
        self.pCenterSprite = pop_one(theSpriteAlloc)
        self.pBottomSprite = pop_one(theSpriteAlloc)
        self.pEdgeSprite = pop_one(theSpriteAlloc)
        self.pDetectSprite = 0
        self.pPageButton = 0
        self.pRollOn = 0
        self.pMouseDown = 0
        self.pDontClick = 0
        self.pShown = 0
        self.pSavedList = [Sym('pShown')]
        M.addObjectGlob(self)
        return self

    def mInitPoolObjects(self):
        self.pRollSound = M.getSoundObject(1, self.pRollSound, self)
        if self.pTextMember:
            self.pPageButton = M.getSimpleButt(self.pTextSprite, self.pTextMember, self, 8)
            self.pPageAudio = M.getExSoundObject(2, self.pPageAudio, self)

    def mReleasePoolObjects(self):
        self.pRollSound = M.recycleSoundObject(self.pRollSound)
        if self.pTextMember:
            self.pPageAudio = M.recycleSoundObject(self.pPageAudio)
            M.recycleSimpleButt(self.pPageButton)
            self.pPageButton = M.recycleSoundObject(self.pPageButton)

    def mDestroy(self): pass
    def mSetDetectSprite(self, theSprite): self.pDetectSprite = theSprite
    def mGetName(self): return self.pName
    def mGetType(self): return Sym('BOOK_PAGE')
    def mLoad(self): pass

    def mLoadList(self, theList):
        theList.append(self.pEdgeNeutral)
        theList.append(self.pEdgeRoll)
        theList.append(self.pCenterMember)
        theList.append(self.pBottomMember)
        theList.append(self.pRollSound)
        theList.append(self.pTextMember)

    def mUnLoad(self):
        unload_mem(self.pEdgeNeutral)
        unload_mem(self.pEdgeRoll)
        unload_mem(self.pCenterMember)
        unload_mem(self.pBottomMember)
        unload_mem(self.pRollSound)
        unload_mem(self.pTextMember)
    mUnload = mUnLoad

    def mUnLoadMiddle(self): pass

    def mLoadEdgeList(self, theList):
        theList.append(self.pEdgeNeutral)
        theList.append(self.pBottomMember)

    def mShowEdge(self):
        S(self.pEdgeSprite).member = self.pEdgeNeutral
        S(self.pBottomSprite).member = self.pBottomMember

    def mHideEdge(self):
        S(self.pEdgeSprite).member = 1
        S(self.pBottomSprite).member = 1

    def mShow(self):
        if self.pTextMember:
            S(self.pTextSprite).cursor = [22, 23]
            self.pPageButton.mShow()
        else:
            S(self.pTextSprite).member = self.pTextMember
            S(self.pTextSprite).ink = 8
        self.mWillRollover()
        S(self.pCenterSprite).member = self.pCenterMember
        S(self.pCenterSprite).ink = 8
        S(self.pEdgeSprite).ink = 36
        S(self.pBottomSprite).member = self.pBottomMember
        set_behavior(self.pDetectSprite, self)

    def mHide(self):
        if M.isUpdating(self.pRollSound):
            self.pRollSound.mKill()
        self.pMouseDown = 0
        self.pDontClick = 0
        if _alive(self.pPageButton):
            self.pPageButton.mHide()
        else:
            blank(self.pTextSprite)
        blank(self.pCenterSprite)
        blank(self.pEdgeSprite)
        blank(self.pBottomSprite)
        remove_behavior(self.pDetectSprite)

    def mWillRollover(self):
        rt = R()
        daLOc = S(self.pDetectSprite).loc
        if rt.will_roll_over(S(self.pDetectSprite).member, daLOc, rt.mouse):
            self.pRollOn = 1
            S(self.pEdgeSprite).member = self.pEdgeRoll
        else:
            S(self.pEdgeSprite).member = self.pEdgeNeutral

    def mPlayPageAudio(self): return 0

    def mCurlPage(self):
        S(self.pEdgeSprite).member = self.pEdgeRoll

    def mouseEnter(self):
        self.pRollOn = 1
        if not M.isUpdating(self.pRollSound):
            self.pRollSound.mPlay()
            S(self.pEdgeSprite).member = self.pEdgeRoll

    def mouseLeave(self):
        self.pRollOn = 0
        if not M.isUpdating(self.pRollSound):
            S(self.pEdgeSprite).member = self.pEdgeNeutral

    def mouseDown(self):
        if not self.pDontClick:
            if M.isUpdating(self.pRollSound):
                self.pMouseDown = 1
            else:
                self.pParent.mButtonActivated(self)

    def mEnable(self):
        self.pDontClick = 0
        if _alive(self.pPageButton):
            S(self.pTextSprite).cursor = [22, 23]
            self.pPageButton.mEnable()
        set_behavior(self.pDetectSprite, self)

    def mDisable(self):
        if _alive(self.pPageButton):
            S(self.pTextSprite).cursor = 0
            self.pPageButton.mDisable()
        remove_behavior(self.pDetectSprite)

    def mButtonActivated(self, theObject):
        M.setInterruptMode(self.pPageAudio)
        self.pPageAudio.mPlay()

    def mButtonDeActivated(self): pass

    def mPlayDone(self, theObject):
        if theObject is self.pPageAudio:
            M.enableGame()
            M.resetCursor()
        else:
            if self.pMouseDown:
                self.pParent.mButtonActivated(self)
            else:
                if not self.pRollOn:
                    self.mouseLeave()

    def mUpdate(self): pass
    def mSetParent(self, theObject): self.pParent = theObject


# ============================================================================================
# BUTT_DRAGON  (ParentScript 83)
# ============================================================================================

@lingo_script('BUTT_DRAGON')
class ButtDragon(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pEnabled = 0
        self.pNeutMember = 0
        self.pRollOnAnimObject = 0
        self.pRollOffAnimObject = 0
        self.pDownAnimObject = 0
        self.pCurrentAnimObject = 0
        self.pRollOnList = []
        self.pRollOffList = []
        self.pRollDownList = []
        self.pCurrentList = 0
        self.pInk = 0
        self.pLoc = Point(320, 240)
        self.pSprite = 0
        self.pParent = 0
        self.pSavedList = []
        self.pRollOn = 0
        self.pDownFlag = 0
        self.pInitialRolloverFlag = 0
        self.pAnimSprite = 0
        self.pUpdateMode = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pAnimSprite = pop_one(theSpriteAlloc)
        self.pRollOnAnimObject = get_object(self.pRollOnAnimObject, [self.pAnimSprite])
        self.pRollOffAnimObject = get_object(self.pRollOffAnimObject, [self.pAnimSprite])
        self.pDownAnimObject = get_object(self.pDownAnimObject, [self.pAnimSprite])
        daList = list(reversed(self.pRollOnAnimObject.pAnimList))          # reverseList
        self.pRollOffAnimObject.pAnimList = daList
        self.pRollOnAnimObject.mSetParent(self)
        self.pRollOffAnimObject.mSetParent(self)
        self.pDownAnimObject.mSetParent(self)
        self.pCurrentAnimObject = 0
        self.pRollOnList = self.pRollOnAnimObject.pAnimList
        self.pRollOffList = self.pRollOffAnimObject.pAnimList
        self.pRollDownList = self.pDownAnimObject.pAnimList
        self.pCurrentList = 0
        self.pDownFlag = 0
        self.pUpdateMode = 0
        self.pRollOn = 0
        self.pEnabled = 1
        self.pSavedList = []
        return self

    def mDestroy(self): pass
    def mSetParent(self, theObject): self.pParent = theObject
    def mGetType(self): return Sym('BUTT_DRAGON')
    def mGetName(self): return self.pName

    def mLoad(self):
        load_mem(self.pNeutMember)
        self.pRollOnAnimObject.mLoad()
        self.pDownAnimObject.mLoad()

    def mLoadList(self, theList):
        theList.append(self.pNeutMember)
        self.pRollOnAnimObject.mLoadList(theList)
        self.pDownAnimObject.mLoadList(theList)

    def mUnLoad(self):
        unload_mem(self.pNeutMember)
        _unload(self.pRollOnAnimObject)
        _unload(self.pDownAnimObject)
    mUnload = mUnLoad

    def mouseDown(self):
        if _alive(self.pCurrentAnimObject):
            self.pCurrentAnimObject.mStop()
        self.pCurrentAnimObject = self.pDownAnimObject
        self.pCurrentAnimObject.mShow()
        self.pCurrentAnimObject.mPlay()
        M.removeUpdateList(self)
        remove_behavior(self.pSprite, self)

    def mouseUp(self): pass
    def mouseUpOutSide(self): pass

    def mouseEnter(self):
        self.pRollOn = 1
        if not self.pInitialRolloverFlag:
            if self.pCurrentAnimObject is self.pRollOffAnimObject:
                daMemberNum = S(self.pAnimSprite).member
                self.pRollOffAnimObject.mStop()
                self.pRollOffAnimObject.mHide()
                self.pCurrentAnimObject = self.pRollOnAnimObject
                self.pCurrentAnimObject.mShow()
                self.pCurrentAnimObject.mSetAnimMemberIndex(daMemberNum)
                self.pCurrentAnimObject.mPlay()
            else:
                if not self.pCurrentAnimObject:
                    self.pCurrentAnimObject = self.pRollOnAnimObject
                    self.pCurrentAnimObject.mShow()
                    self.pCurrentAnimObject.mPlay()

    def mouseLeave(self):
        self.pRollOn = 0
        if not self.pInitialRolloverFlag:
            if self.pCurrentAnimObject is self.pRollOnAnimObject:
                daMemberNum = S(self.pAnimSprite).member
                self.pRollOnAnimObject.mStop()
                self.pRollOnAnimObject.mHide()
                self.pCurrentAnimObject = self.pRollOffAnimObject
                self.pCurrentAnimObject.mShow()
                self.pRollOffAnimObject.mSetAnimMemberIndex(daMemberNum)
                self.pCurrentAnimObject.mPlay()
            else:
                if not self.pCurrentAnimObject:
                    self.pCurrentAnimObject = self.pRollOffAnimObject
                    self.pCurrentAnimObject.mShow()
                    self.pCurrentAnimObject.mPlay()
        self.pInitialRolloverFlag = 0

    def mPlayDone(self, theObject):
        if theObject is self.pRollOffAnimObject:
            self.pCurrentAnimObject.mStop()
            self.pCurrentAnimObject.mHide()
            self.pCurrentAnimObject = 0
            if self.pRollOn:
                self.mouseEnter()
        else:
            if theObject is self.pRollOnAnimObject:
                self.pCurrentAnimObject.mStop()
                self.pCurrentAnimObject = 0
                if not self.pRollOn:
                    self.mouseLeave()
            else:
                if theObject is self.pDownAnimObject:
                    self.pParent.mButtonActivated(self)

    def mEnable(self):
        if self.pUpdateMode:
            M.addUpdateList(self)
        else:
            set_behavior(self.pSprite, self)

    def mDisable(self):
        if self.pUpdateMode:
            M.removeUpdateList(self)
        else:
            remove_behavior(self.pSprite, self)

    def mShow(self):
        rt = R()
        S(self.pSprite).ink = self.pInk
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pNeutMember
        if rt.will_roll_over(self.pNeutMember, Point(320, 240), rt.mouse):
            self.pInitialRolloverFlag = 1
        self.pUpdateMode = 0
        set_behavior(self.pSprite, self)

    def mHide(self):
        if _alive(self.pCurrentAnimObject):
            self.pCurrentAnimObject.mStop()
        self.pRollOnAnimObject.mHide()
        self.pRollOffAnimObject.mHide()
        self.pDownAnimObject.mHide()
        self.pCurrentAnimObject = 0
        self.pDownFlag = 0
        blank(self.pSprite)
        remove_behavior(self.pSprite)
        M.removeUpdateList(self)

    def mUpdate(self):
        if _rollover_chan(self.pSprite) and not self.pRollOn:
            self.mouseEnter()
        else:
            if not _rollover_chan(self.pSprite) and self.pRollOn:
                self.mouseLeave()

    def mEnableUpdateMode(self):
        self.pUpdateMode = 1
        M.addUpdateList(self)
        remove_behavior(self.pSprite, self)

    def mDisableUpdateMode(self):
        self.pUpdateMode = 0
        M.removeUpdateList(self)
        set_behavior(self.pSprite, self)


# ============================================================================================
# SCREEN_BOOK  (ParentScript 93)
# ============================================================================================

@lingo_script('SCREEN_BOOK')
class ScreenBook(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pRightPageObjectList = []
        self.pLeftPageObjectList = []
        self.pRightPageMouseDetect = 0
        self.pLeftPageMouseDetect = 0
        self.pRightBackDetectMember = 0
        self.pFullBackDetectMember = 0
        self.pBackDetectButton = 0
        self.pBackDetectSprite = 0
        self.pMissingPagesAudio = 0
        self.pRightPageMouseDetectSprite = 0
        self.pLeftPageMouseDetectSprite = 0
        self.pMissingPagesMemberList = []
        self.pMissingPageSprite = 0
        self.pMissingPageAudio = 0
        self.pMissingPageAudioList = []
        self.pBackPageAudioPlayed = 0
        self.pAmbientAudio = 0
        self.pHomeButton = 0
        self.pHelpButton = 0
        self.pBackButton = 0
        self.pSavedList = []
        self.pParent = 0
        self.pLeftPageSound = 0
        self.pRightPageSound = 0
        self.pCurrentLeftPageObj = 0
        self.pCurrentRightPageObj = 0
        self.pAllFoundBink = 0
        self.pCurrentPage = 1
        self.pMissingPageAudioPlayed = 0
        self.pEnabled = 0
        self.pLoaderObject = 0
        self.pCurrentPageSound = 0
        self.pLoaderScriptNumber = 0
        self.pVisited = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackDetectSprite = pop_one(theSpriteAlloc)
        self.pRightPageMouseDetectSprite = pop_one(theSpriteAlloc)
        self.pLeftPageMouseDetectSprite = pop_one(theSpriteAlloc)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pMissingPageSprite = pop_one(theSpriteAlloc)
        daRightPageAlloc = pop_list(theSpriteAlloc, 30)
        self.pRightPageObjectList = get_object_list(self.pRightPageObjectList, list(reversed(daRightPageAlloc)))
        self.pLeftPageObjectList = get_object_list(self.pLeftPageObjectList, theSpriteAlloc, 5)
        call_all(self.pRightPageObjectList, 'mSetDetectSprite', self.pRightPageMouseDetectSprite)
        call_all(self.pLeftPageObjectList, 'mSetDetectSprite', self.pLeftPageMouseDetectSprite)
        call_all(self.pRightPageObjectList, 'mSetParent', self)
        call_all(self.pLeftPageObjectList, 'mSetParent', self)
        self.pAllFoundBink = get_object(self.pAllFoundBink, theSpriteAlloc)
        self.pAllFoundBink.mSetParent(self)
        self.pLoaderObject = _new(self.pLoaderScriptNumber)
        self.pLoaderObject.pMinTime = 0
        self.pLoaderObject.mSetParent(self)
        self.pHomeButton = 0
        self.pHelpButton = 0
        self.pBackButton = 0
        self.pVisited = 0
        self.pCurrentLeftPageObj = 0
        self.pCurrentRightPageObj = 0
        self.pCurrentPageSound = 0
        self.pCurrentPage = 1
        self.pEnabled = 1
        self.pMissingPageAudioList = ["D_BK_INTRO1_V.aif", "D_BK_INTRO2_V.aif", "D_BK_INTRO3_V.aif",
                                      "D_BK_Missing1_V.aif", "D_BK_Missing2_V.aif", "D_BK_GetPages_V.AIF"]
        self.pMissingPageAudio = 0
        self.pMissingPageAudioPlayed = 0
        self.pBackPageAudioPlayed = 0
        self.pSavedList = [Sym('pCurrentPage'), Sym('pMissingPageAudioPlayed'), Sym('pBackPageAudioPlayed'),
                           Sym('pVisited')]
        M.addObjectGlob(self)
        return self

    def mInitPoolObjects(self):
        self.pLeftPageSound = M.getSoundObject(1, self.pLeftPageSound, self)
        self.pRightPageSound = M.getSoundObject(1, self.pRightPageSound, self)
        self.pMissingPageAudio = M.getExSoundObject(1, 0, self)
        for daPage in self.pRightPageObjectList:
            daPage.mInitPoolObjects()
        for daPage in self.pLeftPageObjectList:
            daPage.mInitPoolObjects()
        self.pBackDetectButton = M.getSimpleButt(self.pBackDetectSprite, 1, self, 36)

    def mReleasePoolObjects(self):
        self.pLeftPageSound = M.recycleSoundObject(self.pLeftPageSound)
        self.pRightPageSound = M.recycleSoundObject(self.pRightPageSound)
        self.pMissingPageAudio = M.recycleSoundObject(self.pMissingPageAudio)
        for daPage in self.pRightPageObjectList:
            daPage.mReleasePoolObjects()
        for daPage in self.pLeftPageObjectList:
            daPage.mReleasePoolObjects()
        M.recycleSimpleButt(self.pBackDetectButton)

    def mDestroy(self): pass
    def mLoad(self): pass

    def mReadyToPlayBook(self):
        sd = _sd()
        daList = []
        daList.append(1 if sd.mGetLevel() < 2 else 0)
        daList.append(1 if sd.mTokenFoundCount() == len(self.pRightPageObjectList) else 0)
        daList.append(0 if self.pAllFoundBink.pPlayed else 1)
        return min(daList)

    # ---- load / unload -------------------------------------------------------------------------
    def mLoadList(self, theList):
        sd = _sd()
        if self.mReadyToPlayBook():
            self.pAllFoundBink.mLoadList(theList)
            self.pCurrentPage = 1
            self.pRightPageObjectList[len(self.pRightPageObjectList) - 1].mLoadList(theList)
            self.pLeftPageObjectList[len(self.pLeftPageObjectList) - 2].mLoadList(theList)
        theList.append(self.pAmbientAudio)
        theList.append(self.pBackMember)
        theList.append(self.pRightPageSound)
        theList.append(self.pLeftPageSound)
        theList.append(self.pRightPageMouseDetect)
        theList.append(self.pLeftPageMouseDetect)
        if sd.mGetLevel() < 2:
            daCount = min(sd.mTokenFoundCount(), len(self.pRightPageObjectList))
        else:
            daCount = len(self.pRightPageObjectList)
        for i in range(1, daCount + 1):
            self.pRightPageObjectList[i - 1].mLoadList(theList)

    def mUnLoad(self):
        unload_mem(self.pAmbientAudio)
        unload_mem(self.pBackMember)
        _unload(self.pAllFoundBink)
        unload_mem(self.pRightPageMouseDetect)
        unload_mem(self.pLeftPageMouseDetect)
        unload_mem(self.pRightPageSound)
        unload_mem(self.pLeftPageSound)
        for daPage in self.pLeftPageObjectList:
            _unload(daPage)
        for daPage in self.pRightPageObjectList:
            _unload(daPage)
    mUnload = mUnLoad

    def mGetEnabled(self): return self.pEnabled

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    def mHuntObjectFound(self, theObject): pass

    # ---- show / hide ---------------------------------------------------------------------------
    def mShow(self):
        sd = _sd()
        theResetCursorFlag = 0
        self.pVisited = 1
        M.FadeInAmbientSound(self.pAmbientAudio)
        self.pHelpButton = M.getGameHelpButton()
        self.pBackButton = M.getGameBackButton()
        self.pHelpButton.mSetParent(self)
        self.pBackButton.mSetParent(self)
        self.pHelpButton.mShow()
        self.pBackButton.mShow()
        self.pBackDetectButton.mShow()
        S(self.pRightPageMouseDetectSprite).member = self.pRightPageMouseDetect
        S(self.pLeftPageMouseDetectSprite).member = self.pLeftPageMouseDetect
        S(self.pRightPageMouseDetectSprite).ink = 36
        S(self.pLeftPageMouseDetectSprite).ink = 36
        S(self.pMissingPageSprite).ink = 36
        S(self.pBackSprite).member = self.pBackMember
        daMissingPageFlag = self.mShowBook()
        if self.mReadyToPlayBook():
            self.mDisable()
            self.pAllFoundBink.mPlay()
            return
        self.mSetMissingPageAudio()
        if not self.pAllFoundBink.pPlayed:
            if _stringp(self.pMissingPageAudio.pSound):
                M.waitCursor()
                self.mDisable()
                self.pMissingPageAudio.mPlay()
            else:
                theResetCursorFlag = 1
        else:
            theResetCursorFlag = 1
        self.pEnabled = 1
        if not sd.mEnableReminders() and theResetCursorFlag:
            M.resetCursor()

    def mShowBook(self):
        sd = _sd()
        daMissingPageDisplay = 0
        if sd.mGetLevel() < 2:
            daCount = min(sd.mTokenFoundCount(), len(self.pRightPageObjectList))
        else:
            daCount = len(self.pRightPageObjectList)
        daMissingPages = len(self.pRightPageObjectList) - daCount
        if daCount:
            S(self.pBackDetectButton.pSprite).member = 1
            if _alive(self.pCurrentRightPageObj):
                self.pCurrentRightPageObj.mHide()
                self.pCurrentRightPageObj = 0
            if _alive(self.pCurrentLeftPageObj):
                self.pCurrentLeftPageObj.mHide()
                self.pCurrentLeftPageObj = 0
            if daCount >= self.pCurrentPage:
                self.pCurrentRightPageObj = self.pRightPageObjectList[self.pCurrentPage - 1]
                self.pCurrentRightPageObj.mShow()
                if self.pCurrentPage == len(self.pRightPageObjectList):
                    self.pCurrentRightPageObj.mouseLeave()
                    S(self.pRightPageMouseDetectSprite).loc = Point(-600, -600)
                else:
                    S(self.pRightPageMouseDetectSprite).loc = Point(320, 240)
                if daCount > self.pCurrentPage:
                    for i in range(self.pCurrentPage + 1, daCount + 1):
                        self.pRightPageObjectList[i - 1].mShowEdge()
            else:
                S(self.pBackDetectButton.pSprite).member = self.pRightBackDetectMember
                S(self.pMissingPageSprite).member = self.pMissingPagesMemberList[self.pCurrentPage - 1]
                daMissingPageDisplay = 1
            daLeftPageIndex = self.pCurrentPage - 1
            if daLeftPageIndex:
                self.pCurrentLeftPageObj = self.pLeftPageObjectList[daLeftPageIndex - 1]
                self.pCurrentLeftPageObj.mShow()
        else:
            S(self.pBackDetectButton.pSprite).member = self.pFullBackDetectMember
            S(self.pMissingPageSprite).member = self.pMissingPagesMemberList[0]
            daMissingPageDisplay = 1
        return daMissingPageDisplay

    def mHide(self):
        blank(self.pLeftPageMouseDetectSprite)
        blank(self.pRightPageMouseDetectSprite)
        blank(self.pBackSprite)
        blank(self.pMissingPageSprite)
        for daPage in self.pRightPageObjectList:
            daPage.mHideEdge()
        if _alive(self.pCurrentRightPageObj):
            self.pCurrentRightPageObj.mHide()
            self.pCurrentRightPageObj = 0
        if _alive(self.pCurrentLeftPageObj):
            self.pCurrentLeftPageObj.mHide()
            self.pCurrentRightPageObj = 0                # (sic, see module note)
        self.pBackDetectButton.mHide()
        _call_if(self.pHelpButton, 'mHide')
        _call_if(self.pBackButton, 'mHide')
        self.pEnabled = 0

    def mSetMissingPageAudio(self):
        sd = _sd()
        if (sd.mGetLevel() < 2) and not self.pAllFoundBink.pPlayed:
            daSound = 0
            daCount = sd.mTokenFoundCount()
            if daCount == 0:
                if sd.mYoungersterCantFindKeys():
                    self.pMissingPageAudioPlayed = 1
                    daSound = self.pMissingPageAudioList[5]
                else:
                    if not self.pMissingPageAudioPlayed:
                        self.pMissingPageAudioPlayed = 1
                        daSound = self.pMissingPageAudioList[0]
            else:
                if not self.pMissingPageAudioPlayed:
                    if daCount == 1:
                        self.pMissingPageAudioPlayed = 1
                        daSound = self.pMissingPageAudioList[1]
                    else:
                        if daCount > 1:
                            self.pMissingPageAudioPlayed = 1
                            daSound = self.pMissingPageAudioList[2]
                else:
                    if (daCount > 0) and (self.pCurrentPage > daCount) and not self.pBackPageAudioPlayed:
                        self.pBackPageAudioPlayed = 1
                        if sd.mRemainingTokenCount() > 1:
                            daSound = self.pMissingPageAudioList[3]
                        else:
                            daSound = self.pMissingPageAudioList[4]
            self.pMissingPageAudio.pSound = daSound
        else:
            self.pMissingPageAudio.pSound = 0

    def mGetName(self): return self.pName
    def mGetType(self): return Sym('SCREEN_BOOK')

    # ---- enable / disable ----------------------------------------------------------------------
    def mEnable(self):
        self.pEnabled = 1
        _call_if(self.pBackButton, 'mEnable')
        _call_if(self.pHelpButton, 'mEnable')
        if _alive(self.pCurrentLeftPageObj):
            self.pCurrentLeftPageObj.mEnable()
        if _alive(self.pCurrentRightPageObj):
            self.pCurrentRightPageObj.mEnable()

    def mDisable(self):
        self.pEnabled = 0
        _call_if(self.pBackButton, 'mDisable')
        _call_if(self.pHelpButton, 'mDisable')
        if _alive(self.pCurrentLeftPageObj):
            self.pCurrentLeftPageObj.mDisable()
        if _alive(self.pCurrentRightPageObj):
            self.pCurrentRightPageObj.mDisable()

    # ---- buttons -------------------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        sd = _sd()
        if theObject is self.pHelpButton:
            M.gGameDaddy.pCurrentGame.pHelpPlayer.mStartHelp()
        else:
            if theObject is self.pBackButton:
                if self.pAllFoundBink.pPlayed and (sd.mGetLevel() < 2):
                    sd.mNextLevel()
                    sd.mInitScavengerHuntPoolObjects()
                M.navigateBack()
            else:
                if _typ(theObject) == 'BOOK_PAGE':
                    if _get_pos(self.pLeftPageObjectList, theObject):
                        self.pCurrentPage = self.pCurrentPage - 1
                        self.pCurrentPageSound = self.pLeftPageSound
                    else:
                        if _get_pos(self.pRightPageObjectList, theObject):
                            self.pCurrentPage = self.pCurrentPage + 1
                            self.pCurrentPageSound = self.pRightPageSound
                    self.pCurrentPageSound.mPlay()
                    self.mShowBook()
                    self.mDisable()
                else:
                    if self.pBackDetectButton is theObject:
                        pass

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
        elif daType == 'LOADER':
            self.mSoundDone(theObject)

    def mHandleAnimDone(self, theObject): pass

    def mHandleBinkDone(self, theObject):
        if theObject is self.pAllFoundBink:
            self.pCurrentPage = len(self.pRightPageObjectList)
            call_all(self.pRightPageObjectList, 'mHideEdge')
            _sd().mClearReminderAudio()
            self.mShowBook()
            self.mEnable()
            M.resetCursor()

    def mHandlePlayQueue(self, theObject):
        self.mEnable()

    def mSoundDone(self, theObject):
        if theObject is self.pLoaderObject:
            self.pCurrentPageSound.mPlay()
            self.mShowBook()
        else:
            if theObject is self.pCurrentPageSound:
                if _alive(self.pCurrentRightPageObj):
                    self.pCurrentRightPageObj.mWillRollover()
                if _alive(self.pCurrentLeftPageObj):
                    self.pCurrentLeftPageObj.mWillRollover()
                self.pCurrentPageSound = 0
                self.mSetMissingPageAudio()
                if _stringp(self.pMissingPageAudio.pSound):
                    M.waitCursor()
                    self.pMissingPageAudio.mPlay()
                else:
                    if _alive(self.pCurrentRightPageObj):
                        self.pCurrentRightPageObj.mPlayPageAudio()
                        self.mEnable()
                    else:
                        self.mEnable()
            else:
                if theObject is self.pMissingPageAudio:
                    self.pMissingPageAudio.pSound = 0
                    M.resetCursor()
                    self.mEnable()

    def mUpdate(self): pass
    def mSetParent(self, theObject): self.pParent = theObject

    # ---- help ----------------------------------------------------------------------------------
    def mGetHelpState(self):
        sd = _sd()
        count = len(self.pRightPageObjectList)
        found = sd.mTokenFoundCount()
        page = self.pCurrentPage
        if sd.mGetLevel() == 1:
            if found == 0:
                if sd.mAllRiddlesSolved() == 1:
                    return Sym('ALL_GETPAGES')
                else:
                    return Sym('BOOK_EMPTY')
            else:
                if found < count:
                    if (found > 0) and (page == 1):
                        return Sym('BOOK_FIRST')
                    else:
                        if (found > 0) and (page > found):
                            return Sym('BOOK_LAST')
                        else:
                            if (found > 0) and (page <= found) and (page != 1):
                                return Sym('BOOK_MID')
                            else:
                                return Sym('ALL_READBOOK')
                else:
                    if page == 1:
                        return Sym('BOOKDONE_FIRST')
                    else:
                        if page == count:
                            return Sym('BOOKDONE_LAST')
                        else:
                            if (page != count) and (page != 1):
                                return Sym('BOOKDONE_MID')
                            else:
                                if found == count:
                                    return Sym('BOOK_SCAV')
        else:
            if (page == 1) and (found == 0):
                return Sym('BOOKDONE_FIRST')
            else:
                if (page == count) and (found == 0):
                    return Sym('BOOKDONE_LAST')
                else:
                    if (page != count) and (page != 1) and (found == 0):
                        return Sym('BOOKDONE_MID')
                    else:
                        if found > 0:
                            return Sym('BOOK_SCAV')
        return 0
