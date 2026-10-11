# Port of ProjectorRays src/lingodec/ast.h / ast.cpp (MPL-2.0).
from .lingo_names import *   # noqa: F401,F403
from .lingo_names import StandardNames, escape_string, float_to_string


def _is_int_literal(node, value):
    return node.type == kLiteralNode and node.get_value().type == kDatumInt and node.get_value().i == value


# ---------------------------------------------------------------------------------------------
class Datum:
    def __init__(self, type_=kDatumVoid, value=None):
        self.type = type_
        self.i = 0
        self.f = 0.0
        self.s = ''
        self.l = []
        if type_ == kDatumInt:
            self.i = value
        elif type_ == kDatumFloat:
            self.f = value
        elif type_ in (kDatumSymbol, kDatumVarRef, kDatumString):
            self.s = value
        elif type_ in (kDatumList, kDatumArgList, kDatumArgListNoRet, kDatumPropList):
            self.l = value if value is not None else []

    def to_int(self):
        if self.type == kDatumInt:
            return self.i
        if self.type == kDatumFloat:
            try:
                return int(self.f)
            except (OverflowError, ValueError):
                return 0
        return 0

    def write_script_text(self, code, dot, sum_):
        t = self.type
        if t == kDatumVoid:
            code.write("VOID")
        elif t == kDatumSymbol:
            code.write("#" + self.s)
        elif t == kDatumVarRef:
            code.write(self.s)
        elif t == kDatumString:
            s = self.s
            if len(s) == 0:
                code.write("EMPTY")
                return
            if len(s) == 1:
                special = {'\x03': "ENTER", '\x08': "BACKSPACE", '\t': "TAB", '\r': "RETURN", '"': "QUOTE"}
                if s in special:
                    code.write(special[s])
                    return
            if sum_:
                code.write('"' + escape_string(s) + '"')
                return
            code.write('"' + s + '"')
        elif t == kDatumInt:
            code.write(str(self.i))
        elif t == kDatumFloat:
            code.write(float_to_string(self.f))
        elif t in (kDatumList, kDatumArgList, kDatumArgListNoRet):
            if t == kDatumList:
                code.write("[")
            for n, item in enumerate(self.l):
                if n > 0:
                    code.write(", ")
                item.write_script_text(code, dot, sum_)
            if t == kDatumList:
                code.write("]")
        elif t == kDatumPropList:
            code.write("[")
            if len(self.l) == 0:
                code.write(":")
            else:
                for n in range(0, len(self.l), 2):
                    if n > 0:
                        code.write(", ")
                    self.l[n].write_script_text(code, dot, sum_)
                    code.write(": ")
                    self.l[n + 1].write_script_text(code, dot, sum_)
            code.write("]")


# ---------------------------------------------------------------------------------------------
class Node:
    def __init__(self, type_):
        self.type = type_
        self.is_expression = False
        self.is_statement = False
        self.is_label = False
        self.is_loop = False
        self.parent = None

    def write_script_text(self, code, dot, sum_):
        pass

    def get_value(self):
        return Datum()

    def ancestor_statement(self):
        a = self.parent
        while a is not None and not a.is_statement:
            a = a.parent
        return a

    def ancestor_loop(self):
        a = self.parent
        while a is not None and not a.is_loop:
            a = a.parent
        return a

    def has_spaces(self, dot):
        return True


class ExprNode(Node):
    def __init__(self, type_):
        Node.__init__(self, type_)
        self.is_expression = True


class StmtNode(Node):
    def __init__(self, type_):
        Node.__init__(self, type_)
        self.is_statement = True


class LabelNode(Node):
    def __init__(self, type_):
        Node.__init__(self, type_)
        self.is_label = True


class LoopNode(StmtNode):
    def __init__(self, type_, start_index):
        StmtNode.__init__(self, type_)
        self.start_index = start_index
        self.is_loop = True


def _paren(code, node, dot, sum_, need):
    if need:
        code.write("(")
    node.write_script_text(code, dot, sum_)
    if need:
        code.write(")")


