# Port of ProjectorRays src/common/stream.* (MPL-2.0).
import struct
import zlib


class ReadStream:
    """Cursor over a bytes object. endian is '>' (big) or '<' (little)."""

    def __init__(self, data, endian='>', pos=0):
        self.data = bytes(data) if not isinstance(data, bytes) else data
        self.endian = endian
        self.pos = pos

    # -- position -----------------------------------------------------------------------------
    @property
    def size(self):
        return len(self.data)

    def seek(self, pos):
        self.pos = pos

    def skip(self, n):
        self.pos += n

    def eof(self):
        return self.pos >= len(self.data)

    def past_eof(self):
        return self.pos > len(self.data)

    def _take(self, n, what):
        p = self.pos
        self.pos += n
        if self.pos > len(self.data):
            raise EOFError('ReadStream.%s: read past end of stream' % what)
        return p

    # -- numbers ------------------------------------------------------------------------------
    def read_u8(self):
        return self.data[self._take(1, 'u8')]

    def read_i8(self):
        v = self.read_u8()
        return v - 256 if v >= 128 else v

    def read_u16(self):
        return struct.unpack_from(self.endian + 'H', self.data, self._take(2, 'u16'))[0]

    def read_i16(self):
        return struct.unpack_from(self.endian + 'h', self.data, self._take(2, 'i16'))[0]

    def read_u32(self):
        return struct.unpack_from(self.endian + 'I', self.data, self._take(4, 'u32'))[0]

    def read_i32(self):
        return struct.unpack_from(self.endian + 'i', self.data, self._take(4, 'i32'))[0]

    def read_double(self):
        return struct.unpack_from(self.endian + 'd', self.data, self._take(8, 'double'))[0]

    def read_apple_float80(self):
        """80-bit SANE extended -> float, always big endian (same conversion ProjectorRays does)."""
        p = self._take(10, 'float80')
        exponent = struct.unpack_from('>H', self.data, p)[0]
        sign = -1.0 if exponent & 0x8000 else 1.0
        exponent &= 0x7FFF
        fraction = struct.unpack_from('>Q', self.data, p + 2)[0] & 0x7FFFFFFFFFFFFFFF
        if exponent == 0:
            return sign * 0.0
        if exponent == 0x7FFF:
            return sign * float('inf')
        normexp = exponent - 0x3FFF
        if -0x3FE > normexp or normexp >= 0x3FF:
            raise ValueError('Constant float exponent too big for a double')
        bits = (0x8000000000000000 if sign < 0 else 0) | ((normexp + 0x3FF) << 52) | (fraction >> 11)
        return struct.unpack('>d', struct.pack('>Q', bits))[0]

    def read_var_int(self):
        val = 0
        while True:
            b = self.read_u8()
            val = (val << 7) | (b & 0x7F)
            if not (b >> 7):
                return val

    # -- bytes / strings ----------------------------------------------------------------------
    def read_bytes(self, n):
        """Like ProjectorRays' readByteView: no bounds check, the slice is just shorter at the end."""
        p = self.pos
        self.pos += n
        return self.data[p:p + n]

    def read_string(self, n):
        """Latin-1 string; like the C++ original it is cut at the first NUL byte."""
        p = self._take(n, 'string')
        raw = self.data[p:p + n]
        i = raw.find(b'\0')
        if i >= 0:
            raw = raw[:i]
        return raw.decode('latin-1')

    def read_cstring(self):
        out = bytearray()
        while True:
            b = self.read_u8()
            if b == 0:
                break
            out.append(b)
        return out.decode('latin-1')

    def read_pascal_string(self):
        return self.read_string(self.read_u8())

    def read_zlib(self, length, dest_len=None):
        """Read `length` bytes and zlib-inflate them (like uncompress()). Returns bytes or None on error."""
        p = self.pos
        self.pos += length
        if self.pos > len(self.data):
            raise EOFError('ReadStream.read_zlib: read past end of stream')
        try:
            return zlib.decompress(self.data[p:p + length])
        except zlib.error:
            return None
