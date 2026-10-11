# Port of ProjectorRays src/lingodec/enums.h and names.cpp (MPL-2.0).

# ---- OpCode ---------------------------------------------------------------------------------
kOpRet = 0x01
kOpRetFactory = 0x02
kOpPushZero = 0x03
kOpMul = 0x04
kOpAdd = 0x05
kOpSub = 0x06
kOpDiv = 0x07
kOpMod = 0x08
kOpInv = 0x09
kOpJoinStr = 0x0a
kOpJoinPadStr = 0x0b
kOpLt = 0x0c
kOpLtEq = 0x0d
kOpNtEq = 0x0e
kOpEq = 0x0f
kOpGt = 0x10
kOpGtEq = 0x11
kOpAnd = 0x12
kOpOr = 0x13
kOpNot = 0x14
kOpContainsStr = 0x15
kOpContains0Str = 0x16
kOpGetChunk = 0x17
kOpHiliteChunk = 0x18
kOpOntoSpr = 0x19
kOpIntoSpr = 0x1a
kOpGetField = 0x1b
kOpStartTell = 0x1c
kOpEndTell = 0x1d
kOpPushList = 0x1e
kOpPushPropList = 0x1f
kOpSwap = 0x21

kOpPushInt8 = 0x41
kOpPushArgListNoRet = 0x42
kOpPushArgList = 0x43
kOpPushCons = 0x44
kOpPushSymb = 0x45
kOpPushVarRef = 0x46
kOpGetGlobal2 = 0x48
kOpGetGlobal = 0x49
kOpGetProp = 0x4a
kOpGetParam = 0x4b
kOpGetLocal = 0x4c
kOpSetGlobal2 = 0x4e
kOpSetGlobal = 0x4f
kOpSetProp = 0x50
kOpSetParam = 0x51
kOpSetLocal = 0x52
kOpJmp = 0x53
kOpEndRepeat = 0x54
kOpJmpIfZ = 0x55
kOpLocalCall = 0x56
kOpExtCall = 0x57
kOpObjCallV4 = 0x58
kOpPut = 0x59
kOpPutChunk = 0x5a
kOpDeleteChunk = 0x5b
kOpGet = 0x5c
kOpSet = 0x5d
kOpGetMovieProp = 0x5f
kOpSetMovieProp = 0x60
kOpGetObjProp = 0x61
kOpSetObjProp = 0x62
kOpTellCall = 0x63
kOpPeek = 0x64
kOpPop = 0x65
kOpTheBuiltin = 0x66
kOpObjCall = 0x67
kOpPushChunkVarRef = 0x6d
kOpPushInt16 = 0x6e
kOpPushInt32 = 0x6f
kOpGetChainedProp = 0x70
kOpPushFloat32 = 0x71
kOpGetTopLevelProp = 0x72
kOpNewObj = 0x73

# ---- DatumType ------------------------------------------------------------------------------
(kDatumVoid, kDatumSymbol, kDatumVarRef, kDatumString, kDatumInt, kDatumFloat,
 kDatumList, kDatumArgList, kDatumArgListNoRet, kDatumPropList) = range(10)

# ---- ChunkExprType / PutType ----------------------------------------------------------------
kChunkChar = 0x01
kChunkWord = 0x02
kChunkItem = 0x03
kChunkLine = 0x04

kPutInto = 0x01
kPutAfter = 0x02
kPutBefore = 0x03

# ---- NodeType -------------------------------------------------------------------------------
(kNoneNode, kErrorNode, kTempNode, kCommentNode, kLiteralNode, kBlockNode, kHandlerNode, kExitStmtNode,
 kInverseOpNode, kNotOpNode, kBinaryOpNode, kChunkExprNode, kChunkHiliteStmtNode, kChunkDeleteStmtNode,
 kSpriteIntersectsExprNode, kSpriteWithinExprNode, kMemberExprNode, kVarNode, kAssignmentStmtNode,
 kIfStmtNode, kRepeatWhileStmtNode, kRepeatWithInStmtNode, kRepeatWithToStmtNode, kCaseStmtNode,
 kCaseLabelNode, kOtherwiseNode, kEndCaseNode, kTellStmtNode, kSoundCmdStmtNode, kPlayCmdStmtNode,
 kCallNode, kObjCallNode, kObjCallV4Node, kTheExprNode, kLastStringChunkExprNode,
 kStringChunkCountExprNode, kMenuPropExprNode, kMenuItemPropExprNode, kSoundPropExprNode,
 kSpritePropExprNode, kThePropExprNode, kObjPropExprNode, kObjBracketExprNode, kObjPropIndexExprNode,
 kExitRepeatStmtNode, kNextRepeatStmtNode, kPutStmtNode, kWhenStmtNode, kNewObjNode) = range(49)

