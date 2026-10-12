"""Movie-script handlers (MAIN_MOVIE 23, General Handlers 24, Global 21), 1:1 with the Lingo.

Lingo `global gFoo` variables are module globals here. Handler names are unchanged so call sites
translate directly. Things Director did natively (cursor(), puppetSound, updateStage, ...) go through
the runtime in runtime.py / media.py.
"""
import os
import shutil

from . import runtime
from .lingo import Sym, get_range_list, pop_last, pop_last_range, pop_one, get_def, Point

# ---- globals ---------------------------------------------------------------------------------
gCursor = None
gInterruptableObject = 0
gGameDaddy = 0            # root object (GameDaddy, from getGameDaddy)
gScreenDaddy = 0           # the *current game* (a GAME, or the MAIN SCREENDADDY with sign-in/menu/credits)
gCurScreen = 0
gLoadStart = 0
gPlayer = ''
gPlayerDir = ''
gSavedGameDir = ''
gSaveLoadObject = 0
gGlobalSaveLoadObject = 0
gAmbientSound = 0
gBlank = 1
gFlushSound = 132          # silent 'flush' sound in the main cast (INIT_MAIN)
gSoundObjectPool = []
gExSoundObjectPool = []
gSimpleButtPool = []
gWiggleObjectPool = []
gQuitDialogue = 0
gUserHasLamePC = 0         # Lingo global set at startup from isLamePC(); the port always runs as a "fast" PC
gDragSprite = 0
gPlayQueue = 0


def _rt():
    return runtime.rt


# ---- update list -----------------------------------------------------------------------------
def addUpdateList(o): _rt().add_update(o)
def removeUpdateList(o): _rt().remove_update(o)
def clearUpDateList(): _rt().clear_update()
def isUpdating(o): return o in _rt().update_list


# ---- cursor ----------------------------------------------------------------------------------
def _set_cursor(name):
    global gCursor
    if gCursor != name:
        gCursor = name
        rt = _rt()
        rt.set_cursor(rt._sprite_cursor or name)      # a sprite's own cursor wins while the mouse is over it


def waitCursor(): _set_cursor('wait')
def hidecursor(): _set_cursor('hidden')
def SetHandCursor(): _set_cursor('hand')
sethandCursor = SetHandCursor
def setOpenhandCursor(): _set_cursor('hand')
def SetGrabCursor(): _set_cursor('grab')
def resetCursor(): _set_cursor('arrow')
def setLipsCursor(): _set_cursor('lips')


# ---- screens / navigation --------------------------------------------------------------------
def setCurScreen(s):
    global gCurScreen
    gCurScreen = s
    _rt().cur_screen = s


def getCurScreen(): return gCurScreen
def getCurGame(): return gScreenDaddy
def loadGame(theGame): gGameDaddy.mGoToGame(theGame)


def setCurrentGame(obj):
    global gScreenDaddy
    gScreenDaddy = obj
    _rt().screen_daddy = obj


def navigate(screen): gScreenDaddy.mNavigate(screen)
def navigateBack(): gScreenDaddy.mNavigateBack()
def getRegPoint(): return Point(320, 240)
def getOffScreenLoc(): return Point(-1000, -1000)
def getBlank(): return gBlank
def getDragSprite(): return gDragSprite
def getDragChan(): return gDragSprite
def getArrowCursor(): return [8, 9]
def disableGame(): gScreenDaddy.mDisable()
def enableGame(): gScreenDaddy.mEnable()
def disableScreen(): gCurScreen.mDisable()
def enableScreen(): gCurScreen.mEnable()
def isPC(): return 1
def isMac(): return 0
def isLamePC(): return 0
def isOSX(): return 0                     # the port always takes the Windows path
gDisabledGamesList = 0                    # Lingo global: list of game names the player may not enter (void here)
def checkCDROMInDrive(): return 1       # the port runs from the extracted game files; there is no disc to check
def QuitKeyCheck(keycode, flag=0): return 0
def getVersion(): return 1
def getPV(pc, mac): return pc


