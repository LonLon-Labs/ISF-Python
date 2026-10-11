"""Hand-ported parent scripts, part 7: more room screens.

    ParentScript  49  SCREEN_KITCHEN     the Kitchen (recipe card, ingredients dragged into the pot) -- type #KITCHENGAME
    ParentScript  53  SCREEN_IWORKSHOP   the Inventor's Workshop (machine parts, ghost buttons, bottles) -- type #INVENTORSWORKSHOP

(SCREEN_MM 51 and SCREEN_CC 52 are in room_screens3.py.)  Imported at the bottom of rooms.py.
"""
from . import runtime, movie as M
from .runtime import LObject, lingo_script, get_object, get_object_list
from .lingo import Sym, Point, set_properties, pop_one
from .ui import blank
from .screens2 import R, S, _alive, _get_pos, _symeq
from .riddles import call_all, _pos


def _tag(o):
    """mGetEventTag(o) as a lower-case string ('0' / 'none' when unset)."""
    t = o.mGetEventTag()
    return str(t).lower()


def _get_prop(d, key):
    """getProp(propList, key): case-insensitive key lookup (the converter keeps the keys as strings)."""
    if isinstance(d, dict):
        for k, v in d.items():
            if str(k).lower() == str(key).lower():
                return v
    return None


def _call_flag(obj, flag):
    """mDisable(obj, flag): some buttons take the extra argument, some do not."""
    try:
        obj.mDisable(flag)
    except TypeError:
        obj.mDisable()


# ============================================================================================
# SCREEN_KITCHEN  (ParentScript 49)
# ============================================================================================