# ---- BytecodeTag / CaseExpect ---------------------------------------------------------------
(kTagNone, kTagSkip, kTagRepeatWhile, kTagRepeatWithIn, kTagRepeatWithTo, kTagRepeatWithDownTo,
 kTagNextRepeatTarget, kTagEndCase) = range(8)

(kCaseExpectEnd, kCaseExpectOr, kCaseExpectNext, kCaseExpectOtherwise) = range(4)

# ---- ScriptFlag / LiteralType ---------------------------------------------------------------
kScriptFlagFactoryDef = 1 << 0x4
kScriptFlagEventScript = 1 << 0x9

kLiteralString = 1
kLiteralInt = 4
kLiteralFloat = 9

UINT32_MAX = 0xFFFFFFFF


class StandardNames:
    opcodeNames = {
        kOpRet: "ret", kOpRetFactory: "retfactory", kOpPushZero: "pushzero", kOpMul: "mul", kOpAdd: "add",
        kOpSub: "sub", kOpDiv: "div", kOpMod: "mod", kOpInv: "inv", kOpJoinStr: "joinstr",
        kOpJoinPadStr: "joinpadstr", kOpLt: "lt", kOpLtEq: "lteq", kOpNtEq: "nteq", kOpEq: "eq", kOpGt: "gt",
        kOpGtEq: "gteq", kOpAnd: "and", kOpOr: "or", kOpNot: "not", kOpContainsStr: "containsstr",
        kOpContains0Str: "contains0str", kOpGetChunk: "getchunk", kOpHiliteChunk: "hilitechunk",
        kOpOntoSpr: "ontospr", kOpIntoSpr: "intospr", kOpGetField: "getfield", kOpStartTell: "starttell",
        kOpEndTell: "endtell", kOpPushList: "pushlist", kOpPushPropList: "pushproplist", kOpSwap: "swap",
        kOpPushInt8: "pushint8", kOpPushArgListNoRet: "pusharglistnoret", kOpPushArgList: "pusharglist",
        kOpPushCons: "pushcons", kOpPushSymb: "pushsymb", kOpPushVarRef: "pushvarref",
        kOpGetGlobal2: "getglobal2", kOpGetGlobal: "getglobal", kOpGetProp: "getprop",
        kOpGetParam: "getparam", kOpGetLocal: "getlocal", kOpSetGlobal2: "setglobal2",
        kOpSetGlobal: "setglobal", kOpSetProp: "setprop", kOpSetParam: "setparam", kOpSetLocal: "setlocal",
        kOpJmp: "jmp", kOpEndRepeat: "endrepeat", kOpJmpIfZ: "jmpifz", kOpLocalCall: "localcall",
        kOpExtCall: "extcall", kOpObjCallV4: "objcallv4", kOpPut: "put", kOpPutChunk: "putchunk",
        kOpDeleteChunk: "deletechunk", kOpGet: "get", kOpSet: "set", kOpGetMovieProp: "getmovieprop",
        kOpSetMovieProp: "setmovieprop", kOpGetObjProp: "getobjprop", kOpSetObjProp: "setobjprop",
        kOpTellCall: "tellcall", kOpPeek: "peek", kOpPop: "pop", kOpTheBuiltin: "thebuiltin",
        kOpObjCall: "objcall", kOpPushChunkVarRef: "pushchunkvarref", kOpPushInt16: "pushint16",
        kOpPushInt32: "pushint32", kOpGetChainedProp: "getchainedprop", kOpPushFloat32: "pushfloat32",
        kOpGetTopLevelProp: "gettoplevelprop", kOpNewObj: "newobj",
    }

    binaryOpNames = {
        kOpMul: "*", kOpAdd: "+", kOpSub: "-", kOpDiv: "/", kOpMod: "mod", kOpJoinStr: "&",
        kOpJoinPadStr: "&&", kOpLt: "<", kOpLtEq: "<=", kOpNtEq: "<>", kOpEq: "=", kOpGt: ">",
        kOpGtEq: ">=", kOpAnd: "and", kOpOr: "or", kOpContainsStr: "contains", kOpContains0Str: "starts",
    }

    chunkTypeNames = {kChunkChar: "char", kChunkWord: "word", kChunkItem: "item", kChunkLine: "line"}

    putTypeNames = {kPutInto: "into", kPutAfter: "after", kPutBefore: "before"}

    moviePropertyNames = {
        0x00: "floatPrecision", 0x01: "mouseDownScript", 0x02: "mouseUpScript", 0x03: "keyDownScript",
        0x04: "keyUpScript", 0x05: "timeoutScript", 0x06: "short time", 0x07: "abbr time",
        0x08: "long time", 0x09: "short date", 0x0a: "abbr date", 0x0b: "long date",
    }

    whenEventNames = {0x01: "mouseDown", 0x02: "mouseUp", 0x03: "keyDown", 0x04: "keyUp", 0x05: "timeOut"}

    menuPropertyNames = {0x01: "name", 0x02: "number of menuItems"}

    menuItemPropertyNames = {0x01: "name", 0x02: "checkMark", 0x03: "enabled", 0x04: "script"}

    soundPropertyNames = {0x01: "volume"}

    spritePropertyNames = {
        0x01: "type", 0x02: "backColor", 0x03: "bottom", 0x04: "castNum", 0x05: "constraint",
        0x06: "cursor", 0x07: "foreColor", 0x08: "height", 0x09: "immediate", 0x0a: "ink", 0x0b: "left",
        0x0c: "lineSize", 0x0d: "locH", 0x0e: "locV", 0x0f: "movieRate", 0x10: "movieTime",
        0x11: "pattern", 0x12: "puppet", 0x13: "right", 0x14: "startTime", 0x15: "stopTime",
        0x16: "stretch", 0x17: "top", 0x18: "trails", 0x19: "visible", 0x1a: "volume", 0x1b: "width",
        0x1c: "blend", 0x1d: "scriptNum", 0x1e: "moveableSprite", 0x1f: "editableText",
        0x20: "scoreColor", 0x21: "loc", 0x22: "rect", 0x23: "memberNum", 0x24: "castLibNum",
        0x25: "member", 0x26: "scriptInstanceList", 0x27: "currentTime", 0x28: "mostRecentCuePoint",
        0x29: "tweened", 0x2a: "name",
    }

    animationPropertyNames = {
        0x01: "beepOn", 0x02: "buttonStyle", 0x03: "centerStage", 0x04: "checkBoxAccess",
        0x05: "checkboxType", 0x06: "colorDepth", 0x07: "colorQD", 0x08: "exitLock", 0x09: "fixStageSize",
        0x0a: "fullColorPermit", 0x0b: "imageDirect", 0x0c: "doubleClick", 0x0d: "key", 0x0e: "lastClick",
        0x0f: "lastEvent", 0x10: "keyCode", 0x11: "lastKey", 0x12: "lastRoll", 0x13: "timeoutLapsed",
        0x14: "multiSound", 0x15: "pauseState", 0x16: "quickTimePresent", 0x17: "selEnd",
        0x18: "selStart", 0x19: "soundEnabled", 0x1a: "soundLevel", 0x1b: "stageColor",
        0x1d: "switchColorDepth", 0x1e: "timeoutKeyDown", 0x1f: "timeoutLength", 0x20: "timeoutMouse",
        0x21: "timeoutPlay", 0x22: "timer", 0x23: "preLoadRAM", 0x24: "videoForWindowsPresent",
        0x25: "netPresent", 0x26: "safePlayer", 0x27: "soundKeepDevice", 0x28: "soundMixMedia",
    }

    animation2PropertyNames = {
        0x01: "perFrameHook", 0x02: "number of castMembers", 0x03: "number of menus",
        0x04: "number of castLibs", 0x05: "number of xtras",
    }

    memberPropertyNames = {
        0x01: "name", 0x02: "text", 0x03: "textStyle", 0x04: "textFont", 0x05: "textHeight",
        0x06: "textAlign", 0x07: "textSize", 0x08: "picture", 0x09: "hilite", 0x0a: "number", 0x0b: "size",
        0x0c: "loop", 0x0d: "duration", 0x0e: "controller", 0x0f: "directToStage", 0x10: "sound",
        0x11: "foreColor", 0x12: "backColor", 0x13: "type",
    }

    @staticmethod
    def get_opcode_name(op_id):
        if op_id >= 0x40:
            op_id = 0x40 + op_id % 0x40
        name = StandardNames.opcodeNames.get(op_id)
        if name is None:
            return "unk%02X" % op_id
        return name

    @staticmethod
    def get_name(name_map, id_):
        return name_map.get(id_, "ERROR")