def changeGameCast(cast_id):
    """ChangeCast(castID, 3): castLib 3 is the current game's cast (S, D or b -> Exports/S, D, B).
    Returns 1 if it changed (Lingo: the cast file was swapped)."""
    rt = _rt()
    name = str(cast_id).upper()
    if name == 'EXTERNAL':
        return 0            # (Lingo swaps in an empty cast to free memory; the port keeps the images the stage still shows)
    if os.path.isdir(os.path.join(rt.exports_root, name)):
        if rt.current_game_cast != name:
            rt.current_game_cast = name
            return 1
    return 0


def changeRiddleCast(cast_id):
    """ChangeCast(castID, 4): castLib 4 is the current room / riddle / sign-in cast (SIGNIN, S_AA, D_FI, ...).
    Returns 1 if it changed."""
    rt = _rt()
    room = str(cast_id).upper()
    if room == 'EXTERNAL':
        return 0
    if os.path.isdir(os.path.join(rt.exports_root, room)):
        if rt.current_room != room:
            rt.current_room = room
            return 1
    return 0


# ---- interrupt mode (mouseDownScript = "interruptHandler") -----------------------------------
def setInterruptMode(obj):
    global gInterruptableObject
    if obj is not None:
        gInterruptableObject = obj


def clearInterruptMode(stopFlag=None):
    global gInterruptableObject
    if gInterruptableObject and stopFlag:
        gInterruptableObject.mStop()
    gInterruptableObject = 0


def interruptHandler():
    """Runs on every mouseDown while an interruptable object is set (then `pass()` lets the click through)."""
    global gInterruptableObject
    if gInterruptableObject:
        o = gInterruptableObject
        gInterruptableObject = 0
        o.mStop()


# ---- sound object pools ----------------------------------------------------------------------
def _new(name, *a):
    from .core import new_script
    return new_script(name, *a)


def getSoundObject(channel, sound, parent):
    if isinstance(sound, runtime.LObject):
        return sound
    o = gSoundObjectPool.pop(0) if gSoundObjectPool else _new('INTERNALSOUND', 'extra')
    o.pChannel, o.pSound, o.pParent = channel, sound, parent
    return o


def getExSoundObject(channel, sound, parent):
    if isinstance(sound, runtime.LObject):
        sound.pSound = sound
        return sound
    o = gExSoundObjectPool.pop(0) if gExSoundObjectPool else _new('EXTERNALSOUND', 'extra', '')
    o.pChannel, o.pSound, o.pParent = channel, sound, parent
    return o


def recycleSoundObject(obj):
    if isinstance(obj, runtime.LObject):
        t = str(obj.mGetType()).lower()
        snd = obj.pSound
        if t == 'internalsound' and obj not in gSoundObjectPool:
            obj.mRecycle()
            gSoundObjectPool.append(obj)
        elif t == 'externalsound' and obj not in gExSoundObjectPool:
            obj.mRecycle()
            gExSoundObjectPool.append(obj)
        return snd
    return obj


def getSimpleButt(sprite, member, parent, ink=None):
    o = gSimpleButtPool.pop(0) if gSimpleButtPool else _new('BUTT_SIMPLE')
    o.pSprite, o.pMember, o.pParent, o.pInk = sprite, member, parent, get_def(ink, 0)
    return o


def recycleSimpleButt(obj):
    if isinstance(obj, runtime.LObject):
        obj.pSprite = obj.pMember = obj.pParent = obj.pInk = 0
        if obj not in gSimpleButtPool:
            gSimpleButtPool.append(obj)


# ---- wiggle object pool (MAIN_MOVIE getWiggleObject / recycleWiggleObject / getWiggleSound) -------
def getWiggleObject(parent=None):
    o = gWiggleObjectPool.pop(0) if gWiggleObjectPool else _new('ANIM_WIGGLE')
    o.pParent = parent
    return o


def recycleWiggleObject(obj):
    obj.pParent = None
    obj.pSprite = 0
    obj.pAnimMembers = []
    obj.pSoundChannel = 0
    obj.pInk = 0
    obj.pBackMember = 0
    obj.pBackSprite = 0
    if obj not in gWiggleObjectPool:
        gWiggleObjectPool.append(obj)


def getWiggleSound():
    if str(gScreenDaddy.mGetType()).upper() == 'GAME':
        return gScreenDaddy.mGetWiggleSound()