class ErrorNode(ExprNode):
    def __init__(self):
        ExprNode.__init__(self, kErrorNode)

    def write_script_text(self, code, dot, sum_):
        code.write("ERROR")

    def has_spaces(self, dot):
        return False


class CommentNode(Node):
    def __init__(self, text):
        Node.__init__(self, kCommentNode)
        self.text = text

    def write_script_text(self, code, dot, sum_):
        code.write("-- ")
        code.write(self.text)


class LiteralNode(ExprNode):
    def __init__(self, value):
        ExprNode.__init__(self, kLiteralNode)
        self.value = value

    def write_script_text(self, code, dot, sum_):
        self.value.write_script_text(code, dot, sum_)

    def get_value(self):
        return self.value

    def has_spaces(self, dot):
        return False


class BlockNode(Node):
    def __init__(self):
        Node.__init__(self, kBlockNode)
        self.children = []
        self.end_pos = UINT32_MAX
        self.current_case_label = None

    def write_script_text(self, code, dot, sum_):
        for child in self.children:
            child.write_script_text(code, dot, sum_)
            code.write_line()

    def add_child(self, child):
        child.parent = self
        self.children.append(child)


class HandlerNode(Node):
    def __init__(self, handler):
        Node.__init__(self, kHandlerNode)
        self.handler = handler
        self.block = BlockNode()
        self.block.parent = self

    def write_script_text(self, code, dot, sum_):
        h = self.handler
        if h.is_generic_event:
            self.block.write_script_text(code, dot, sum_)
            return
        script = h.script
        is_method = script.is_factory()
        code.write("method " if is_method else "on ")
        code.write(h.name)
        if len(h.argument_names) > 0:
            code.write(" ")
            for i, n in enumerate(h.argument_names):
                if i > 0:
                    code.write(", ")
                code.write(n)
        code.write_line()
        code.indent()
        if is_method and len(script.property_names) > 0 and h is script.handlers[0]:
            code.write("instance ")
            for i, n in enumerate(script.property_names):
                if i > 0:
                    code.write(", ")
                code.write(n)
            code.write_line()
        if len(h.global_names) > 0:
            code.write("global ")
            for i, n in enumerate(h.global_names):
                if i > 0:
                    code.write(", ")
                code.write(n)
            code.write_line()
        self.block.write_script_text(code, dot, sum_)
        code.unindent()
        if not is_method:
            code.write_line("end")


class ExitStmtNode(StmtNode):
    def __init__(self):
        StmtNode.__init__(self, kExitStmtNode)

    def write_script_text(self, code, dot, sum_):
        code.write("exit")


class InverseOpNode(ExprNode):
    def __init__(self, operand):
        ExprNode.__init__(self, kInverseOpNode)
        self.operand = operand
        operand.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("-")
        _paren(code, self.operand, dot, sum_, self.operand.has_spaces(dot))


class NotOpNode(ExprNode):
    def __init__(self, operand):
        ExprNode.__init__(self, kNotOpNode)
        self.operand = operand
        operand.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("not ")
        _paren(code, self.operand, dot, sum_, self.operand.has_spaces(dot))


class BinaryOpNode(ExprNode):
    def __init__(self, opcode, a, b):
        ExprNode.__init__(self, kBinaryOpNode)
        self.opcode = opcode
        self.left = a
        a.parent = self
        self.right = b
        b.parent = self

    def get_precedence(self):
        op = self.opcode
        if op in (kOpMul, kOpDiv, kOpMod):
            return 1
        if op in (kOpAdd, kOpSub):
            return 2
        if op in (kOpLt, kOpLtEq, kOpNtEq, kOpEq, kOpGt, kOpGtEq):
            return 3
        if op == kOpAnd:
            return 4
        if op == kOpOr:
            return 5
        return 0

    def write_script_text(self, code, dot, sum_):
        precedence = self.get_precedence()
        paren_left = False
        paren_right = False
        if precedence:
            if self.left.type == kBinaryOpNode:
                paren_left = (self.left.get_precedence() != precedence)
            paren_right = (self.right.type == kBinaryOpNode)
        _paren(code, self.left, dot, sum_, paren_left)
        code.write(" ")
        code.write(StandardNames.get_name(StandardNames.binaryOpNames, self.opcode))
        code.write(" ")
        _paren(code, self.right, dot, sum_, paren_right)


