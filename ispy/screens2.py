"""Hand-ported parent scripts, part 3: drag & drop, slide / sprite-cell animation, rect hotspots,
name-in-letters, dissolve, play queue, the Secret Message painting screen and the help player.

    ParentScript  77  DRAG                 draggable sprite (follows the mouse until clicked / released)
    ParentScript  78  DRAG_N_DROP_SIMPLE   puzzle piece: pick up, drop, snap or slide back
    ParentScript  81  BUTT_SIMPLE_RECT     invisible rectangular hotspot on a shared sprite
    ParentScript 103  ANIM_SC              sprite-cell animation (list of members)
    ParentScript 105  ANIM_SLIDE           sine-eased slide of a sprite from A to B
    ParentScript 114  SIMPLE_NAME          player name spelled with one sprite per letter
    ParentScript 116  DISSOLVE_BLEND       blend sprites in / out
    ParentScript 118  PLAY_QUEUE           plays a list of objects one after another
    ParentScript  54  SCREEN_SMESSAGE      the Secret Message painting
    ParentScript 188  HELP_PLAYER          the contextual help (hand + voice-over) player

Same conventions as ui.py / game.py: one class per Lingo parent script, method and property names
unchanged, `S(chan)` is `sprite(chan)`, `R()` is the runtime, `_done(parent, obj)` is `mPlayDone(parent, obj)`.
"""
import math

from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, Point, Rect, set_properties, pop_one, pop_list
from .ui import (load_mem, unload_mem, load_object, unload_object, call_all, is_enabled,
                 set_behavior, remove_behavior, blank, _done)


def R():
    return runtime.rt


def S(chan):
    return runtime.rt.sprites[chan]


def _new(ref, *a):
    from .core import new_script
    return new_script(ref, *a)


# ============================================================================================
# small Lingo helpers that ui.py does not have
# ============================================================================================

def _alive(o):
    return isinstance(o, LObject)


def _nz(v):
    """`v <> 0` where v may also be VOID (None): a VOID / 0 value means 'not set'."""
    return v is not None and v != 0


def _integer(x):
    """Lingo integer(): rounds to nearest."""
    return int(math.floor(x + 0.5))


def _get_pos(lst, obj):
    """getPos(list, obj): 1-based index, 0 when absent (identity for objects)."""
    for i, o in enumerate(lst or []):
        if o is obj:
            return i + 1
    return 0


def _inside(pt, rect):
    """inside(point, rect)"""
    l, t, r, b = rect
    return l <= pt[0] < r and t <= pt[1] < b


def _get_dist(p):
    """getDist(point): length of a point treated as a vector."""
    return math.sqrt(p[0] * p[0] + p[1] * p[1])