# ---- ambient sound (channel 3) ---------------------------------------------------------------
def FadeOutAmbientSound(speed=None): _rt().sound.stop(3)
def ReStartAmbientSound():
    if gAmbientSound:
        _rt().sound.puppet(3, gAmbientSound)


def FadeInAmbientSound(snd=None, speed=None):
    global gAmbientSound
    if snd is not None and snd != gAmbientSound:
        gAmbientSound = snd
        _rt().sound.puppet(3, snd)


def clearAmbientSound():
    global gAmbientSound
    _rt().sound.stop(3)
    gAmbientSound = 0


# ---- save / load / players ---------------------------------------------------------------------
def addObjectGlob(obj):
    if gSaveLoadObject:
        gSaveLoadObject.mAddObjectGlob(obj)


def setSaveLoadObject(o):
    global gSaveLoadObject
    gSaveLoadObject = o


def getPlayerDir(): return gPlayerDir
def getPlayer(): return gPlayer
def getSavedGamesDir(): return gSavedGameDir


def setPlayer(name):
    global gPlayer, gPlayerDir
    gPlayer = name
    gPlayerDir = os.path.join(gSavedGameDir, name) + os.sep
    os.makedirs(gPlayerDir, exist_ok=True)
    gSaveLoadObject.pFileDir = gPlayerDir
    gSaveLoadObject.mSetCurFile('GLOBAL')
    gSaveLoadObject.mRestore()


def getSavedGamesList():
    if not os.path.isdir(gSavedGameDir):
        return []
    return sorted(d for d in os.listdir(gSavedGameDir) if os.path.isdir(os.path.join(gSavedGameDir, d)))


def deleteGame(user):
    if user != '':
        d = os.path.join(gSavedGameDir, user)
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)


def savegame():
    if gPlayer != '':
        if gGlobalSaveLoadObject:
            gGlobalSaveLoadObject.mSave()
        if gGameDaddy:
            gGameDaddy.mSaveGames()


def savegame_safe():
    """savegame() that can never take the game down (used by the autosave hooks)."""
    try:
        savegame()
    except Exception as e:
        print('[save] failed:', e)


# ---- game helpers ----------------------------------------------------------------------------
def tokenFound(t):
    return gScreenDaddy.mTokenFound(t) if str(gScreenDaddy.mGetType()).upper() == 'GAME' else 0


def addGameToken(t):
    return gScreenDaddy.mAddToken(t) if str(gScreenDaddy.mGetType()).upper() == 'GAME' else 0


def riddlePlayed(): return gGameDaddy.pRiddlePlayed
def setRiddlePlayed(): gGameDaddy.pRiddlePlayed = 1