class ChunkExprNode(ExprNode):
    def __init__(self, chunk_type, first, last, string):
        ExprNode.__init__(self, kChunkExprNode)
        self.chunk_type = chunk_type
        self.first = first
        first.parent = self
        self.last = last
        last.parent = self
        self.string = string
        string.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write(StandardNames.get_name(StandardNames.chunkTypeNames, self.chunk_type))
        code.write(" ")
        self.first.write_script_text(code, dot, sum_)
        if not _is_int_literal(self.last, 0):
            code.write(" to ")
            self.last.write_script_text(code, dot, sum_)
        code.write(" of ")
        bigger = self.string.type == kChunkExprNode and self.string.chunk_type > self.chunk_type
        paren_string = (not bigger) and self.string.has_spaces(dot)
        if paren_string:
            code.write("(")
        self.string.write_script_text(code, False, sum_)    # always verbose
        if paren_string:
            code.write(")")


class ChunkHiliteStmtNode(StmtNode):
    def __init__(self, chunk):
        StmtNode.__init__(self, kChunkHiliteStmtNode)
        self.chunk = chunk
        chunk.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("hilite ")
        self.chunk.write_script_text(code, dot, sum_)


class ChunkDeleteStmtNode(StmtNode):
    def __init__(self, chunk):
        StmtNode.__init__(self, kChunkDeleteStmtNode)
        self.chunk = chunk
        chunk.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("delete ")
        self.chunk.write_script_text(code, dot, sum_)


class SpriteIntersectsExprNode(ExprNode):
    def __init__(self, a, b):
        ExprNode.__init__(self, kSpriteIntersectsExprNode)
        self.first_sprite = a
        a.parent = self
        self.second_sprite = b
        b.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("sprite ")
        _paren(code, self.first_sprite, dot, sum_, self.first_sprite.type == kBinaryOpNode)
        code.write(" intersects ")
        _paren(code, self.second_sprite, dot, sum_, self.second_sprite.type == kBinaryOpNode)


class SpriteWithinExprNode(ExprNode):
    def __init__(self, a, b):
        ExprNode.__init__(self, kSpriteWithinExprNode)
        self.first_sprite = a
        a.parent = self
        self.second_sprite = b
        b.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("sprite ")
        _paren(code, self.first_sprite, dot, sum_, self.first_sprite.type == kBinaryOpNode)
        code.write(" within ")
        _paren(code, self.second_sprite, dot, sum_, self.second_sprite.type == kBinaryOpNode)


class MemberExprNode(ExprNode):
    def __init__(self, member_type, member_id, cast_id):
        ExprNode.__init__(self, kMemberExprNode)
        self.member_type = member_type
        self.member_id = member_id
        member_id.parent = self
        self.cast_id = None
        if cast_id is not None:
            self.cast_id = cast_id
            cast_id.parent = self

    def write_script_text(self, code, dot, sum_):
        has_cast = self.cast_id is not None and not _is_int_literal(self.cast_id, 0)
        code.write(self.member_type)
        if dot:
            code.write("(")
            self.member_id.write_script_text(code, dot, sum_)
            if has_cast:
                code.write(", ")
                self.cast_id.write_script_text(code, dot, sum_)
            code.write(")")
        else:
            code.write(" ")
            _paren(code, self.member_id, dot, sum_, self.member_id.type == kBinaryOpNode)
            if has_cast:
                code.write(" of castLib ")
                _paren(code, self.cast_id, dot, sum_, self.cast_id.type == kBinaryOpNode)

    def has_spaces(self, dot):
        return not dot


