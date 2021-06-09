import struct
from io import BytesIO

# These are the GPMF data types mapped onto standard struct pack/unpack formats.
# Because GPMF supports 2-D arrays somewhat I store the elemental datum size too.
KLV_STD_TYPE_MAP = {
    b'B': (1, 'B'),
    b'b': (1, 'b'),
    b'd': (8, 'd'),
    b'f': (4, 'f'),
    b'L': (4, 'I'),
    b'l': (4, 'i'),
    b'J': (8, 'Q'),
    b'j': (8, 'q'),
    b's': (2, 'h'),
    b'S': (2, 'H')
}

# OO - a Frame class 
class Frame:
    def add_element(self, fourcc, data):
        if fourcc in self.__dict__:
            if type(self.__dict__[fourcc]) is list:
                self.__dict__[fourcc].append(data)
            else:
                self.__dict__[fourcc] = [self.__dict__[fourcc], data]
        else:
            self.__dict__[fourcc] = data

    def __repr__(self):
        txt = "Frame ("
        for x, v in self.__dict__.items():
            xtxt = x
            if type(v) is list:
                xtxt += f"[{len(v)}]"
            txt += xtxt + ","
        txt = txt[0:-1] + ")"
        return txt 

def ReadKLV(stream):
    r = Frame()

    while True:
        
        buf = stream.read(4)
        if len(buf) == 0: return r
        fourcc = buf.decode('UTF-8')
        header = stream.read(4)
        klv_type, klv_size, klv_count = struct.unpack('>cBH', header)
        
        n_bytes = klv_size * klv_count
        n_aligned = 4 * ((n_bytes + 3) // 4)
        buf = stream.read(n_aligned)

        if klv_type == b'\x00':
            # null type means nested stream
            data = ReadKLV(BytesIO(buf))
        elif klv_type == b'c':
            # Somehow strings feel different 
            fmt = f'{n_bytes}s'
            data, = struct.unpack(fmt, buf[:n_bytes])
            try:
                data = data.decode('iso-8859-1')
            except UnicodeDecodeError:
                print ("ERROR DECODING STRING:", data)
                data = None
        elif klv_type == b'U':
            # UTC date/time 16-character string
            data, = struct.unpack('>16s', buf)
            data = data.decode('iso-8859-1')
        else:
            if klv_type in KLV_STD_TYPE_MAP:
                size, fmt_char = KLV_STD_TYPE_MAP[klv_type]
                c = klv_size // size
                fmt = f'>{c*klv_count}{fmt_char}'
                try:
                    data = struct.unpack(fmt, buf[:n_bytes])
                    if len(data) == 1: data = data[0]
                except Exception as err:
                    print ("*** Error in decoding std type:")
                    print (f"***  - klv = {klv_type}, {klv_size}, {klv_count}")
                    print (f"***  - fmt string = {fmt}")
                    print (f"***  - bufferlength = {len(buf)}")
            else:
                data = (klv_type, klv_size, klv_count)

        # print (fourcc, klv_type, klv_size, klv_count, data)

        r.add_element(fourcc, data)
        

