# From Lists to Objects
Quick idea: I started the GPMF stream reader in Python. My zeroth implementation
was 100% functional programming and I used list pairs of `(FOURCC, DATA)` to 
represent the in-memory structure in the GPMF file. It works fine but it's a 
little clumsy and frankly just doesn't seem like what one would expect from a
decent Python implementation. 

So I use the opportunity to document my objectification of the basic functional
implementation. Maybe this is useful to someone.

## Intro to GPMF
This is better documented in the GitHub gpmf-parser repo. Look there for a full
explanation of GPMF which is how I got from zero to hero on the topic. Briefly,
GPMF is a streaming binary somewhat-self-documenting-and-flexible format for
capturing GoPro telemetry data in an MP4 file as one of the streams.

GPMF allows nesting data so I guess you can think of it like a filesystem 
with nested directories, some arbitrary number of files in each directory, 
and data in those files.

## Implementation Zero: List Pairs
My first attempt to get something quickly together to read a file into a 
somewhat more usable in-memory Python data structure was simply to have a
list of `(FOURCC, DATA)` pairs. The DATA could be itself a list of `(FOURCC, DATA)`
pairs and so-on &c. Here's the code

```python
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
        
```

This works OK. Would be nice if I could navigate the data structure a bit less
clumsily than `my_list[1][1][14][27][1]`.