class VarNode(ExprNode):
    def __init__(self, var_name):
        ExprNode.__init__(self, kVarNode)
        self.var_name = var_name

    def write_script_text(self, code, dot, sum_):
        code.write(self.var_name)

    def has_spaces(self, dot):
        return False


class AssignmentStmtNode(StmtNode):
    def __init__(self, var, val, force_verbose=False):
        StmtNode.__init__(self, kAssignmentStmtNode)
        self.variable = var
        var.parent = self
        self.value = val
        val.parent = self
        self.force_verbose = force_verbose

    def write_script_text(self, code, dot, sum_):
        if not dot or self.force_verbose:
            code.write("set ")
            self.variable.write_script_text(code, False, sum_)     # always verbose
            code.write(" to ")
            self.value.write_script_text(code, dot, sum_)
        else:
            self.variable.write_script_text(code, dot, sum_)
            code.write(" = ")
            self.value.write_script_text(code, dot, sum_)


class IfStmtNode(StmtNode):
    def __init__(self, condition):
        StmtNode.__init__(self, kIfStmtNode)
        self.has_else = False
        self.condition = condition
        condition.parent = self
        self.block1 = BlockNode()
        self.block1.parent = self
        self.block2 = BlockNode()
        self.block2.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("if ")
        self.condition.write_script_text(code, dot, sum_)
        code.write(" then")
        if sum_:
            if self.has_else:
                code.write(" / else")
        else:
            code.write_line()
            code.indent()
            self.block1.write_script_text(code, dot, sum_)
            code.unindent()
            if self.has_else:
                code.write_line("else")
                code.indent()
                self.block2.write_script_text(code, dot, sum_)
                code.unindent()
            code.write("end if")


class RepeatWhileStmtNode(LoopNode):
    def __init__(self, start_index, condition):
        LoopNode.__init__(self, kRepeatWhileStmtNode, start_index)
        self.condition = condition
        condition.parent = self
        self.block = BlockNode()
        self.block.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("repeat while ")
        self.condition.write_script_text(code, dot, sum_)
        if not sum_:
            code.write_line()
            code.indent()
            self.block.write_script_text(code, dot, sum_)
            code.unindent()
            code.write("end repeat")


class RepeatWithInStmtNode(LoopNode):
    def __init__(self, start_index, var_name, lst):
        LoopNode.__init__(self, kRepeatWithInStmtNode, start_index)
        self.var_name = var_name
        self.list = lst
        lst.parent = self
        self.block = BlockNode()
        self.block.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("repeat with ")
        code.write(self.var_name)
        code.write(" in ")
        self.list.write_script_text(code, dot, sum_)
        if not sum_:
            code.write_line()
            code.indent()
            self.block.write_script_text(code, dot, sum_)
            code.unindent()
            code.write("end repeat")


class RepeatWithToStmtNode(LoopNode):
    def __init__(self, start_index, var_name, start, up, end):
        LoopNode.__init__(self, kRepeatWithToStmtNode, start_index)
        self.var_name = var_name
        self.start = start
        start.parent = self
        self.up = up
        self.end = end
        end.parent = self
        self.block = BlockNode()
        self.block.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("repeat with ")
        code.write(self.var_name)
        code.write(" = ")
        self.start.write_script_text(code, dot, sum_)
        code.write(" to " if self.up else " down to ")
        self.end.write_script_text(code, dot, sum_)
        if not sum_:
            code.write_line()
            code.indent()
            self.block.write_script_text(code, dot, sum_)
            code.unindent()
            code.write("end repeat")


