import struct
from io import BytesIO

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

def ReadKLV(stream):
    r = []

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
            fmt = f'{n_bytes}s'
            data, = struct.unpack(fmt, buf[:n_bytes])
            try:
                data = data.decode('iso-8859-1')
            except UnicodeDecodeError:
                print ("ERROR DECODING STRING:", data)
                data = None
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
        r.append((fourcc, data))
        