def _loc_from_rect(rect):
    """getLocFromRect(rect): centre of the rect (integer maths, as in Lingo)."""
    l, t, r, b = rect
    return Point((r - l) // 2 + l, (b - t) // 2 + t)


def _sprite_rect(chan):
    """the rect of sprite chan, from the member's registration point and size."""
    s = S(chan)
    b = R().sprite_box(s)
    if not b:
        return (s.loc[0], s.loc[1], s.loc[0], s.loc[1])
    return (b[0], b[1], b[0] + b[2], b[1] + b[3])


def _rollover(chan):
    """rollover(chan): is the mouse over the sprite (matte / bg-transparent pixels do not count)."""
    rt = R()
    s = S(chan)
    b = rt.sprite_box(s)
    if not b:
        return False
    x, y = rt.mouse[0] - b[0], rt.mouse[1] - b[1]
    if 0 <= x < b[2] and 0 <= y < b[3]:
        img = b[4]
        if img is not None and s.ink in (8, 36) and img.get_at((int(x), int(y))).a == 0:
            return False
        return True
    return False


def _set_loc(chan, h, v):
    """set the locH / locV of sprite chan (Director stores integers)."""
    S(chan).loc = Point(int(round(h)), int(round(v)))


def add_behavior(chan, obj):
    """AddBehavior(sprite, obj): append to the scriptInstanceList unless already there."""
    s = S(chan)
    if not any(b is obj for b in s.behaviors):
        s.behaviors = list(s.behaviors) + [obj]


def get_mem_num(x):
    """getMemNum(): member *names* ("GL_HELPHAND_02") -> member numbers; numbers pass through."""
    if isinstance(x, (list, tuple)):
        return [get_mem_num(i) for i in x]
    if not isinstance(x, str) or x == '':
        return x if x is not None else 0
    rt = R()
    want = x.lower()
    import os
    folders = [(1, os.path.join(rt.exports_root, 'ISPYMAIN8'))]
    if rt.current_room:
        folders.append((3, os.path.join(rt.exports_root, rt.current_room.upper())))
    for cast, folder in folders:
        for n, nm in rt._index(folder)['name'].items():
            if nm.lower() == want:
                return n if cast == 1 else ((3 << 16) | n)
    print('[screens2] unknown member name:', x)
    return 0


def _T(t):
    """a #symbol type as an upper-case string for `case` comparisons."""
    return str(t).upper()


def _symeq(a, b):
    return str(a).lower() == str(b).lower()


class _HandHotspot:
    """Stand-in for `sprite(n).cursor = [33, 34]` (the pointing-hand cursor over a hotspot): attached
    to the stretched cursor sprite of a BUTT_SIMPLE_RECT, it only drives the mouse cursor."""

    def mouseEnter(self):
        if M.gCursor != 'wait':
            M.SetHandCursor()

    def mouseLeave(self):
        if M.gCursor != 'wait':
            M.resetCursor()


def _rect_cursor(chan, on):
    s = S(chan)
    mine = [b for b in s.behaviors if isinstance(b, _HandHotspot)]
    if on:
        if s.member and not mine:
            s.behaviors = list(s.behaviors) + [_HandHotspot()]
    elif mine:
        s.behaviors = [b for b in s.behaviors if not isinstance(b, _HandHotspot)]


# ============================================================================================
# DRAG  (ParentScript 77)
# ============================================================================================

@lingo_script('DRAG')
class Drag(LObject):
    def __init__(self, theDragMember=0, theParent=0, theRect=None):
        self.pDragMember = theDragMember
        self.pParent = theParent
        self.pInk = 36
        self.pLoc = Point(320, 240)
        self.pStartLoc = Point(320, 240)
        self.pSprite = M.getDragSprite()
        self.pPlayTime = 0
        self.pClickCount = 0
        self.pMouseDownMode = 0
        self.pDragOffset = Point(0, 0)
        self.pMouseOffset = 0
        if isinstance(theRect, (tuple, list)) and len(theRect) == 4:
            self.pConstrainRect = theRect
        else:
            self.pConstrainRect = Rect(0, 0, 640, 480)

    def mInit(self, *a):
        return self

    def mDestroy(self):
        pass

    def mShow(self):
        S(self.pSprite).ink = self.pInk
        S(self.pSprite).member = self.pDragMember

    def mHide(self):
        self.pDragOffset = Point(0, 0)
        S(self.pSprite).member = 1

    def mPlay(self):
        self.pPlayTime = R().milliseconds()
        self.pMouseDownMode = 1
        self.pClickCount = 0
        M.SetGrabCursor()
        set_behavior(self.pSprite, self)
        M.addUpdateList(self)
        self.mUpdate()          # place the piece under the pointer at once (Director redraws after the handler)

    def mStop(self):
        remove_behavior(self.pSprite, self)
        M.removeUpdateList(self)
        _done(self.pParent, self)

    def mUpdate(self):
        mouse = R().mouse
        daNewPos = mouse + self.pDragOffset
        rc = self.pConstrainRect
        if _inside(daNewPos, rc):
            S(self.pSprite).loc = daNewPos
        else:
            h, v = daNewPos[0], daNewPos[1]
            if mouse[0] < rc[0]:
                h = rc[0]
            elif mouse[0] > rc[2]:
                h = rc[2]
            if mouse[1] < rc[1]:
                v = rc[1]
            elif mouse[1] > rc[3]:
                v = rc[3]
            S(self.pSprite).loc = Point(h, v)

    def mouseDown(self):
        if not self.pMouseDownMode:
            self.mStop()

    def mouseUp(self):
        if not self.pClickCount and (self.pPlayTime > (R().milliseconds() - 250)):
            self.pMouseDownMode = 0
        else:
            self.mStop()
        self.pClickCount += 1


# ============================================================================================
# ANIM_SLIDE  (ParentScript 105)
# ============================================================================================

@lingo_script('ANIM_SLIDE')
class AnimSlide(LObject):
    def __init__(self, theParent=None, daSprite=None):
        self.pParent = theParent
        self.pSprite = M.getDragSprite() if daSprite is None else daSprite
        self.pPixelsPerSecond = 400
        self.pLastUpdate = 0
        self.pSrcH = 0
        self.pSrcV = 0
        self.pFPS = 30
        self.pHDist = 0
        self.pVDist = 0
        self.pSinCounter = 0
        self.pDistanceTimer = 2400
        self.pInk = 0
        self.pMember = 0
        self.pStartLoc = 0
        self.pStopLoc = 0
        self.pSound = 0
        self.pSoundChannel = 1
        self.pName = None
        self.pEventTag = None

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        return self

    def mDestroy(self):
        pass

    def mSetReturnLoc(self, theReturnLoc):
        self.pStopLoc = theReturnLoc

    def mSetMember(self, theMember):
        self.pMember = get_mem_num(theMember)

    def mSetStartLoc(self, theLoc):
        self.pStartLoc = theLoc

    def mSetPixelsPerSecond(self, daPPS):
        self.pPixelsPerSecond = daPPS

    def mSetDistanceTimer(self, daDT):
        self.pDistanceTimer = daDT

    def mShow(self):
        S(self.pSprite).member = self.pMember
        S(self.pSprite).loc = self.pStartLoc
        S(self.pSprite).ink = self.pInk

    def mHide(self):
        S(self.pSprite).member = 1

    def mPlay(self):
        if self.pSound:
            R().sound.puppet(self.pSoundChannel or 1, self.pSound)
        loc = S(self.pSprite).loc
        self.pSrcH = loc[0]
        self.pSrcV = loc[1]
        self.pCurrH = loc[0]
        self.pCurrV = loc[1]
        self.pHDist = self.pStopLoc[0] - loc[0]
        self.pVDist = self.pStopLoc[1] - loc[1]
        daDist = _get_dist(loc - self.pStopLoc) * 1.0
        if daDist == 0:
            _done(self.pParent, self)
            return
        self.pIncrement = self.pDistanceTimer / daDist
        daTotalUpdates = daDist / self.pPixelsPerSecond * self.pFPS
        self.pStepHDist = self.pHDist / daTotalUpdates * 1.0
        self.pStepVDist = self.pVDist / daTotalUpdates * 1.0
        self.pStepDist = _get_dist(Point(self.pStepHDist, self.pStepVDist))
        self.pSinCounter = -90
        self.pLastUpdate = R().milliseconds() - (1000 // self.pFPS)
        M.addUpdateList(self)

    def mStop(self):
        M.removeUpdateList(self)

    def mUpdate(self):
        now = R().milliseconds()
        if (now - self.pLastUpdate) >= (1000 // self.pFPS):
            self.pLastUpdate = now
            if self.pSinCounter >= 90:
                S(self.pSprite).loc = self.pStopLoc
                M.removeUpdateList(self)
                _done(self.pParent, self)
            else:
                radians = math.pi / 180 * self.pSinCounter
                ratio = 1 + math.sin(radians)
                ratio = ratio * 0.5
                self.pCurrH = self.pSrcH + (ratio * self.pHDist)
                self.pCurrV = self.pSrcV + (ratio * self.pVDist)
                _set_loc(self.pSprite, self.pCurrH, self.pCurrV)
            self.pSinCounter = self.pSinCounter + self.pIncrement

    def mLoad(self):
        load_mem(self.pSound)
        load_mem(self.pMember)

    def mLoadList(self, theList):
        theList.append(self.pSound)
        theList.append(self.pMember)

    def mUnload(self):
        unload_mem(self.pSound)
        unload_mem(self.pMember)

    def mGetType(self):
        return Sym('ANIM_MOVE')

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag

    def mSetInk(self, theInk):
        self.pInk = theInk


# ============================================================================================
# DRAG_N_DROP_SIMPLE  (ParentScript 78)
# ============================================================================================

@lingo_script('DRAG_N_DROP_SIMPLE')
class DragNDropSimple(LObject):
    def __init__(self):
        self.pType = None
        self.pName = None
        self.pSprite = 0
        self.pTokenName = None
        self.pDropRect = 0
        self.pMember = 0
        self.pDragMember = 0
        self.pPlacedMember = 0
        self.pDropped = 0
        self.pPickupSound = 0
        self.pDropSound = 0
        self.pDragObject = 0
        self.pDropObject = 0
        self.pDownTime = 0
        self.pBackMember = 0
        self.pBackSprite = 0
        self.pBGSCmember = 0
        self.pBGSCSprite = 0
        self.pDragReturnLoc = 0
        self.pParent = 0
        self.pInk = 0
        self.pSnapPoint = 0
        self.pSnapDist = 0
        self.pSnapSprite = 0
        self.pStartLoc = 0
        self.pLoc = Point(320, 240)
        self.pEventTag = None

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        if self.pMember == 0:
            self.pMember = self.pDragMember
        self.pBGSCSprite = pop_one(theSpriteAlloc)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pLoc = Point(320, 240)
        self.pDropped = 0
        self.pDownTime = 0
        self.pDragObject = _new(self.pDragScriptNumber, self.pDragMember, self)
        self.pDropObject = _new(self.pAnimSlideScriptNumber, self)
        self.pDragReturnLoc = self.pStartLoc
        self.pSavedList = [Sym(n) for n in ('pDropped', 'pMember', 'pDragMember', 'pBackMember',
                                            'pDropRect', 'pSprite')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mLoad(self):
        load_mem(self.pBackMember)
        load_mem(self.pPlacedMember)
        load_mem(self.pBGSCmember)
        if not self.pDropped:
            load_mem(self.pPickupSound)
            load_mem(self.pDropSound)
            load_mem(self.pDragMember)
            load_mem(self.pMember)
        else:
            if self.pMember == self.pDragMember:
                load_mem(self.pDragMember)
            else:
                load_mem(self.pMember)

    def mLoadList(self, theList):
        theList.append(self.pBackMember)
        theList.append(self.pBGSCmember)
        if not self.pDropped:
            theList.append(self.pPickupSound)
            theList.append(self.pDropSound)
            theList.append(self.pDragMember)
            theList.append(self.pPlacedMember)
            if self.pMember != self.pDragMember:
                theList.append(self.pMember)
        else:
            if self.pMember == self.pDragMember:
                theList.append(self.pDragMember)
            else:
                theList.append(self.pMember)
            theList.append(self.pPlacedMember)

    def mUnload(self):
        unload_mem(self.pPickupSound)
        unload_mem(self.pDropSound)
        unload_mem(self.pBackMember)
        unload_mem(self.pDragMember)
        unload_mem(self.pMember)
        unload_mem(self.pPlacedMember)

    def mSetBackSprite(self, theSpriteAlloc):
        self.pBackSprite = pop_one(theSpriteAlloc)

    def mGetType(self):
        return Sym('DRAG_N_DROP_SIMPLE')

    def mGetName(self):
        return self.pName

    def mGetTokenName(self):
        return self.pTokenName

    def mSetDropRect(self, daRect):
        self.pDropRect = daRect

    def mSetDragMember(self, daDragMemberList):
        daSimpleMode = 1 if self.pMember == self.pDragMember else 0
        self.pDragMember = daDragMemberList[0]
        self.pDragObject.pDragMember = daDragMemberList[0]
        if daSimpleMode:
            self.pMember = daDragMemberList[0]
        else:
            self.pMember = daDragMemberList[1]
            self.pBackMember = daDragMemberList[2]

    def mGetSnapped(self):
        return self.pDropped

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mShow(self):
        if not self.pDropped:
            S(self.pBackSprite).member = self.pBackMember
            S(self.pBackSprite).ink = self.pInk
            S(self.pBackSprite).loc = self.pLoc
            S(self.pSprite).member = self.pMember
            S(self.pSprite).ink = self.pInk
            if self.pMember == self.pDragMember:
                S(self.pSprite).loc = self.pStartLoc
            else:
                S(self.pSprite).loc = self.pLoc
            set_behavior(self.pSprite, self)
        else:
            S(self.pBGSCSprite).member = self.pBGSCmember
            S(self.pBGSCSprite).ink = self.pInk
            S(self.pBGSCSprite).loc = Point(320, 240)
            if _nz(self.pSnapPoint):
                S(self.pSprite).loc = self.pSnapPoint
            else:
                S(self.pSprite).loc = self.pStartLoc
            if self.pPlacedMember:
                S(self.pSprite).member = self.pPlacedMember
                S(self.pSprite).loc = Point(320, 240)
            else:
                S(self.pSprite).member = self.pMember
            S(self.pSprite).ink = self.pInk

    def mHide(self):
        S(self.pBGSCSprite).member = self.pBGSCmember
        S(self.pBGSCSprite).ink = self.pInk
        S(self.pBGSCSprite).loc = Point(320, 240)
        blank(self.pBackSprite)
        blank(self.pSprite)
        remove_behavior(self.pSprite, self)

    def mEnable(self):
        if not is_enabled(self.pSprite, self) and not self.pDropped:
            if _rollover(self.pSprite):
                M.setOpenhandCursor()
            set_behavior(self.pSprite, self)

    def mDisable(self):
        if is_enabled(self.pSprite, self):
            remove_behavior(self.pSprite, self)

    def mChangeSprite(self, newSprite):
        blank(self.pSprite)
        self.pSprite = newSprite
        S(self.pSprite).member = self.pMember
        S(self.pSprite).ink = self.pInk
        S(self.pSprite).loc = self.pSnapPoint

    def mouseEnter(self):
        M.setOpenhandCursor()

    def mouseLeave(self):
        if S(self.pSprite).member == self.pMember:
            M.resetCursor()

    def mouseDown(self):
        if _rollover(self.pSprite):
            rt = R()
            daMouseLoc = rt.mouse
            if self.pBackMember:
                self.pDragReturnLoc = _loc_from_rect(_sprite_rect(self.pBackSprite))
            else:
                self.pDragReturnLoc = _loc_from_rect(_sprite_rect(self.pSprite))
            daDragOffset = self.pDragReturnLoc - daMouseLoc
            S(self.pBackSprite).member = 1
            S(self.pSprite).member = self.pDragMember
            daholdLoc = S(self.pSprite).loc
            S(self.pSprite).loc = rt.mouse + daDragOffset
            # updateStage()
            if (not _inside(rt.mouse, _sprite_rect(self.pSprite))) or \
                    ((self.pDragMember != self.pMember) and not self.pBackMember):
                daDragOffset = Point(0, 0)
            S(self.pSprite).loc = daholdLoc
            S(self.pSprite).member = 1
            S(self.pBGSCSprite).member = self.pBGSCmember
            S(self.pBGSCSprite).ink = self.pInk
            S(self.pBGSCSprite).loc = Point(320, 240)
            self.pDragObject.pDragMember = self.pDragMember
            self.pDragObject.pDragOffset = daDragOffset
            self.pDragObject.mShow()
            rt.sound.puppet(1, self.pPickupSound)
            self.pDragObject.mPlay()
            M.disableGame()

    def mPlay(self):
        if not self.pDropped:
            pass
        else:
            _done(self.pParent, self)

    def mouseUp(self):
        # Lingo: empty.  The port's mouse dispatcher can deliver the release to the pressed (now blank)
        # sprite instead of the drag sprite; hand it on so a drag always ends.
        self._release_drag()

    def mouseUpOutSide(self):
        self._release_drag()

    def _release_drag(self):
        d = self.pDragObject
        if _alive(d) and is_enabled(d.pSprite, d):
            d.mouseUp()

    def mPlayDone(self, theObject):
        if theObject is self.pDropObject:
            self.pDropObject.mHide()
            S(self.pBackSprite).member = self.pBackMember
            if self.pDropped and self.pPlacedMember:
                S(self.pSprite).member = self.pPlacedMember
                S(self.pSprite).loc = Point(320, 240)
            else:
                S(self.pSprite).member = self.pMember
            S(self.pBGSCSprite).member = 1
            _done(self.pParent, self)
        else:
            if self.pDropRect is not None and self.pDropRect != 0:
                if _inside(S(theObject.pSprite).loc, self.pDropRect):
                    self.mSnapIt()
                else:
                    self.DropIt()
            else:
                if _nz(self.pSnapPoint):
                    daDist = _get_dist(S(self.pDragObject.pSprite).loc - self.pSnapPoint)
                    if daDist <= self.pSnapDist:
                        self.mSnapIt()
                    else:
                        self.DropIt()
                else:
                    self.DropIt()

    def mSnapIt(self):
        self.pDropped = 1
        if _nz(self.pSnapPoint):
            self.pDropObject.mSetReturnLoc(self.pSnapPoint)
            M.resetCursor()
            self.pDropObject.mPlay()
        else:
            self.pDragObject.mHide()
            M.resetCursor()
            _done(self.pParent, self)

    def DropIt(self):
        R().sound.puppet(1, self.pDropSound)
        self.pDropObject.mSetReturnLoc(self.pDragReturnLoc)
        self.pDropObject.mPlay()
        M.resetCursor()

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


# ============================================================================================
# BUTT_SIMPLE_RECT  (ParentScript 81)
# ============================================================================================

@lingo_script('BUTT_SIMPLE_RECT')
class ButtSimpleRect(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pInk = 0
        self.pLoc = Point(320, 240)
        self.pSprite = 0
        self.pMember = 0
        self.pParent = 0
        self.prect = Rect(0, 0, 0, 0)
        self.pcursorSprite = 0
        self.pCursorMem = 0
        self.pEnabled = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pcursorSprite = pop_one(theSpriteAlloc)
        self.pEnabled = 1
        return self

    def mDestroy(self):
        pass

    def mGetType(self):
        return Sym('BUTT_SIMPLE_RECT')

    def mouseDown(self):
        if _inside(R().mouse, self.prect):
            if self.pParent:
                self.pParent.mButtonActivated(self)
            # flush()  (flushInputEvents) -- nothing queued in the port

    def mLoad(self):
        load_mem(self.pMember)

    def mLoadList(self, theList):
        theList.append(self.pMember)
        theList.append(self.pCursorMem)

    def mUnload(self):
        unload_mem(self.pMember)
        unload_mem(self.pCursorMem)

    def mDisable(self):
        self.pEnabled = 0
        remove_behavior(self.pSprite, self)

    def mEnable(self):
        self.pEnabled = 1
        add_behavior(self.pSprite, self)

    def mShow(self):
        S(self.pcursorSprite).stretch_rect = self.prect      # stretch = 1; rect = prect
        S(self.pcursorSprite).member = self.pCursorMem
        self.mEnable()

    def mHide(self):
        blank(self.pcursorSprite)
        self.mDisable()

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName


# ============================================================================================
# ANIM_SC  (ParentScript 103)
# ============================================================================================

@lingo_script('ANIM_SC')
class AnimSC(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pPlayed = 0
        self.pAnimSound = 0
        self.pLastUpdate = 0
        self.pSpeed = 10
        self.pStep = 0
        self.pAnimMembers = []
        self.pInk = 0
        self.pLoc = Point(320, 240)
        self.pSprite = 0
        self.pMember = None
        self.pParent = 0
        self.pEventTag = None

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pSprite = pop_one(theSpriteAlloc)
        self.pPlayed = 0
        self.pLastUpdate = 0
        self.pSpeed = 1000 // self.pSpeed
        self.pStep = 0
        self.pLoc = Point(320, 240)
        if self.pMember is None:
            self.pMember = self.pAnimMembers[0]
        self.pSavedList = [Sym('pPlayed'), Sym('pMember')]
        M.addObjectGlob(self)
        return self

    def mDestroy(self):
        pass

    def mLoad(self):
        load_mem(self.pMember)
        if not self.pPlayed:
            load_mem(self.pAnimSound)
            load_mem(self.pAnimMembers)

    def mLoadList(self, theList):
        theList.append(self.pMember)
        if not self.pPlayed:
            theList.append(self.pAnimSound)
            theList.extend(self.pAnimMembers)

    def mUnload(self):
        unload_mem(self.pAnimSound)
        unload_mem(self.pMember)
        unload_mem(self.pAnimMembers)

    def mGetName(self):
        return self.pName

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetType(self):
        return Sym('ANIM_SC')

    def mShow(self):
        S(self.pSprite).ink = self.pInk
        S(self.pSprite).loc = self.pLoc
        S(self.pSprite).member = self.pMember

    def mHide(self):
        blank(self.pSprite)

    def mouseDown(self):
        if self.pParent:
            self.pParent.mButtonActivated(self)

    def mPlay(self):
        if not self.pPlayed:
            self.pPlayed = 1
            R().sound.puppet(1, self.pAnimSound)
            remove_behavior(self.pSprite)
            self.pLastUpdate = R().milliseconds() - self.pSpeed
            M.addUpdateList(self)
        else:
            _done(self.pParent, self)

    def mStop(self):
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
                self.pMember = self.pAnimMembers[n - 1]
                self.mStop()
                _done(self.pParent, self)

    def mDisable(self):
        remove_behavior(self.pSprite)

    def mEnable(self):
        set_behavior(self.pSprite, self)

    def mKill(self):
        self.mStop()

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


# ============================================================================================
# SIMPLE_NAME  (ParentScript 114)
# ============================================================================================

@lingo_script('SIMPLE_NAME')
class SimpleName(LObject):
    def __init__(self):
        self.pType = None
        self.pSavedList = []
        self.pEnabled = 1
        self.pName = None
        self.pParent = 0
        self.pFirstCharMem = 0
        self.pSpriteList = []
        self.pNameLocs = []
        self.pCommaFlag = 0
        self.pNameString = ''
        self.pNameList = []
        self.pCharHash = {}
        self.pSpriteCount = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pNameString = ''
        self.pNameList = []
        self.pEnabled = 1
        self.pSpriteList = pop_list(theSpriteAlloc, self.pSpriteCount)
        self.pSavedList = []
        return self

    def mSetNameString(self, theString):
        self.pNameString = theString
        self.pNameList = []
        daSize = min(len(theString), len(self.pSpriteList))
        for i in range(daSize):
            daNameChar = ord(theString[i])
            # the converter keeps propList keys as strings ("65"); Lingo looked them up as integers
            daMember = self.pCharHash.get(daNameChar)
            if daMember is None:
                daMember = self.pCharHash.get(str(daNameChar))
            if daMember is not None:
                self.pNameList.append(daMember)

    def mGetNameString(self):
        return self.pNameString

    def mGetType(self):
        return Sym('SIMPLE_NAME')

    def mDestroy(self):
        pass

    def mShow(self):
        for i in range(len(self.pNameList)):
            S(self.pSpriteList[i]).member = self.pNameList[i]
            S(self.pSpriteList[i]).loc = self.pNameLocs[i]
            S(self.pSpriteList[i]).ink = 36

    def mLoad(self):
        for daMember in self.pNameList:
            load_mem(daMember)

    def mLoadList(self, theList):
        for daMember in self.pNameList:
            theList.append(daMember)

    def mUnload(self):
        for daMember in self.pNameList:
            unload_mem(daMember)

    def mHide(self):
        for chan in self.pSpriteList:
            blank(chan)

    def mSetBehavior(self):
        pass

    def mMove(self, theOffset):
        pass

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetName(self):
        return self.pName


# ============================================================================================
# DISSOLVE_BLEND  (ParentScript 116)
# ============================================================================================

@lingo_script('DISSOLVE_BLEND')
class DissolveBlend(LObject):
    def __init__(self, daParent=None):
        self.pName = None
        self.pParent = daParent
        self.pSpriteList = []
        self.pTotalSteps = 1
        self.pDissolveRate = 1
        self.pLastUpdate = 0
        self.pUpdateInterval = 0
        self.pStep = 1
        self.pIsDissolveIn = 1
        self.pEventTag = None

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pUpdateInterval = self.pDissolveRate * 1000 / self.pTotalSteps
        self.pStep = 1
        return self

    def mDestroy(self):
        pass

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mLoad(self):
        pass

    def mLoadList(self, theList=None):
        pass

    def mUnload(self):
        pass

    def mGetType(self):
        return Sym('DISSOLVE_BLEND')

    def mGetName(self):
        return self.pName

    def mPlay(self):
        self.pLastUpdate = R().milliseconds()
        if self.pIsDissolveIn:
            self.mSetBlend(0)
        else:
            self.mSetBlend(100)
        M.addUpdateList(self)
        self.pStep = 1

    def mStop(self):
        if self.pIsDissolveIn:
            self.mSetBlend(100)
        else:
            self.mSetBlend(0)
        M.removeUpdateList(self)
        _done(self.pParent, self)

    def mUpdate(self):
        if (R().milliseconds() - self.pLastUpdate) >= self.pUpdateInterval:
            self.pLastUpdate = R().milliseconds()
            frac = 100.0 * float(self.pStep) / float(self.pTotalSteps)
            if self.pIsDissolveIn:
                self.mSetBlend(_integer(frac))
            else:
                self.mSetBlend(100 - _integer(frac))
            if self.pStep == self.pTotalSteps:
                self.mStop()
                return
            self.pStep += 1

    def mSetBlend(self, daBlend):
        for chan in self.pSpriteList:
            S(chan).blend = daBlend

    def mSetBlendDissolve(self, daSpriteList, daDissolveRate, daTotalSteps, daIsDissolveIn):
        self.pSpriteList = daSpriteList
        self.pDissolveRate = daDissolveRate
        self.pTotalSteps = daTotalSteps
        self.pUpdateInterval = self.pDissolveRate * 1000 / self.pTotalSteps
        self.pIsDissolveIn = daIsDissolveIn

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


# ============================================================================================
# PLAY_QUEUE  (ParentScript 118)
# ============================================================================================

@lingo_script('PLAY_QUEUE')
class PlayQueue(LObject):
    def __init__(self):
        self.pType = None
        self.pObjectList = []
        self.pFlushCount = 0
        self.pParent = 0
        self.pIndex = 0
        self.pCurrentObject = None
        self.pOriginalParentList = {}      # propList keyed by object -> its original pParent
        self.pEventTag = None

    def mInit(self, theObjectData=None, theSpriteAlloc=None):
        return self

    def mDestroy(self):
        pass

    def mRecycle(self):
        self.pObjectList = []
        self.pParent = 0

    def mPlay(self):
        if isinstance(self.pObjectList, list):
            call_all(self.pObjectList, 'mSetParent', self)
            self.pIndex = 1
            self.pCurrentObject = self.pObjectList[self.pIndex - 1]
            self.pCurrentObject.mSetParent(self)
            self.pCurrentObject.mPlay()

    def mPlayDone(self, theObject):
        if self.pIndex < len(self.pObjectList):
            self.pIndex += 1
            self.pCurrentObject = self.pObjectList[self.pIndex - 1]
            self.pCurrentObject.mPlay()
        else:
            self.pIndex = 0
            for daObject in list(self.pObjectList):
                daObject.pParent = self.pOriginalParentList.get(daObject, 0)
            self.pOriginalParentList.clear()
            _done(self.pParent, self)

    def mStop(self):
        if _alive(self.pCurrentObject):
            del self.pObjectList[:]
            self.pCurrentObject.mStop()

    def mGetObjectFromStack(self, thePosition):
        if thePosition < len(self.pObjectList):
            return self.pObjectList[thePosition - 1]
        return 0

    def mContainsObject(self, theObject):
        return _get_pos(self.pObjectList, theObject)

    def mGetType(self):
        return Sym('PLAY_QUEUE')

    def mAddItem(self, theObject):
        self.pOriginalParentList[theObject] = theObject.pParent
        self.pObjectList.append(theObject)

    def mUpdate(self):
        pass

    def mSetEventTag(self, daEvent):
        self.pEventTag = daEvent

    def mGetEventTag(self):
        return self.pEventTag


# ============================================================================================
# SCREEN_SMESSAGE  (ParentScript 54)
# ============================================================================================

@lingo_script('SCREEN_SMESSAGE')
class ScreenSMessage(LObject):
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
        self.pSimpleNameObj = 0
        self.pEnabled = 0
        self.pSnapSpriteList = []
        self.pPuzzPieceObjectList = []
        self.pHintButtonList = []
        self.pHintAudioList = []
        self.pSnapSound = 0
        self.pMessageSprite = 0
        self.pMessageMemList = []
        self.pMessageAnimObject = 0
        self.pFirstTimeFlag = 1
        self.pPlayMessageFlag = 0
        self.pMessageMusic = 0
        self.pQueObject = 0
        self.pDissolveBlendObject = 0
        self.pSolvedSessionCount = 0

    # ---- init ---------------------------------------------------------------------------------
    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pMessage1CurSprite = pop_one(theSpriteAlloc)
        self.pMessage2CurSprite = pop_one(theSpriteAlloc)
        self.pMessage3CurSprite = pop_one(theSpriteAlloc)
        self.pBackSprite = pop_one(theSpriteAlloc)
        # the data lists are shared with the decoded handler data; this one is rewritten in place later
        self.pHintAudioList = list(self.pHintAudioList or [])
        self.pHintButtonList = get_object_list(self.pHintButtonList, theSpriteAlloc)
        call_all(self.pHintButtonList, 'mSetParent', self)
        self.pSnapSpriteList = pop_list(theSpriteAlloc, 15)
        self.pPuzzPieceObjectList = get_object_list(self.pPuzzPieceObjectList, theSpriteAlloc)
        call_all(self.pPuzzPieceObjectList, 'mSetParent', self)
        self.pMessageSprite = pop_one(theSpriteAlloc)
        blank(self.pMessageSprite)
        self.pMessageAnimObject = get_object(self.pMessageAnimObject, [self.pMessageSprite])
        self.pMessageAnimObject.mSetParent(self)
        self.pSimpleNameObj = get_object(self.pSimpleNameObj, theSpriteAlloc)
        self.pSimpleNameObj.mSetParent(self)
        self.pSimpleNameObj.mSetNameString(M.gPlayer + ',')
        self.pHandSprite = pop_one(theSpriteAlloc)
        for n in ('pHand1On', 'pHand1Off', 'pHand2On', 'pHand2Off', 'pHand3On', 'pHand3Off'):
            o = get_object(getattr(self, n), [self.pHandSprite])
            setattr(self, n, o)
            o.mSetParent(self)
        self.pMessage1Rect = get_object(self.pMessage1Rect, [self.pMessageSprite, self.pMessage1CurSprite])
        self.pMessage1Rect.mSetParent(self)
        self.pMessage2Rect = get_object(self.pMessage2Rect, [self.pMessageSprite, self.pMessage2CurSprite])
        self.pMessage2Rect.mSetParent(self)
        self.pMessage3Rect = get_object(self.pMessage3Rect, [self.pMessageSprite, self.pMessage3CurSprite])
        self.pMessage3Rect.mSetParent(self)
        self.pTimerObject = get_object(self.pTimerObject, [])
        self.pTimerObject.mSetParent(self)
        self.pEnabled = 1
        self.pFirstTimeFlag = 1
        self.pPlayMessageFlag = 0
        self.pQueObject = 0
        self.pSolvedSessionCount = 0
        self.pSavedList = [Sym('pFirstTimeFlag')]
        M.addObjectGlob(self)
        return self

    def mInitPoolObjects(self):
        self.pSnapSound = M.getSoundObject(1, self.pSnapSound, self)
        self.pMessageMusic = M.getSoundObject(1, self.pMessageMusic, self)
        for i in range(len(self.pHintAudioList)):
            self.pHintAudioList[i] = M.getExSoundObject(2, self.pHintAudioList[i], self)
        self.pFirstTimeAudio = M.getExSoundObject(2, self.pFirstTimeAudio, self)
        self.p1PieceNotInAudio = M.getExSoundObject(2, self.p1PieceNotInAudio, self)
        self.pMoreN1PieceNotInAudio = M.getExSoundObject(2, self.pMoreN1PieceNotInAudio, self)
        self.pGotThatOneAudio = M.getExSoundObject(2, self.pGotThatOneAudio, self)
        self.pMessageAudio1 = M.getExSoundObject(2, self.pMessageAudio1, self)
        self.pMessageAudio2 = M.getExSoundObject(2, self.pMessageAudio2, self)
        self.pMessageAudio3 = M.getExSoundObject(2, self.pMessageAudio3, self)
        self.pFirstTimeLoosePieceAudio = M.getExSoundObject(2, self.pFirstTimeLoosePieceAudio, self)

    def mReleasePoolObjects(self):
        self.pSnapSound = M.recycleSoundObject(self.pSnapSound)
        self.pMessageMusic = M.recycleSoundObject(self.pMessageMusic)
        for i in range(len(self.pHintAudioList)):
            self.pHintAudioList[i] = M.recycleSoundObject(self.pHintAudioList[i])
        self.pFirstTimeAudio = M.recycleSoundObject(self.pFirstTimeAudio)
        self.p1PieceNotInAudio = M.recycleSoundObject(self.p1PieceNotInAudio)
        self.pMoreN1PieceNotInAudio = M.recycleSoundObject(self.pMoreN1PieceNotInAudio)
        self.pGotThatOneAudio = M.recycleSoundObject(self.pGotThatOneAudio)
        self.pMessageAudio1 = M.recycleSoundObject(self.pMessageAudio1)
        self.pMessageAudio2 = M.recycleSoundObject(self.pMessageAudio2)
        self.pMessageAudio3 = M.recycleSoundObject(self.pMessageAudio3)
        self.pDissolveBlendObject = 0
        self.pQueObject = 0
        self.pFirstTimeLoosePieceAudio = M.recycleSoundObject(self.pFirstTimeLoosePieceAudio)

    def mDestroy(self):
        pass

    def mGetEnabled(self):
        return self.pEnabled

    def mLoad(self):
        pass

    def mLoadList(self, theList):
        theList.append(self.pAmbientAudio)
        theList.append(self.pBackMember)
        level = M.gScreenDaddy.mGetLevel()
        if level == 1:
            call_all(self.pHintButtonList, 'mLoadList', theList)
            theList.append(self.pSnapSound)
            self.mLoadPuzzPieces(theList)
        elif level == 2:
            theList.append(self.pMessageMemList[3])
            self.pSimpleNameObj.mLoadList(theList)
            for n in ('pHand1On', 'pHand1Off', 'pHand2On', 'pHand2Off', 'pHand3On', 'pHand3Off'):
                getattr(self, n).mLoadList(theList)

    def mUnload(self):
        unload_mem(self.pSnapSound)
        unload_mem(self.pMessageMusic)
        unload_mem(self.pBackMember)
        # call(#unload, pPuzzPieceObjectList) / call(#unload, pHintButtonList): no such handler -> no-ops
        unload_mem(self.pSnapSound)
        unload_mem(self.pMessageAnimObject)
        unload_mem(self.pSimpleNameObj)
        for n in ('pHand1On', 'pHand1Off', 'pHand2On', 'pHand2Off', 'pHand3On', 'pHand3Off'):
            unload_mem(getattr(self, n))

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    def mHuntObjectFound(self, theObject):
        pass

    # ---- show / hide --------------------------------------------------------------------------
    def mShow(self):
        sd = M.gScreenDaddy
        M.FadeInAmbientSound(self.pAmbientAudio)
        self.pHelpButton = M.getGameHelpButton()
        self.pBackButton = M.getGameBackButton()
        self.pHelpButton.mSetParent(self)
        self.pBackButton.mSetParent(self)
        self.pHelpButton.mShow()
        self.pBackButton.mShow()
        S(self.pBackSprite).member = self.pBackMember
        level = sd.mGetLevel()
        if level == 1:
            self.mShowHintButts()
            self.mShowPieces()
        elif level == 2:
            S(self.pMessageSprite).member = self.pMessageMemList[3]
            S(self.pMessageSprite).ink = 8
            self.pSimpleNameObj.mShow()
            self.pMessage1Rect.mShow()
            self.pMessage2Rect.mShow()
            self.pMessage3Rect.mShow()
            _rect_cursor(self.pMessage1CurSprite, True)
            _rect_cursor(self.pMessage2CurSprite, True)
            _rect_cursor(self.pMessage3CurSprite, True)
        self.pPlayMessageFlag = 0
        self.pEnabled = 1
        piecesLoose = self.mGetloosePieceCount()
        if self.pFirstTimeFlag and not sd.mAllTokensFound():
            self.pFirstTimeFlag = 0
            sd.mDisable()
            if piecesLoose:
                self.pFirstTimeLoosePieceAudio.mPlay()
            else:
                self.pFirstTimeAudio.mPlay()
        else:
            if piecesLoose:
                self.pFirstTimeFlag = 0
                M.resetCursor()
                if piecesLoose == 1:
                    M.setInterruptMode(self.p1PieceNotInAudio)
                    self.p1PieceNotInAudio.mPlay()
                else:
                    M.setInterruptMode(self.pMoreN1PieceNotInAudio)
                    self.pMoreN1PieceNotInAudio.mPlay()
            else:
                if not sd.mEnableReminders():
                    M.resetCursor()

    def mHide(self):
        blank(self.pBackSprite)
        blank(self.pMessageSprite)
        if _alive(self.pBackButton):
            self.pBackButton.mHide()
        if _alive(self.pHelpButton):
            self.pHelpButton.mHide()
        # call(#hide, pHintButtonList, me) / call(#hide, pPuzzPieceObjectList, me): no such handler -> no-ops
        self.pSimpleNameObj.mHide()
        self.pMessage1Rect.mHide()
        self.pMessage2Rect.mHide()
        self.pMessage3Rect.mHide()
        _rect_cursor(self.pMessage1CurSprite, False)
        _rect_cursor(self.pMessage2CurSprite, False)
        _rect_cursor(self.pMessage3CurSprite, False)
        self.pQueObject = 0
        self.pEnabled = 0

    def mLoadPuzzPieces(self, theList):
        sd = M.gScreenDaddy
        if sd.mGetLevel() == 1:
            for daPuzz in self.pPuzzPieceObjectList:
                if sd.mTokenFound(daPuzz.pTokenName):
                    daPuzz.mLoadList(theList)

    def mShowPieces(self):
        sd = M.gScreenDaddy
        if sd.mGetLevel() == 1:
            for daPuzz in self.pPuzzPieceObjectList:
                if sd.mTokenFound(daPuzz.pTokenName):
                    daPuzz.mShow()

    def mGetloosePieceCount(self):
        sd = M.gScreenDaddy
        loosepiececount = 0
        for daPuzz in self.pPuzzPieceObjectList:
            if sd.mTokenFound(daPuzz.pTokenName):
                if not daPuzz.mGetSnapped():
                    loosepiececount += 1
        return loosepiececount

    def mShowHintButts(self):
        if M.gScreenDaddy.mGetLevel() == 1:
            for i in range(len(self.pHintButtonList)):
                if not self.pPuzzPieceObjectList[i].mGetSnapped():
                    self.pHintButtonList[i].mShow()

    def mShowMessage(self):
        self.pMessageAnimObject.mLoad()
        self.pMessageMusic.mLoad()
        self.pSimpleNameObj.mLoad()
        for n in ('pHand1On', 'pHand1Off', 'pHand2On', 'pHand2Off', 'pHand3On', 'pHand3Off'):
            getattr(self, n).mLoad()
        S(self.pMessageSprite).ink = 8
        self.pMessageMusic.mPlay()
        self.pTimerObject.mPlay()

    def mGetName(self):
        return self.pName

    def mGetType(self):
        return Sym('SCREEN_SMESSAGE')

    # ---- enable / disable ---------------------------------------------------------------------
    def mEnable(self):
        call_all(self.pPuzzPieceObjectList, 'mEnable')
        call_all(self.pHintButtonList, 'mEnable')
        if _alive(self.pBackButton):
            self.pBackButton.mEnable()
        if _alive(self.pHelpButton):
            self.pHelpButton.mEnable()
        self.pEnabled = 1
        if M.gScreenDaddy.mGetLevel() == 2:
            _rect_cursor(self.pMessage1CurSprite, True)
            _rect_cursor(self.pMessage2CurSprite, True)
            _rect_cursor(self.pMessage3CurSprite, True)

    def mDisable(self):
        self.pEnabled = 0
        call_all(self.pPuzzPieceObjectList, 'mDisable')
        call_all(self.pHintButtonList, 'mDisable')
        if _alive(self.pBackButton):
            self.pBackButton.mDisable()
        if _alive(self.pHelpButton):
            self.pHelpButton.mDisable()
        _rect_cursor(self.pMessage1CurSprite, False)
        _rect_cursor(self.pMessage2CurSprite, False)
        _rect_cursor(self.pMessage3CurSprite, False)

    def mApplicationActivated(self):
        pass

    def mApplicationDeactivated(self):
        pass

    # ---- buttons ------------------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        sd = M.gScreenDaddy
        if theObject is self.pHelpButton:
            sd.pHelpPlayer.mStartHelp()
        elif theObject is self.pBackButton:
            M.navigateBack()
        else:
            i = _get_pos(self.pHintButtonList, theObject)
            if i:
                if sd.mTokenFound(self.pPuzzPieceObjectList[i - 1].pTokenName):
                    M.setInterruptMode(self.pGotThatOneAudio)
                    self.pGotThatOneAudio.mPlay()
                else:
                    M.setInterruptMode(self.pHintAudioList[i - 1])
                    self.pHintAudioList[i - 1].mPlay()
            elif theObject is self.pMessage1Rect:
                self._play_hand(self.pHand1On, self.pMessageAudio1, self.pHand1Off)
            elif theObject is self.pMessage2Rect:
                self._play_hand(self.pHand2On, self.pMessageAudio2, self.pHand2Off)
            elif theObject is self.pMessage3Rect:
                self._play_hand(self.pHand3On, self.pMessageAudio3, self.pHand3Off)

    def _play_hand(self, handOn, audio, handOff):
        self.pQueObject = M.getPlayQueueObject(self)
        self.pQueObject.mSetEventTag(Sym('RECTBUTTON'))
        self.pQueObject.mAddItem(handOn)
        self.pQueObject.mAddItem(audio)
        self.pQueObject.mAddItem(handOff)
        M.setInterruptMode(self.pQueObject)
        self.pQueObject.mPlay()

    # ---- play-done dispatch ---------------------------------------------------------------------
    def mPlayDone(self, theObject):
        daType = _T(theObject.mGetType())
        if daType in ('INTERNALSOUND', 'EXTERNALSOUND'):
            self.mSoundDone(theObject)
        elif daType == 'DRAG_N_DROP_SIMPLE':
            self.mHandleDroppedObject(theObject)
        elif daType == 'PLAY_QUEUE':
            self.mHandlePlayQueue(theObject)
        elif daType in ('ANIM_SC', 'ANIM_LIN'):
            self.mHandleAnimDone(theObject)
        elif daType == 'BINK':
            self.mHandleBinkDone(theObject)
        elif daType == 'SIMPLE_NAME':
            self.mHandleNameDone(theObject)
        elif daType == 'TIMER':
            self.mHandleTimerDone(theObject)

    def mHandleTimerDone(self, theObject):
        self.pMessageAnimObject.mPlay()
        call_all(self.pPuzzPieceObjectList, 'mHide')
        self.pPlayMessageFlag = 1

    def mHandleAnimDone(self, theObject):
        if theObject is self.pMessageAnimObject:
            theObject.mHide()
            theObject.mUnload()
            S(self.pMessageSprite).member = self.pMessageMemList[3]
            S(self.pMessageSprite).ink = 8
            # updateStage()
            self.pSimpleNameObj.mShow()
            self.pDissolveBlendObject = M.getBlendDissolveObject(self)
            self.pDissolveBlendObject.mSetBlendDissolve(self.pSimpleNameObj.pSpriteList, 1.5, 20, 1)
            self.pDissolveBlendObject.mPlay()
        else:
            M.resetCursor()
            M.gScreenDaddy.mEnable()

    def mSoundDone(self, theObject):
        sd = M.gScreenDaddy
        if theObject is self.pSnapSound:
            if self.mAllPiecesDropped():
                sd.mDisable()
                M.waitCursor()
                sd.mNextLevel()
                self.pSolvedSessionCount = sd.mGetSessionCount()
                self.mShowMessage()
            else:
                M.resetCursor()
                sd.mEnable()
        elif theObject is self.pMessageMusic:
            self.pQueObject = M.getPlayQueueObject(self)
            for n in ('pHand1On', 'pMessageAudio1', 'pHand1Off',
                      'pHand2On', 'pMessageAudio2', 'pHand2Off',
                      'pHand3On', 'pMessageAudio3', 'pHand3Off'):
                self.pQueObject.mAddItem(getattr(self, n))
            self.pQueObject.mPlay()
        else:
            M.resetCursor()
            sd.mEnable()

    def mHandleNameDone(self, theObject):
        pass

    def mHandleBinkDone(self, theObject):
        self.mEnable()

    def mHandleDroppedObject(self, theObject):
        i = _get_pos(self.pPuzzPieceObjectList, theObject)
        if i:
            if theObject.mGetSnapped():
                self.pSnapSound.mPlay()
                self.pHintButtonList[i - 1].mHide()
                theObject.mChangeSprite(self.pSnapSpriteList[i - 1])
            else:
                M.gScreenDaddy.mEnable()

    def mHandlePlayQueue(self, theObject):
        if self.pPlayMessageFlag:
            theObject.mRecycle()
            M.recycleBlendDissolve()
            self.pMessage1Rect.mShow()
            self.pMessage2Rect.mShow()
            self.pMessage3Rect.mShow()
            _rect_cursor(self.pMessage1CurSprite, True)
            _rect_cursor(self.pMessage2CurSprite, True)
            _rect_cursor(self.pMessage3CurSprite, True)
            M.resetCursor()
            M.gScreenDaddy.mEnable()
            self.pPlayMessageFlag = 0
        else:
            if _symeq(theObject.mGetEventTag(), 'RECTBUTTON'):
                theObject.mRecycle()
                for n in ('pHand1On', 'pHand1Off', 'pHand2On', 'pHand2Off', 'pHand3On', 'pHand3Off'):
                    getattr(self, n).mHide()
            else:
                theObject.mRecycle()

    def mAllPiecesDropped(self):
        daReturnVal = 1
        for daPuzz in self.pPuzzPieceObjectList:
            daReturnVal = min(daReturnVal, daPuzz.pDropped)
            if not daReturnVal:
                break
        return daReturnVal

    def mHackPuzz(self):
        for i in range(len(self.pPuzzPieceObjectList) - 1):
            self.pPuzzPieceObjectList[i].pDropped = 1

    def mUpdate(self):
        pass

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetHelpState(self):
        return 0


# ============================================================================================
# HELP_PLAYER  (ParentScript 188)
# ============================================================================================

@lingo_script('HELP_PLAYER')
class HelpPlayer(LObject):
    def __init__(self):
        self.pType = None
        self.pParent = 0
        self.pAnimObj = 0
        self.pHelpList = {}
        self.pCurrHelpPos = 1
        self.pCurrSequenceList = []
        self.pCurrSequencePos = 0
        self.pSequenceTotal = 0
        self.pHelpVO = 0
        self.pMoving = 0
        self.pStopped = 0
        self.pMemberList = []
        self.pLoaderObject = 0
        self.pPopSound = 0
        self.pSlideSound = 0
        self.pAnimSlideScriptNumber = 0
        self.pLoaderScriptNumber = 0

    def mInit(self, theObjectData, theSpriteAlloc=None):
        set_properties(theObjectData, self)
        self.pAnimObj = _new(self.pAnimSlideScriptNumber, self)
        self.pAnimObj.mSetParent(self)
        self.pAnimObj.mSetInk(8)
        self.pCurrHelpPos = 1
        if len(self.pHelpList):
            self.pCurrSequenceList = self._help_values()[self.pCurrHelpPos - 1]
        self.pCurrSequencePos = 0
        self.pMoving = 0
        self.pStopped = 0
        self.pLoaderObject = _new(self.pLoaderScriptNumber)
        self.pLoaderObject.mSetParent(self)
        return self

    def _help_values(self):
        h = self.pHelpList
        return list(h.values()) if isinstance(h, dict) else list(h)

    # ---- pool objects -------------------------------------------------------------------------
    def mInitPoolObjects(self):
        if not _alive(self.pHelpVO):
            self.pHelpVO = M.getExSoundObject(2, '', self)

    def mReleasePoolObjects(self):
        M.recycleSoundObject(self.pHelpVO)
        self.pHelpVO = 0

    # ---- sequence control ---------------------------------------------------------------------
    def mChooseSequence(self):
        if self.pCurrSequencePos < self.pSequenceTotal:
            self.pCurrSequencePos += 1
            return self.pCurrSequencePos
        return 0

    def mStartHelp(self):
        if not len(self.pHelpList):
            print('[help] Help is not yet available for this game world.')     # alert(...)
            M.resetCursor()
            M.enableGame()
            return
        M.waitCursor()
        M.gScreenDaddy.mDisable()
        self.pLoaderObject.mSetLoadList(self.pMemberList)
        self.pLoaderObject.mPlay()
        self.mChooseHelp()
        self.mChooseSequence()

    def mPlay(self):
        step = self.pCurrSequenceList[self.pCurrSequencePos - 1]
        theSoundFile = step[0]
        theHandMem = step[1]
        theStartLoc = step[2]
        theEndLoc = step[3]
        self.pHelpVO.pSound = theSoundFile
        if theHandMem != 0:
            R().sound.puppet(1, self.pPopSound)
        self.pAnimObj.mSetMember(theHandMem)
        self.pAnimObj.mSetStartLoc(theStartLoc)
        self.pAnimObj.mSetReturnLoc(theEndLoc)
        self.pAnimObj.mShow()
        if theStartLoc != theEndLoc:
            self.pAnimObj.mPlay()
            R().sound.puppet(1, self.pSlideSound)
            self.pMoving = 1
        else:
            self.mPlayVO()

    def mStop(self):
        self.pStopped = 1
        self.pAnimObj.mStop()
        self.pAnimObj.mHide()
        if _alive(self.pHelpVO):
            self.pHelpVO.mStop()
        unload_mem(self.pMemberList)
        M.clearInterruptMode()
        M.gScreenDaddy.mEnable()

    def mPlayDone(self, theObject):
        if theObject is self.pLoaderObject:
            M.resetCursor()
            M.setInterruptMode(self)
            self.mPlay()
            self.pStopped = 0
        else:
            if self.pStopped == 0:
                if self.pMoving == 0:
                    if self.mChooseSequence():
                        self.mPlay()
                    else:
                        self.mStop()
                else:
                    self.pMoving = 0
                    R().sound.stop(1)
                    self.mPlayVO()

    def mPlayVO(self):
        self.pHelpVO.mPlay()

    def mLoad(self):
        load_object(self.pAnimObj)

    def mLoadList(self, theList):
        self.pAnimObj.mLoadList(theList)

    def mUnload(self):
        unload_object(self.pAnimObj)

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mDestroy(self):
        pass

    # ---- which help sequence to play ----------------------------------------------------------------
    def mChooseHelp(self):
        self.mChooseHelp_BASIC()

    def mChooseHelp_BASIC(self):
        sd = M.gScreenDaddy
        scr = sd.pCurrentScreen
        seqPropName = None
        if sd.mGetLevel() == 1 and sd.mRemainingTokenCount() > 0:
            t = _T(scr.mGetType())
            if t == 'SCREEN_DOOR':
                if _symeq(sd.mGetCurrentVersion(), 'a'):
                    seqPropName = 'FRONT_A'
                else:
                    seqPropName = 'FRONT_B_C'
            elif t == 'SCREEN_NAV':
                if _symeq(scr.mGetName(), 'FOYER'):
                    if _symeq(sd.mGetCurrentVersion(), 'a'):
                        seqPropName = 'ENTRY_A'
                    else:
                        seqPropName = 'ENTRY_B_C'
                else:
                    seqPropName = 'NAVIGATION'
            elif t in ('SCREEN_RIDDLE', 'SCREEN_RIDDLE_MAG'):
                if scr.pSolved:
                    seqPropName = 'RIDDLE_DONE'
                else:
                    seqPropName = 'RIDDLE_ALL'
            elif t == 'SCREEN_MM':
                if scr.mGetFinishCount() < 3:
                    seqPropName = 'MYSTERY_BEFORE'
                else:
                    seqPropName = 'MYSTERY_AFTER'
            elif t == 'SCREEN_CC':
                if scr.mGetWinCount() < 3:
                    seqPropName = 'CREEPY_BEFORE'
                else:
                    seqPropName = 'CREEPY_AFTER'
            elif t == 'SCREEN_SMESSAGE':
                seqPropName = 'MESSAGE_A'
            elif t == 'KITCHENGAME':
                seqPropName = 'KITCHEN_B'
            elif t == 'SCREEN_STUDY':
                seqPropName = 'STUDY_EXIT'
            elif t == 'INVENTORSWORKSHOP':
                seqPropName = 'MACHINE_C'
        else:
            ver = sd.mGetCurrentVersion()
            if _symeq(ver, 'a'):
                if sd.mGetLevel() == 1:
                    if _T(scr.mGetType()) != 'SCREEN_SMESSAGE':
                        seqPropName = 'MESSAGE_INCOMPLETE'
                    else:
                        if scr.mGetloosePieceCount() == len(scr.pPuzzPieceObjectList):
                            seqPropName = 'MESSAGE_A'
                        else:
                            seqPropName = 'MESSAGE_B'
                elif sd.mGetLevel() == 2:
                    if _T(scr.mGetType()) == 'SCREEN_STUDY':
                        seqPropName = 'STUDY_EXIT'
                    else:
                        if sd.mTokenFoundCount() == 3:
                            seqPropName = 'STUDY_REVEALED'
                        else:
                            if _T(scr.mGetType()) == 'SCREEN_SMESSAGE':
                                seqPropName = 'MESSAGE_DONE'
                            else:
                                seqPropName = 'SECRET_DONE'
            if _symeq(ver, 'b'):
                if sd.mGetLevel() == 1:
                    if _T(scr.mGetType()) != 'KITCHENGAME':
                        seqPropName = 'KITCHEN_UNFOUND'
                    else:
                        seqPropName = 'KITCHEN_FOUND'
                elif sd.mGetLevel() == 2:
                    seqPropName = 'SOUP_DONE'
            if _symeq(ver, 'c'):
                if sd.mGetLevel() == 1:
                    if _T(scr.mGetType()) != 'INVENTORSWORKSHOP':
                        seqPropName = 'MACHINE_UNFOUND'
                    else:
                        if scr.pOpenPlansFlag == 1:
                            seqPropName = 'PLANS_OPEN'
                        else:
                            seqPropName = 'PLANS_CLOSED'
                elif sd.mGetLevel() == 2:
                    if _T(scr.mGetType()) != 'INVENTORSWORKSHOP':
                        if sd.mGetHuntIndex() != 0:
                            t = _T(scr.mGetType())
                            if t == 'SCREEN_MM':
                                seqPropName = 'MYSTERY_AFTER'
                            elif t == 'SCREEN_CC':
                                seqPropName = 'CREEPY_AFTER'
                            else:
                                seqPropName = 'SCAVENGER_START'
                        else:
                            t = _T(scr.mGetType())
                            if t == 'SCREEN_MM':
                                seqPropName = 'MYSTERY_AFTER'
                            elif t == 'SCREEN_CC':
                                seqPropName = 'CREEPY_AFTER'
                            else:
                                seqPropName = 'MACHINE_DONE'
                    else:
                        if sd.mGetHuntIndex() == 0:
                            seqPropName = 'MACHINE_DONE'
                        else:
                            if scr.pIsGoButtonOpen == 0:
                                seqPropName = 'SCAVENGER_START'
                            else:
                                seqPropName = 'SCAVENGER_DONE'
        # pCurrHelpPos = pHelpList.getPos(pHelpList.getProp(seqPropName))
        values = self._help_values()
        found = None
        if seqPropName is not None and isinstance(self.pHelpList, dict):
            for k, v in self.pHelpList.items():
                if str(k).lower() == seqPropName.lower():
                    found = v
                    break
        if found is None:
            print('[help] no help sequence for', _T(scr.mGetType()), '(', seqPropName, ') -- using the first')
            self.pCurrHelpPos = 1
        else:
            self.pCurrHelpPos = values.index(found) + 1
        self.pCurrSequenceList = values[self.pCurrHelpPos - 1]
        self.pSequenceTotal = len(self.pCurrSequenceList)
        self.pCurrSequencePos = 0