class CaseLabelNode(LabelNode):
    def __init__(self, value, expect):
        LabelNode.__init__(self, kCaseLabelNode)
        self.value = value
        value.parent = self
        self.expect = expect
        self.next_or = None
        self.next_label = None
        self.block = None

    def write_script_text(self, code, dot, sum_):
        if sum_:
            code.write("(case) ")
            if self.parent.type == kCaseLabelNode:
                if self.parent.next_or is self:
                    code.write("..., ")
            _paren(code, self.value, dot, sum_, self.value.has_spaces(dot))
            if self.next_or is not None:
                code.write(", ...")
            else:
                code.write(":")
        else:
            _paren(code, self.value, dot, sum_, self.value.has_spaces(dot))
            if self.next_or is not None:
                code.write(", ")
                self.next_or.write_script_text(code, dot, sum_)
            else:
                code.write_line(":")
                code.indent()
                self.block.write_script_text(code, dot, sum_)
                code.unindent()
            if self.next_label is not None:
                self.next_label.write_script_text(code, dot, sum_)


class OtherwiseNode(LabelNode):
    def __init__(self):
        LabelNode.__init__(self, kOtherwiseNode)
        self.block = BlockNode()
        self.block.parent = self

    def write_script_text(self, code, dot, sum_):
        if sum_:
            code.write("(case) otherwise:")
        else:
            code.write_line("otherwise:")
            code.indent()
            self.block.write_script_text(code, dot, sum_)
            code.unindent()


class EndCaseNode(LabelNode):
    def __init__(self):
        LabelNode.__init__(self, kEndCaseNode)

    def write_script_text(self, code, dot, sum_):
        code.write("end case")


class CaseStmtNode(StmtNode):
    def __init__(self, value):
        StmtNode.__init__(self, kCaseStmtNode)
        self.value = value
        value.parent = self
        self.first_label = None
        self.otherwise = None
        self.end_pos = -1
        self.potential_otherwise_pos = -1

    def add_otherwise(self):
        self.otherwise = OtherwiseNode()
        self.otherwise.parent = self
        self.otherwise.block.end_pos = self.end_pos

    def write_script_text(self, code, dot, sum_):
        code.write("case ")
        self.value.write_script_text(code, dot, sum_)
        code.write(" of")
        if sum_:
            if self.first_label is None:
                if self.otherwise is not None:
                    code.write(" / otherwise:")
                else:
                    code.write(" / end case")
        else:
            code.write_line()
            code.indent()
            if self.first_label is not None:
                self.first_label.write_script_text(code, dot, sum_)
            if self.otherwise is not None:
                self.otherwise.write_script_text(code, dot, sum_)
            code.unindent()
            code.write("end case")


class TellStmtNode(StmtNode):
    def __init__(self, window):
        StmtNode.__init__(self, kTellStmtNode)
        self.window = window
        window.parent = self
        self.block = BlockNode()
        self.block.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("tell ")
        self.window.write_script_text(code, dot, sum_)
        if not sum_:
            code.write_line()
            code.indent()
            self.block.write_script_text(code, dot, sum_)
            code.unindent()
            code.write("end tell")


class SoundCmdStmtNode(StmtNode):
    def __init__(self, cmd, arg_list):
        StmtNode.__init__(self, kSoundCmdStmtNode)
        self.cmd = cmd
        self.arg_list = arg_list
        arg_list.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("sound ")
        code.write(self.cmd)
        if len(self.arg_list.get_value().l) > 0:
            code.write(" ")
            self.arg_list.write_script_text(code, dot, sum_)


class PlayCmdStmtNode(StmtNode):
    def __init__(self, arg_list):
        StmtNode.__init__(self, kPlayCmdStmtNode)
        self.arg_list = arg_list
        arg_list.parent = self

    def write_script_text(self, code, dot, sum_):
        raw = self.arg_list.get_value().l
        code.write("play")
        if len(raw) == 0:
            code.write(" done")
            return
        frame = raw[0]
        if len(raw) == 1:
            code.write(" frame ")
            frame.write_script_text(code, dot, sum_)
            return
        movie = raw[1]
        if not _is_int_literal(frame, 1):
            code.write(" frame ")
            frame.write_script_text(code, dot, sum_)
            code.write(" of")
        code.write(" movie ")
        movie.write_script_text(code, dot, sum_)


