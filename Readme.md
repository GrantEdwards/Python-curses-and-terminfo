
## Python and Terminfo

Notes on using terminfo functions from the curses module without using
any of the curses windowing functions.

The naive approch to doing low-level terminal control in Python is to
use the following terminfo functions from the `curses` module:

 * `tigetstr()` to fetch the desired control sequence.
 * `tparm()` to parameterize the control sequence if required.
 * `putp()` to write the control sequence to the terminal
 
Those functions work and do what they're supposed to (see man curses).
However, when intermixed with calls to print() or sys.stdout.write(),
the combination doesn't work. The problem is due to buffering of the
output. The `putp()` call is writing to the libc FILE *stdout stream,
which has built-in buffering before it writes to Unix file descriptor
1. Python's `sys.stdout` object also has built-in buffering before it
writes to file descriptor 1. If you make interleaved calls like this,

~~~
sys.stdout.write('hi there. ')
curses.putp(bold)
sys.stdout.write('how are you? ')
curses.putp(normal)
curses.putp('I am fine. ')
~~~

The output almost certainly isn't going to arrive at the terminal in
the order you intended, and the bold/normal attributes won't be
applied as desired.

There are several solutions to this problem.

### Don't Use libc FILE *stdout

The first option is to use only Python output mechanisms and to not
use curses.putp() at all (avoiding the libc FILE *stdout stuff
completely). Though this sounds simple enough, it turns out that
curses.putp() does more than just write a byte-string to stdout. It
also parses the byte-string and replaces terminfo delay specifiers
with the required number of ASCII NUL bytes to produce the required
amount of delay in the byte stream.

These delays are only need by old terminals, connected to real serial
ports, without any flow control. If you don't run into anything like
that, then you can just delete the termino delay specifiers from the
control sequences when you look them up. This is easiest if you wrap
the curses tigets() call like this:

~~~
def tigetstr(name):
    seq = curses.tigetstr(name)
    return re.sub(b'\$<[0-9.]+[\*/]{0,2}>', b'', seq)
~~~

The delay specifier looks like this:
~~~
$<N.N*/>
~~~

