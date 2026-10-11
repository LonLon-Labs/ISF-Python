# Port of ProjectorRays src/lingodec/handler.cpp (MPL-2.0).
import struct

from .lingo_names import *   # noqa: F401,F403
from .lingo_names import StandardNames
from .lingo_ast import *     # noqa: F401,F403
from .lingo_ast import Datum, AST


class Bytecode:
    __slots__ = ('op_id', 'opcode', 'obj', 'pos', 'tag', 'owner_loop', 'translation')

    def __init__(self, op, obj, pos):
        self.op_id = op
        self.obj = obj
        self.pos = pos
        self.tag = kTagNone
        self.owner_loop = UINT32_MAX
        self.opcode = (0x40 + op % 0x40) if op >= 0x40 else op
        self.translation = None


def _idiv(a, b):
    return int(a / b)


def _pos_to_string(pos):
    return "[%3d]" % pos


class Handler:
    def __init__(self, script):
        self.script = script
        self.name_id = 0
        self.argument_name_ids = []
        self.local_name_ids = []
        self.global_name_ids = []
        self.bytecode_array = []
        self.bytecode_pos_map = {}
        self.argument_names = []
        self.local_names = []
        self.global_names = []
        self.name = ''
        self.stack = []
        self.ast = None
        self.is_generic_event = False
        self.stack_height = 0

    # ---- reading ----------------------------------------------------------------------------
    def read_record(self, stream):
        self.name_id = stream.read_i16()
        self.vector_pos = stream.read_u16()
        self.compiled_len = stream.read_u32()
        self.compiled_offset = stream.read_u32()
        self.argument_count = stream.read_u16()
        self.argument_offset = stream.read_u32()
        self.locals_count = stream.read_u16()
        self.locals_offset = stream.read_u32()
        self.globals_count = stream.read_u16()
        self.globals_offset = stream.read_u32()
        self.unknown1 = stream.read_u32()
        self.unknown2 = stream.read_u16()
        self.line_count = stream.read_u16()
        self.line_offset = stream.read_u32()
        if self.script.version >= 850:
            self.stack_height = stream.read_u32()

    def read_data(self, stream):
        stream.seek(self.compiled_offset)
        end = self.compiled_offset + self.compiled_len
        while stream.pos < end:
            pos = stream.pos - self.compiled_offset
            op = stream.read_u8()
            opcode = (0x40 + op % 0x40) if op >= 0x40 else op
            obj = 0
            if op >= 0xc0:
                obj = stream.read_i32()
            elif op >= 0x80:
                if opcode == kOpPushInt16 or opcode == kOpPushInt8:
                    obj = stream.read_i16()
                else:
                    obj = stream.read_u16()
            elif op >= 0x40:
                if opcode == kOpPushInt8:
                    obj = stream.read_i8()
                else:
                    obj = stream.read_u8()
            self.bytecode_array.append(Bytecode(op, obj, pos))
            self.bytecode_pos_map[pos] = len(self.bytecode_array) - 1

        self.argument_name_ids = self._read_varnames_table(stream, self.argument_count, self.argument_offset)
        self.local_name_ids = self._read_varnames_table(stream, self.locals_count, self.locals_offset)
        self.global_name_ids = self._read_varnames_table(stream, self.globals_count, self.globals_offset)

    @staticmethod
    def _read_varnames_table(stream, count, offset):
        stream.seek(offset)
        return [stream.read_u16() for _ in range(count)]

    def read_names(self):
        if not self.is_generic_event:
            self.name = self.get_name(self.name_id)
        for i, nid in enumerate(self.argument_name_ids):
            if i == 0 and self.script.is_factory():
                continue
            self.argument_names.append(self.get_name(nid))
        for nid in self.local_name_ids:
            if self.valid_name(nid):
                self.local_names.append(self.get_name(nid))
        for nid in self.global_name_ids:
            if self.valid_name(nid):
                self.global_names.append(self.get_name(nid))

    def valid_name(self, id_):
        return self.script.valid_name(id_)

    def get_name(self, id_):
        return self.script.get_name(id_)

    def get_argument_name(self, id_):
        if -1 < id_ < len(self.argument_name_ids):
            return self.get_name(self.argument_name_ids[id_])
        return "UNKNOWN_ARG_%d" % id_

    def get_local_name(self, id_):
        if -1 < id_ < len(self.local_name_ids):
            return self.get_name(self.local_name_ids[id_])
        return "UNKNOWN_LOCAL_%d" % id_

    # ---- stack ------------------------------------------------------------------------------
    def pop(self):
        if not self.stack:
            return ErrorNode()
        return self.stack.pop()

    def variable_multiplier(self):
        v = self.script.version
        if v >= 850:
            return 1
        if v >= 500:
            return 8
        return 6

    def read_var(self, var_type):
        cast_id = None
        if var_type == 0x6 and self.script.version >= 500:
            cast_id = self.pop()
        id_ = self.pop()
        if var_type in (0x1, 0x2, 0x3):
            return id_
        if var_type == 0x4:
            name = self.get_argument_name(_idiv(id_.get_value().i, self.variable_multiplier()))
            return LiteralNode(Datum(kDatumVarRef, name))
        if var_type == 0x5:
            name = self.get_local_name(_idiv(id_.get_value().i, self.variable_multiplier()))
            return LiteralNode(Datum(kDatumVarRef, name))
        if var_type == 0x6:
            return MemberExprNode("field", id_, cast_id)
        return ErrorNode()

    def get_var_name_from_set(self, bytecode):
        op = bytecode.opcode
        if op in (kOpSetGlobal, kOpSetGlobal2, kOpSetProp):
            return self.get_name(bytecode.obj)
        if op == kOpSetParam:
            return self.get_argument_name(_idiv(bytecode.obj, self.variable_multiplier()))
        if op == kOpSetLocal:
            return self.get_local_name(_idiv(bytecode.obj, self.variable_multiplier()))
        return "ERROR"

    def read_v4_property(self, property_type, property_id):
        sn = StandardNames
        if property_type == 0x00:
            if property_id <= 0x0b:
                return TheExprNode(sn.get_name(sn.moviePropertyNames, property_id))
            string = self.pop()
            return LastStringChunkExprNode(property_id - 0x0b, string)
        if property_type == 0x01:
            string = self.pop()
            return StringChunkCountExprNode(property_id, string)
        if property_type == 0x02:
            menu_id = self.pop()
            return MenuPropExprNode(menu_id, property_id)
        if property_type == 0x03:
            menu_id = self.pop()
            item_id = self.pop()
            return MenuItemPropExprNode(menu_id, item_id, property_id)
        if property_type == 0x04:
            sound_id = self.pop()
            return SoundPropExprNode(sound_id, property_id)
        if property_type == 0x05:
            return CommentNode("ERROR: Resource property")
        if property_type == 0x06:
            sprite_id = self.pop()
            return SpritePropExprNode(sprite_id, property_id)
        if property_type == 0x07:
            return TheExprNode(sn.get_name(sn.animationPropertyNames, property_id))
        if property_type == 0x08:
            if property_id == 0x02 and self.script.version >= 500:
                cast_lib = self.pop()
                if not (cast_lib.type == kLiteralNode and cast_lib.get_value().type == kDatumInt
                        and cast_lib.get_value().to_int() == 0):
                    cast_lib_node = MemberExprNode("castLib", cast_lib, None)
                    return ThePropExprNode(cast_lib_node, sn.get_name(sn.animation2PropertyNames, property_id))
            return TheExprNode(sn.get_name(sn.animation2PropertyNames, property_id))
        if 0x09 <= property_type <= 0x15:
            prop_name = sn.get_name(sn.memberPropertyNames, property_id)
            cast_id = None
            if self.script.version >= 500:
                cast_id = self.pop()
            member_id = self.pop()
            if property_type in (0x0b, 0x0c):
                prefix = "field"
            elif property_type in (0x14, 0x15):
                prefix = "script"
            else:
                prefix = "member" if self.script.version >= 500 else "cast"
            member = MemberExprNode(prefix, member_id, cast_id)
            if property_type in (0x0a, 0x0c, 0x15):
                entity = self.read_chunk_ref(member)
            else:
                entity = member
            return ThePropExprNode(entity, prop_name)
        return CommentNode("ERROR: Unknown property type %d" % property_type)

    def read_chunk_ref(self, string):
        last_line = self.pop()
        first_line = self.pop()
        last_item = self.pop()
        first_item = self.pop()
        last_word = self.pop()
        first_word = self.pop()
        last_char = self.pop()
        first_char = self.pop()

        def is_zero(n):
            return n.type == kLiteralNode and n.get_value().type == kDatumInt and n.get_value().to_int() == 0

        if not is_zero(first_line):
            string = ChunkExprNode(kChunkLine, first_line, last_line, string)
        if not is_zero(first_item):
            string = ChunkExprNode(kChunkItem, first_item, last_item, string)
        if not is_zero(first_word):
            string = ChunkExprNode(kChunkWord, first_word, last_word, string)
        if not is_zero(first_char):
            string = ChunkExprNode(kChunkChar, first_char, last_char, string)
        return string

    # ---- loop tagging -----------------------------------------------------------------------
    def tag_loops(self):
        arr = self.bytecode_array
        for start_index in range(len(arr)):
            jmpifz = arr[start_index]
            if jmpifz.opcode != kOpJmpIfZ:
                continue
            jmp_pos = jmpifz.pos + jmpifz.obj
            end_index = self.bytecode_pos_map.get(jmp_pos, 0)
            end_repeat = arr[end_index - 1]
            if end_repeat.opcode != kOpEndRepeat or ((end_repeat.pos - end_repeat.obj) & 0xFFFFFFFF) > jmpifz.pos:
                continue

            loop_type = self.identify_loop(start_index, end_index)
            arr[start_index].tag = loop_type

            if loop_type == kTagRepeatWithIn:
                for i in range(start_index - 7, start_index):
                    arr[i].tag = kTagSkip
                for i in range(start_index + 1, start_index + 6):
                    arr[i].tag = kTagSkip
                arr[end_index - 3].tag = kTagNextRepeatTarget
                arr[end_index - 3].owner_loop = start_index
                arr[end_index - 2].tag = kTagSkip
                arr[end_index - 1].tag = kTagSkip
                arr[end_index - 1].owner_loop = start_index
                arr[end_index].tag = kTagSkip
            elif loop_type in (kTagRepeatWithTo, kTagRepeatWithDownTo):
                condition_start_index = self.bytecode_pos_map.get(end_repeat.pos - end_repeat.obj, 0)
                arr[condition_start_index - 1].tag = kTagSkip
                arr[condition_start_index].tag = kTagSkip
                arr[start_index - 1].tag = kTagSkip
                arr[end_index - 5].tag = kTagNextRepeatTarget
                arr[end_index - 5].owner_loop = start_index
                arr[end_index - 4].tag = kTagSkip
                arr[end_index - 3].tag = kTagSkip
                arr[end_index - 2].tag = kTagSkip
                arr[end_index - 1].tag = kTagSkip
                arr[end_index - 1].owner_loop = start_index
            elif loop_type == kTagRepeatWhile:
                arr[end_index - 1].tag = kTagNextRepeatTarget
                arr[end_index - 1].owner_loop = start_index

    def is_repeat_with_in(self, start_index, end_index):
        arr = self.bytecode_array
        if start_index < 7 or start_index > len(arr) - 6:
            return False
        a = lambda i: arr[i]   # noqa: E731
        if not (a(start_index - 7).opcode == kOpPeek and a(start_index - 7).obj == 0):
            return False
        if not (a(start_index - 6).opcode == kOpPushArgList and a(start_index - 6).obj == 1):
            return False
        if not (a(start_index - 5).opcode == kOpExtCall and self.get_name(a(start_index - 5).obj) == "count"):
            return False
        if not (a(start_index - 4).opcode == kOpPushInt8 and a(start_index - 4).obj == 1):
            return False
        if not (a(start_index - 3).opcode == kOpPeek and a(start_index - 3).obj == 0):
            return False
        if not (a(start_index - 2).opcode == kOpPeek and a(start_index - 2).obj == 2):
            return False
        if not (a(start_index - 1).opcode == kOpLtEq):
            return False
        if not (a(start_index + 1).opcode == kOpPeek and a(start_index + 1).obj == 2):
            return False
        if not (a(start_index + 2).opcode == kOpPeek and a(start_index + 2).obj == 1):
            return False
        if not (a(start_index + 3).opcode == kOpPushArgList and a(start_index + 3).obj == 2):
            return False
        if not (a(start_index + 4).opcode == kOpExtCall and self.get_name(a(start_index + 4).obj) == "getAt"):
            return False
        if a(start_index + 5).opcode not in (kOpSetGlobal, kOpSetProp, kOpSetParam, kOpSetLocal):
            return False
        if end_index < 3:
            return False
        if not (a(end_index - 3).opcode == kOpPushInt8 and a(end_index - 3).obj == 1):
            return False
        if not (a(end_index - 2).opcode == kOpAdd):
            return False
        if not (a(end_index).opcode == kOpPop and a(end_index).obj == 3):
            return False
        return True

    def identify_loop(self, start_index, end_index):
        arr = self.bytecode_array
        if self.is_repeat_with_in(start_index, end_index):
            return kTagRepeatWithIn
        if start_index < 1:
            return kTagRepeatWhile
        prev = arr[start_index - 1].opcode
        if prev == kOpLtEq:
            up = True
        elif prev == kOpGtEq:
            up = False
        else:
            return kTagRepeatWhile

        end_repeat = arr[end_index - 1]
        condition_start_index = self.bytecode_pos_map.get(end_repeat.pos - end_repeat.obj, 0)
        if condition_start_index < 1:
            return kTagRepeatWhile

        set_op = arr[condition_start_index - 1].opcode
        get_map = {kOpSetGlobal: kOpGetGlobal, kOpSetGlobal2: kOpGetGlobal2, kOpSetProp: kOpGetProp,
                   kOpSetParam: kOpGetParam, kOpSetLocal: kOpGetLocal}
        if set_op not in get_map:
            return kTagRepeatWhile
        get_op = get_map[set_op]
        var_id = arr[condition_start_index - 1].obj

        if not (arr[condition_start_index].opcode == get_op and arr[condition_start_index].obj == var_id):
            return kTagRepeatWhile
        if end_index < 5:
            return kTagRepeatWhile
        want = 1 if up else -1
        if not (arr[end_index - 5].opcode == kOpPushInt8 and arr[end_index - 5].obj == want):
            return kTagRepeatWhile
        if not (arr[end_index - 4].opcode == get_op and arr[end_index - 4].obj == var_id):
            return kTagRepeatWhile
        if not (arr[end_index - 3].opcode == kOpAdd):
            return kTagRepeatWhile
        if not (arr[end_index - 2].opcode == set_op and arr[end_index - 2].obj == var_id):
            return kTagRepeatWhile
        return kTagRepeatWithTo if up else kTagRepeatWithDownTo

    # ---- translation ------------------------------------------------------------------------
    def parse(self):
        self.tag_loops()
        self.stack = []
        self.ast = AST(self)
        arr = self.bytecode_array
        i = 0
        while i < len(arr):
            bytecode = arr[i]
            pos = bytecode.pos
            # exit last block if at end
            while self.ast.current_block is not None and pos == self.ast.current_block.end_pos:
                exited_block = self.ast.current_block
                ancestor_stmt = self.ast.current_block.ancestor_statement()
                self.ast.exit_block()
                if ancestor_stmt is not None:
                    if ancestor_stmt.type == kIfStmtNode:
                        if ancestor_stmt.has_else and exited_block is ancestor_stmt.block1:
                            self.ast.enter_block(ancestor_stmt.block2)
                    elif ancestor_stmt.type == kCaseStmtNode:
                        case_label = self.ast.current_block.current_case_label if self.ast.current_block else None
                        if case_label is not None:
                            if case_label.expect == kCaseExpectOtherwise:
                                self.ast.current_block.current_case_label = None
                                ancestor_stmt.add_otherwise()
                                otherwise_index = self.bytecode_pos_map.get(ancestor_stmt.potential_otherwise_pos, 0)
                                arr[otherwise_index].translation = ancestor_stmt.otherwise
                                self.ast.enter_block(ancestor_stmt.otherwise.block)
                            elif case_label.expect == kCaseExpectEnd:
                                self.ast.current_block.current_case_label = None
            if self.ast.current_block is None:
                break
            i += self.translate_bytecode(bytecode, i)

    def translate_bytecode(self, bytecode, index):
        arr = self.bytecode_array
        script = self.script
        if bytecode.tag == kTagSkip or bytecode.tag == kTagNextRepeatTarget:
            return 1

        translation = None
        next_block = None
        op = bytecode.opcode

        if op in (kOpRet, kOpRetFactory):
            if index == len(arr) - 1:
                return 1
            translation = ExitStmtNode()
        elif op == kOpPushZero:
            translation = LiteralNode(Datum(kDatumInt, 0))
        elif op in (kOpMul, kOpAdd, kOpSub, kOpDiv, kOpMod, kOpJoinStr, kOpJoinPadStr, kOpLt, kOpLtEq,
                    kOpNtEq, kOpEq, kOpGt, kOpGtEq, kOpAnd, kOpOr, kOpContainsStr, kOpContains0Str):
            b = self.pop()
            a = self.pop()
            translation = BinaryOpNode(op, a, b)
        elif op == kOpInv:
            translation = InverseOpNode(self.pop())
        elif op == kOpNot:
            translation = NotOpNode(self.pop())
        elif op == kOpGetChunk:
            string = self.pop()
            translation = self.read_chunk_ref(string)
        elif op == kOpHiliteChunk:
            cast_id = None
            if script.version >= 500:
                cast_id = self.pop()
            field_id = self.pop()
            field = MemberExprNode("field", field_id, cast_id)
            chunk = self.read_chunk_ref(field)
            if chunk.type == kCommentNode:
                translation = chunk
            else:
                translation = ChunkHiliteStmtNode(chunk)
        elif op == kOpOntoSpr:
            second = self.pop()
            first = self.pop()
            translation = SpriteIntersectsExprNode(first, second)
        elif op == kOpIntoSpr:
            second = self.pop()
            first = self.pop()
            translation = SpriteWithinExprNode(first, second)
        elif op == kOpGetField:
            cast_id = None
            if script.version >= 500:
                cast_id = self.pop()
            field_id = self.pop()
            translation = MemberExprNode("field", field_id, cast_id)
        elif op == kOpStartTell:
            window = self.pop()
            tell = TellStmtNode(window)
            translation = tell
            next_block = tell.block
        elif op == kOpEndTell:
            self.ast.exit_block()
            return 1
        elif op == kOpPushList:
            lst = self.pop()
            lst.get_value().type = kDatumList
            translation = lst
        elif op == kOpPushPropList:
            lst = self.pop()
            lst.get_value().type = kDatumPropList
            translation = lst
        elif op == kOpSwap:
            if len(self.stack) >= 2:
                self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]
            return 1
        elif op in (kOpPushInt8, kOpPushInt16, kOpPushInt32):
            translation = LiteralNode(Datum(kDatumInt, bytecode.obj))
        elif op == kOpPushFloat32:
            f = struct.unpack('<f', struct.pack('<i', bytecode.obj))[0]
            translation = LiteralNode(Datum(kDatumFloat, f))
        elif op in (kOpPushArgListNoRet, kOpPushArgList):
            arg_count = bytecode.obj
            args = [None] * arg_count
            while arg_count:
                arg_count -= 1
                args[arg_count] = self.pop()
            dtype = kDatumArgListNoRet if op == kOpPushArgListNoRet else kDatumArgList
            translation = LiteralNode(Datum(dtype, args))
        elif op == kOpPushCons:
            literal_id = _idiv(bytecode.obj, self.variable_multiplier())
            if -1 < literal_id < len(script.literals):
                translation = LiteralNode(script.literals[literal_id].value)
            else:
                translation = ErrorNode()
        elif op == kOpPushSymb:
            translation = LiteralNode(Datum(kDatumSymbol, self.get_name(bytecode.obj)))
        elif op == kOpPushVarRef:
            translation = LiteralNode(Datum(kDatumVarRef, self.get_name(bytecode.obj)))
        elif op in (kOpGetGlobal, kOpGetGlobal2):
            translation = VarNode(self.get_name(bytecode.obj))
        elif op == kOpGetProp:
            translation = VarNode(self.get_name(bytecode.obj))
        elif op == kOpGetParam:
            translation = VarNode(self.get_argument_name(_idiv(bytecode.obj, self.variable_multiplier())))
        elif op == kOpGetLocal:
            translation = VarNode(self.get_local_name(_idiv(bytecode.obj, self.variable_multiplier())))
        elif op in (kOpSetGlobal, kOpSetGlobal2):
            var = VarNode(self.get_name(bytecode.obj))
            value = self.pop()
            translation = AssignmentStmtNode(var, value)
        elif op == kOpSetProp:
            var = VarNode(self.get_name(bytecode.obj))
            value = self.pop()
            translation = AssignmentStmtNode(var, value)
        elif op == kOpSetParam:
            var = VarNode(self.get_argument_name(_idiv(bytecode.obj, self.variable_multiplier())))
            value = self.pop()
            translation = AssignmentStmtNode(var, value)
        elif op == kOpSetLocal:
            var = VarNode(self.get_local_name(_idiv(bytecode.obj, self.variable_multiplier())))
            value = self.pop()
            translation = AssignmentStmtNode(var, value)
        elif op == kOpJmp:
            target_pos = bytecode.pos + bytecode.obj
            target_index = self.bytecode_pos_map.get(target_pos, 0)
            target_bytecode = arr[target_index]
            ancestor_loop = self.ast.current_block.ancestor_loop()
            done = False
            if ancestor_loop is not None:
                if arr[target_index - 1].opcode == kOpEndRepeat and arr[target_index - 1].owner_loop == ancestor_loop.start_index:
                    translation = ExitRepeatStmtNode()
                    done = True
                elif target_bytecode.tag == kTagNextRepeatTarget and target_bytecode.owner_loop == ancestor_loop.start_index:
                    translation = NextRepeatStmtNode()
                    done = True
            if not done:
                next_pos = arr[index + 1].pos if index + 1 < len(arr) else None
                ancestor_statement = self.ast.current_block.ancestor_statement()
                if ancestor_statement is not None and next_pos is not None and next_pos == self.ast.current_block.end_pos:
                    if ancestor_statement.type == kIfStmtNode:
                        if self.ast.current_block is ancestor_statement.block1:
                            ancestor_statement.has_else = True
                            ancestor_statement.block2.end_pos = target_pos
                            return 1
                    elif ancestor_statement.type == kCaseStmtNode:
                        ancestor_statement.potential_otherwise_pos = bytecode.pos
                        ancestor_statement.end_pos = target_pos
                        target_bytecode.tag = kTagEndCase
                        return 1
                if target_bytecode.opcode == kOpPop and target_bytecode.obj == 1:
                    value = self.pop()
                    case_stmt = CaseStmtNode(value)
                    case_stmt.end_pos = target_pos
                    target_bytecode.tag = kTagEndCase
                    case_stmt.add_otherwise()
                    translation = case_stmt
                    next_block = case_stmt.otherwise.block
                else:
                    translation = CommentNode("ERROR: Could not identify jmp")
        elif op == kOpEndRepeat:
            translation = CommentNode("ERROR: Stray endrepeat")
        elif op == kOpJmpIfZ:
            end_pos = bytecode.pos + bytecode.obj
            end_index = self.bytecode_pos_map.get(end_pos, 0)
            tag = bytecode.tag
            if tag == kTagRepeatWhile:
                condition = self.pop()
                loop = RepeatWhileStmtNode(index, condition)
                loop.block.end_pos = end_pos
                translation = loop
                next_block = loop.block
            elif tag == kTagRepeatWithIn:
                lst = self.pop()
                var_name = self.get_var_name_from_set(arr[index + 5])
                loop = RepeatWithInStmtNode(index, var_name, lst)
                loop.block.end_pos = end_pos
                translation = loop
                next_block = loop.block
            elif tag in (kTagRepeatWithTo, kTagRepeatWithDownTo):
                up = (tag == kTagRepeatWithTo)
                end = self.pop()
                start = self.pop()
                end_repeat = arr[end_index - 1]
                condition_start_index = self.bytecode_pos_map.get(end_repeat.pos - end_repeat.obj, 0)
                var_name = self.get_var_name_from_set(arr[condition_start_index - 1])
                loop = RepeatWithToStmtNode(index, var_name, start, up, end)
                loop.block.end_pos = end_pos
                translation = loop
                next_block = loop.block
            else:
                condition = self.pop()
                if_stmt = IfStmtNode(condition)
                if_stmt.block1.end_pos = end_pos
                translation = if_stmt
                next_block = if_stmt.block1
        elif op == kOpLocalCall:
            arg_list = self.pop()
            try:
                name = script.handlers[bytecode.obj].name
            except IndexError:
                name = "UNKNOWN_HANDLER_%d" % bytecode.obj
            translation = CallNode(name, arg_list)
        elif op in (kOpExtCall, kOpTellCall):
            name = self.get_name(bytecode.obj)
            arg_list = self.pop()
            is_statement = (arg_list.get_value().type == kDatumArgListNoRet)
            raw = arg_list.get_value().l
            nargs = len(raw)
            if (is_statement and name == "sound" and nargs > 0 and raw[0].type == kLiteralNode
                    and raw[0].get_value().type == kDatumSymbol):
                cmd = raw[0].get_value().s
                del raw[0]
                translation = SoundCmdStmtNode(cmd, arg_list)
            elif is_statement and name == "play" and nargs <= 2:
                translation = PlayCmdStmtNode(arg_list)
            else:
                translation = CallNode(name, arg_list)
        elif op == kOpObjCallV4:
            obj = self.read_var(bytecode.obj)
            arg_list = self.pop()
            raw = arg_list.get_value().l
            if len(raw) > 0:
                raw[0] = VarNode(raw[0].get_value().s)
            translation = ObjCallV4Node(obj, arg_list)
        elif op == kOpPut:
            put_type = (bytecode.obj >> 4) & 0xF
            var_type = bytecode.obj & 0xF
            var = self.read_var(var_type)
            val = self.pop()
            translation = PutStmtNode(put_type, var, val)
        elif op == kOpPutChunk:
            put_type = (bytecode.obj >> 4) & 0xF
            var_type = bytecode.obj & 0xF
            var = self.read_var(var_type)
            chunk = self.read_chunk_ref(var)
            val = self.pop()
            if chunk.type == kCommentNode:
                translation = chunk
            else:
                translation = PutStmtNode(put_type, chunk, val)
        elif op == kOpDeleteChunk:
            var = self.read_var(bytecode.obj)
            chunk = self.read_chunk_ref(var)
            if chunk.type == kCommentNode:
                translation = chunk
            else:
                translation = ChunkDeleteStmtNode(chunk)
        elif op == kOpGet:
            property_id = self.pop().get_value().to_int()
            translation = self.read_v4_property(bytecode.obj, property_id)
        elif op == kOpSet:
            property_id = self.pop().get_value().to_int()
            value = self.pop()
            if (bytecode.obj == 0x00 and 0x01 <= property_id <= 0x05
                    and value.get_value().type == kDatumString):
                script_text = value.get_value().s
                if len(script_text) > 0 and (script_text[0] == ' ' or '\r' in script_text):
                    translation = WhenStmtNode(property_id, script_text)
            if translation is None:
                prop = self.read_v4_property(bytecode.obj, property_id)
                if prop.type == kCommentNode:
                    translation = prop
                else:
                    translation = AssignmentStmtNode(prop, value, True)
        elif op == kOpGetMovieProp:
            translation = TheExprNode(self.get_name(bytecode.obj))
        elif op == kOpSetMovieProp:
            value = self.pop()
            prop = TheExprNode(self.get_name(bytecode.obj))
            translation = AssignmentStmtNode(prop, value)
        elif op in (kOpGetObjProp, kOpGetChainedProp):
            obj = self.pop()
            translation = ObjPropExprNode(obj, self.get_name(bytecode.obj))
        elif op == kOpSetObjProp:
            value = self.pop()
            obj = self.pop()
            prop = ObjPropExprNode(obj, self.get_name(bytecode.obj))
            translation = AssignmentStmtNode(prop, value)
        elif op == kOpPeek:
            return self._translate_peek(bytecode, index)
        elif op == kOpPop:
            if bytecode.tag == kTagEndCase:
                bytecode.translation = EndCaseNode()
                return 1
            if bytecode.obj == 1 and len(self.stack) == 1:
                value = self.pop()
                translation = CaseStmtNode(value)
            else:
                return 1
        elif op == kOpTheBuiltin:
            self.pop()
            translation = TheExprNode(self.get_name(bytecode.obj))
        elif op == kOpObjCall:
            translation = self._translate_objcall(bytecode)
        elif op == kOpPushChunkVarRef:
            translation = self.read_var(bytecode.obj)
        elif op == kOpGetTopLevelProp:
            translation = VarNode(self.get_name(bytecode.obj))
        elif op == kOpNewObj:
            obj_type = self.get_name(bytecode.obj)
            obj_args = self.pop()
            translation = NewObjNode(obj_type, obj_args)
        else:
            comment_text = StandardNames.get_opcode_name(bytecode.op_id)
            if bytecode.opcode >= 0x40:
                comment_text += " %d" % bytecode.obj
            translation = CommentNode(comment_text)
            self.stack = []

        if translation is None:
            translation = ErrorNode()

        bytecode.translation = translation
        if translation.is_expression:
            self.stack.append(translation)
        else:
            self.ast.add_statement(translation)

        if next_block is not None:
            self.ast.enter_block(next_block)
        return 1

    def _translate_peek(self, bytecode, index):
        arr = self.bytecode_array
        prev_label = self.ast.current_block.current_case_label

        original_stack_size = len(self.stack)
        curr_index = index + 1
        curr = arr[curr_index]
        while True:
            self.translate_bytecode(curr, curr_index)
            curr_index += 1
            if curr_index >= len(arr):
                break
            curr = arr[curr_index]
            if len(self.stack) == original_stack_size + 1 and curr.opcode in (kOpEq, kOpNtEq):
                break
        if curr_index >= len(arr):
            bytecode.translation = CommentNode("ERROR: Expected eq or nteq!")
            self.ast.add_statement(bytecode.translation)
            return curr_index - index + 1

        not_eq = (curr.opcode == kOpNtEq)
        case_value = self.pop()

        curr_index += 1
        if curr_index >= len(arr) or arr[curr_index].opcode != kOpJmpIfZ:
            bytecode.translation = CommentNode("ERROR: Expected jmpifz!")
            self.ast.add_statement(bytecode.translation)
            return curr_index - index + 1
        curr = arr[curr_index]

        jmpifz = curr
        jmp_pos = jmpifz.pos + jmpifz.obj
        target_index = self.bytecode_pos_map.get(jmp_pos, 0)
        target_bytecode = arr[target_index]
        prev_from_target = arr[target_index - 1]
        if not_eq:
            expect = kCaseExpectOr
        elif target_bytecode.opcode == kOpPeek:
            expect = kCaseExpectNext
        elif (target_bytecode.opcode == kOpPop and target_bytecode.obj == 1
              and (prev_from_target.opcode != kOpJmp
                   or prev_from_target.pos + prev_from_target.obj == target_bytecode.pos)):
            expect = kCaseExpectEnd
        else:
            expect = kCaseExpectOtherwise

        curr_label = CaseLabelNode(case_value, expect)
        jmpifz.translation = curr_label
        self.ast.current_block.current_case_label = curr_label

        if prev_label is None:
            peeked_value = self.pop()
            case_stmt = CaseStmtNode(peeked_value)
            case_stmt.first_label = curr_label
            curr_label.parent = case_stmt
            bytecode.translation = case_stmt
            self.ast.add_statement(case_stmt)
        elif prev_label.expect == kCaseExpectOr:
            prev_label.next_or = curr_label
            curr_label.parent = prev_label
        elif prev_label.expect == kCaseExpectNext:
            prev_label.next_label = curr_label
            curr_label.parent = prev_label

        if curr_label.expect != kCaseExpectOr:
            curr_label.block = BlockNode()
            curr_label.block.parent = curr_label
            curr_label.block.end_pos = jmp_pos
            self.ast.enter_block(curr_label.block)

        return curr_index - index + 1

    def _translate_objcall(self, bytecode):
        method = self.get_name(bytecode.obj)
        arg_list = self.pop()
        raw = arg_list.get_value().l
        nargs = len(raw)

        def is_sym(n):
            return raw[n].get_value().type == kDatumSymbol

        if method == "getAt" and nargs == 2:
            return ObjBracketExprNode(raw[0], raw[1])
        if method == "setAt" and nargs == 3:
            prop_expr = ObjBracketExprNode(raw[0], raw[1])
            return AssignmentStmtNode(prop_expr, raw[2])
        if method in ("getProp", "getPropRef") and nargs in (3, 4) and is_sym(1):
            obj = raw[0]
            prop_name = raw[1].get_value().s
            i = raw[2]
            i2 = raw[3] if nargs == 4 else None
            return ObjPropIndexExprNode(obj, prop_name, i, i2)
        if method == "setProp" and nargs in (4, 5) and is_sym(1):
            obj = raw[0]
            prop_name = raw[1].get_value().s
            i = raw[2]
            i2 = raw[3] if nargs == 5 else None
            prop_expr = ObjPropIndexExprNode(obj, prop_name, i, i2)
            return AssignmentStmtNode(prop_expr, raw[nargs - 1])
        if method == "count" and nargs == 2 and is_sym(1):
            obj = raw[0]
            prop_name = raw[1].get_value().s
            prop_expr = ObjPropExprNode(obj, prop_name)
            return ObjPropExprNode(prop_expr, "count")
        if method in ("setContents", "setContentsAfter", "setContentsBefore") and nargs == 2:
            put_type = {"setContents": kPutInto, "setContentsAfter": kPutAfter}.get(method, kPutBefore)
            return PutStmtNode(put_type, raw[0], raw[1])
        if method == "hilite" and nargs == 1:
            return ChunkHiliteStmtNode(raw[0])
        if method == "delete" and nargs == 1:
            return ChunkDeleteStmtNode(raw[0])
        return ObjCallNode(method, arg_list)

    # ---- bytecode listing (.lasm) -----------------------------------------------------------
    def write_bytecode_text(self, code, dot_syntax):
        is_method = self.script.is_factory()
        if not self.is_generic_event:
            code.write("method " if is_method else "on ")
            code.write(self.name)
            if len(self.argument_names) > 0:
                code.write(" ")
                for i, n in enumerate(self.argument_names):
                    if i > 0:
                        code.write(", ")
                    code.write(n)
            code.write_line()
            code.indent()
        for bc in self.bytecode_array:
            code.write(_pos_to_string(bc.pos))
            code.write(" ")
            code.write(StandardNames.get_opcode_name(bc.op_id))
            if bc.opcode in (kOpJmp, kOpJmpIfZ):
                code.write(" ")
                code.write(_pos_to_string(bc.pos + bc.obj))
            elif bc.opcode == kOpEndRepeat:
                code.write(" ")
                code.write(_pos_to_string(bc.pos - bc.obj))
            elif bc.opcode == kOpPushFloat32:
                from .lingo_names import float_to_string
                code.write(" ")
                code.write(float_to_string(struct.unpack('<f', struct.pack('<i', bc.obj))[0]))
            else:
                if bc.op_id > 0x40:
                    code.write(" ")
                    code.write(str(bc.obj))
            if bc.translation is not None:
                code.write(" ...")
                while code.line_width < 49:
                    code.write(".")
                code.write(" ")
                if bc.translation.is_expression:
                    code.write("<")
                bc.translation.write_script_text(code, dot_syntax, True)
                if bc.translation.is_expression:
                    code.write(">")
            code.write_line()
        if not self.is_generic_event:
            code.unindent()
            if not is_method:
                code.write_line("end")