class CallNode(Node):
    def __init__(self, name, arg_list):
        Node.__init__(self, kCallNode)
        self.name = name
        self.arg_list = arg_list
        arg_list.parent = self
        if arg_list.get_value().type == kDatumArgListNoRet:
            self.is_statement = True
        else:
            self.is_expression = True

    def no_parens(self):
        if self.is_statement:
            if self.name == "put" or self.name == "return":
                return True
        return False

    def is_member_expr(self):
        if self.is_expression:
            nargs = len(self.arg_list.get_value().l)
            n = self.name
            if n == "cast" and nargs in (1, 2):
                return True
            if n == "member" and nargs in (1, 2):
                return True
            if n == "script" and nargs in (1, 2):
                return True
            if n == "castLib" and nargs == 1:
                return True
            if n == "window" and nargs == 1:
                return True
        return False

    def write_script_text(self, code, dot, sum_):
        if self.is_expression and len(self.arg_list.get_value().l) == 0:
            if self.name == "pi":
                code.write("PI")
                return
            if self.name == "space":
                code.write("SPACE")
                return
            if self.name == "void":
                code.write("VOID")
                return
        if not dot and self.is_member_expr():
            code.write(self.name)
            code.write(" ")
            raw = self.arg_list.get_value().l
            member_id = raw[0]
            _paren(code, member_id, dot, sum_, member_id.type == kBinaryOpNode)
            if len(raw) == 2:
                code.write(" of castLib ")
                cast_id = raw[1]
                _paren(code, cast_id, dot, sum_, cast_id.type == kBinaryOpNode)
            return
        code.write(self.name)
        if self.no_parens():
            code.write(" ")
            self.arg_list.write_script_text(code, dot, sum_)
        else:
            code.write("(")
            self.arg_list.write_script_text(code, dot, sum_)
            code.write(")")

    def has_spaces(self, dot):
        if not dot and self.is_member_expr():
            return True
        if self.no_parens():
            return True
        return False


class ObjCallNode(Node):
    def __init__(self, name, arg_list):
        Node.__init__(self, kObjCallNode)
        self.name = name
        self.arg_list = arg_list
        arg_list.parent = self
        if arg_list.get_value().type == kDatumArgListNoRet:
            self.is_statement = True
        else:
            self.is_expression = True

    def write_script_text(self, code, dot, sum_):
        raw = self.arg_list.get_value().l
        obj = raw[0]
        _paren(code, obj, dot, sum_, obj.has_spaces(dot))
        code.write(".")
        code.write(self.name)
        code.write("(")
        for i in range(1, len(raw)):
            if i > 1:
                code.write(", ")
            raw[i].write_script_text(code, dot, sum_)
        code.write(")")

    def has_spaces(self, dot):
        return False


class ObjCallV4Node(Node):
    def __init__(self, obj, arg_list):
        Node.__init__(self, kObjCallV4Node)
        self.obj = obj
        self.arg_list = arg_list
        arg_list.parent = self
        if arg_list.get_value().type == kDatumArgListNoRet:
            self.is_statement = True
        else:
            self.is_expression = True

    def write_script_text(self, code, dot, sum_):
        self.obj.write_script_text(code, dot, sum_)
        code.write("(")
        self.arg_list.write_script_text(code, dot, sum_)
        code.write(")")

    def has_spaces(self, dot):
        return False


class TheExprNode(ExprNode):
    def __init__(self, prop):
        ExprNode.__init__(self, kTheExprNode)
        self.prop = prop

    def write_script_text(self, code, dot, sum_):
        code.write("the ")
        code.write(self.prop)


class LastStringChunkExprNode(ExprNode):
    def __init__(self, chunk_type, obj):
        ExprNode.__init__(self, kLastStringChunkExprNode)
        self.chunk_type = chunk_type
        self.obj = obj
        obj.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("the last ")
        code.write(StandardNames.get_name(StandardNames.chunkTypeNames, self.chunk_type))
        code.write(" in ")
        if self.obj.type == kBinaryOpNode:
            code.write("(")
        self.obj.write_script_text(code, False, sum_)
        if self.obj.type == kBinaryOpNode:
            code.write(")")


