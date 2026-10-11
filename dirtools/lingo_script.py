# Port of ProjectorRays src/lingodec/script.* and context.* (MPL-2.0).
from .lingo_names import *   # noqa: F401,F403
from .lingo_names import CodeWriter
from .lingo_ast import Datum
from .lingo_handler import Handler


class LiteralStore:
    def __init__(self):
        self.type = 0
        self.offset = 0
        self.value = None

    def read_record(self, stream, version):
        if version >= 500:
            self.type = stream.read_u32()
        else:
            self.type = stream.read_u16()
        self.offset = stream.read_u32()

    def read_data(self, stream, start_offset):
        if self.type == kLiteralInt:
            off = self.offset
            if off >= 0x80000000:        # (int)offset in C++
                off -= 0x100000000
            self.value = Datum(kDatumInt, off)
            return
        stream.seek(start_offset + self.offset)
        length = stream.read_u32()
        if self.type == kLiteralString:
            self.value = Datum(kDatumString, stream.read_string(length - 1))
        elif self.type == kLiteralFloat:
            f = 0.0
            if length == 8:
                f = stream.read_double()
            elif length == 10:
                f = stream.read_apple_float80()
            self.value = Datum(kDatumFloat, f)
        else:
            self.value = Datum()


class Script:
    def __init__(self, version):
        self.version = version
        self.context = None
        self.handlers = []
        self.literals = []
        self.factories = []
        self.property_names = []
        self.global_names = []
        self.factory_name = ''
        self.script_flags = 0
        self.factory_name_id = -1
        self.parent_number = 0

    def read(self, stream):
        stream.endian = '>'        # Lingo scripts are always big endian regardless of file endianness
        stream.seek(8)
        self.total_length = stream.read_u32()
        self.total_length2 = stream.read_u32()
        self.header_length = stream.read_u16()
        self.script_number = stream.read_u16()
        self.unk20 = stream.read_i16()
        self.parent_number = stream.read_i16()

        stream.seek(38)
        self.script_flags = stream.read_u32()
        self.unk42 = stream.read_i16()
        self.cast_id = stream.read_i32()
        self.factory_name_id = stream.read_i16()
        self.handler_vectors_count = stream.read_u16()
        self.handler_vectors_offset = stream.read_u32()
        self.handler_vectors_size = stream.read_u32()
        self.properties_count = stream.read_u16()
        self.properties_offset = stream.read_u32()
        self.globals_count = stream.read_u16()
        self.globals_offset = stream.read_u32()
        self.handlers_count = stream.read_u16()
        self.handlers_offset = stream.read_u32()
        self.literals_count = stream.read_u16()
        self.literals_offset = stream.read_u32()
        self.literals_data_count = stream.read_u32()
        self.literals_data_offset = stream.read_u32()

        self.property_name_ids = self.read_varnames_table(stream, self.properties_count, self.properties_offset)
        self.global_name_ids = self.read_varnames_table(stream, self.globals_count, self.globals_offset)

        self.handlers = [Handler(self) for _ in range(self.handlers_count)]
        if (self.script_flags & kScriptFlagEventScript) and self.handlers_count > 0:
            self.handlers[0].is_generic_event = True

        stream.seek(self.handlers_offset)
        for h in self.handlers:
            h.read_record(stream)
        for h in self.handlers:
            h.read_data(stream)

        stream.seek(self.literals_offset)
        self.literals = []
        for _ in range(self.literals_count):
            lit = LiteralStore()
            lit.read_record(stream, self.version)
            self.literals.append(lit)
        for lit in self.literals:
            lit.read_data(stream, self.literals_data_offset)

    @staticmethod
    def read_varnames_table(stream, count, offset):
        stream.seek(offset)
        return [stream.read_i16() for _ in range(count)]

    def valid_name(self, id_):
        return self.context.valid_name(id_)

    def get_name(self, id_):
        return self.context.get_name(id_)

    def set_context(self, ctx):
        self.context = ctx
        if self.factory_name_id != -1:
            self.factory_name = self.get_name(self.factory_name_id)
        for nid in self.property_name_ids:
            if self.valid_name(nid):
                name = self.get_name(nid)
                if self.is_factory() and name == 'me':
                    continue
                self.property_names.append(name)
        for nid in self.global_name_ids:
            if self.valid_name(nid):
                self.global_names.append(self.get_name(nid))
        for h in self.handlers:
            h.read_names()

    def parse(self):
        for h in self.handlers:
            h.parse()

    def write_var_declarations(self, code):
        if not self.is_factory():
            if self.property_names:
                code.write('property ')
                code.write(', '.join(self.property_names))
                code.write_line()
        if self.global_names:
            code.write('global ')
            code.write(', '.join(self.global_names))
            code.write_line()

    def write_script_text(self, code, dot_syntax):
        orig = code.size
        self.write_var_declarations(code)
        if self.is_factory():
            if code.size != orig:
                code.write_line()
            code.write('factory ')
            code.write_line(self.factory_name)
        for i, h in enumerate(self.handlers):
            if (not self.is_factory() or i > 0) and code.size != orig:
                code.write_line()
            h.ast.write_script_text(code, dot_syntax, False)
        for f in self.factories:
            if code.size != orig:
                code.write_line()
            f.write_script_text(code, dot_syntax)

    def script_text(self, line_ending, dot_syntax):
        code = CodeWriter(line_ending)
        self.write_script_text(code, dot_syntax)
        return code.str()

    def write_bytecode_text(self, code, dot_syntax):
        orig = code.size
        self.write_var_declarations(code)
        if self.is_factory():
            if code.size != orig:
                code.write_line()
            code.write('factory ')
            code.write_line(self.factory_name)
        for i, h in enumerate(self.handlers):
            if (not self.is_factory() or i > 0) and code.size != orig:
                code.write_line()
            h.write_bytecode_text(code, dot_syntax)
        for f in self.factories:
            if code.size != orig:
                code.write_line()
            f.write_bytecode_text(code, dot_syntax)

    def bytecode_text(self, line_ending, dot_syntax):
        code = CodeWriter(line_ending)
        self.write_bytecode_text(code, dot_syntax)
        return code.str()

    def is_factory(self):
        return bool(self.script_flags & kScriptFlagFactoryDef)