class ScriptNames:
    def __init__(self, version):
        self.version = version
        self.names = []

    def read(self, stream):
        stream.endian = '>'     # Lingo scripts are always big endian
        self.unknown0 = stream.read_i32()
        self.unknown1 = stream.read_i32()
        self.len1 = stream.read_u32()
        self.len2 = stream.read_u32()
        self.names_offset = stream.read_u16()
        self.names_count = stream.read_u16()
        stream.seek(self.names_offset)
        self.names = []
        for _ in range(self.names_count):
            length = stream.read_u8()
            self.names.append(stream.read_string(length))

    def valid_name(self, id_):
        return -1 < id_ < len(self.names)

    def get_name(self, id_):
        if self.valid_name(id_):
            return self.names[id_]
        return "UNKNOWN_NAME_%d" % id_


class CodeWriter:
    def __init__(self, line_ending='\n', indentation='  '):
        self._parts = []
        self._line_ending = line_ending
        self._indentation = indentation
        self._level = 0
        self._indent_written = False
        self._line_width = 0
        self._size = 0
        self.do_indentation = True

    def _write_indentation(self):
        if self._indent_written or not self.do_indentation:
            return
        for _ in range(self._level):
            self._parts.append(self._indentation)
        self._indent_written = True
        self._line_width = self._level * len(self._indentation)
        self._size += self._line_width

    def write(self, s):
        if not s:
            return
        self._write_indentation()
        self._parts.append(s)
        self._line_width += len(s)
        self._size += len(s)

    def write_line(self, s=''):
        if not s:
            self._parts.append(self._line_ending)
            self._indent_written = False
            self._line_width = 0
            self._size += len(self._line_ending)
            return
        self._write_indentation()
        self._parts.append(s)
        self._parts.append(self._line_ending)
        self._indent_written = False
        self._line_width = 0
        self._size += len(s) + len(self._line_ending)

    def indent(self):
        self._level += 1

    def unindent(self):
        if self._level > 0:
            self._level -= 1

    def str(self):
        return ''.join(self._parts)

    @property
    def line_width(self):
        return self._line_width

    @property
    def size(self):
        return self._size


def float_to_string(f):
    """std::fixed with max_digits10 (17) digits, then trailing zeros trimmed down to one decimal."""
    if f != f:
        return 'nan'
    if f in (float('inf'), float('-inf')):
        return 'inf' if f > 0 else '-inf'
    res = '%.17f' % f
    while res[-1] == '0' and res[-2] != '.':
        res = res[:-1]
    return res


def escape_string(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif ch == '\b':
            out.append('\\b')
        elif ch == '\f':
            out.append('\\f')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\r':
            out.append('\\r')
        elif ch == '\t':
            out.append('\\t')
        elif ch == '\v':
            out.append('\\v')
        elif o < 0x20 or o > 0x7f:
            out.append('\\x%02X' % (o & 0xFF))
        else:
            out.append(ch)
    return ''.join(out)
