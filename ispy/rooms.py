"""Hand-ported parent scripts, part 5: the room helpers (and, below them, the room screens).

    ParentScript 102  ANIM_WIGGLE            wiggle animation: cycles a member list while its sound plays
    ParentScript 113  VisibleTimer           mm:ss clock drawn with four digit sprites
    ParentScript 115  WIN_COUNTER            the 0..3 win counter of Creepy Crawlies
    ParentScript 117  SKELLY_TALK_ANIM       Skelly talking: random cycle of 4 mouth animations over one voice-over
    ParentScript  82  BUTT_ROLL_DOWN_MULTI   roll-over / down button that releases its twins when pressed
    ParentScript  83  IW_BOTTLES             the Inventor's Workshop bottle shelf (7 sliding bottles)
    ParentScript  84  BOOK_BUTTON            the three book anims + the navigation button of the Study

Same conventions as ui.py / screens2.py / riddles.py: one class per Lingo parent script, method and
property names unchanged, `S(chan)` is `sprite(chan)`, `R()` is the runtime, `_done(parent, obj)` is
`mPlayDone(parent, obj)`.  Lingo lists are 1-based: every `list[i]` below is written `list[i - 1]`.
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, Point, Rect, set_properties, pop_one, pop_list, randomize_list, get_def
from .ui import (load_mem, unload_mem, is_enabled, set_behavior, remove_behavior, blank, _done)
from .screens2 import (R, S, _new, _alive, _nz, _integer, _get_pos, _symeq, _T)
from .riddles import call_all, move_sprite


# ============================================================================================
# small helpers
# ============================================================================================

def _pop_random(lst):
    """PopRandomFromList(list): remove and return a random item."""
    import random
    return lst.pop(random.randrange(len(lst)))


def _add_behavior(chan, obj):
    """add(sprite(chan).scriptInstanceList, me)"""
    s = S(chan)
    s.behaviors = list(s.behaviors) + [obj]


# ============================================================================================
# ANIM_WIGGLE  (ParentScript 102)
# ============================================================================================

@lingo_script('ANIM_WIGGLE')
class AnimWiggle(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pAnimSound = 0
        self.pLastUpdate = 0
        self.pSpeed = 100
        self.pStep = 0
        self.pAnimMembers = []
        self.pInk = 0
        self.pSprite = 0
        self.pPlayed = 0
        self.pParent = None
        self.pSavedList = []
        self.pSoundChannel = 0
        self.pBackSprite = 0
        self.pBackMember = 0
        self.pEventTag = None
        self.pLoc = Point(320, 240)

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pPlayed = 0
        self.pLastUpdate = 0
        self.pSpeed = _integer(1000 / self.pSpeed)
        self.pStep = 0
        self.pPlayed = 0
        self.pLoc = Point(320, 240)
        self.pSavedList = [Sym('pPlayed')]
        # `if stringp(pAnimSound) then pAnimSound = getPath(the moviePath, ["AIFF"], pAnimSound)`:
        # SoundSystem.play_file() looks the file name up in the AIFF folders itself, so the name stays as is
        M.addObjectGlob(self)

    def mDestroy(self):
        pass

    def mLoad(self):
        load_mem(self.pAnimMembers)
        if isinstance(self.pAnimSound, int):
            load_mem(self.pAnimSound)
        load_mem(self.pBackMember)

    def mLoadList(self, theList):
        theList.extend(self.pAnimMembers)
        if isinstance(self.pAnimSound, int):
            theList.append(self.pAnimSound)
        theList.append(self.pBackMember)

    def mUnload(self):
        # unloadMem(...) of members: nothing to do in the port
        pass

    def mGetName(self):
        return self.pName

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('ANIM_WIGGLE')

    def mShow(self):
        pass

    def mHide(self):
        blank(self.pSprite)

    def mPlay(self):
        self.pPlayed += 1
        if isinstance(self.pAnimSound, int):
            R().sound.puppet(self.pSoundChannel, self.pAnimSound)
        else:
            R().sound.play_file(self.pSoundChannel, self.pAnimSound)       # sound playFile
        S(self.pSprite).ink = self.pInk
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pAnimMembers[0]
        self.pLastUpdate = R().milliseconds() - self.pSpeed
        M.addUpdateList(self)

    def mStop(self):
        R().sound.stop(self.pSoundChannel)
        M.removeUpdateList(self)
        self.pLastUpdate = 0
        self.pStep = 0
        if self.pBackMember:
            blank(self.pBackSprite)
        _done(self.pParent, self)

    def mUpdate(self):
        if R().sound.busy(self.pSoundChannel):
            now = R().milliseconds()
            if (now - self.pLastUpdate) >= self.pSpeed:
                self.pLastUpdate = now
                daIndex = (self.pStep % len(self.pAnimMembers)) + 1
                S(self.pSprite).member = self.pAnimMembers[daIndex - 1]
                if daIndex != 1:
                    if self.pBackMember:
                        S(self.pBackSprite).ink = self.pInk
                        S(self.pBackSprite).member = self.pBackMember
                else:
                    if self.pBackSprite:       # Lingo would touch sprite(0) here when there is no back sprite
                        S(self.pBackSprite).member = 1
                self.pStep += 1
        else:
            self.mStop()

    def mDisable(self):
        if is_enabled(self.pSprite, self):
            remove_behavior(self.pSprite)

    def mEnable(self):
        if not is_enabled(self.pSprite, self):
            set_behavior(self.pSprite, self)

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


# ============================================================================================
# VisibleTimer  (ParentScript 113)
# ============================================================================================

@lingo_script('VisibleTimer')
class VisibleTimer(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pBGSprite = 0
        self.pBGMember = 0
        self.pNumberList = []
        self.pNumberSpriteList = []
        self.pNumberLocs = []
        self.pStartTime = 0
        self.pCurrentTime = 0
        self.pOldTime = 0
        self.pParent = None
        self.pFlashMode = 0
        self.pNextFlash = 0
        self.pFlashSpeed = 0
        self.pEventTag = None
        self.pEnable = 0
        self.pRunMode = 0
        self.pSavedList = []

    def mInit(self, theObjectData, theSpriteAlloc):
        self.pStartTime = 0
        self.pCurrentTime = 0
        self.pNextFlash = 0
        self.pFlashMode = 0
        self.pOldTime = 0
        self.pEnable = 0
        self.pRunMode = 0
        set_properties(theObjectData, self)
        self.pBGSprite = pop_one(theSpriteAlloc)
        self.pNumberSpriteList = pop_list(theSpriteAlloc, 4)
        self.pSavedList = [Sym(n) for n in ('pCurrentTime', 'pStartTime', 'pOldTime', 'pRunMode', 'pEnable')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mGetType(self):
        return Sym('VisibleTimer')

    def mLoad(self):
        load_mem(self.pBGMember)
        load_mem(self.pNumberList)

    def mLoadList(self, theList):
        theList.append(self.pBGMember)
        theList.extend(self.pNumberList)

    def mUnload(self):
        pass

    def mDisable(self):
        if not self.pEnable:
            return
        if self.pRunMode:
            M.removeUpdateList(self)
            if self.pCurrentTime != 0:
                self.pOldTime = self.pCurrentTime
        self.pEnable = 0

    def mEnable(self):
        if self.pEnable:
            return
        if self.pRunMode:
            self.mPlay()
        self.pEnable = 1

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName

    def mPlay(self):
        self.pStartTime = R().milliseconds() // 1000
        if self.pOldTime != 0:
            self.pStartTime = self.pStartTime - self.pOldTime
        self.pRunMode = 1
        M.addUpdateList(self)
        self.pEnable = 1

    def mStop(self):
        self.pRunMode = 0
        M.removeUpdateList(self)

    def mKill(self):
        self.pRunMode = 0
        M.removeUpdateList(self)

    def mUpdate(self):
        if self.pFlashMode:
            if R().milliseconds() >= self.pNextFlash:
                if S(self.pNumberSpriteList[0]).member == M.gBlank:
                    self.mDraw()
                else:
                    self.mBlankClock()
                self.pNextFlash = R().milliseconds() + self.pFlashSpeed
        else:
            self.pCurrentTime = (R().milliseconds() // 1000) - self.pStartTime
            self.mDraw()

    def mBlankClock(self):
        for i in range(4):
            S(self.pNumberSpriteList[i]).member = M.gBlank

    def mFlashOn(self):
        self.pFlashMode = 1

    def mFlashOff(self):
        self.mDraw()
        self.pFlashMode = 0
        self.mStop()

    def mReset(self):
        self.pCurrentTime = 0
        self.pOldTime = 0
        self.mSetTime(self.pCurrentTime)

    def mShow(self):
        S(self.pBGSprite).ink = 36
        S(self.pBGSprite).member = self.pBGMember
        for i in range(len(self.pNumberSpriteList)):
            daSprite = self.pNumberSpriteList[i]
            S(daSprite).loc = self.pNumberLocs[i]
            S(daSprite).ink = 36
        self.mDraw()
        if self.pCurrentTime != 0:
            self.pOldTime = self.pCurrentTime

    def mHide(self):
        blank(self.pBGSprite)
        for daSprite in self.pNumberSpriteList:
            blank(daSprite)

    def mGetTime(self):
        return self.pCurrentTime

    def mSetTime(self, theSeconds):
        self.pCurrentTime = theSeconds
        self.pStartTime = (R().milliseconds() // 1000) - self.pCurrentTime

    def mDraw(self):
        t = int(self.pCurrentTime)
        daSeconds = t % 60
        daMinutes = (t % 3600) // 60
        daTenMinuteIndex = (daMinutes // 10) + 1
        daOneMinuteIndex = (daMinutes % 10) + 1
        daTenSecondIndex = (daSeconds // 10) + 1
        daOneSecondIndex = (daSeconds % 10) + 1
        n = self.pNumberList
        S(self.pNumberSpriteList[0]).member = n[daTenMinuteIndex - 1]
        S(self.pNumberSpriteList[1]).member = n[daOneMinuteIndex - 1]
        S(self.pNumberSpriteList[2]).member = n[daTenSecondIndex - 1]
        S(self.pNumberSpriteList[3]).member = n[daOneSecondIndex - 1]

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


# ============================================================================================
# WIN_COUNTER  (ParentScript 115)
# ============================================================================================

@lingo_script('WIN_COUNTER')
class WinCounter(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pBGSprite = 0
        self.pBGMember = 0
        self.pNumberList = []
        self.pNumberSpriteList = []
        self.pNumberLocs = []
        self.pEventTag = None
        self.pCounter = 0
        self.pParent = None
        self.pWinSound = 0
        self.pSavedList = []

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBGSprite = pop_one(theSpriteAlloc)
        self.pNumberSpriteList = pop_list(theSpriteAlloc, 3)
        self.pSavedList = [Sym('pCounter')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mGetType(self):
        return Sym('WinCounter')

    def mLoad(self):
        pass

    def mLoadList(self, theList):
        theList.append(self.pBGMember)
        theList.extend(self.pNumberList)
        theList.append(self.pWinSound)

    def mUnload(self):
        pass

    def mDisable(self):
        pass

    def mEnable(self):
        pass

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName

    def mBlankCounter(self):
        for i in range(3):
            S(self.pNumberSpriteList[i]).member = M.gBlank

    def mReset(self):
        self.pCounter = 0

    def mShow(self):
        S(self.pBGSprite).ink = 36
        S(self.pBGSprite).member = self.pBGMember
        for i in range(len(self.pNumberSpriteList)):
            daSprite = self.pNumberSpriteList[i]
            S(daSprite).loc = self.pNumberLocs[i]
            S(daSprite).ink = 36
        self.mDraw()

    def mHide(self):
        blank(self.pBGSprite)
        for daSprite in self.pNumberSpriteList:
            blank(daSprite)

    def mIncrementCount(self):
        self.pCounter += 1
        self.mDraw()
        if self.pCounter <= 3:
            R().sound.puppet(1, self.pWinSound)
            R().update_stage()
            R().wait_sound(1)             # repeat while soundBusy(1) / end repeat
            R().wait_ticks(10)

    def mGetWinCount(self):
        return self.pCounter

    def mSetCounter(self, theCount):
        self.pCounter = theCount

    def mDraw(self):
        sp, nl = self.pNumberSpriteList, self.pNumberList
        if not self.pCounter:
            self.mBlankCounter()
        else:
            if self.pCounter == 1:
                S(sp[0]).member = nl[0]
                S(sp[1]).member = M.gBlank
                S(sp[2]).member = M.gBlank
            else:
                if self.pCounter == 2:
                    S(sp[0]).member = nl[0]
                    S(sp[1]).member = nl[1]
                    S(sp[2]).member = M.gBlank
                else:
                    if self.pCounter >= 3:
                        S(sp[0]).member = nl[0]
                        S(sp[1]).member = nl[1]
                        S(sp[2]).member = nl[2]

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


# ============================================================================================
# SKELLY_TALK_ANIM  (ParentScript 117)
# ============================================================================================

@lingo_script('SKELLY_TALK_ANIM')
class SkellyTalkAnim(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pParent = None
        self.pSkellyVO = 0
        self.pSkellyAnimList = []
        self.pSkellyCycleList = []
        self.pAnimPos = 1
        self.pAnimSprite = 0
        self.pSoundFile = ''
        self.pEventTag = None

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pAnimSprite = pop_one(theSpriteAlloc)
        self.pSkellyAnimList = get_object_list(self.pSkellyAnimList, [self.pAnimSprite], 1)
        call_all(self.pSkellyAnimList, 'mSetParent', self)
        self.pSkellyVO = 0
        self.pAnimPos = 1
        self.pSoundFile = ''

    def mInitPoolObjects(self):
        self.pSkellyVO = M.getExSoundObject(2, self.pSoundFile, self)

    def mReleasePoolObjects(self):
        self.pSkellyVO = M.recycleSoundObject(self.pSkellyVO)

    def mDisable(self):
        pass

    def mEnable(self):
        pass

    def mDestroy(self):
        pass

    def mShow(self):
        self.pSkellyCycleList = self.mMakeSkellyRandList()
        self.pAnimPos = 1

    def mSetSkellyVO(self, theVO):
        self.pSoundFile = theVO
        self.pSkellyVO.mSetSoundFile(self.pSoundFile)

    def _cur(self):
        return self.pSkellyAnimList[self.pSkellyCycleList[self.pAnimPos - 1] - 1]

    def mPlay(self):
        self.mShow()
        self.pSkellyVO.mPlay()
        self._cur().mPlay()

    def mHide(self):
        pass

    def mLoad(self):
        call_all(self.pSkellyAnimList, 'mLoad')

    def mLoadList(self, theList, theForceFlag=None):
        call_all(self.pSkellyAnimList, 'mLoadList', theList)

    def mUnload(self, theForceFlag=None):
        call_all(self.pSkellyAnimList, 'mUnload')

    def mPlayDone(self, theObject):
        if theObject is self.pSkellyVO:
            self._cur().mStop()
            self._cur().mHide()
            self.pSkellyCycleList = self.mMakeSkellyRandList()
            _done(self.pParent, self)
        else:
            self.pAnimPos += 1
            if self.pAnimPos > len(self.pSkellyCycleList):
                self.pAnimPos = 1
            self._cur().mPlay()

    def mStop(self):
        call_all(self.pSkellyAnimList, 'mStop')
        self.pSkellyVO.mStop()

    def mGetName(self):
        return self.pName

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('SKELLY_TALK_ANIM')

    def mMakeSkellyRandList(self):
        """12 mouth-animation picks: three cycles of 1..4, no animation repeated across a cycle boundary."""
        seedList = [1, 2, 3, 4]
        cycle = [[], [], []]
        cycle[0] = randomize_list(seedList)
        seedList2 = list(seedList)
        lastone = cycle[0][3]
        seedList2.remove(lastone)
        nextfirstone = _pop_random(seedList2)
        cycle[1].append(nextfirstone)
        seedList2.append(cycle[0][3])
        cycle[1].extend(randomize_list(seedList2))
        seedList2 = list(seedList)
        lastone = cycle[1][3]
        seedList2.remove(lastone)
        nextfirstone = _pop_random(seedList2)
        cycle[2].append(nextfirstone)
        seedList2.append(cycle[1][3])
        cycle[2].extend(randomize_list(seedList2))
        cycle[0].extend(cycle[1])
        cycle[0].extend(cycle[2])
        return cycle[0]

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


# ============================================================================================
# BUTT_ROLL_DOWN_MULTI  (ParentScript 82)
# ============================================================================================

@lingo_script('BUTT_ROLL_DOWN_MULTI')
class ButtRollDownMulti(LObject):
    def __init__(self):
        self.pType = None
        self.pSavedList = []
        self.pNeutMember = 0
        self.pDisMember = 0
        self.pRollMember = 0
        self.pDownMember = 0
        self.pUpSound = 0
        self.pDownSound = 0
        self.pRollSound = 0
        self.pInSound = 0
        self.pTwinList = []
        self.pEnabled = None
        self.pActive = 0
        self.pInk = 0
        self.pLoc = None
        self.pSprite = 0
        self.pName = None
        self.pParent = 0
        self.pSkipRolloverSoundFlag = 0
        self.pWaitForSound = 0
        self.pWaitCounter = 0
        self.pLastSoundPlayed = 0
        self.pDownFlag = 0
        self.pDetectMember = 0
        self.pDetectSprite = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pLoc = get_def(self.pLoc, M.getRegPoint())
        self.pSkipRolloverSoundFlag = 0
        self.pDownFlag = 0
        self.pActive = 0
        self.pTwinList = []
        self.pSavedList = [Sym('pDownFlag'), Sym('pActive')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mShow(self):
        S(self.pSprite).ink = self.pInk
        S(self.pSprite).loc = self.pLoc
        if self.pActive:
            if self.pDownFlag:
                S(self.pSprite).member = self.pDownMember
            else:
                S(self.pSprite).member = self.pNeutMember
                set_behavior(self.pSprite, self)
        else:
            S(self.pSprite).member = self.pDisMember
            set_behavior(self.pSprite, self)

    def mHide(self):
        self.pLastSoundPlayed = 0
        blank(self.pSprite)
        S(self.pSprite).behaviors = []

    def mLoad(self):
        for m in (self.pDetectMember, self.pNeutMember, self.pDisMember, self.pRollMember, self.pDownMember,
                  self.pUpSound, self.pDownSound, self.pRollSound):
            load_mem(m)

    def mLoadList(self, theList):
        for m in (self.pDetectMember, self.pNeutMember, self.pDisMember, self.pRollMember, self.pDownMember,
                  self.pUpSound, self.pDownSound, self.pRollSound):
            theList.append(m)

    def mUnload(self):
        pass

    def mSetBehavior(self):
        set_behavior(self.pSprite, self)

    def mRemoveBehavior(self):
        S(self.pSprite).behaviors = []
        self.pEnabled = 1

    def mSetTwins(self, twinObjList):
        for o in twinObjList:
            if o is not self:
                self.pTwinList.append(o)

    def mouseDown(self):
        if not self.pEnabled:
            return
        if self.pActive and not self.pDownFlag:
            S(self.pSprite).member = self.pDownMember
            R().sound.puppet(1, self.pDownSound)
            self.pDownFlag = 1
            call_all(self.pTwinList, 'mReleaseButt')
            self.mRemoveBehavior()
            self.pParent.mButtonActivated(self)
            R().update_stage()
            R().flush_input()
        else:
            if not self.pActive:
                self.pParent.mButtonActivated(self)

    def mSetStateDown(self):
        S(self.pSprite).member = self.pDownMember
        self.pDownFlag = 1
        call_all(self.pTwinList, 'mReleaseButt')
        self.mRemoveBehavior()

    def mReleaseButt(self):
        if self.pDownFlag:
            S(self.pSprite).member = self.pNeutMember
            self.pDownFlag = 0
            _add_behavior(self.pSprite, self)

    def mouseUp(self):
        pass

    def mouseUpOutSide(self):
        pass

    def mouseEnter(self):
        if not self.pEnabled or not self.pActive:
            return
        if not self.pDownFlag:
            R().sound.puppet(1, self.pRollSound)
            S(self.pSprite).member = self.pRollMember

    def mouseLeave(self):
        if not self.pEnabled or not self.pActive:
            return
        if not self.pDownFlag:
            S(self.pSprite).member = self.pNeutMember

    def mEnable(self):
        set_behavior(self.pSprite, self)
        self.pEnabled = 1

    def mDisable(self):
        self.mRemoveBehavior()
        self.pEnabled = 0

    def mActivate(self):
        S(self.pSprite).member = self.pNeutMember
        self.pActive = 1

    def mDeactivate(self):
        S(self.pSprite).member = self.pDisMember
        self.pActive = 0
        self.pDownFlag = 0

    def mMove(self, theOffset):
        move_sprite(self.pSprite, theOffset)
        if self.pDetectSprite:
            move_sprite(self.pDetectSprite, theOffset)

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetParent(self):
        return self.pParent

    def mGetType(self):
        return Sym('BUTT_ROLL_DOWN_MULTI')

    def mGetName(self):
        return self.pName


# ============================================================================================
# IW_BOTTLES  (ParentScript 83)
#   pGhostNBottleHashTable[ghost] = [ghostNameMember, [7 bottle members], [7 token names]]
# ============================================================================================

@lingo_script('IW_BOTTLES')
class IWBottles(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pInk = 0
        self.pDownLoc = None
        self.pUpLoc = None
        self.pBottleSpriteList = []
        self.pNeutBottleMemberList = []
        self.pGhostNBottleHashTable = []
        self.pGhostNameSoundList = []
        self.pSlideObjectList = []
        self.pAnimSlideScriptNumber = 0
        self.pDownSound = 0
        self.pUpSound = 0
        self.pDT = 1000
        self.pParent = None
        self.pSavedList = []
        self.pNewButton = 0
        self.pEventTag = None
        self.pEnabled = 1
        self.pLastUpdate = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        self.pEnabled = 1
        self.pLastUpdate = 0
        self.pNewButton = 0
        self.pDT = 1000
        set_properties(theObjectData, self)
        # the data is a Lingo property list keyed by ghost name; the script only ever indexes it by position
        if isinstance(self.pGhostNBottleHashTable, dict):
            self.pGhostNBottleHashTable = list(self.pGhostNBottleHashTable.values())
        self.pBottleSpriteList = pop_list(theSpriteAlloc, 7)
        self.pSlideObjectList = []
        for i in range(7):
            daSprite = pop_one(theSpriteAlloc)
            self.pSlideObjectList.append(_new(self.pAnimSlideScriptNumber, self, daSprite))
            self.pSlideObjectList[i].mSetDistanceTimer(self.pDT)
        call_all(self.pSlideObjectList, 'mSetParent', self)
        self.pSavedList = [Sym('pNewButton')]
        M.addObjectGlob(self)
        return self

    def mInitPoolObjects(self):
        for i in range(7):
            self.pGhostNameSoundList[i] = M.getSoundObject(2, self.pGhostNameSoundList[i], self)

    def mReleasePoolObjects(self):
        for i in range(7):
            self.pGhostNameSoundList[i] = M.recycleSoundObject(self.pGhostNameSoundList[i])

    def mDestroy(self):
        pass

    def mGetType(self):
        return Sym('IW_BOTTLES')

    def mLoad(self):
        pass

    def mLoadList(self, theList):
        for i in range(7):
            theList.append(self.pNeutBottleMemberList[i])
            theList.append(self.pGhostNBottleHashTable[i][0])
            theList.extend(self.pGhostNBottleHashTable[i][1])
        theList.extend(self.pGhostNameSoundList)
        theList.append(self.pUpSound)
        theList.append(self.pDownSound)

    def mUnload(self):
        pass

    def _tbl(self, ghost):
        """pGhostNBottleHashTable[ghost]  (ghost is the 1-based button index)"""
        return self.pGhostNBottleHashTable[ghost - 1]

    def _bottle_member(self, ghost, i):
        """the member a bottle shows for a ghost: its 'ghost' bottle once the token is found, else the neutral one
        (i is 1-based)"""
        t = self._tbl(ghost)
        if M.gScreenDaddy.mTokenFound(t[2][i - 1]):
            return t[1][i - 1]
        return self.pNeutBottleMemberList[i - 1]

    def mShow(self):
        daButt = self.pParent.pGhostButtonState
        if daButt:
            self.pParent.mShowGhostName(self._tbl(daButt)[0])
            for i in range(1, 8):
                if self._tbl(daButt)[1][i - 1]:
                    S(self.pBottleSpriteList[i - 1]).member = self._bottle_member(daButt, i)
                    S(self.pBottleSpriteList[i - 1]).ink = self.pInk
                    S(self.pBottleSpriteList[i - 1]).loc = self.pDownLoc
                    continue
                S(self.pBottleSpriteList[i - 1]).member = M.getBlank()
        else:
            self.pParent.mHideGhostName()
            for i in range(7):
                S(self.pBottleSpriteList[i]).member = self.pNeutBottleMemberList[i]
                S(self.pBottleSpriteList[i]).ink = self.pInk
                S(self.pBottleSpriteList[i]).loc = self.pDownLoc

    def mSetBottlesNoSlide(self):
        daButt = self.pParent.pGhostButtonState
        if daButt:
            for i in range(1, 8):
                if self._tbl(daButt)[1][i - 1]:
                    S(self.pBottleSpriteList[i - 1]).member = self.pNeutBottleMemberList[i - 1]
                    S(self.pBottleSpriteList[i - 1]).ink = self.pInk
                    S(self.pBottleSpriteList[i - 1]).loc = self.pDownLoc
                    continue
                S(self.pBottleSpriteList[i - 1]).member = M.getBlank()
        else:
            self.pParent.mHideGhostName()
            for i in range(7):
                S(self.pBottleSpriteList[i]).member = self.pNeutBottleMemberList[i]
                S(self.pBottleSpriteList[i]).ink = self.pInk
                S(self.pBottleSpriteList[i]).loc = self.pDownLoc

    def mHide(self):
        self.pParent.mHideGhostName()
        self.mHideBottles()

    def mHideBottles(self):
        for i in range(7):
            S(self.pBottleSpriteList[i]).member = M.getBlank()

    def mSetBottles(self, daButt):
        self.mRaiseEmUp()
        self.mHideBottles()
        self.pNewButton = daButt

    def mRaiseEmUp(self):
        for i in range(7):
            o = self.pSlideObjectList[i]
            o.mSetMember(S(self.pBottleSpriteList[i]).member)
            o.mSetStartLoc(self.pDownLoc)
            o.mShow()
            o.mSetReturnLoc(self.pUpLoc)
            o.mSetEventTag(Sym('MOVEUP'))
            o.mPlay()
        R().sound.puppet(2, self.pUpSound)

    def mPlayDone(self, theObject):
        if _get_pos(self.pSlideObjectList, theObject):
            tag = theObject.pEventTag
            if _symeq(tag, 'MOVEUP'):
                self.mHandleMoveUpDone(theObject)
            elif _symeq(tag, 'NEUTBOTTLESDOWN'):
                self.mHandleNeutBottlesDownDone(theObject)
            elif _symeq(tag, 'NEWBOTTLESDOWN'):
                self.mHandleNewBottlesDownDone(theObject)
        else:
            if _symeq(theObject.pEventTag, 'PLAYNAME'):
                self.mHandleNameDone(theObject)

    def mHandleMoveUpDone(self, theObject):
        theObject.mHide()
        R().update_stage()
        if self.mTestForAllSlideUpsDone():
            self.pParent.mShowGhostName(self._tbl(self.pNewButton)[0])
            snd = self.pGhostNameSoundList[self.pNewButton - 1]
            snd.mSetEventTag(Sym('PLAYNAME'))
            snd.mLoad()               # `if not member(...).loaded then mLoad`
            snd.mPlay()

    def mHandleNameDone(self, theObject):
        if self.pNewButton:
            for i in range(1, 8):
                t = self._tbl(self.pNewButton)
                if t[1][i - 1]:
                    o = self.pSlideObjectList[i - 1]
                    o.mSetMember(self._bottle_member(self.pNewButton, i))
                    o.mSetStartLoc(self.pUpLoc)
                    o.mShow()
                    o.mSetReturnLoc(self.pDownLoc)
                    o.mSetEventTag(Sym('NEWBOTTLESDOWN'))
                    o.mPlay()
                    continue
                S(self.pBottleSpriteList[i - 1]).member = M.getBlank()
        else:
            self.pParent.mHideGhostName()
            for i in range(7):
                o = self.pSlideObjectList[i]
                o.mSetMember(self.pNeutBottleMemberList[i])
                o.mSetStartLoc(self.pUpLoc)
                o.mShow()
                o.mSetReturnLoc(self.pDownLoc)
                o.mSetEventTag(Sym('NEUTBOTTLESDOWN'))
                o.mPlay()
        R().sound.puppet(2, self.pDownSound)

    def mHandleNewBottlesDownDone(self, theObject):
        i = _get_pos(self.pSlideObjectList, theObject)
        if self._tbl(self.pNewButton)[1][i - 1]:
            S(self.pBottleSpriteList[i - 1]).member = self._bottle_member(self.pNewButton, i)
            S(self.pBottleSpriteList[i - 1]).ink = self.pInk
            S(self.pBottleSpriteList[i - 1]).loc = self.pDownLoc
        else:
            S(self.pBottleSpriteList[i - 1]).member = M.getBlank()
        theObject.mHide()
        R().update_stage()
        if self.mTestForAllSlidesDone():
            _done(self.pParent, self)

    def mHandleNeutBottlesDownDone(self, theObject):
        i = _get_pos(self.pSlideObjectList, theObject)
        S(self.pBottleSpriteList[i - 1]).member = self.pNeutBottleMemberList[i - 1]
        S(self.pBottleSpriteList[i - 1]).ink = self.pInk
        S(self.pBottleSpriteList[i - 1]).loc = self.pDownLoc
        theObject.mHide()
        R().update_stage()
        if self.mTestForAllSlidesDone():
            _done(self.pParent, self)

    def mTestForAllSlidesDone(self):
        for o in self.pSlideObjectList:
            # memberNum <> 1: an empty channel is member 1 in Director (blankSprite resets to 0 in the port)
            if S(o.pSprite).member not in (0, 1):
                return 0
        return 1

    def mTestForAllSlideUpsDone(self):
        for o in self.pSlideObjectList:
            if M.isUpdating(o):
                return 0
        return 1

    def mIsAllTokensFound(self):
        t = self._tbl(self.pNewButton)
        for i in range(7):
            if t[2][i] != 0:
                if not M.gScreenDaddy.mTokenFound(t[2][i]):
                    return 0
        return 1

    def mDisable(self):
        self.pEnabled = 0

    def mEnable(self):
        self.pEnabled = 1

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName

    def mPlay(self):
        pass

    def mStop(self):
        pass

    def mKill(self):
        pass

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


# ============================================================================================
# BOOK_BUTTON  (ParentScript 84)
# ============================================================================================

@lingo_script('BOOK_BUTTON')
class BookButton(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pSprite = 0
        self.pNavButton = 0
        self.pAnimList = []
        self.pOpenAnim = 0
        self.pEnabled = 1

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pAnimList = get_object_list(self.pAnimList, theSpriteAlloc)
        call_all(self.pAnimList, 'mSetParent', self)
        self.pNavButton = get_object(self.pNavButton, theSpriteAlloc)
        self.pNavButton.mSetParent(self)
        self.pOpenAnim = get_object(self.pOpenAnim, theSpriteAlloc)
        self.pOpenAnim.mSetParent(self)
        self.pEnabled = 1
        return self

    def mLoad(self):
        call_all(self.pAnimList, 'mLoad')
        self.pNavButton.mLoad()
        self.pOpenAnim.mLoad()

    def mLoadList(self, theList):
        call_all(self.pAnimList, 'mLoadList', theList)
        self.pNavButton.mLoadList(theList)
        self.pOpenAnim.mLoadList(theList)

    def mUnload(self):
        call_all(self.pAnimList, 'mUnload')
        self.pNavButton.mUnload()
        self.pOpenAnim.mUnload()

    def mGetEnabled(self):
        return self.pEnabled

    def mShow(self):
        sd = M.gScreenDaddy
        if sd.mGetLevel() == 2:
            daTokenFoundCount = sd.mTokenFoundCount()
            if daTokenFoundCount < len(self.pAnimList):
                daActiveBook = daTokenFoundCount + 1
                for i in range(1, daActiveBook + 1):
                    self.pAnimList[i - 1].mShow()
                    if i == daActiveBook:
                        self.pAnimList[i - 1].mEnable()
            else:
                self.pNavButton.mShow()

    def mHide(self):
        call_all(self.pAnimList, 'mHide')
        self.pNavButton.mHide()

    def mButtonActivated(self, theObject):
        daAnimIndex = _get_pos(self.pAnimList, theObject)
        if daAnimIndex:
            if daAnimIndex == len(self.pAnimList):
                M.waitCursor()
            M.gScreenDaddy.mDisable()
            theObject.mPlay()
        else:
            M.gScreenDaddy.mNavigate(theObject.pDestination)

    def mPlayDone(self, theObject):
        daAnimIndex = _get_pos(self.pAnimList, theObject)
        if daAnimIndex:
            M.gScreenDaddy.mAddToken(theObject.pName)
            if daAnimIndex < len(self.pAnimList):
                self.pAnimList[daAnimIndex].mShow()          # pAnimList[daAnimIndex + 1] (1-based)
                M.gScreenDaddy.mEnable()
            else:
                M.waitCursor()
                self.pOpenAnim.mPlay()
        else:
            if theObject is self.pOpenAnim:
                M.gScreenDaddy.mNavigate(self.pNavButton.pDestination)

    def mButtonDeActivated(self, theButton):
        pass

    def mEnable(self):
        sd = M.gScreenDaddy
        if sd.mGetLevel() == 2:
            daTokenFoundCount = sd.mTokenFoundCount()
            if daTokenFoundCount < len(self.pAnimList):
                self.pAnimList[daTokenFoundCount].mEnable()      # pAnimList[daTokenFoundCount + 1]
            else:
                self.pNavButton.mEnable()
        self.pEnabled = 1

    def mDisable(self):
        self.pEnabled = 0
        sd = M.gScreenDaddy
        if sd.mGetLevel() == 2:
            daTokenFoundCount = sd.mTokenFoundCount()
            if daTokenFoundCount < len(self.pAnimList):
                call_all(self.pAnimList, 'mDisable')
            else:
                self.pNavButton.mDisable()

    def mGetType(self):
        return Sym('BOOK_BUTTON')

    def mGetName(self):
        return self.pName


# ============================================================================================
# room screens (SCREEN_STUDY 48, SCREEN_KITCHEN 49, SCREEN_CREDIT 50, SCREEN_MM 51, SCREEN_CC 52,
# SCREEN_IWORKSHOP 53): room_screens.py (STUDY 48, CREDIT 50), room_screens2.py (KITCHEN 49, IWORKSHOP 53),
# room_screens3.py (MM 51, CC 52).

from . import room_screens, room_screens2, room_screens3  # noqa: E402,F401  (placed here so the helpers above exist first)
# ============================================================================================