class ScriptContextMapEntry:
    def read(self, stream):
        self.unknown0 = stream.read_i32()
        self.section_id = stream.read_i32()
        self.unknown1 = stream.read_u16()
        self.unknown2 = stream.read_u16()


class ScriptContext:
    def __init__(self, version, resolver):
        self.version = version
        self.resolver = resolver
        self.lnam = None
        self.section_map = []
        self.scripts = {}          # insertion order == C++ std::map order (ids are inserted ascending)

    def read(self, stream):
        stream.endian = '>'        # Lingo scripts are always big endian regardless of file endianness
        self.unknown0 = stream.read_i32()
        self.unknown1 = stream.read_i32()
        self.entry_count = stream.read_u32()
        self.entry_count2 = stream.read_u32()
        self.entries_offset = stream.read_u16()
        self.unknown2 = stream.read_i16()
        self.unknown3 = stream.read_i32()
        self.unknown4 = stream.read_i32()
        self.unknown5 = stream.read_i32()
        self.lnam_section_id = stream.read_i32()
        self.valid_count = stream.read_u16()
        self.flags = stream.read_u16()
        self.free_pointer = stream.read_i16()

        stream.seek(self.entries_offset)
        self.section_map = []
        for _ in range(self.entry_count):
            e = ScriptContextMapEntry()
            e.read(stream)
            self.section_map.append(e)

        self.lnam = self.resolver.get_script_names(self.lnam_section_id)
        for i in range(1, self.entry_count + 1):
            section = self.section_map[i - 1]
            if section.section_id > -1:
                script = self.resolver.get_script(section.section_id)
                script.set_context(self)
                self.scripts[i] = script

        for i in sorted(self.scripts):
            script = self.scripts[i]
            if script.is_factory():
                parent = self.scripts.get(script.parent_number + 1)
                if parent is not None:
                    parent.factories.append(script)

    def valid_name(self, id_):
        return self.lnam.valid_name(id_)

    def get_name(self, id_):
        return self.lnam.get_name(id_)

    def parse_scripts(self):
        for i in sorted(self.scripts):
            self.scripts[i].parse()