class StringChunkCountExprNode(ExprNode):
    def __init__(self, chunk_type, obj):
        ExprNode.__init__(self, kStringChunkCountExprNode)
        self.chunk_type = chunk_type
        self.obj = obj
        obj.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("the number of ")
        code.write(StandardNames.get_name(StandardNames.chunkTypeNames, self.chunk_type))
        code.write("s in ")
        if self.obj.type == kBinaryOpNode:
            code.write("(")
        self.obj.write_script_text(code, False, sum_)
        if self.obj.type == kBinaryOpNode:
            code.write(")")


class MenuPropExprNode(ExprNode):
    def __init__(self, menu_id, prop):
        ExprNode.__init__(self, kMenuPropExprNode)
        self.menu_id = menu_id
        menu_id.parent = self
        self.prop = prop

    def write_script_text(self, code, dot, sum_):
        code.write("the ")
        code.write(StandardNames.get_name(StandardNames.menuPropertyNames, self.prop))
        code.write(" of menu ")
        _paren(code, self.menu_id, dot, sum_, self.menu_id.type == kBinaryOpNode)


class MenuItemPropExprNode(ExprNode):
    def __init__(self, menu_id, item_id, prop):
        ExprNode.__init__(self, kMenuItemPropExprNode)
        self.menu_id = menu_id
        menu_id.parent = self
        self.item_id = item_id
        item_id.parent = self
        self.prop = prop

    def write_script_text(self, code, dot, sum_):
        code.write("the ")
        code.write(StandardNames.get_name(StandardNames.menuItemPropertyNames, self.prop))
        code.write(" of menuItem ")
        _paren(code, self.item_id, dot, sum_, self.item_id.type == kBinaryOpNode)
        code.write(" of menu ")
        _paren(code, self.menu_id, dot, sum_, self.menu_id.type == kBinaryOpNode)


class SoundPropExprNode(ExprNode):
    def __init__(self, sound_id, prop):
        ExprNode.__init__(self, kSoundPropExprNode)
        self.sound_id = sound_id
        sound_id.parent = self
        self.prop = prop

    def write_script_text(self, code, dot, sum_):
        code.write("the ")
        code.write(StandardNames.get_name(StandardNames.soundPropertyNames, self.prop))
        code.write(" of sound ")
        _paren(code, self.sound_id, dot, sum_, self.sound_id.type == kBinaryOpNode)


class SpritePropExprNode(ExprNode):
    def __init__(self, sprite_id, prop):
        ExprNode.__init__(self, kSpritePropExprNode)
        self.sprite_id = sprite_id
        sprite_id.parent = self
        self.prop = prop

    def write_script_text(self, code, dot, sum_):
        code.write("the ")
        code.write(StandardNames.get_name(StandardNames.spritePropertyNames, self.prop))
        code.write(" of sprite ")
        _paren(code, self.sprite_id, dot, sum_, self.sprite_id.type == kBinaryOpNode)


class ThePropExprNode(ExprNode):
    def __init__(self, obj, prop):
        ExprNode.__init__(self, kThePropExprNode)
        self.obj = obj
        obj.parent = self
        self.prop = prop

    def write_script_text(self, code, dot, sum_):
        code.write("the ")
        code.write(self.prop)
        code.write(" of ")
        if self.obj.type == kBinaryOpNode:
            code.write("(")
        self.obj.write_script_text(code, False, sum_)
        if self.obj.type == kBinaryOpNode:
            code.write(")")


class ObjPropExprNode(ExprNode):
    def __init__(self, obj, prop):
        ExprNode.__init__(self, kObjPropExprNode)
        self.obj = obj
        obj.parent = self
        self.prop = prop

    def write_script_text(self, code, dot, sum_):
        if dot:
            _paren(code, self.obj, dot, sum_, self.obj.has_spaces(dot))
            code.write(".")
            code.write(self.prop)
        else:
            code.write("the ")
            code.write(self.prop)
            code.write(" of ")
            _paren(code, self.obj, dot, sum_, self.obj.type == kBinaryOpNode)

    def has_spaces(self, dot):
        return not dot


