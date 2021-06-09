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

        r.append((fourcc, data))
        
```

This works OK. Would be nice if I could navigate the data structure a bit less
clumsily than `my_list[1][1][14][27][1]`.

## Adding Objects
Actually, just one object, the Frame class:

```python
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
```

It's very lightweight coming in under 20 LoC but it does have some
very nice features already to facilitate navigation of the nested
structures:

* the class instance `__dict__` is run-time filled in with the `FOURCC`
_key_, _value_ pairs;
* auto-promotion to lists when encountering repeated `FOURCC` keys.

I didn't expect to be able to re-use the `ReadKLV` function as much as
I ended up doing: I have added some additional functionality here to
decode UTC strings which is orthogonal to the object implementation.
The honest-to-goodness truth is that in swapping lists for objects the
only things I had to change were the initial object creation at the 
beginning of the function and the list append became the Frame's
`add_element` method. I just copy the function itself below as 
the object declaration is above and the rest of the code is unchanged
from before too:

```python
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
```