@lingo_script('SCREEN_KITCHEN')
class ScreenKitchen(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pBackMember = 0
        self.pFrontMember1 = 0
        self.pFrontMember2 = 0
        self.pBackSprite = 0
        self.pFrontSprite1 = 0
        self.pFrontSprite2 = 0
        self.pAmbientAudio = 0
        self.pHelpButton = 0
        self.pBackButton = 0
        self.pSavedList = []
        self.pParent = 0
        self.pEnabled = 0
        self.pIngObjectList = []
        self.pRecipeCount = 0
        self.pFirstTimeFlag = 1
        self.pCurrentToken = 0
        self.pQueObject = 0
        self.pDissolveBlendObject = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pIngObjectList = get_object_list(self.pIngObjectList, theSpriteAlloc)
        call_all(self.pIngObjectList, 'mSetParent', self)
        call_all(self.pIngObjectList, 'mDisable')
        self.pSkellyButton = get_object(self.pSkellyButton, theSpriteAlloc)
        self.pSkellyButton.mSetParent(self)
        self.pSkellyAnimObject = get_object(self.pSkellyAnimObject, theSpriteAlloc)
        self.pSkellyAnimObject.mSetParent(self)
        self.pPatchSprite = pop_one(theSpriteAlloc)
        self.pRecipeSprite = pop_one(theSpriteAlloc)
        self.pIntroRecipeAnim = get_object(self.pIntroRecipeAnim, [self.pRecipeSprite])
        self.pIntroRecipeAnim.mSetParent(self)
        self.pRecipeButton = get_object(self.pRecipeButton, [self.pRecipeSprite])
        self.pRecipeButton.mSetParent(self)
        self.pRecipeAnimList = get_object_list(self.pRecipeAnimList, [self.pRecipeSprite], 1)
        call_all(self.pRecipeAnimList, 'mSetParent', self)
        self.pScavSprite = pop_one(theSpriteAlloc)
        self.pScavButton = get_object(self.pScavButton, [self.pScavSprite])
        self.pScavButton.mSetParent(self)
        self.pFrontSprite1 = pop_one(theSpriteAlloc)
        self.pFrontSprite2 = pop_one(theSpriteAlloc)
        self.pLadlePatchSprite = pop_one(theSpriteAlloc)
        self.pIngAnimList = get_object_list(self.pIngAnimList, theSpriteAlloc)
        call_all(self.pIngAnimList, 'mSetParent', self)
        self.pRecipeDoneBink = get_object(self.pRecipeDoneBink, theSpriteAlloc)
        self.pRecipeDoneBink.mSetParent(self)
        self.pRecipeCount = 0
        self.pFirstTimeFlag = 1
        self.pTimerObject = get_object(self.pTimerObject, [])
        self.pTimerObject.mSetParent(self)
        self.pEnabled = 1
        self.pCurrentToken = 0
        self.pQueObject = 0
        self.pSavedList = [Sym('pRecipeCount'), Sym('pFirstTimeFlag')]
        M.addObjectGlob(self)

    def mInitPoolObjects(self):
        self.pSkellyAnimObject.mInitPoolObjects()
        M.gScreenDaddy.mInitScavengerHuntPoolObjects()

    def mReleasePoolObjects(self):
        self.pSkellyAnimObject.mReleasePoolObjects()
        self.pQueObject = 0
        M.gScreenDaddy.mReleaseScavengerHuntPoolObjects()

    def mDestroy(self):
        pass

    def mGetEnabled(self):
        return self.pEnabled

    def mLoad(self):
        pass

    def mLoadList(self, theList):
        sd = M.gScreenDaddy
        theList.append(self.pAmbientAudio)
        theList.append(self.pBackMember)
        theList.append(self.pFrontMember1)
        theList.append(self.pFrontMember2)
        self.mLoadIngredients(theList)
        self.pSkellyButton.mLoadList(theList)
        self.pSkellyAnimObject.mLoadList(theList)
        if sd.mGetLevel() == 1:
            if self.pFirstTimeFlag:
                self.pIntroRecipeAnim.mLoadList(theList)
            theList.extend(self.pRecipeButtMemList)
            n = self.pRecipeCount
            if (n > 0) and (n < 8):
                self.pRecipeAnimList[n - 1].mLoadList(theList)
            theList.append(self.pLadlePatch)
            if ((n - 1) > 0) and ((n - 1) < 7):
                self.pIngAnimList[n - 2].mLoadList(theList)
            if (n == 1) or (n == 0):
                self.pIngAnimList[0].mLoadList(theList)
            self.pScavButton.mLoadList(theList)
            theList.append(self.pDoneBinkPatch)
        elif sd.mGetLevel() == 2:
            self.pScavButton.mLoadList(theList)
            theList.append(self.pDoneBinkPatch)

    def mLoadIngredients(self, theList):
        for i in range(1, 16):
            daIng = self.pIngObjectList[i - 1]
            if M.gScreenDaddy.mTokenFound(daIng.pTokenName):
                daIng.mLoadList(theList)
        for i in range(16, len(self.pIngObjectList) + 1):
            self.pIngObjectList[i - 1].mLoadList(theList)

    def mUnload(self):
        call_all(self.pIngObjectList, 'mUnload')
        self.pIntroRecipeAnim.mUnload()
        self.pScavButton.mUnload()
        call_all(self.pRecipeAnimList, 'mUnload')
        call_all(self.pIngAnimList, 'mUnload')
        self.pSkellyButton.mUnload()
        self.pSkellyAnimObject.mUnload()

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
        S(self.pFrontSprite1).member = self.pFrontMember1
        S(self.pFrontSprite1).ink = 8
        S(self.pFrontSprite2).member = self.pFrontMember2
        S(self.pFrontSprite2).ink = 8
        S(self.pRecipeSprite).ink = 8
        if not self.pFirstTimeFlag:
            self.mShowRecipeButt()
        self.pSkellyButton.mShow()
        S(self.pRecipeSprite).cursor = [33, 34]
        self.mShowIngredients()
        call_all(self.pIngObjectList, 'mDisable')
        if sd.mGetLevel() == 1:
            if self.pFirstTimeFlag:
                self.pFirstTimeFlag = 0
                sd.mDisable()
                self.pRecipeCount = 1
                self.pTimerObject.mSetEventTag(Sym('FIRSTTIMEANIM'))
                self.pTimerObject.mPlay()
            else:
                if sd.mAllTokensFound():
                    if self.pRecipeCount == 1:
                        sd.mDisable()
                        self.pSkellyAnimObject.mSetEventTag(Sym('FOUNDTHEMALL'))
                        self.pSkellyAnimObject.mSetSkellyVO(self.pGotThemAllAudio)
                        self.pSkellyAnimObject.mPlay()
                    else:
                        call_all(self.pIngObjectList, 'mEnable')
                        M.resetCursor()
                else:
                    M.resetCursor()
        elif sd.mGetLevel() == 2:
            self.pScavButton.mShow()
            S(self.pScavSprite).cursor = [25, 26]
            S(self.pPatchSprite).member = self.pDoneBinkPatch
            S(self.pPatchSprite).ink = 8
            M.resetCursor()
        self.pEnabled = 1

    def mHide(self):
        blank(self.pBackSprite)
        blank(self.pRecipeSprite)
        for o in (self.pBackButton, self.pHelpButton):
            if _alive(o):
                o.mHide()
        self.pRecipeButton.mHide()
        self.pScavButton.mHide()
        # call(#hide, pIngObjectList, me): there is no `hide` handler (the real one is mHide) -> a no-op
        self.pQueObject = 0
        self.pEnabled = 0
        S(self.pRecipeSprite).cursor = 0
        if M.gScreenDaddy.mGetLevel() == 2:
            blank(self.pPatchSprite)
            S(self.pScavSprite).cursor = 0

    def mShowIngredients(self):
        sd = M.gScreenDaddy
        if sd.mGetLevel() == 1:
            for i in range(1, 16):
                Ing = self.pIngObjectList[i - 1]
                if sd.mTokenFound(Ing.pTokenName):
                    Ing.mShow()
                    continue
                Ing.mHide()
        elif sd.mGetLevel() == 2:
            for i in range(1, 16):
                self.pIngObjectList[i - 1].mShow()
        for i in range(16, 23):
            self.pIngObjectList[i - 1].mShow()

    def mShowRecipeButt(self):
        self.pRecipeButton.mSetMember(self.pRecipeButtMemList[self.pRecipeCount - 1])
        self.pRecipeButton.mShow()

    def mIncrementRecipe(self):
        n = self.pRecipeCount
        if (n > 1) and (n < 8):
            self.pIngObjectList[self.mGetPosOfIngByToken(self.pIngTokenLookUp[n - 2]) - 1].mSetDropRect(self.pNullRect)
        if n < 8:
            self.pCurrentToken = self.pIngTokenLookUp[n - 1]
            self.pIngObjectList[self.mGetPosOfIngByToken(self.pCurrentToken) - 1].mSetDropRect(self.pDropRect)
        self.pRecipeAnimList[n - 1].mLoad()
        self.pRecipeAnimList[n - 1].mPlay()
        self.pRecipeCount = n + 1

    def mGetPosOfIngByToken(self, daToken):
        num = 0
        for i in range(1, 17):
            if self.pIngObjectList[i - 1].mGetTokenName() == daToken:
                num = i
                break
        return num

    def mGetName(self):
        return self.pName

    def mGetType(self):
        return Sym('KITCHENGAME')

    def mEnable(self):
        sd = M.gScreenDaddy
        if sd.mAllTokensFound():
            call_all(self.pIngObjectList, 'mEnable')
        self.pRecipeButton.mEnable()
        self.pBackButton.mEnable()
        self.pHelpButton.mEnable()
        self.pSkellyButton.mEnable()
        if sd.mGetLevel() == 2:
            self.pScavButton.mEnable()
        self.pEnabled = 1
        S(self.pRecipeSprite).cursor = [33, 34]
        S(self.pScavSprite).cursor = [25, 26]

    def mDisable(self):
        self.pEnabled = 0
        call_all(self.pIngObjectList, 'mDisable')
        self.pRecipeButton.mDisable()
        self.pBackButton.mDisable()
        self.pHelpButton.mDisable()
        self.pSkellyButton.mDisable()
        if M.gScreenDaddy.mGetLevel() == 2:
            self.pScavButton.mDisable()
        S(self.pRecipeSprite).cursor = 0
        S(self.pScavSprite).cursor = 0

    def mApplicationActivated(self):
        pass

    def mApplicationDeactivated(self):
        pass

    # ---- buttons --------------------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        sd = M.gScreenDaddy
        if theObject is self.pHelpButton:
            sd.pHelpPlayer.mStartHelp()
        elif theObject is self.pBackButton:
            M.navigateBack()
        elif self.pRecipeButton is theObject:
            self.mReadRecipeCard(0)
        elif self.pSkellyButton is theObject:
            self.mClickOnSkelly()
        elif self.pScavButton is theObject:
            M.setInterruptMode(self.pSkellyAnimObject)
            self.pSkellyAnimObject.mSetEventTag(Sym('SCAVBUTT'))
            self.pSkellyAnimObject.mSetSkellyVO(self.pScavButtAif)
            self.pSkellyAnimObject.mPlay()
            sd.mEnable()
            M.resetCursor()

    def mReadRecipeCard(self, daEventTag):
        M.setInterruptMode(self.pSkellyAnimObject)
        self.pSkellyAnimObject.mSetEventTag(daEventTag)
        self.pSkellyAnimObject.mSetSkellyVO(self.pRecipeAudioList[self.pRecipeCount - 1])
        self.pSkellyAnimObject.mPlay()

    def mClickOnSkelly(self):
        sd = M.gScreenDaddy
        if sd.mAllTokensFound() or (sd.mGetLevel() == 2):
            self.mReadRecipeCard(0)
        else:
            M.setInterruptMode(self.pSkellyAnimObject)
            self.pSkellyAnimObject.mSetEventTag(0)
            self.pSkellyAnimObject.mSetSkellyVO(self.pSkellyButtAudio)
            self.pSkellyAnimObject.mPlay()

    # ---- play-done dispatch ---------------------------------------------------------------------
    def mPlayDone(self, theObject):
        t = _tag(theObject)
        fn = {'foundthemall': self.mHandleFoundThemAllDone,
              'dragging': self.mHandleDraggingDone,
              'recipeanim': self.mHandleRecipeAnimDone,
              'firsttimeanim': self.mHandleFirstTimeAnimDone,
              'readrecipecarddone': self.mHandleReadRecipeCardDone,
              'scavbutt': self.mHandleSCAVBUTTDone}.get(t)
        if fn:
            fn(theObject)

    def mHandleFoundThemAllDone(self, theObject):
        if theObject is self.pSkellyAnimObject:
            self.mIncrementRecipe()

    def mHandleDraggingDone(self, theObject):
        sd = M.gScreenDaddy
        i = _get_pos(self.pIngObjectList, theObject)
        if i:
            if i < 17:
                if theObject.mGetSnapped():
                    theObject.mHide()
                    self.pCurrentToken = theObject.mGetTokenName()
                    if i < 16:
                        self.pIngAnimList[_pos(self.pIngTokenLookUp, self.pCurrentToken) - 1].mPlay()
                    else:
                        sd.mNextLevel()
                        S(self.pLadlePatchSprite).member = self.pLadlePatch
                        S(self.pLadlePatchSprite).loc = Point(346, 128)
                        S(self.pLadlePatchSprite).ink = 8
                        R().update_stage()
                        self.pRecipeDoneBink.mSetEventTag(Sym('DRAGGING'))
                        self.pRecipeDoneBink.mLoad()
                        self.pRecipeDoneBink.mPlay()
                else:
                    sd.mEnable()
            else:
                sd.mEnable()
        else:
            k = _pos(self.pIngTokenLookUp, self.pCurrentToken)
            if k and theObject is self.pIngAnimList[k - 1]:
                ing = self.pIngObjectList[self.mGetPosOfIngByToken(self.pCurrentToken) - 1]
                if any(self.pCurrentToken == s for s in (Sym('MG'), Sym('IW'), Sym('SS'))):
                    ing.mSetDragMember(_get_prop(self.pIngStateChangeLookUp, self.pCurrentToken))
                theObject.mHide()
                if self.pCurrentToken != Sym('IW'):
                    ing.pDropped = 0
                ing.mShow()
                n = self.pRecipeCount
                if (n > 0) and (n < 7):
                    self.pIngAnimList[n - 1].mLoad()
                self.mIncrementRecipe()
            else:
                if theObject is self.pRecipeDoneBink:
                    self.pRecipeDoneBink.mUnload()
                    blank(self.pLadlePatchSprite)
                    self.pRecipeCount += 1
                    ing = self.pIngObjectList[self.mGetPosOfIngByToken(self.pCurrentToken) - 1]
                    ing.pDropped = 0
                    ing.mSetDropRect(self.pNullRect)
                    S(self.pPatchSprite).member = self.pDoneBinkPatch
                    S(self.pPatchSprite).ink = 8
                    S(self.pPatchSprite).loc = Point(320, 240)
                    sd.mInitScavengerHuntPoolObjects()
                    sd.mEnable()
                    M.resetCursor()
                    self.mStartScavHuntKT()

    def mHandleRecipeAnimDone(self, theObject):
        self.mShowRecipeButt()
        R().update_stage()
        M.gScreenDaddy.mEnable()
        M.resetCursor()
        self.mReadRecipeCard(Sym('READRECIPECARDDONE'))

    def mHandleReadRecipeCardDone(self, theObject):
        if theObject is self.pSkellyAnimObject:
            n = self.pRecipeCount
            if ((n - 2) > 0) and ((n - 2) < 7):
                self.pIngAnimList[n - 3].mUnload()
            if ((n - 1) > 0) and ((n - 1) < 8):
                self.pRecipeAnimList[n - 2].mUnload()

    def mHandleFirstTimeAnimDone(self, theObject):
        sd = M.gScreenDaddy
        sk = self.pSkellyAnimObject
        if theObject is self.pTimerObject:
            sk.mSetEventTag(Sym('FIRSTTIMEANIM'))
            sk.mSetSkellyVO(self.pFirstTimeAudio)
            sk.mPlay()
        else:
            if (theObject is sk) and (sk.pSoundFile == self.pFirstTimeAudio):
                theObject.mHide()
                self.pIntroRecipeAnim.mSetEventTag(Sym('FIRSTTIMEANIM'))
                self.pIntroRecipeAnim.mPlay()
            else:
                if theObject is self.pIntroRecipeAnim:
                    theObject.mUnload()
                    if sd.mAllTokensFound():
                        sk.mSetEventTag(Sym('FOUNDTHEMALL'))
                        sk.mSetSkellyVO(self.pGotThemAllAudio)
                        sk.mPlay()
                    else:
                        sk.mSetEventTag(Sym('FIRSTTIMEANIM'))
                        sk.mSetSkellyVO(self.pFirstTimeAudio2)
                        sk.mPlay()
                else:
                    if (theObject is sk) and (sk.pSoundFile == self.pFirstTimeAudio2):
                        theObject.mHide()
                        self.mShowRecipeButt()
                        sd.mEnable()
                        M.resetCursor()

    def mHandleSCAVBUTTDone(self, theObject):
        pass

    def mStartScavHuntKT(self):
        self.mShowRecipeButt()
        self.pScavButton.mShow()
        self.mReadRecipeCard(0)

    def mHandleTimerDone(self, theObject):
        pass

    def mHandleAnimDone(self, theObject):
        pass

    def mSoundDone(self, theObject):
        pass

    def mHandleNameDone(self, theObject):
        pass

    def mHandleBinkDone(self, theObject):
        pass

    def mHandleDroppedObject(self, theObject):
        pass

    def mHandlePlayQueue(self, theObject):
        theObject.mRecycle()
        M.resetCursor()
        M.gScreenDaddy.mEnable()

    def mHackShowScavengerHunt(self):
        pass

    def mUpdate(self):
        pass

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetHelpState(self):
        return 0


# ============================================================================================
# SCREEN_IWORKSHOP  (ParentScript 53)
# ============================================================================================

@lingo_script('SCREEN_IWORKSHOP')
class ScreenIWorkshop(LObject):
    def __init__(self):
        self.pName = None
        self.pType = None
        self.pBackMember = 0
        self.pFrontMember1 = 0
        self.pBackSprite = 0
        self.pFrontSprite1 = 0
        self.pGhostNameSprite = 0
        self.pAmbientAudio = 0
        self.pHelpButton = 0
        self.pBackButton = 0
        self.pSavedList = []
        self.pParent = 0
        self.pEnabled = 0
        self.pPlansSprite = 0
        self.pPartObjectList = []
        self.pGhostButtList = []
        self.pGhostBinkList = []
        self.pFirstTimeFlag = 0
        self.pOpenPlansFlag = 0
        self.pGhostButtonState = 0
        self.pGhostButtonStateCandidate = 0
        self.pIsGoButtonOpen = 0
        self.pGhostButtonsActiveList = [1, 1, 1, 1, 1, 1, 0]
        self.pFirstGhostButtonFlag = 1
        self.pFirstGhostDoneFlag = 1
        self.pDissolveBlendObject = 0

    def mInit(self, theObjectData, theSpriteAlloc):
        set_properties(theObjectData, self)
        self.pBackSprite = pop_one(theSpriteAlloc)
        self.pSkellyAnimObject = get_object(self.pSkellyAnimObject, theSpriteAlloc)
        self.pSkellyAnimObject.mSetParent(self)
        self.pBottleObject = get_object(self.pBottleObject, theSpriteAlloc)
        self.pBottleObject.mSetParent(self)
        self.pPartObjectList = get_object_list(self.pPartObjectList, theSpriteAlloc)
        call_all(self.pPartObjectList, 'mSetParent', self)
        call_all(self.pPartObjectList, 'mDisable')
        self.pSHTokenObject = get_object(self.pSHTokenObject, theSpriteAlloc)
        self.pSHTokenObject.mSetParent(self)
        self.pMachineOnAnim = get_object(self.pMachineOnAnim, theSpriteAlloc)
        self.pMachineOnAnim.mSetParent(self)
        self.pGhostNameSprite = pop_one(theSpriteAlloc)
        self.pGoButton = get_object(self.pGoButton, theSpriteAlloc)
        self.pGoButton.mSetParent(self)
        self.pOpenGoAnim = get_object(self.pOpenGoAnim, theSpriteAlloc)
        self.pOpenGoAnim.mSetParent(self)
        self.pCloseGoAnim = get_object(self.pCloseGoAnim, theSpriteAlloc)
        self.pCloseGoAnim.mSetParent(self)
        self.pGhostButtList = get_object_list(self.pGhostButtList, theSpriteAlloc)
        call_all(self.pGhostButtList, 'mSetParent', self)
        call_all(self.pGhostButtList, 'mSetTwins', self.pGhostButtList)
        self.pBUTT7Wiggle = get_object(self.pBUTT7Wiggle, theSpriteAlloc)
        self.pBUTT7Wiggle.mSetParent(self)
        self.pFrontSprite1 = pop_one(theSpriteAlloc)
        self.pPlansSprite = pop_one(theSpriteAlloc)
        for n in ('pPlansOpenButton', 'pPlansCloseButton', 'pPlansWiggle', 'pOpenPlansAnim', 'pClosePlansAnim'):
            o = get_object(getattr(self, n), [self.pPlansSprite])
            setattr(self, n, o)
            o.mSetParent(self)
        self.pGhostBinkList = get_object_list(self.pGhostBinkList, theSpriteAlloc)
        call_all(self.pGhostBinkList, 'mSetParent', self)
        self.pFirstTimeFlag = 0
        self.pOpenPlansFlag = 0
        self.pGhostButtonState = 0
        self.pGhostButtonStateCandidate = 0
        self.pIsGoButtonOpen = 0
        self.pGhostButtonsActiveList = [1, 1, 1, 1, 1, 1, 0]
        self.pFirstGhostButtonFlag = 1
        self.pFirstGhostDoneFlag = 1
        self.pTimerObject = get_object(self.pTimerObject, [])
        self.pTimerObject.mSetParent(self)
        self.pEnabled = 1
        self.pSavedList = [Sym(n) for n in ('pFirstTimeFlag', 'pGhostButtonsActiveList', 'pIsGoButtonOpen',
                                            'pGhostButtonState', 'pFirstGhostButtonFlag', 'pFirstGhostDoneFlag')]
        M.addObjectGlob(self)

    def mInitPoolObjects(self):
        self.pSnapSound = M.getSoundObject(1, self.pSnapSound, self)
        self.pBottleObject.mInitPoolObjects()
        self.pSkellyAnimObject.mInitPoolObjects()
        M.gScreenDaddy.mInitScavengerHuntPoolObjects()

    def mReleasePoolObjects(self):
        self.pSnapSound = M.recycleSoundObject(self.pSnapSound)
        self.pBottleObject.mReleasePoolObjects()
        self.pSkellyAnimObject.mReleasePoolObjects()
        self.pDissolveBlendObject = 0
        M.gScreenDaddy.mReleaseScavengerHuntPoolObjects()

    def mDestroy(self):
        pass

    def mGetEnabled(self):
        return self.pEnabled

    def mLoad(self):
        pass

    def mLoadList(self, theList):
        sd = M.gScreenDaddy
        theList.append(self.pBackMember)
        theList.append(self.pFrontMember1)
        theList.append(self.pAmbientAudio)
        theList.append(self.pSnapSound)
        self.pSkellyAnimObject.mLoadList(theList)
        call_all(self.pGhostButtList, 'mLoadList', theList)
        self.pBottleObject.mLoadList(theList)
        if sd.mGetLevel() == 1:
            for n in ('pMachineOnAnim', 'pPlansOpenButton', 'pPlansCloseButton', 'pPlansWiggle',
                      'pOpenPlansAnim', 'pClosePlansAnim'):
                getattr(self, n).mLoadList(theList)
        elif sd.mGetLevel() == 2:
            for n in ('pGoButton', 'pOpenGoAnim', 'pCloseGoAnim', 'pSHTokenObject'):
                getattr(self, n).mLoadList(theList)
        self.mLoadIngredients(theList)

    def mLoadIngredients(self, theList):
        for daIng in self.pPartObjectList:
            if M.gScreenDaddy.mTokenFound(daIng.pTokenName):
                daIng.mLoadList(theList)

    def mUnload(self):
        call_all(self.pPartObjectList, 'mUnload')
        call_all(self.pGhostBinkList, 'mUnload')
        for n in ('pSkellyAnimObject', 'pMachineOnAnim', 'pPlansOpenButton', 'pPlansCloseButton', 'pPlansWiggle',
                  'pOpenPlansAnim'):
            getattr(self, n).mUnload()
        call_all(self.pGhostButtList, 'mUnload')
        for n in ('pBottleObject', 'pGoButton', 'pOpenGoAnim', 'pCloseGoAnim', 'pSHTokenObject'):
            getattr(self, n).mUnload()

    def mCheckKey(self, daKeyCode):
        if self.pEnabled:
            M.QuitKeyCheck(daKeyCode, 1)

    def mHuntObjectFound(self, theObject):
        M.gScreenDaddy.mEnable()
        M.resetCursor()

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
        S(self.pFrontSprite1).member = self.pFrontMember1
        S(self.pFrontSprite1).ink = 8
        self.pBottleObject.mShow()
        self.pOpenPlansFlag = 0
        self.mShowIngredients()
        self.pEnabled = 0
        if self.mAllPiecesDropped():
            self.mEnableGhostButtons()
            call_all(self.pGhostButtList, 'mShow')
            self.pMachineOnAnim.mShow()
        if sd.mGetLevel() == 1:
            self.pPlansOpenButton.mShow()
            if not self.pFirstTimeFlag and not sd.mAllTokensFound():
                self.pFirstTimeFlag = 1
                sd.mDisable()
                M.waitCursor()
                self.pTimerObject.mSetEventTag(Sym('FIRSTTIMEANIM'))
                self.pTimerObject.mSetTimeOutLength(0.5 * 1000)
                self.pTimerObject.mPlay()
            else:
                if self.mGetloosePieceCount():
                    if not self.pFirstTimeFlag:
                        self.pFirstTimeFlag = 1
                    M.resetCursor()
                    self.pTimerObject.mSetEventTag(Sym('PUTEMIN'))
                    self.pTimerObject.mSetTimeOutLength(0.5 * 1000)
                    self.pTimerObject.mPlay()
                else:
                    sd.mEnable()
                    M.resetCursor()
        elif sd.mGetLevel() == 2:
            if sd.mGetHuntIndex():
                sd.mShowScavengerHunt()
            self.pSHTokenObject.mShow()
            if self.mIsAllTokensFound():
                self.pTimerObject.mSetEventTag(Sym('OpenGoAnim'))
                self.pTimerObject.mSetTimeOutLength(1 * 1000)
                self.pTimerObject.mPlay()
            else:
                sd.mEnable()
                M.resetCursor()
        if not sd.mEnableReminders():
            pass

    def mShowGhostName(self, daNameMem):
        S(self.pGhostNameSprite).member = daNameMem
        S(self.pGhostNameSprite).loc = Point(320, 240)

    def mHideGhostName(self):
        S(self.pGhostNameSprite).member = M.getBlank()

    def mHide(self):
        blank(self.pBackSprite)
        blank(self.pFrontSprite1)
        self.pBackButton.mHide()
        self.pHelpButton.mHide()
        self.pMachineOnAnim.mHide()
        self.pSkellyAnimObject.mHide()
        call_all(self.pPartObjectList, 'mHide')
        call_all(self.pGhostButtList, 'mHide')
        self.pBottleObject.mHide()
        self.pGoButton.mHide()
        self.pSHTokenObject.mHide()
        self.pEnabled = 0

    def mAllPiecesDropped(self):
        for daPart in self.pPartObjectList:
            if not daPart.pDropped:
                return 0
        return 1

    def mGetloosePieceCount(self):
        loosepiececount = 0
        for daPart in self.pPartObjectList:
            if M.gScreenDaddy.mTokenFound(daPart.pTokenName):
                if not daPart.mGetSnapped():
                    loosepiececount += 1
        return loosepiececount

    def mHackIW(self):
        for i in range(len(self.pPartObjectList) - 1):
            self.pPartObjectList[i].pDropped = 1

    def mHACK_TOGHOSTHUNT(self):
        sd = M.gScreenDaddy
        for p in self.pPartObjectList:
            p.pDropped = 1
        self.pGhostButtonsActiveList = [1, 0, 0, 0, 0, 0, 0]
        self.pGhostButtonState = 0
        self.pFirstTimeFlag = 1
        self.pFirstGhostButtonFlag = 0
        self.pFirstGhostDoneFlag = 0
        fn = getattr(M, 'HACK_RIDDLES', None)
        if fn:
            fn(0)
        sd.mNextLevel()
        for daToken in ('lantern', 'BROKENBONE', 'RIP', 'HOURGLASS', 'CLOCK', 'domino', 'nails', 'oilcan', 'SPRING',
                        'gears', 'MOUSE', 'yarn', 'CAT', 'cheese', 'frog', 'SNAKE', 'spider', 'flies', 'eye',
                        'SHMAKE', 'GYMAKE', 'TTMAKE', 'RUMAKE', 'BCMAKE', 'CRMAKE', 'SKMAKE'):
            sd.mAddToken(Sym(daToken))

    def mShowIngredients(self):
        sd = M.gScreenDaddy
        if sd.mGetLevel() == 1:
            for Ing in self.pPartObjectList:
                if sd.mTokenFound(Ing.pTokenName):
                    Ing.mShow()
                    continue
                Ing.mHide()
        else:
            call_all(self.pPartObjectList, 'mShow')

    def mIsAllTokensFound(self):
        if self.pGhostButtonState:
            return 1 if self.pBottleObject.mIsAllTokensFound() else 0
        return 0

    def mAllGhostsMade(self):
        for i in range(6):
            if self.pGhostButtonsActiveList[i] == 1:
                return 0
        return 1

    def mGetPosOfIngByToken(self, daToken):
        num = 0
        for i in range(1, 17):
            if self.pPartObjectList[i - 1].mGetTokenName() == daToken:
                num = i
                break
        return num

    def mGetName(self):
        return self.pName

    def mGetType(self):
        return Sym('INVENTORSWORKSHOP')

    def mEnableGhostButtons(self):
        for i in range(len(self.pGhostButtonsActiveList)):
            if self.pGhostButtonsActiveList[i]:
                self.pGhostButtList[i].mActivate()
                continue
            self.pGhostButtList[i].mDeactivate()

    def mEnable(self):
        sd = M.gScreenDaddy
        call_all(self.pPartObjectList, 'mEnable')
        self.pBackButton.mEnable()
        self.pHelpButton.mEnable()
        if sd.mGetLevel() == 1:
            if self.pOpenPlansFlag:
                self.pPlansCloseButton.mEnable()
            else:
                self.pPlansOpenButton.mEnable()
        if sd.mGetLevel() == 2:
            call_all(self.pGhostButtList, 'mEnable')
            if self.pIsGoButtonOpen:
                self.pGoButton.mEnable()
            self.pSHTokenObject.mEnable()
        self.pEnabled = 1

    def mDisable(self):
        sd = M.gScreenDaddy
        self.pEnabled = 0
        call_all(self.pPartObjectList, 'mDisable')
        self.pBackButton.mDisable()
        self.pHelpButton.mDisable()
        if sd.mGetLevel() == 1:
            if self.pOpenPlansFlag:
                self.pPlansCloseButton.mDisable()
            else:
                self.pPlansOpenButton.mDisable()
        if sd.mGetLevel() == 2:
            call_all(self.pGhostButtList, 'mDisable')
            if self.pIsGoButtonOpen:
                _call_flag(self.pGoButton, 0)
            self.pSHTokenObject.mDisable()

    def mApplicationActivated(self):
        pass

    def mApplicationDeactivated(self):
        pass

    # ---- buttons --------------------------------------------------------------------------------
    def mButtonActivated(self, theObject):
        sd = M.gScreenDaddy
        if theObject is self.pHelpButton:
            sd.pHelpPlayer.mStartHelp()
        elif theObject is self.pBackButton:
            M.navigateBack()
        elif self.pPlansOpenButton is theObject:
            self.MOPENPLANS()
        elif self.pPlansCloseButton is theObject:
            self.mClosePlans()
        elif _get_pos(self.pGhostButtList, theObject):
            self.pGhostButtonStateCandidate = _get_pos(self.pGhostButtList, theObject)
            self.mHandleGhostButtonDown()
        elif theObject is self.pGoButton:
            self.mGoButtonDown()
        elif theObject is self.pSHTokenObject:
            self.pSHTokenObject.mUnload()
            self.pTimerObject.mSetEventTag(Sym('OpenGoAnim'))
            self.pTimerObject.mSetTimeOutLength(1 * 1000)
            self.pTimerObject.mPlay()

    def mButtonDeActivated(self, theObject):
        pass

    def MOPENPLANS(self):
        self.pPlansOpenButton.mHide()
        self.pOpenPlansAnim.mSetEventTag(Sym('OPENPLANS'))
        self.pOpenPlansAnim.mPlay()
        self.pOpenPlansFlag = 1

    def mClosePlans(self):
        self.pPlansCloseButton.mHide()
        self.pClosePlansAnim.mSetEventTag(Sym('CLOSEPLANS'))
        self.pClosePlansAnim.mPlay()
        self.pOpenPlansFlag = 0

    def mHandleGhostButtonDown(self):
        sd = M.gScreenDaddy
        sd.mDisable()
        cand = self.pGhostButtonStateCandidate
        if self.pGhostButtonsActiveList[cand - 1]:
            if self.pIsGoButtonOpen:
                self.pGhostBinkList[self.pGhostButtonState - 1].mUnload()
            self.pGhostButtonState = cand
            if sd.mGetHuntIndex():
                self.mReleaseScavHunt()
            self.pBottleObject.mSetEventTag(Sym('BOTTLES'))
            self.pBottleObject.mSetBottles(self.pGhostButtonState)
            if not self.mIsAllTokensFound() and self.pIsGoButtonOpen:
                _call_flag(self.pGoButton, 0)
        else:
            if cand == 7:
                self.pSkellyAnimObject.mSetEventTag(Sym('GHOSTBUTTONDOWN'))
                M.setInterruptMode(self.pSkellyAnimObject)
                self.pSkellyAnimObject.mSetSkellyVO(self.pNO7GhostVO)
                self.pSkellyAnimObject.mPlay()
            else:
                R().sound.puppet(1, self.pInactiveButtSound)
                sd.mEnable()
                M.resetCursor()

    def mGoButtonDown(self):
        if not self.mIsAllTokensFound():
            return
        sd = M.gScreenDaddy
        sd.mDisable()
        M.waitCursor()
        self.mReleaseScavHunt()
        if self.pGhostButtonState < 7:
            bink = self.pGhostBinkList[self.pGhostButtonState - 1]
            bink.mSetEventTag(Sym('GOBUTTONDOWN'))
            bink.mPlay()
        else:
            sd.mPlayFinale()

    # ---- play-done dispatch ---------------------------------------------------------------------
    def mPlayDone(self, theObject):
        t = _tag(theObject)
        fn = {'foundthemall': self.mHandleFoundThemAllDone,
              'dragging': self.mHandleDraggingDone,
              'openplans': self.mHandleOpenPlansDone,
              'closeplans': self.mHandleClosePlansDone,
              'firsttimeanim': self.mHandleFirstTimeAnimDone,
              'putemin': self.mHandlePutEmInDone,
              'bottles': self.mHandleBottlesDone,
              'opengoanim': self.mHandleOpenGoAnimDone,
              'closegoanim': self.mHandleCloseGoAnimDone,
              'gobuttondown': self.mHandleGoButtonDownDone,
              'ghostbuttondown': self.mHandleGhostButtonDownDone}.get(t)
        if fn:
            fn(theObject)

    def mHandleCloseGoAnimDone(self, theObject):
        # #CLOSEGOANIM is handled by a handler the original never defines (it is never raised)
        pass

    def mHandleFoundThemAllDone(self, theObject):
        if theObject is self.pSkellyAnimObject:
            theObject.mHide()
            self.mIncrementRecipe()          # not defined in the original either (never raised)

    def mHandleDraggingDone(self, theObject):
        sd = M.gScreenDaddy
        if _get_pos(self.pPartObjectList, theObject):
            if theObject.mGetSnapped():
                self.pSnapSound.mSetEventTag(Sym('DRAGGING'))
                self.pSnapSound.mPlay()
            else:
                sd.mEnable()
        else:
            if theObject is self.pSnapSound:
                if self.mAllPiecesDropped():
                    M.waitCursor()
                    self.pMachineOnAnim.mSetEventTag(Sym('DRAGGING'))
                    self.pMachineOnAnim.mPlay()
                    self.pDissolveBlendObject = M.getBlendDissolveObject(self)
                    self.pDissolveBlendObject.mSetBlendDissolve([self.pPlansOpenButton.pSprite], 1.5, 20, 0)
                    self.pDissolveBlendObject.mSetEventTag(Sym('DRAGGING'))
                    self.pDissolveBlendObject.mPlay()
                else:
                    sd.mEnable()
            else:
                if theObject is self.pMachineOnAnim:
                    for i in range(6):
                        self.pGhostButtList[i].mActivate()
                        self.pGhostButtList[i].mShow()
                    self.pGhostButtList[6].mDeactivate()
                    self.pGhostButtList[6].mShow()
                    self.pSkellyAnimObject.mSetEventTag(Sym('DRAGGING'))
                    self.pSkellyAnimObject.mSetSkellyVO(self.pMachineComplete)
                    self.pSkellyAnimObject.mPlay()
                    sd.mNextLevel()
                else:
                    if theObject is self.pSkellyAnimObject:
                        theObject.mHide()
                        sd.mEnable()
                        M.resetCursor()
                    else:
                        if theObject is self.pDissolveBlendObject:
                            self.pPlansOpenButton.mHide()
                            M.recycleBlendDissolve()

    def mHandleOpenPlansDone(self, theObject):
        theObject.mHide()
        self.pPlansCloseButton.mShow()
        M.gScreenDaddy.mEnable()
        call_all(self.pPartObjectList, 'mDisable')
        M.resetCursor()

    def mHandleClosePlansDone(self, theObject):
        theObject.mHide()
        self.pPlansOpenButton.mShow()
        M.gScreenDaddy.mEnable()
        M.resetCursor()

    def mHandleFirstTimeAnimDone(self, theObject):
        sd = M.gScreenDaddy
        sk = self.pSkellyAnimObject
        if theObject is self.pTimerObject:
            sk.mSetEventTag(Sym('FIRSTTIMEANIM'))
            sk.mSetSkellyVO(self.pFirstTimeAudio1)
            sk.mPlay()
        else:
            if (theObject is sk) and (sk.pSoundFile == self.pFirstTimeAudio1):
                theObject.mHide()
                self.pPlansOpenButton.mHide()
                self.pPlansWiggle.mSetEventTag(Sym('FIRSTTIMEANIM'))
                self.pPlansWiggle.mPlay()
            else:
                if theObject is self.pPlansWiggle:
                    theObject.mHide()
                    self.pPlansOpenButton.mShow()
                    self.pPlansOpenButton.mDisable()
                    sk.mSetEventTag(Sym('FIRSTTIMEANIM'))
                    sk.mSetSkellyVO(self.pFirstTimeAudio2)
                    sk.mPlay()
                else:
                    if (theObject is sk) and (sk.pSoundFile == self.pFirstTimeAudio2):
                        theObject.mHide()
                        sd.mEnable()
                        M.resetCursor()

    def mHandlePutEmInDone(self, theObject):
        if theObject is self.pTimerObject:
            self.pSkellyAnimObject.mSetEventTag(Sym('PUTEMIN'))
            M.setInterruptMode(self.pSkellyAnimObject)
            self.pSkellyAnimObject.mSetSkellyVO(self.pPiecesNotInAudio)
            self.pSkellyAnimObject.mPlay()
        else:
            if theObject is self.pSkellyAnimObject:
                theObject.mHide()
                M.gScreenDaddy.mEnable()
                M.resetCursor()

    def mHandleOpenGoAnimDone(self, theObject):
        sd = M.gScreenDaddy
        if theObject is self.pTimerObject:
            self.pOpenGoAnim.mSetEventTag(Sym('OpenGoAnim'))
            self.pOpenGoAnim.mPlay()
        else:
            if theObject is self.pOpenGoAnim:
                self.pGoButton.mShow()
                theObject.mHide()
                self.pIsGoButtonOpen = 1
                M.resetCursor()
                if self.pGhostButtonState < 7:
                    self.pGhostBinkList[self.pGhostButtonState - 1].mLoad()
                    sd.mEnable()
                else:
                    if not sd.mTokenFound(Sym('SK_GHOST')):
                        _call_flag(self.pGoButton, 1)
                        sd.mExternalSHTokenFound(self.pSHTokenObject)

    def mHandleBottlesDone(self, theObject):
        sd = M.gScreenDaddy
        if theObject is self.pBottleObject:
            if self.pFirstGhostButtonFlag:
                M.waitCursor()
                self.pFirstGhostButtonFlag = 0
                self.pSkellyAnimObject.mSetEventTag(Sym('BOTTLES'))
                self.pSkellyAnimObject.mSetSkellyVO(self.pBeforeFirstGhostVO)
                self.pSkellyAnimObject.mPlay()
            else:
                sd.mSetHuntIndex(self.pGhostButtonState)
                sd.mInitScavengerHuntPoolObjects()
                sd.mLoadScavengerHunt()
                sd.mShowScavengerHunt()
                allf = self.mIsAllTokensFound()
                if allf and not self.pIsGoButtonOpen:
                    self.pOpenGoAnim.mSetEventTag(Sym('OpenGoAnim'))
                    self.pOpenGoAnim.mPlay()
                else:
                    if not allf and self.pIsGoButtonOpen:
                        self.pGoButton.mHide()
                        self.pIsGoButtonOpen = 0
                        self.pCloseGoAnim.mSetEventTag(Sym('BOTTLES'))
                        self.pCloseGoAnim.mPlay()
                    else:
                        if allf and self.pIsGoButtonOpen:
                            self.pGhostBinkList[self.pGhostButtonState - 1].mLoad()
                            self.pGoButton.mEnable()
                            sd.mEnable()
                            M.resetCursor()
                        else:
                            sd.mEnable()
                            M.resetCursor()
        else:
            if theObject is self.pSkellyAnimObject:
                sd.mSetHuntIndex(self.pGhostButtonState)
                sd.mInitScavengerHuntPoolObjects()
                sd.mLoadScavengerHunt()
                sd.mShowScavengerHunt()
                sd.mEnable()
                M.resetCursor()
            else:
                if theObject is self.pCloseGoAnim:
                    theObject.mHide()
                    self.pIsGoButtonOpen = 0
                    sd.mEnable()
                    M.resetCursor()

    def mHandleGoButtonDownDone(self, theObject):
        sd = M.gScreenDaddy
        sk = self.pSkellyAnimObject
        if _get_pos(self.pGhostBinkList, theObject):
            self.pBottleObject.mSetBottlesNoSlide()
            R().update_stage()                    # + `set the stageColor to the stageColor` (forces a repaint)
            theObject.mUnload()
            self.pIsGoButtonOpen = 0
            _call_flag(self.pGoButton, 0)
            self.pTimerObject.mSetEventTag(Sym('GOBUTTONDOWN'))
            self.pTimerObject.mSetTimeOutLength(0.5 * 1000)
            self.pTimerObject.mPlay()
        else:
            if theObject is self.pTimerObject:
                self.pGoButton.mHide()
                self.pCloseGoAnim.mSetEventTag(Sym('GOBUTTONDOWN'))
                self.pCloseGoAnim.mPlay()
            else:
                if theObject is self.pCloseGoAnim:
                    self.pCloseGoAnim.mHide()
                    R().update_stage()
                    if self.pGhostButtonState < 7:
                        st = self.pGhostButtonState
                        self.pGhostButtList[st - 1].mDeactivate()
                        self.pGhostButtonsActiveList[st - 1] = 0
                        self.mHideGhostName()
                        sd.mAddToken(Sym(('SHMAKE', 'GYMAKE', 'TTMAKE', 'RUMAKE', 'BCMAKE', 'CRMAKE')[st - 1]))
                        if self.pFirstGhostDoneFlag:
                            self.pFirstGhostDoneFlag = 0
                            sk.mSetEventTag(Sym('GOBUTTONDOWN'))
                            sk.mSetSkellyVO(self.pAfterFirstGhostVO)
                            sk.mPlay()
                        else:
                            if self.mAllGhostsMade():
                                self.pBUTT7Wiggle.mSetEventTag(Sym('GOBUTTONDOWN'))
                                self.pBUTT7Wiggle.mPlay()
                            else:
                                self.pGhostButtonState = 0
                                sd.mEnable()
                                M.resetCursor()
                else:
                    if theObject is self.pBUTT7Wiggle:
                        self.pBUTT7Wiggle.mHide()
                        self.pGhostButtList[6].mActivate()
                        self.pGhostButtonsActiveList[6] = 1
                        sd.mAddToken(Sym('SKMAKE'))
                        sk.mSetEventTag(Sym('GOBUTTONDOWN'))
                        sk.mSetSkellyVO(self.pReady7GhostVO)
                        sk.mPlay()
                    else:
                        if (theObject is sk) and (sk.pSoundFile == self.pAfterFirstGhostVO):
                            self.pGhostButtonState = 0
                            sd.mEnable()
                            M.resetCursor()
                        else:
                            if (theObject is sk) and (sk.pSoundFile == self.pReady7GhostVO):
                                self.pGhostButtonState = 0
                                sd.mEnable()
                                M.resetCursor()

    def mHandleGhostButtonDownDone(self, theObject):
        sk = self.pSkellyAnimObject
        if (theObject is sk) and (sk.pSoundFile == self.pNO7GhostVO):
            theObject.mHide()
            M.gScreenDaddy.mEnable()
            M.resetCursor()

    def mReleaseScavHunt(self):
        sd = M.gScreenDaddy
        sd.mReleaseScavengerHuntPoolObjects()
        sd.mUnloadScavengerHunt()
        sd.mHideScavengerHunt()
        sd.mSetHuntIndex(0)

    def mHandlePlayQueue(self, theObject):
        theObject.mRecycle()
        M.resetCursor()
        M.gScreenDaddy.mEnable()

    def mHackShowScavengerHunt(self):
        pass

    def mUpdate(self):
        pass

    def mSetParent(self, theObject):
        self.pParent = theObject

    def mGetHelpState(self):
        return 0