class ObjBracketExprNode(ExprNode):
    def __init__(self, obj, prop):
        ExprNode.__init__(self, kObjBracketExprNode)
        self.obj = obj
        obj.parent = self
        self.prop = prop
        prop.parent = self

    def write_script_text(self, code, dot, sum_):
        _paren(code, self.obj, dot, sum_, self.obj.has_spaces(dot))
        code.write("[")
        self.prop.write_script_text(code, dot, sum_)
        code.write("]")

    def has_spaces(self, dot):
        return False


class ObjPropIndexExprNode(ExprNode):
    def __init__(self, obj, prop, index, index2):
        ExprNode.__init__(self, kObjPropIndexExprNode)
        self.obj = obj
        obj.parent = self
        self.prop = prop
        self.index = index
        index.parent = self
        self.index2 = None
        if index2 is not None:
            self.index2 = index2
            index2.parent = self

    def write_script_text(self, code, dot, sum_):
        _paren(code, self.obj, dot, sum_, self.obj.has_spaces(dot))
        code.write(".")
        code.write(self.prop)
        code.write("[")
        self.index.write_script_text(code, dot, sum_)
        if self.index2 is not None:
            code.write("..")
            self.index2.write_script_text(code, dot, sum_)
        code.write("]")

    def has_spaces(self, dot):
        return False


class ExitRepeatStmtNode(StmtNode):
    def __init__(self):
        StmtNode.__init__(self, kExitRepeatStmtNode)

    def write_script_text(self, code, dot, sum_):
        code.write("exit repeat")


class NextRepeatStmtNode(StmtNode):
    def __init__(self):
        StmtNode.__init__(self, kNextRepeatStmtNode)

    def write_script_text(self, code, dot, sum_):
        code.write("next repeat")


class PutStmtNode(StmtNode):
    def __init__(self, put_type, var, val):
        StmtNode.__init__(self, kPutStmtNode)
        self.put_type = put_type
        self.variable = var
        var.parent = self
        self.value = val
        val.parent = self

    def write_script_text(self, code, dot, sum_):
        code.write("put ")
        self.value.write_script_text(code, dot, sum_)
        code.write(" ")
        code.write(StandardNames.get_name(StandardNames.putTypeNames, self.put_type))
        code.write(" ")
        self.variable.write_script_text(code, False, sum_)


class WhenStmtNode(StmtNode):
    def __init__(self, event, script):
        StmtNode.__init__(self, kWhenStmtNode)
        self.event = event
        self.script = script

    def write_script_text(self, code, dot, sum_):
        code.write("when ")
        code.write(StandardNames.get_name(StandardNames.whenEventNames, self.event))
        code.write(" then")
        code.do_indentation = False
        n = len(self.script)
        for i, ch in enumerate(self.script):
            if ch == '\r':
                if i != n - 1:
                    code.write_line()
            else:
                code.write(ch)
        code.do_indentation = True


class NewObjNode(ExprNode):
    def __init__(self, obj_type, obj_args):
        ExprNode.__init__(self, kNewObjNode)
        self.obj_type = obj_type
        self.obj_args = obj_args

    def write_script_text(self, code, dot, sum_):
        code.write("new ")
        code.write(self.obj_type)
        code.write("(")
        self.obj_args.write_script_text(code, dot, sum_)
        code.write(")")


class AST:
    def __init__(self, handler):
        self.root = HandlerNode(handler)
        self.current_block = self.root.block

    def write_script_text(self, code, dot, sum_):
        self.root.write_script_text(code, dot, sum_)

    def add_statement(self, statement):
        self.current_block.add_child(statement)

    def enter_block(self, block):
        self.current_block = block

    def exit_block(self):
        ancestor = self.current_block.ancestor_statement()
        if ancestor is None:
            self.current_block = None
            return
        block = ancestor.parent
        if block is None or block.type != kBlockNode:
            self.current_block = None
            return
        self.current_block = block