where N.N is a floating point number with at most one decimal place
followed and optional '*' and/or '/' suffix. The re.sub() call above
removes that specifier (the re is a _bit_ off in that it will accept
`$<1.2**>` and `$<1.2//` which aren't quite kosher delay specifiers).

After you've removed the delay specifier as shown above, then you can
(after parameterizing with curses.tparm() as required) output them
using the normal Python I/O calls. Note that tigetstr() returns a byte
string, and tparm() accepts and returns a byte string. Either you have
to write them using sys.stdout.buffer.write(), or you need to decode
them as ASCII to convert them from bytestr to str before writing them
using print() or sys.stdout.write().

Converting them to ASCII is convenient, because then it allows easy
insertion into normal string data as it's being output:

~~~

bold = tigetstr('bold').decode('ascii')
norm = tigetstr('sgr0').decode('ascii')

write = sys.stdout.write

name = <whatever>

write(f'Hello {bold}{name}{norm}, how are you?\n')

~~~

### Flushing Both Output Streams

A second work-around is to explicity flush the two independent output
streams to force the output to be written to the file descriptor in
the desired order. Python provides no native access to libc's FILE
*stdout stream, so ctypes must be used to both look up the libc stdout
variable and call libc's fflush() function. This option _will_ work
with terminals that require delays, are attached to real serial ports,
and don't have flow control. However, it may increase overhead due to
the constant flushing of output buffers.

The simplest way to make this work to wrap the curses.putp() call like
this:

~~~

import cytypes
libc = ctypes.CDLL(None, use_errno=True)
stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
def putp(b):
    sys.stdout.flush()
    curses.putp(b)
    libc.fflush(stdout)

~~~

Note that the C standard doesn't require that stdout be a global
variable that can be accessed as shown above. It may be a macro that
returns a pointer of the correct type. If that's how your libc works,
then the above code may not be feasible — but there is a
workaround. If you pass a NULL pointer to fflush() it will flush all
output streams:

~~~

import cytypes
libc = ctypes.CDLL(None, use_errno=True)
def putp(b):
    sys.stdout.flush()
    curses.putp(b)
    libc.fflush(None)

~~~

It also does not allow inserting control sequences into the text
stream as shown in the first option, since control sequences must be
output using curses.putp() so that delay specifiers can be replaced by
an appropriate number of ASCII NUL characters.

Note that it's not safe write arbitrary byte strings using
curses.putp(), since putp() scans the byte string for terminfo delay
specifiers and replaces them with zero or more NUL bytes.


### Use Only libc FILE *stdout

The third option will, like the second, work with terminals on serial
ports that require delays and don't have flow control. This option is
to route Python's stdout data through libc's FILE *stdout stream that
is being used by curses.putp(). This require a bit more code, but is
still pretty easy. Unless you wnat to call sys.stdout.flush() before
every call to putp(), you need to disable buffer in the TextIOWrapper
by setting write_through to True.

~~~

import ctypes,sys
from io import BufferedIOBase, TextIOWrapper

libc = ctypes.CDLL(None, use_errno=True)

class MyBufferedWriter(BufferedIOBase):
    def __init__(self,fpName):
        self.stream = ctypes.c_void_p.in_dll(libc, fpName)
    def write(self,data):
        n = libc.fwrite(data,1,len(data),self.stream)
        if n >= 0:
            return n
        raise Exception(f'fwrite returned {n}')
    def flush(self):
        libc.fflush(self.stream)
    def seekable(self):
        return False
    def readable(self):
        return False
    def writable(self):
        return True;
    def close(self):
        libc.fclose(self.stream)
        BufferedIOBase.close(self)

sys.stdout = TextIOWrapper(MyBufferedWriter('stdout'),write_through=True,encoding=sys.stdout.encoding)


~~~

Also like the second option, this option does _not_ allow inserting
control sequences into the text stream as shown in the first option,
since control sequences must be output using curses.putp() so that
delay specifiers can be replaced by an appropriate number of ASCII NUL
characters.

### Demo Applications

Four demo applications are provided:

 * `demo-broken.py` is a naieve attempt that doesn't work due due to
   the independent buffering done by libc and Python.
   
 * `demo-pyoutput` is a working demonstration that show doing all
   output via native Python calls.
   
 * `demo-flush.py` is a working demo showing the use of both Python
   and libc output with flush() and fflush() calls.
   
 * `demo-libcoutput.py` is a working demo showing Python stdout data
   being output via libc FILE *stdout.

The demo applications _should_ clear the screan, prompt for a name,
and then say 'Hi there' 8 times (first, third, fifth, seventh times
are bold), with the output in a slanting line with vertical gaps as
shown below. Then it will wait for [Enter], clear the screen and exit.


~~~
+--------------------------------------------------------------------------------+
|Enter your name: asdf                                                           |
|                                                                                |
|                                                                                |
|        Hi there asdf                                                           |
|         Hi there asdf                                                          |
|          Hi there asdf                                                         |
|           Hi there asdf                                                        |
|                                                                                |
|                                                                                |
|                                                                                |
|               Hi there asdf                                                    |
|                Hi there asdf                                                   |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                         Hi there asdf                                          |
|                          Hi there asdf                                         |
|                                                                                |
|Press enter to exit: ▮                                                          |
+--------------------------------------------------------------------------------+
~~~

The odd-numbered "Hi there asdf" output lines should be bold.

On my systems, the "broken" demo will clear the screen and then wait
for input (the prompt string won't appear).  Then the hi-there strings
get printed 8 times without being positioned or bolded, followed by
the exit prompt. Then, the cursor will repsoition to the bottom left,
and it will wait for Enter:

~~~
+--------------------------------------------------------------------------------+
|asdf                                                                            |
|Hi there asdfHi there asdfHi there asdfHi there asdfHi there asdfHi there asdfHi|
| there asdfHi there asdfPress enter to exit:                                    |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|▮                                                                               |
+--------------------------------------------------------------------------------+
~~~