def _dup(v):
    """Fresh copy of handler data (propLists / lists only): in Lingo every call to a data handler builds a new
    literal, and objects keep and change pieces of it."""
    if isinstance(v, dict):
        return {k: _dup(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_dup(x) for x in v]
    return v


def getHandlerData(name):
    return _dup(_rt().handlers.get(name))


def getGameDaddy(): return getHandlerData('getGameDaddy')
def getQuitDialogue(): return getHandlerData('getQuitDialogue')


_GAME_HANDLERS = {'s': 'getSandCastle', 'b': 'getBlast', 'd': 'getDeep'}


def getGameData(theGame, theVersion):
    """General Handlers / Global (MovieScript 21): game #S/#b/#D + version #a/#b/#c -> data handler."""
    base = _GAME_HANDLERS.get(str(theGame).lower())
    if base is None:
        return None
    return getHandlerData('%s_%s' % (base, str(theVersion).upper()))


def GlobalPlayDone(obj):
    """TIMER with no parent: nothing to notify (Fantasy's GameDaddy always sets pParent)."""
    pass


# ---- sprite / game helpers used by the screens ------------------------------------------------
def setMember(chan, num):
    if isinstance(chan, (list, tuple)):
        for c, m in zip(chan, num):
            setMember(c, m)
        return
    s = _rt().sprites[chan]
    s.member = num
    s.loc = Point(320, 240)


def _game_attr(name):
    if str(gScreenDaddy.mGetType()).upper() == 'GAME':
        return getattr(gScreenDaddy, name)
    return None


def getGameHomeButton(): return _game_attr('pHomeButton')
def getGameHelpButton(): return _game_attr('pHelpButton')
def getGameBackButton(): return _game_attr('pBackButton')
def getGameRiddleStrip(): return _game_attr('pRiddleStripObject')
def getGameClueStrip(): return _game_attr('pClueStripObject')
def getGameCongratsAudio(): return _game_attr('pCongratsAudio')


def getPlayQueueObject(parent=None):
    if isinstance(parent, runtime.LObject):
        gPlayQueue.pParent = parent
    return gPlayQueue


def recyclePlayStack():
    gPlayQueue.pParent = 0
    gPlayQueue.pObjectList = []


def quitDialogue():
    gQuitDialogue.mLoad()
    gQuitDialogue.mShow()


def doshutDown():
    try:
        savegame()
    finally:
        raise SystemExit(0)


# ---- INIT_MAIN -------------------------------------------------------------------------------
def _saved_games_dir(project_root):
    """Per-user save folder, under the same root the launcher uses: %LOCALAPPDATA%\\ISpyFantasyPort\\SAVED GAMES
    (ISPY_PORT_HOME overrides the root; XDG data dir on non-Windows)."""
    root = os.environ.get('ISPY_PORT_HOME')
    if not root:
        if os.name == 'nt':
            base = os.environ.get('LOCALAPPDATA') or os.path.join(os.path.expanduser('~'), 'AppData', 'Local')
        else:
            base = os.environ.get('XDG_DATA_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'share')
        root = os.path.join(base, 'ISpyFantasyPort')
    new = os.path.join(root, 'SAVED GAMES')
    os.makedirs(new, exist_ok=True)
    return new


def INIT_MAIN():
    """MovieScript 23 INIT_MAIN, line for line (loadCursors / exitLock / the Mac-only paths are not needed)."""
    global gGameDaddy, gScreenDaddy, gSavedGameDir, gGlobalSaveLoadObject, gSaveLoadObject, gLoadStart
    global gQuitDialogue, gDragSprite, gPlayQueue, gBlank, gPlayer, gPlayerDir, gAmbientSound, gFlushSound
    global gInterruptableObject
    from . import core, ui, game, screens, screens2, riddles, rooms, video, hunts, master_screens  # noqa: F401  (registers the parent scripts)
    from . import scavenger, fantasy_anims, fantasy_screens, fantasy_book  # noqa: F401  (Fantasy-only parent scripts)
    rt = _rt()
    gLoadStart = rt.milliseconds()
    gBlank = 1
    rt.clear_update()                     # gUpdateList = []
    gInterruptableObject = 0
    gPlayer = ''
    gPlayerDir = ''
    gAmbientSound = 0
    gSavedGameDir = _saved_games_dir(rt.project_root)
    print('[saves] saved games in', gSavedGameDir)
    gPlayQueue = _new('PLAY_QUEUE')
    initSimpleButtonPool()
    del gSoundObjectPool[:], gExSoundObjectPool[:], gWiggleObjectPool[:]
    gFlushSound = 132
    for i in range(1, 22):
        gSoundObjectPool.append(_new('INTERNALSOUND', Sym(str(i))))
        gExSoundObjectPool.append(_new('EXTERNALSOUND', Sym(str(i)), 'AIFF'))
        gWiggleObjectPool.append(_new('ANIM_WIGGLE'))
    gGlobalSaveLoadObject = _new('SAVELOAD', '')
    gSaveLoadObject = gGlobalSaveLoadObject
    alloc = get_range_list(1, 150)
    gDragSprite = pop_last(alloc)
    gQuitDialogue = runtime.get_object(getQuitDialogue(), pop_last_range(alloc, 5))
    gGameDaddy = runtime.get_object(getGameDaddy(), alloc)
    gScreenDaddy = gGameDaddy.mGetCurrentGame()
    rt.screen_daddy = gScreenDaddy
    gGameDaddy.mLoad()
    gGameDaddy.mShow()


def initSimpleButtonPool():
    del gSimpleButtPool[:]
    for _ in range(20):
        gSimpleButtPool.append(runtime.get_object({'pType': 'BUTT_SIMPLE', 'pName': Sym('POOL')}, [0]))
