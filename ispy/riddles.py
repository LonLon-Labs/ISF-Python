"""Hand-ported parent scripts, part 4: the riddle objects.

    ParentScript 131  RIDDLE_LIN                 riddle object that animates a list of members, then rests on the last
    ParentScript 132  RIDDLE_SC                  same, but keeps the end frame (state change) and a click rect
    ParentScript 133  RIDDLE_MULTI               several RIDDLE_* objects that must all be found (then all wiggle)
    ParentScript 134  RIDDLEWORD_RECT            a word of the riddle strip: invisible rect, or the 'selected' bitmap
    ParentScript 135  RIDDLEWORD                 same, with just a click sound
    ParentScript 136  RIDDLE_DRAG                drag the piece onto its target rect
    ParentScript 137  RIDDLE_NAME                the player's name as one clickable sprite per letter
    ParentScript 138  RIDDLE_NOBUTT_LAMENAME     a letter sprite of RIDDLE_NAME (no behaviour)
    ParentScript 139  RIDDLESTRIP                the strip of riddle words + the ear button
    ParentScript 140  RIDDLE_WIG_SC              wiggle (loops while the wiggle sound plays), keeps the end frame
    ParentScript 141  RIDDLE_BUTT_NAME           a letter sprite of RIDDLE_NAME (clickable, jitters while playing)
    ParentScript 142  SHTokenObject              scavenger-hunt token wrapper (ancestor composition)
    ParentScript 143  RiddleTokenObject          riddle-object token wrapper (ancestor composition)
    ParentScript 144  RIDDLE_WIG                 wiggle (loops while the wiggle sound plays), back to the first frame
    ParentScript  75  BUTT_MM                    Mystery Mansion tile button
    ParentScript  76  BUTT_CC                    Creepy Crawlies tile button (decays over time)

The two riddle screens (SCREEN_RIDDLE 45, SCREEN_RIDDLE_MAG 46) live in riddle_screens.py and are
imported at the bottom of this file so `from . import riddles` registers everything.

Same conventions as ui.py / screens2.py: one class per Lingo parent script, method and property names
unchanged, `S(chan)` is `sprite(chan)`, `R()` is the runtime, `_done(parent, obj)` is `mPlayDone(parent, obj)`.
Lingo lists are 1-based: every `list[i]` below is written `list[i - 1]`.
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object
from .lingo import Sym, Point, Rect, set_properties, pop_one, pop_list, random_
from .ui import (load_mem, unload_mem, is_enabled, set_behavior, remove_behavior, blank, _done)
from .screens2 import (R, S, _new, _alive, _nz, _integer, _get_pos, _inside, _loc_from_rect,
                       _sprite_rect, _symeq, _T)


# ============================================================================================
# small Lingo helpers shared by riddles.py / riddle_screens.py / rooms.py
# ============================================================================================

def call_all(objs, name, *a):
    """call(#mFoo, list, args): like Lingo, silently skips items that are not objects or do not define the handler
    (e.g. RIDDLE_NOBUTT_LAMENAME has no mUpdate, RIDDLE_BUTT_NAME has no mEnable / mDisable)."""
    for o in list(objs or []):
        if isinstance(o, LObject):
            fn = getattr(o, name, None)
            if fn is not None:
                fn(*a)


def _idiv(a, b):
    """Lingo `integer(a / b)` for the usual int / int case (truncating integer division)."""
    if isinstance(a, int) and isinstance(b, int) and b:
        return int(a // b)
    return _integer(a / float(b))


def _pos(lst, v):
    """getPos(list, value): 1-based position using Lingo `=` (case-insensitive symbols), 0 when absent."""
    for i, o in enumerate(lst or []):
        if o == v:
            return i + 1
    return 0


def randomize_loc(loc, rng):
    """RandomizeLoc(locPoint, range)"""
    return loc + Point(random_(rng) - rng // 2, random_(rng) - rng // 2)


def move_sprite(chan, delta):
    """moveSprite(sprite, deltaPoint)"""
    if isinstance(chan, (list, tuple)):
        for c in chan:
            move_sprite(c, delta)
    else:
        S(chan).loc = S(chan).loc + delta


def set_ink(chan, ink):
    """setInk(chan, ink)"""
    if isinstance(chan, (list, tuple)):
        for c in chan:
            set_ink(c, ink)
    else:
        S(chan).ink = ink


def _found(o):
    """mGetFound(obj) as a 0/1 integer."""
    v = o.mGetFound()
    return 1 if v else 0


# ============================================================================================
# RIDDLE_LIN  (ParentScript 131)
# ============================================================================================

@lingo_script('RIDDLE_LIN')
class RiddleLin(LObject):
    def __init__(self):
        self.pMicroView = Sym('_01X')
        self.pFound = 0
        self.pParent = 0
        self.pStep = 0
        self.pLastUpdate = 0
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pClickRect = 0

    def mShowMicro(self, theView):
        if theView == self.pMicroView:
            self.mShow()

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pFound = 0
        self.pLastUpdate = 0
        self.pSpeed = _idiv(1000, self.pSpeed)
        self.pStep = 0
        self.pLoc = Point(320, 240)
        self.pSavedList = [Sym('pFound')]
        daIndex = min(3, len(self.pAnimMembers) // 2)
        self.pMultiMember = self.pAnimMembers[daIndex - 1]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mSetBackSprite(self, theSpriteAlloc):
        if self.pBackMember:
            self.pBackSprite = pop_one(theSpriteAlloc)

    def mGetBackMember(self):
        return self.pBackMember

    def mGetWordSound(self):
        return self.pWordSound

    def mGetWordClickedSound(self):
        return self.pWordSound

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName

    def mGetType(self):
        return Sym('RIDDLE_LIN')

    def mPlayWordSound(self):
        R().sound.puppet(1, self.pWordSound)

    def mShow(self):
        S(self.pSprite).ink = self.pInk
        if self.pInk == 32:
            S(self.pSprite).blend = 50
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pMember
        if _nz(self.pBackMember):
            S(self.pBackSprite).ink = self.pInk
        set_behavior(self.pSprite, self)

    def mHide(self):
        blank(self.pSprite)
        if _nz(self.pBackMember):
            blank(self.pBackSprite)

    def mouseDown(self):
        if _nz(self.pClickRect):
            if _inside(R().mouse, self.pClickRect):
                self.pParent.mRiddleButtonClicked(self)
        else:
            self.pParent.mRiddleButtonClicked(self)

    def mPlay(self):
        self.pFound = 1
        self.pLastUpdate = R().milliseconds() - self.pSpeed
        if self.pBackMember:
            load_mem(self.pBackMember)
            S(self.pBackSprite).member = self.pBackMember
            S(self.pSprite).member = self.pAnimMembers[0]
        load_mem(self.pAnimMembers)
        load_mem(self.pAnimSound)
        R().sound.puppet(1, self.pAnimSound)
        M.addUpdateList(self)

    def mStop(self):
        if self.pBackMember:
            unload_mem(self.pBackMember)
            S(self.pBackSprite).member = 1
        S(self.pSprite).member = self.pMember
        unload_mem(self.pAnimMembers)
        unload_mem(self.pAnimSound)
        M.removeUpdateList(self)
        self.pLastUpdate = 0
        self.pStep = 0

    def mUpdate(self):
        now = R().milliseconds()
        if (now - self.pLastUpdate) >= self.pSpeed:
            self.pLastUpdate = now
            self.pStep += 1
            if (self.pStep <= len(self.pAnimMembers)) or R().sound.busy(1):
                if self.pStep > len(self.pAnimMembers):
                    S(self.pSprite).member = self.pMember
                else:
                    S(self.pSprite).member = self.pAnimMembers[self.pStep - 1]
            else:
                self.mStop()
                R().sound.puppet(1, M.gFlushSound)
                _done(self.pParent, self)

    def mDisable(self):
        if is_enabled(self.pSprite, self):
            remove_behavior(self.pSprite)

    def mEnable(self):
        if not is_enabled(self.pSprite, self):
            set_behavior(self.pSprite, self)

    def mLoad(self):
        load_mem(self.pMember)

    def mLoadList(self, theList):
        theList.append(self.pMember)

    def mUnload(self):
        unload_mem(self.pMember)

    def mSetFound(self):
        self.pFound = 1

    def mGetFound(self):
        return self.pFound


# ============================================================================================
# RIDDLE_SC  (ParentScript 132)
# ============================================================================================

@lingo_script('RIDDLE_SC')
class RiddleSC(LObject):
    def __init__(self):
        self.pMicroView = Sym('01X')
        self.pFound = 0
        self.pParent = 0
        self.pStep = 0
        self.pLastUpdate = 0
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pClickRect = 0
        self.pEndClickRect = 0
        self.pMagStampRect = 0

    def mShowMicro(self, theView):
        if theView == self.pMicroView:
            self.mShow()

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pFound = 0
        self.pLastUpdate = 0
        self.pSpeed = _idiv(1000, self.pSpeed)
        self.pStep = 0
        self.pLoc = Point(320, 240)
        self.pCurMember = self.pMember
        self.pBackSprite = 0
        self.pSavedList = [Sym('pFound'), Sym('pCurMember'), Sym('pMagStampRect'), Sym('pClickRect')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mSetBackSprite(self, theSpriteAlloc):
        if self.pBackMember:
            self.pBackSprite = pop_one(theSpriteAlloc)

    def mGetBackMember(self):
        return self.pBackMember

    def mGetWordSound(self):
        return self.pWordSound

    def mGetWordClickedSound(self):
        return self.pWordSound

    def mGetName(self):
        return self.pName

    def mPlayWordSound(self):
        R().sound.puppet(1, self.pWordSound)

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('RIDDLE_SC')

    def mShow(self, theView=None):
        S(self.pSprite).ink = self.pInk
        if self.pInk == 32:
            S(self.pSprite).blend = 50
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pCurMember
        if _nz(self.pBackMember):
            if self.pFound:
                S(self.pBackSprite).member = self.pBackMember
            S(self.pBackSprite).ink = self.pInk
        set_behavior(self.pSprite, self)

    def mHide(self):
        blank(self.pSprite)
        if _nz(self.pBackMember):
            blank(self.pBackSprite)

    def mouseDown(self):
        if _nz(self.pClickRect):
            if _inside(R().mouse, self.pClickRect):
                self.pParent.mRiddleButtonClicked(self)
        else:
            self.pParent.mRiddleButtonClicked(self)

    def mPlay(self):
        if not self.pFound:
            self.pFound = 1
            load_mem(self.pAnimMembers)
            load_mem(self.pAnimSound)
            if _nz(self.pBackMember):
                load_mem(self.pBackMember)
                S(self.pBackSprite).member = self.pBackMember
                S(self.pBackSprite).ink = self.pInk
                S(self.pSprite).member = self.pAnimMembers[0]
            self.pLastUpdate = R().milliseconds() - self.pSpeed
            R().sound.puppet(1, self.pAnimSound)
            M.addUpdateList(self)
            S(self.pSprite).ink = self.pInk
            if _nz(self.pEndClickRect):
                self.pClickRect = self.pEndClickRect
        else:
            _done(self.pParent, self)

    def mStop(self):
        S(self.pSprite).member = self.pCurMember
        unload_mem(self.pBackMember)
        unload_mem(self.pAnimSound)
        unload_mem(self.pAnimMembers)
        M.removeUpdateList(self)
        self.pLastUpdate = 0
        self.pStep = 0

    def mUpdate(self):
        now = R().milliseconds()
        if (now - self.pLastUpdate) >= self.pSpeed:
            self.pLastUpdate = now
            self.pStep += 1
            n = len(self.pAnimMembers)
            if (self.pStep <= n) or R().sound.busy(1):
                daIndex = min(self.pStep, n)
                S(self.pSprite).member = self.pAnimMembers[daIndex - 1]
            else:
                self.pCurMember = self.pAnimMembers[n - 1]
                self.mStop()
                R().sound.puppet(1, M.gFlushSound)
                _done(self.pParent, self)

    def mDisable(self):
        if is_enabled(self.pSprite, self):
            remove_behavior(self.pSprite)

    def mEnable(self):
        if not is_enabled(self.pSprite, self):
            set_behavior(self.pSprite, self)

    def mLoad(self):
        load_mem(self.pCurMember)

    def mLoadList(self, theList):
        theList.append(self.pCurMember)

    def mUnload(self):
        unload_mem(self.pCurMember)
        unload_mem(self.pMember)

    def mSetFound(self):
        self.pFound = 1
        self.pCurMember = self.pAnimMembers[-1]
        if _nz(self.pEndClickRect):
            self.pClickRect = self.pEndClickRect

    def mGetFound(self):
        return self.pFound


# ============================================================================================
# RIDDLE_MULTI  (ParentScript 133)
# ============================================================================================

@lingo_script('RIDDLE_MULTI')
class RiddleMulti(LObject):
    def __init__(self):
        self.pPlayAllFound = 1
        self.pFound = 0
        self.pClickedCount = 0
        self.pParent = 0
        self.pClickAnimObjList = []
        self.pClickedSoundList = []
        self.pAllFoundAnimList = []
        self.pAllFoundReturnCount = 0
        self.pAllFoundWiggleSound = 0
        self.pCurrentRiddleObject = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        self.pPlayAllFound = 1
        set_properties(theObjectData, self)
        self.pFound = 0
        self.pClickedCount = 0
        self.pAllFoundWiggleSound = 0
        self.pCurrentRiddleObject = 0
        self.pClickedSoundList = []
        self.pAllFoundAnimList = []
        self.pAllFoundReturnCount = 0
        # the list still holds the *names* of the member objects here; call() skips anything that is not an object
        call_all(self.pClickAnimObjList, 'mSetParent', self)
        self.pSavedList = [Sym('pFound'), Sym('pClickedCount')]
        M.addObjectGlob(self)
        return self

    def mShowMicro(self, theView):
        if self.pPlayAllFound:
            self.mInitMultiAnimObjects()
        call_all(self.pClickAnimObjList, 'mShowMicro', theView)

    def mDestroy(self):
        pass

    def mSetBackSprite(self, theSpriteAlloc):
        pass

    def mLoad(self):
        call_all(self.pClickAnimObjList, 'mLoad')

    def mLoadList(self, theList):
        call_all(self.pClickAnimObjList, 'mLoadList', theList)

    def mUnload(self):
        call_all(self.pClickAnimObjList, 'mUnload')

    def mGrabRiddleObjects(self, theAnimList):
        """Take the riddle objects named in pClickAnimObjList out of the screen's list and keep them."""
        daTempClickAnimObjList = []
        for daObject in theAnimList:
            daName = daObject.pName
            daPosition = _pos(self.pClickAnimObjList, daName)
            if daPosition:
                if not _pos(self.pClickedSoundList, daObject.pWordSound):
                    self.pClickedSoundList.append(daObject.pWordSound)
                daTempClickAnimObjList.append(daObject)
        for daObject in daTempClickAnimObjList:
            daPos = _get_pos(theAnimList, daObject)
            if daPos:
                del theAnimList[daPos - 1]
        self.pClickAnimObjList = daTempClickAnimObjList
        self.pClickedSoundList.sort()
        call_all(self.pClickAnimObjList, 'mSetParent', self)

    def mInitMultiAnimObjects(self):
        daTempList = list(self.pAllFoundAnimList)
        del self.pAllFoundAnimList[:]
        for daObject in daTempList:
            M.recycleWiggleObject(daObject)
        for daObject in self.pClickAnimObjList:
            daWiggle = M.getWiggleObject(self)
            daWiggle.pSprite = daObject.pSprite
            daWiggle.pAnimMembers = daObject.pMultiAnimList
            daWiggle.pSoundChannel = 1
            daWiggle.pInk = daObject.pInk
            daWiggle.pName = daObject.pName
            if daObject.pBackMember:
                daWiggle.pBackMember = daObject.pBackMember
                daWiggle.pBackSprite = daObject.pBackSprite
            self.pAllFoundAnimList.append(daWiggle)

    def mGetWordClickedSound(self):
        return self.pClickedSoundList[-1] if self.pClickedSoundList else 0

    def mGetWordSound(self):
        if not self.pClickedSoundList:
            return 0
        daIndex = min(self.pClickedCount, len(self.pClickAnimObjList))
        return self.pClickedSoundList[max(daIndex, 1) - 1]

    def mRiddleButtonClicked(self, theObject):
        self.pCurrentRiddleObject = 0
        self.pCurrentRiddleObject = theObject
        if not theObject.pFound:
            self.pClickedCount += 1
        self.pParent.mRiddleButtonClicked(self)

    def mPlay(self):
        if self.mAllObjectsFound() and self.pPlayAllFound:
            self.mDisable()
            self.pAllFoundReturnCount = 0
            self.pAllFoundWiggleSound = M.getWiggleSound()
            load_mem(self.pAllFoundWiggleSound)
            R().sound.puppet(1, self.pAllFoundWiggleSound)
            for daObject in self.pAllFoundAnimList:
                daObject.mLoad()
            for daObject in self.pAllFoundAnimList:
                daObject.mShow()
            for daObject in list(self.pAllFoundAnimList):
                daObject.mPlay()
        else:
            self.pCurrentRiddleObject.mPlay()

    def mPlayDone(self, theObject):
        if theObject is self.pCurrentRiddleObject:
            for daOtherObject in self.pClickAnimObjList:
                if (daOtherObject is not theObject) and (daOtherObject.pName == theObject.pName):
                    daOtherObject.mSetFound()
            if self.mAllObjectsFound() and self.pPlayAllFound:
                self.mPlay()
            else:
                _done(self.pParent, self)
        else:
            if _get_pos(self.pAllFoundAnimList, theObject):
                self.pAllFoundReturnCount += 1
                if self.pAllFoundReturnCount == len(self.pAllFoundAnimList):
                    unload_mem(self.pAllFoundWiggleSound)
                    call_all(self.pAllFoundAnimList, 'mUnload')
                    call_all(self.pClickAnimObjList, 'mShow')
                    call_all(self.pClickAnimObjList, 'mDisable')
                    _done(self.pParent, self)

    def mShow(self):
        if self.pPlayAllFound:
            self.mInitMultiAnimObjects()
        call_all(self.pClickAnimObjList, 'mShow')

    def mHide(self):
        call_all(self.pClickAnimObjList, 'mHide')
        for daObject in self.pAllFoundAnimList:
            M.recycleWiggleObject(daObject)
        del self.pAllFoundAnimList[:]

    def mSetFound(self):
        pass

    def mGetFound(self):
        return self.mAllObjectsFound()

    def mEnable(self):
        call_all(self.pClickAnimObjList, 'mEnable')

    def mDisable(self):
        call_all(self.pClickAnimObjList, 'mDisable')

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName

    def mAllObjectsFound(self):
        daFound = 1
        for daObject in self.pClickAnimObjList:
            if isinstance(daObject, LObject):
                daFound = min(daFound, _found(daObject))
        return daFound

    def mGetFoundCount(self):
        daFound = 0
        for daObject in self.pClickAnimObjList:
            if isinstance(daObject, LObject):
                daFound += _found(daObject)
        return daFound

    def mObjectsRemaining(self):
        daFound = 0
        for daObject in self.pClickAnimObjList:
            if isinstance(daObject, LObject):
                daFound += 0 if _found(daObject) else 1
        return daFound

    def mGetType(self):
        return Sym('RIDDLE_MULTI')


# ============================================================================================
# RIDDLEWORD_RECT  (ParentScript 134)
# ============================================================================================

@lingo_script('RIDDLEWORD_RECT')
class RiddleWordRect(LObject):
    def __init__(self):
        self.pSprite = 0
        self.pHotSprite = 0
        self.pMouseOn = 0
        self.pMouseDown = 0
        self.pCurrentMember = 1
        self.pKeepCursor = 0
        self.pEnabled = 0
        self.pParent = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = 0
        self.pHotSprite = 0
        self.pMouseOn = 0
        self.pMouseDown = 0
        self.pCurrentMember = 1
        self.pKeepCursor = 0
        self.pSavedList = [Sym('pCurrentMember')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mInitSprites(self, theSpriteAlloc):
        self.pSprite = pop_one(theSpriteAlloc)

    def mLoad(self):
        load_mem(self.pCurrentMember)

    def mLoadList(self, theList):
        theList.append(self.pMember)
        theList.append(self.pCurrentMember)

    def mUnload(self):
        unload_mem(self.pCurrentMember)
        unload_mem(self.pMember)

    def mShow(self):
        self.pEnabled = 1
        if self.pCurrentMember != self.pMember:
            S(self.pSprite).ink = 32
            S(self.pSprite).blend = 0
            S(self.pSprite).loc = Point(320, 240)
            S(self.pSprite).member = 1
            S(self.pSprite).stretch_rect = self.prect         # stretch = 1; rect = prect
        else:
            S(self.pSprite).ink = 36
            S(self.pSprite).member = self.pCurrentMember
        S(self.pSprite).cursor = [22, 23]
        set_behavior(self.pSprite, self)

    def mSetSelected(self):
        self.pCurrentMember = self.pMember
        S(self.pSprite).stretch_rect = None                  # stretch = 0
        S(self.pSprite).loc = Point(320, 240)
        S(self.pSprite).ink = 36
        S(self.pSprite).blend = 100
        S(self.pSprite).member = self.pCurrentMember

    def mHide(self):
        remove_behavior(self.pSprite, self)
        blank(self.pSprite)

    def mouseEnter(self):
        pass

    def mouseLeave(self):
        pass

    def mouseDown(self):
        if self.pEnabled:
            self.pParent.mWordClicked(self)

    def mouseUp(self):
        pass

    def mPlay(self):
        self.mSetSelected()
        _done(self.pParent, self)

    def mUpdate(self):
        if not R().sound.busy(1):
            R().sound.puppet(1, M.gFlushSound)
            _done(self.pParent, self)

    def mKeepCursor(self):
        self.pKeepCursor = 1

    def mDisable(self):
        self.pEnabled = 0
        if not self.pKeepCursor:
            S(self.pSprite).cursor = 0
        else:
            self.pKeepCursor = 0

    def mEnable(self):
        self.pEnabled = 1
        S(self.pSprite).cursor = [22, 23]

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('RIDDLEWORD_RECT')

    def mGetName(self):
        return self.pName


# ============================================================================================
# RIDDLEWORD  (ParentScript 135)
# ============================================================================================

@lingo_script('RIDDLEWORD')
class RiddleWord(LObject):
    def __init__(self):
        self.pSprite = 0
        self.pKeepCursor = 0
        self.pEnabled = 0
        self.pParent = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = 0
        self.pKeepCursor = 0
        return self

    def mDestroy(self):
        pass

    def mInitSprites(self, theSpriteAlloc):
        self.pSprite = pop_one(theSpriteAlloc)

    def mLoad(self):
        load_mem(self.pClickSound)

    def mLoadList(self, theList):
        theList.append(self.pClickSound)

    def mUnload(self):
        unload_mem(self.pClickSound)

    def mShow(self):
        self.pEnabled = 1
        S(self.pSprite).ink = 32
        S(self.pSprite).blend = 0
        S(self.pSprite).loc = Point(320, 240)
        S(self.pSprite).member = 1                            # Fantasy: the blank member (no getWordRectBlank)
        S(self.pSprite).stretch_rect = self.prect             # stretch = 1; rect = prect
        S(self.pSprite).cursor = [22, 23]
        set_behavior(self.pSprite, self)

    def mSetSelected(self):
        pass

    def mHide(self):
        remove_behavior(self.pSprite, self)
        blank(self.pSprite)

    def mPlay(self):
        R().sound.puppet(1, self.pClickSound)
        M.addUpdateList(self)

    def mUpdate(self):
        if not R().sound.busy(1):
            R().sound.puppet(1, M.gFlushSound)
            _done(self.pParent, self)

    def mouseEnter(self):
        pass

    def mouseLeave(self):
        pass

    def mouseDown(self):
        if self.pEnabled:
            self.pParent.mWordClicked(self)

    def mouseUp(self):
        pass

    def mKeepCursor(self):
        self.pKeepCursor = 1

    def mDisable(self):
        self.pEnabled = 0
        if not self.pKeepCursor:
            S(self.pSprite).cursor = 0
        else:
            self.pKeepCursor = 0

    def mEnable(self):
        self.pEnabled = 1
        S(self.pSprite).cursor = [22, 23]

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('RIDDLEWORD')

    def mGetName(self):
        return self.pName


# ============================================================================================
# RIDDLE_DRAG  (ParentScript 136)
# ============================================================================================

@lingo_script('RIDDLE_DRAG')
class RiddleDrag(LObject):
    def __init__(self):
        self.pBackSprite = 0
        self.pNeutBackSprite = 0
        self.pBackMember = 0
        self.pNeutBackMember = 0
        self.pDropped = 0
        self.pFound = 0
        self.pParent = 0
        self.pDragReturnLoc = 0
        self.pStateChangeAnim = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackSprite = 0
        self.pNeutBackSprite = 0
        self.pSprite = pop_one(theSpriteAlloc)
        self.pInk = 8
        self.pLoc = Point(320, 240)
        self.pStartLoc = Point(320, 240)
        self.pDropped = 0
        self.pDownTime = 0
        self.pFound = 0
        self.pStateChangeAnim = get_object(self.pStateChangeAnim, theSpriteAlloc)
        self.pStateChangeAnim.mSetParent(self)
        self.pDragObject = _new(self.pDragScriptNumber, self.pDragMember, self, Rect(0, 0, 640, 420))
        self.pDropObject = _new(self.pAnimSlideScriptNumber, self)
        self.pDragReturnLoc = 0
        self.pSavedList = [Sym('pFound')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mLoad(self):
        load_mem(self.pBackMember)
        if not self.pFound:
            load_mem(self.pPickupSound)
            load_mem(self.pDropSoundCorrect)
            load_mem(self.pDropSoundWrong)
            load_mem(self.pMember)
            load_mem(self.pDragMember)
            if _alive(self.pStateChangeAnim):
                self.pStateChangeAnim.mLoad()
        else:
            if _alive(self.pStateChangeAnim):
                self.pStateChangeAnim.mLoad()

    def mLoadList(self, theList):
        theList.append(self.pBackMember)
        if not self.pFound:
            theList.append(self.pPickupSound)
            theList.append(self.pDropSoundCorrect)
            theList.append(self.pDropSoundWrong)
            theList.append(self.pMember)
            theList.append(self.pDragMember)
            if _alive(self.pStateChangeAnim):
                theList.append(self.pStateChangeAnim)
        else:
            if _alive(self.pStateChangeAnim):
                theList.append(self.pStateChangeAnim)

    def mUnload(self):
        unload_mem(self.pPickupSound)
        unload_mem(self.pDropSoundCorrect)
        unload_mem(self.pDropSoundWrong)
        unload_mem(self.pBackMember)
        unload_mem(self.pDragMember)
        unload_mem(self.pMember)
        if _alive(self.pStateChangeAnim):
            self.pStateChangeAnim.mUnload()
        unload_mem(self.pNeutBackMember)

    def mSetBackSprite(self, theSpriteAlloc):
        if _alive(self.pStateChangeAnim):
            self.pStateChangeAnim.mSetBackSprite(theSpriteAlloc)
        if self.pBackMember:
            self.pBackSprite = pop_one(theSpriteAlloc)
        if self.pNeutBackMember:
            self.pNeutBackSprite = pop_one(theSpriteAlloc)

    def mGetType(self):
        return Sym('RIDDLE_DRAG')

    def mGetName(self):          # `on mGetName` (no `me` parameter) in the original
        return self.pName

    def mGetFound(self):
        return self.pFound

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mShow(self):
        if not self.pFound:
            S(self.pSprite).member = self.pMember
            S(self.pSprite).ink = 8
            if self.pNeutBackMember:
                S(self.pNeutBackSprite).member = self.pNeutBackMember
                S(self.pNeutBackSprite).ink = 8
            self.pStateChangeAnim.mDisable()
            set_behavior(self.pSprite, self)
        else:
            self.pStateChangeAnim.mShow()

    def mHide(self):
        self.pStateChangeAnim.mHide()
        blank(self.pBackSprite)
        blank(self.pSprite)
        if self.pNeutBackMember:
            blank(self.pNeutBackSprite)
        remove_behavior(self.pSprite, self)

    def mSetFound(self):
        self.pFound = 1

    def mGetWordSound(self):
        return self.pStateChangeAnim.mGetWordSound()

    def mGetWordClickedSound(self):
        return self.pStateChangeAnim.mGetWordClickedSound()

    def mouseEnter(self):
        M.setOpenhandCursor()

    def mouseLeave(self):
        if S(self.pSprite).member == self.pMember:
            M.resetCursor()

    def mouseDown(self):
        rt = R()
        daMouseLoc = rt.mouse
        self.pDragReturnLoc = _loc_from_rect(_sprite_rect(self.pSprite))
        daDragOffset = self.pDragReturnLoc - daMouseLoc
        if self.pNeutBackMember:
            S(self.pNeutBackSprite).member = 1
        S(self.pSprite).member = self.pDragMember
        daholdLoc = S(self.pSprite).loc
        S(self.pSprite).loc = rt.mouse + daDragOffset
        # updateStage()
        if not _inside(rt.mouse, _sprite_rect(self.pSprite)):
            daDragOffset = Point(0, 0)
        S(self.pSprite).loc = daholdLoc
        S(self.pSprite).member = 1
        self.pDragObject.pDragOffset = daDragOffset
        self.pDragObject.mShow()
        rt.sound.puppet(1, self.pPickupSound)
        self.pDragObject.mPlay()
        M.disableGame()

    def mPlay(self):
        self.pStateChangeAnim.mPlay()

    def mouseUp(self):
        # Lingo: empty.  The port's mouse dispatcher can deliver the release to the pressed (now blank)
        # sprite instead of the drag sprite; hand it on so a drag always ends (as DRAG_N_DROP_SIMPLE does).
        self._release_drag()

    def mouseUpOutSide(self):
        self._release_drag()

    def _release_drag(self):
        d = self.pDragObject
        if _alive(d) and is_enabled(d.pSprite, d):
            d.mouseUp()

    def mPlayDone(self, theObject):
        if theObject is self.pStateChangeAnim:
            _done(self.pParent, self)
        else:
            if theObject is self.pDropObject:
                self.pDropObject.mHide()
                S(self.pSprite).member = self.pMember
                if self.pNeutBackMember:
                    S(self.pNeutBackSprite).member = self.pNeutBackMember
                M.enableGame()
            else:
                if _inside(S(theObject.pSprite).loc, self.pDropRect):
                    self.pFound = 1
                    R().sound.puppet(1, self.pDropSoundCorrect)
                    self.pDragObject.mHide()
                    self.pParent.mRiddleButtonClicked(self)
                else:
                    R().sound.puppet(1, self.pDropSoundWrong)
                    self.pDropObject.mSetReturnLoc(self.pDragReturnLoc)
                    self.pDropObject.mPlay()
                M.resetCursor()

    def mRiddleButtonClicked(self, theObject):
        self.pParent.mRiddleButtonClicked(self)

    def mEnable(self):
        if self.pFound:
            self.pStateChangeAnim.mEnable()
        else:
            if not is_enabled(self.pSprite, self):
                set_behavior(self.pSprite, self)

    def mDisable(self):
        if self.pFound:
            self.pStateChangeAnim.mDisable()
        else:
            if is_enabled(self.pSprite, self):
                remove_behavior(self.pSprite, self)


# ============================================================================================
# RIDDLE_NAME  (ParentScript 137)  +  its letter sprites (138 / 141)
# ============================================================================================

@lingo_script('RIDDLE_NAME')
class RiddleName(LObject):
    def __init__(self):
        self.pFound = 0
        self.pEnabled = 1
        self.pLastUpdate = 0
        self.pParent = 0
        self.pLetterButtList = []
        self.pBackMember = 0
        self.pBackSprite = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pLetterButtList = []
        self.pPlayerName = M.gPlayer
        self.pPlayerNameLength = len(self.pPlayerName)
        for objIdx in range(1, self.pPlayerNameLength + 1):
            curLet = self.pPlayerName[objIdx - 1]
            curLoc = self.pLocList[objIdx - 1]
            newObj = _new(self.pLetterButtType, self.pFirstLetterMemberNum, curLet, pop_one(theSpriteAlloc), curLoc)
            self.pLetterButtList.append(newObj)
            newObj.mSetParent(self)
        self.pFound = 0
        self.pEnabled = 1
        self.pLastUpdate = 0
        self.pSpeed = _idiv(1000, 10)
        self.pSavedList = [Sym('pFound')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mShow(self):
        self.pEnabled = 1
        call_all(self.pLetterButtList, 'mShow')

    def mHide(self):
        call_all(self.pLetterButtList, 'mHide')

    def mSetWordRef(self, theObj):
        self.pWordObj = theObj

    def mGetWordSound(self):
        return self.pWordSound

    def mGetWordClickedSound(self):
        return self.pWordSound

    def mPlay(self):
        self.pFound = 1
        daSound = M.getWiggleSound()
        R().sound.puppet(1, daSound)
        self.pLastUpdate = R().milliseconds() - self.pSpeed
        M.addUpdateList(self)

    def mUpdate(self):
        if R().sound.busy(1):
            now = R().milliseconds()
            if (now - self.pLastUpdate) >= self.pSpeed:
                self.pLastUpdate = now
                call_all(self.pLetterButtList, 'mUpdate')
        else:
            self.mStop()
            R().sound.puppet(1, M.gFlushSound)
            _done(self.pParent, self)

    def mStop(self):
        call_all(self.pLetterButtList, 'mResetLoc')
        M.removeUpdateList(self)
        self.pLastUpdate = 0

    def mClickName(self):
        if self.pEnabled == 1:
            self.pParent.mRiddleButtonClicked(self)

    def mLoad(self):
        call_all(self.pLetterButtList, 'mLoad')

    def mLoadList(self, theList):
        call_all(self.pLetterButtList, 'mLoadList', theList)

    def mUnload(self):
        call_all(self.pLetterButtList, 'mUnload')

    def mGetName(self):
        return self.pName

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mIsStateChange(self):
        return 0

    def mResetMem(self):
        call_all(self.pLetterButtList, 'mShow')

    def mSetFound(self):
        self.pFound = 1

    def mGetFound(self):
        return self.pFound

    def mEnable(self):
        self.pEnabled = 1
        call_all(self.pLetterButtList, 'mEnable')

    def mDisable(self):
        self.pEnabled = 0
        call_all(self.pLetterButtList, 'mDisable')

    def mSetBackSprite(self, theSpriteAlloc):
        self.pBackSprite = pop_one(theSpriteAlloc)

    def mGetBackMember(self):
        return self.pBackMember

    def mGetType(self):
        return Sym('RIDDLE_NAME')


def _letter_member(first, ch):
    """charToNum(curLet) -> member: the letters are consecutive members starting at 'A'; a space is 91."""
    n = ord(ch)
    if n == 32:
        n = 91
    return first + n - 65


@lingo_script('RIDDLE_NOBUTT_LAMENAME')
class RiddleNoButtLameName(LObject):
    def __init__(self, pFirstLetterMemberNum=0, curLet=' ', daSpr=0, curLoc=None):
        self.pEnabled = 1
        self.pSprite = daSpr
        self.pMember = _letter_member(pFirstLetterMemberNum, curLet)
        self.pLoc = curLoc
        self.pSavedList = []
        self.pParent = 0

    def mGetType(self):
        return Sym('RIDDLE_NOBUTT_LAMENAME')

    def mDestroy(self):
        pass

    def mShow(self):
        S(self.pSprite).ink = 36
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pMember

    def mLoad(self):
        load_mem(self.pMember)

    def mLoadList(self, theList):
        theList.append(self.pMember)

    def mUnload(self):
        unload_mem(self.pMember)

    def mHide(self):
        blank(self.pSprite)

    def mSetBehavior(self):
        set_behavior(self.pSprite, self)

    def mResetMem(self):
        S(self.pSprite).member = self.pMember

    def mChangeMem(self, theMember):
        S(self.pSprite).member = theMember

    def mGetCurMem(self):
        return S(self.pSprite).member

    def mSetMem(self, theMember):
        self.pMember = theMember

    def mGetMem(self):
        return self.pMember

    def mMove(self, theOffset):
        move_sprite(self.pSprite, theOffset)

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName


@lingo_script('RIDDLE_BUTT_NAME')
class RiddleButtName(LObject):
    def __init__(self, pFirstLetterMemberNum=0, curLet=' ', daSpr=0, curLoc=None):
        self.pEnabled = 1
        self.pSprite = daSpr
        self.pMember = _letter_member(pFirstLetterMemberNum, curLet)
        self.pLoc = curLoc
        self.pSavedList = []
        self.pParent = 0

    def mDestroy(self):
        pass

    def mShow(self):
        S(self.pSprite).ink = 36
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pMember
        self.mSetBehavior()

    def mUpdate(self):
        S(self.pSprite).loc = randomize_loc(self.pLoc, 4)

    def mResetLoc(self):
        S(self.pSprite).loc = self.pLoc

    def mLoad(self):
        load_mem(self.pMember)

    def mLoadList(self, theList):
        theList.append(self.pMember)

    def mUnload(self):
        unload_mem(self.pMember)

    def mouseDown(self):
        self.pParent.mClickName()

    def mHide(self):
        blank(self.pSprite)

    def mSetBehavior(self):
        set_behavior(self.pSprite, self)

    def mResetMem(self):
        S(self.pSprite).member = self.pMember

    def mChangeMem(self, theMember):
        S(self.pSprite).member = theMember

    def mGetCurMem(self):
        return S(self.pSprite).member

    def mGetType(self):
        return Sym('RIDDLE_BUTT_NAME')

    def mSetMem(self, theMember):
        self.pMember = theMember

    def mGetMem(self):
        return self.pMember

    def mMove(self, theOffset):
        move_sprite(self.pSprite, theOffset)

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName


# ============================================================================================
# RIDDLESTRIP  (ParentScript 139)
# ============================================================================================

@lingo_script('RIDDLESTRIP')
class RiddleStrip(LObject):
    def __init__(self):
        self.pRiddleWordList = []
        self.pParent = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pRiddleSprite = pop_one(theSpriteAlloc)
        self.pEarButton = get_object(self.pEarButton, theSpriteAlloc)
        self.pRiddleWordList = []
        self.pWordAlloc = pop_list(theSpriteAlloc, 30)
        self.pEarButton.mSetParent(self)
        return self

    def mDestroy(self):
        pass

    def mLoad(self):
        load_mem(self.pBackMember)
        load_mem(self.pPaperSound)
        self.pEarButton.mLoad()

    def mLoadList(self, theList):
        theList.append(self.pBackMember)
        theList.append(self.pPaperSound)
        self.pEarButton.mLoadList(theList)

    def mUnload(self):
        unload_mem(self.pBackMember)
        unload_mem(self.pPaperSound)
        self.pEarButton.mUnload()

    def mSetWordList(self, theWordList):
        self.pRiddleWordList = theWordList
        daAlloc = list(self.pWordAlloc)
        for daWordObj in self.pRiddleWordList:
            daWordObj.mInitSprites(daAlloc)
        call_all(self.pRiddleWordList, 'mSetParent', self)

    def mDisable(self):
        self.pEarButton.mDisable()
        call_all(self.pRiddleWordList, 'mDisable')

    def mEnable(self):
        self.pEarButton.mEnable()
        call_all(self.pRiddleWordList, 'mEnable')

    def mShow(self):
        M.setMember(self.pBackSprite, self.pBackMember)
        M.setMember(self.pRiddleSprite, self.pRiddleStripMember)
        set_ink(self.pBackSprite, 8)
        set_ink(self.pRiddleSprite, 36)
        self.pEarButton.mShow()

    def mPlaySound(self):
        R().sound.puppet(1, self.pPaperSound)

    def mHide(self):
        blank(self.pBackSprite)
        blank(self.pRiddleSprite)
        self.pEarButton.mHide()
        call_all(self.pRiddleWordList, 'mHide')

    def mWordClicked(self, theObject):
        call_all(self.pRiddleWordList, 'mKeepCursor')
        self.pParent.mWordClicked(theObject)

    def mPlayDone(self, theObject):
        if _get_pos(self.pRiddleWordList, theObject):
            _done(self.pParent, theObject)

    def mButtonActivated(self, theButton):
        if theButton is self.pEarButton:
            self.pParent.mButtonActivated(self)

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('RIDDLESTRIP')


# ============================================================================================
# RIDDLE_WIG_SC  (ParentScript 140)  /  RIDDLE_WIG  (ParentScript 144)
# ============================================================================================

@lingo_script('RIDDLE_WIG_SC')
class RiddleWigSC(LObject):
    def __init__(self):
        self.pFound = 0
        self.pStep = 0
        self.pLoc = Point(320, 240)
        self.pMicroView = Sym('_01X')
        self.pAnimSound = 0
        self.pParent = 0
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pClickRect = 0
        self.pLastUpdate = 0

    def mShowMicro(self, theView):
        if theView == self.pMicroView:
            self.mShow()

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pLastUpdate = 0
        self.pSpeed = _idiv(1000, self.pSpeed)
        daIndex = min(3, len(self.pAnimMembers) // 2)
        self.pMultiMember = self.pAnimMembers[daIndex - 1]
        self.pSavedList = [Sym('pFound')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mSetBackSprite(self, theSpriteAlloc):
        if self.pBackMember:
            self.pBackSprite = pop_one(theSpriteAlloc)

    def mGetBackMember(self):
        return self.pBackMember

    def mGetWordSound(self):
        return self.pWordSound

    def mGetWordClickedSound(self):
        return self.pWordSound

    def mGetName(self):
        return self.pName

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('RIDDLE_WIG_SC')

    def mShow(self):
        S(self.pSprite).ink = self.pInk
        if self.pInk == 32:
            S(self.pSprite).blend = 50
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pMember
        if _nz(self.pBackMember):
            S(self.pBackSprite).ink = self.pInk
        set_behavior(self.pSprite, self)

    def mHide(self):
        blank(self.pSprite)
        if _nz(self.pBackMember):
            blank(self.pBackSprite)

    def mouseDown(self):
        if _nz(self.pClickRect):
            if _inside(R().mouse, self.pClickRect):
                self.pParent.mRiddleButtonClicked(self)
        else:
            self.pParent.mRiddleButtonClicked(self)

    def mPlay(self):
        if not self.pFound:
            self.pFound = 1
            self.pAnimSound = M.getWiggleSound()
            load_mem(self.pAnimMembers)
            load_mem(self.pAnimSound)
            if self.pBackMember:
                load_mem(self.pBackMember)
                S(self.pBackSprite).member = self.pBackMember
            S(self.pSprite).ink = self.pInk
            S(self.pSprite).member = self.pAnimMembers[0]
            self.pStep = 1
            R().sound.puppet(1, self.pAnimSound)
            self.pLastUpdate = R().milliseconds() - self.pSpeed
            M.addUpdateList(self)
        else:
            _done(self.pParent, self)

    def mStop(self):
        S(self.pSprite).member = self.pAnimMembers[-1]
        self.pMember = self.pAnimMembers[-1]
        if self.pBackMember:
            S(self.pBackSprite).member = 1
        unload_mem(self.pAnimMembers)
        unload_mem(self.pAnimSound)
        unload_mem(self.pBackMember)
        M.removeUpdateList(self)
        self.pLastUpdate = 0

    def mUpdate(self):
        if R().sound.busy(1):
            now = R().milliseconds()
            if (now - self.pLastUpdate) >= self.pSpeed:
                self.pLastUpdate = now
                daIndex = (self.pStep % len(self.pAnimMembers)) + 1
                S(self.pSprite).member = self.pAnimMembers[daIndex - 1]
                self.pStep += 1
        else:
            self.mStop()
            R().sound.puppet(1, M.gFlushSound)
            _done(self.pParent, self)

    def mDisable(self):
        remove_behavior(self.pSprite)

    def mEnable(self):
        if not is_enabled(self.pSprite, self):
            set_behavior(self.pSprite, self)

    def mLoad(self):
        load_mem(self.pMember)

    def mLoadList(self, theList):
        theList.append(self.pMember)

    def mUnload(self):
        unload_mem(self.pMember)

    def mSetFound(self):
        self.pFound = 1

    def mGetFound(self):
        return self.pFound


@lingo_script('RIDDLE_WIG')
class RiddleWig(LObject):
    def __init__(self):
        self.pFound = 0
        self.pStep = 0
        self.pLoc = Point(320, 240)
        self.pMicroView = Sym('_01X')
        self.pAnimSound = 0
        self.pParent = 0
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pClickRect = 0
        self.pLastUpdate = 0

    def mShowMicro(self, theView):
        if theView == self.pMicroView:
            self.mShow()

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pLastUpdate = 0
        self.pSpeed = _idiv(1000, self.pSpeed)
        daIndex = min(3, len(self.pAnimMembers) // 2)
        self.pMultiMember = self.pAnimMembers[daIndex - 1]
        self.pSavedList = [Sym('pFound')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mSetBackSprite(self, theSpriteAlloc):
        if self.pBackMember:
            self.pBackSprite = pop_one(theSpriteAlloc)

    def mGetBackMember(self):
        return self.pBackMember

    def mGetWordSound(self):
        return self.pWordSound

    def mGetWordClickedSound(self):
        return self.pWordSound

    def mGetName(self):
        return self.pName

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('RIDDLE_WIG')

    def mShow(self):
        S(self.pSprite).ink = self.pInk
        if self.pInk == 32:
            S(self.pSprite).blend = 50
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pMember
        if _nz(self.pBackMember):
            S(self.pBackSprite).ink = self.pInk
        set_behavior(self.pSprite, self)

    def mHide(self):
        blank(self.pSprite)
        if _nz(self.pBackMember):
            blank(self.pBackSprite)

    def mouseDown(self):
        if _nz(self.pClickRect):
            if _inside(R().mouse, self.pClickRect):
                self.pParent.mRiddleButtonClicked(self)
        else:
            self.pParent.mRiddleButtonClicked(self)

    def mPlay(self):
        self.pFound = 1
        self.pAnimSound = M.getWiggleSound()
        load_mem(self.pAnimMembers)
        load_mem(self.pAnimSound)
        if self.pBackMember:
            load_mem(self.pBackMember)
            S(self.pBackSprite).member = self.pBackMember
        S(self.pSprite).member = self.pAnimMembers[0]
        self.pLastUpdate = R().milliseconds() - self.pSpeed
        self.pStep = 1
        R().sound.puppet(1, self.pAnimSound)
        M.addUpdateList(self)

    def mStop(self):
        S(self.pSprite).member = self.pMember
        R().update_stage()
        if self.pBackMember:
            S(self.pBackSprite).member = 1
        unload_mem(self.pAnimMembers)
        unload_mem(self.pAnimSound)
        unload_mem(self.pBackMember)
        M.removeUpdateList(self)
        self.pLastUpdate = 0

    def mUpdate(self):
        if R().sound.busy(1):
            now = R().milliseconds()
            if (now - self.pLastUpdate) >= self.pSpeed:
                self.pLastUpdate = now
                daIndex = (self.pStep % len(self.pAnimMembers)) + 1
                S(self.pSprite).member = self.pAnimMembers[daIndex - 1]
                self.pStep += 1
        else:
            # `repeat while the milliSeconds < pLastUpdate` -- pLastUpdate is never in the future, so it never spins
            self.mStop()
            R().sound.puppet(1, M.gFlushSound)
            _done(self.pParent, self)

    def mDisable(self):
        remove_behavior(self.pSprite)

    def mEnable(self):
        if not is_enabled(self.pSprite, self):
            set_behavior(self.pSprite, self)

    def mLoad(self):
        load_mem(self.pMember)

    def mLoadList(self, theList):
        theList.append(self.pMember)

    def mUnload(self):
        unload_mem(self.pMember)

    def mSetFound(self):
        self.pFound = 1

    def mGetFound(self):
        return self.pFound


# ============================================================================================
# SHTokenObject (142) / RiddleTokenObject (143)   -- `ancestor` composition
# ============================================================================================

@lingo_script('SHTokenObject')
class SHTokenObject(LObject):
    def __init__(self):
        self.ancestor = None
        self.pParent = 0
        self.pGhostToken = None

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.ancestor = get_object(self.ancestor, theSpriteAlloc)
        self.ancestor.mSetParent(self)
        return self

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('SHTokenObject')

    def mLoadList(self, theList):
        if self.mObjectVisible():
            self.ancestor.mLoadList(theList)

    def mLoad(self):
        if self.mObjectVisible():
            self.ancestor.mLoad()

    def mShow(self):
        if self.mObjectVisible():
            self.ancestor.mShow()
            if self.mObjectActive():
                self.ancestor.mEnable()

    def mEnable(self):
        if self.mObjectActive():
            self.ancestor.mEnable()

    def mButtonActivated(self, theObject):
        M.waitCursor()
        M.gScreenDaddy.mDisable()
        theObject.mPlay()

    def mPlayDone(self, theObject):
        self.pParent.mButtonActivated(self)

    def mObjectActive(self):
        return (not self.ancestor.pPlayed) and (M.gScreenDaddy.mGetCurrentHuntName() == self.ancestor.pName)

    def mObjectVisible(self):
        if isinstance(self.pGhostToken, Sym):
            return M.gScreenDaddy.mTokenFound(self.pGhostToken)
        else:
            if M.gScreenDaddy.mGetLevel() > 1:
                return 1
        return None


@lingo_script('RiddleTokenObject')
class RiddleTokenObject(LObject):
    def __init__(self):
        self.ancestor = None
        self.pParent = 0
        self.pGhostToken = None

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.ancestor = get_object(self.ancestor, theSpriteAlloc)
        self.ancestor.mSetParent(self)
        return self

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('RiddleTokenObject')

    def mShow(self):
        if self.mObjectVisible():
            self.ancestor.mShow()
            if not self.mObjectActive():
                self.ancestor.mDisable()

    def mEnable(self):
        if self.mObjectActive():
            self.ancestor.mEnable()

    def mRiddleButtonClicked(self, theObject):
        if self.mObjectActive():
            M.waitCursor()
            self.pParent.mRiddleButtonClicked(self)

    def mPlayDone(self, theObject):
        self.pParent.mPlayDone(self)

    def mObjectActive(self):
        return (not self.ancestor.pFound) and (M.gScreenDaddy.mGetCurrentHuntName() == self.ancestor.pName)

    def mObjectVisible(self):
        if isinstance(self.pGhostToken, Sym):
            return M.gScreenDaddy.mTokenFound(self.pGhostToken) and not self.ancestor.pFound
        else:
            if M.gScreenDaddy.mGetLevel() > 1:
                return 1
        return None


# ============================================================================================
# BUTT_MM  (ParentScript 75)
# ============================================================================================

@lingo_script('BUTT_MM')
class ButtMM(LObject):
    def __init__(self):
        self.pAnimSpeed = 100
        self.pEnabled = 1
        self.pLastUpdate = 0
        self.pMatch = 0
        self.pParent = 0
        self.pEventTag = None

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pHiSprite = pop_one(theSpriteAlloc)
        self.pMember = 1
        self.pSavedList = [Sym('pMember'), Sym('pMatch')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mGetType(self):
        return Sym('BUTT_MM')

    def mouseDown(self):
        self.pParent.mButtonActivated(self)

    def mLoad(self):
        load_mem(self.pMember)
        load_mem(self.pHiMember)

    def mLoadList(self, theList):
        theList.append(self.pMember)
        theList.append(self.pHiMember)

    def mUnload(self):
        unload_mem(self.pMember)
        unload_mem(self.pHiMember)

    def mDisable(self):
        self.pEnabled = 0
        remove_behavior(self.pSprite, self)

    def mEnable(self):
        self.pEnabled = 1
        set_behavior(self.pSprite, self)

    def mShow(self):
        S(self.pSprite).ink = 36
        S(self.pHiSprite).ink = 36
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pMember
        set_behavior(self.pSprite, self)

    def mSelect(self):
        S(self.pHiSprite).member = self.pHiMember

    def mDeSelect(self):
        S(self.pHiSprite).member = 1

    def mGetSelected(self):
        return S(self.pHiSprite).member == self.pHiMember

    def mSetMatch(self, theMember, theMatch):
        self.pMember = theMember
        self.pMatch = theMatch

    def mClearMatch(self):
        self.pMember = 1
        self.pMatch = 0

    def mGetMatch(self):
        return self.pMatch

    def mHide(self):
        blank(self.pSprite)
        blank(self.pHiSprite)

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName

    def mPlay(self):
        self.pLastUpdate = R().milliseconds()
        M.addUpdateList(self)

    def mStop(self):
        S(self.pHiSprite).member = 1
        M.removeUpdateList(self)

    def mKill(self):
        S(self.pHiSprite).member = 1
        M.removeUpdateList(self)

    def mUpdate(self):
        now = R().milliseconds()
        if (now - self.pLastUpdate) > self.pAnimSpeed:
            self.pLastUpdate = now
            if S(self.pHiSprite).member == self.pHiMember:
                S(self.pHiSprite).member = 1
            else:
                S(self.pHiSprite).member = self.pHiMember

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


# ============================================================================================
# BUTT_CC  (ParentScript 76)
# ============================================================================================

@lingo_script('BUTT_CC')
class ButtCC(LObject):
    def __init__(self):
        self.pEnabled = 1
        self.pLastUpdate = 0
        self.pMatch = 0
        self.pFound = 0
        self.pDecayTime = 0
        self.pStartTime = 0
        self.pHilight = 0
        self.pOldTimeLeft = 0
        self.pParent = 0
        self.pEventTag = None

    def mInit(self, theObjectData, theSpriteAlloc):
        self.pEnabled = 1
        self.pLastUpdate = 0
        self.pMatch = 0
        self.pFound = 0
        self.pDecayTime = 0
        self.pStartTime = 0
        self.pHilight = 0
        self.pOldTimeLeft = 0
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pHiSprite = pop_one(theSpriteAlloc)
        self.pMember = 1
        self.pSavedList = [Sym('pMember'), Sym('pMatch'), Sym('pDecayTime'), Sym('pFound'), Sym('pHilight')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mGetType(self):
        return Sym('BUTT_CC')

    def mouseDown(self):
        self.pParent.mButtonActivated(self)

    def mLoad(self):
        load_mem(self.pMember)
        load_mem(self.pHiMember)

    def mLoadList(self, theList):
        theList.append(self.pMember)
        theList.append(self.pHiMember)

    def mUnload(self):
        unload_mem(self.pMember)
        unload_mem(self.pHiMember)

    def mDisable(self):
        self.pEnabled = 0
        remove_behavior(self.pSprite, self)
        self.mSuspendDecay()

    def mEnable(self):
        self.pEnabled = 1
        set_behavior(self.pSprite, self)
        self.mResumeDecay()

    def mSuspendDecay(self):
        if (self.pOldTimeLeft == 0) and self.mGetSelected() and not self.mGetFound():
            self.pOldTimeLeft = self.pDecayTime - (R().milliseconds() - self.pStartTime)

    def mResumeDecay(self):
        if not self.mGetSelected():
            return
        self.pStartTime = R().milliseconds()
        if self.pOldTimeLeft != 0:
            self.pDecayTime = self.pOldTimeLeft
            self.pOldTimeLeft = 0

    def mShow(self):
        S(self.pSprite).ink = 36
        S(self.pHiSprite).ink = 36
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pMember
        set_behavior(self.pSprite, self)
        if self.pHilight:
            self.mSelect()

    def mSelect(self):
        S(self.pHiSprite).member = self.pHiMember
        self.pHilight = 1

    def mDeSelect(self):
        S(self.pHiSprite).member = 1
        self.pHilight = 0

    def mGetSelected(self):
        return self.pHilight

    def mSetMatch(self, theMember, theMatch):
        self.pMember = theMember
        self.pMatch = theMatch

    def mReset(self):
        self.pMember = 1
        self.pMatch = 0
        self.pFound = 0
        self.pHilight = 0
        self.pOldTimeLeft = 0

    def mGetMatch(self):
        return self.pMatch

    def mSetFound(self):
        self.pFound = 1

    def mGetFound(self):
        return self.pFound

    def mHide(self):
        blank(self.pSprite)
        blank(self.pHiSprite)

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName

    def mPlay(self):
        self.pStartTime = R().milliseconds()
        self.mResumeDecay()
        M.addUpdateList(self)

    def mStop(self):
        S(self.pHiSprite).member = 1
        self.pHilight = 0
        M.removeUpdateList(self)

    def mKill(self):
        self.pOldTimeLeft = 0
        M.removeUpdateList(self)

    def mUpdate(self):
        if (R().milliseconds() - self.pStartTime) >= self.pDecayTime:
            self.pOldTimeLeft = 0
            M.removeUpdateList(self)
            _done(self.pParent, self)

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


from . import riddle_screens  # noqa: E402,F401  (SCREEN_RIDDLE / SCREEN_RIDDLE_MAG)
