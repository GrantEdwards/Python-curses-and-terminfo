#!/usr/bin/python3

import ctypes,sys,curses
from io import BufferedIOBase, TextIOWrapper

curses.setupterm()

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

bold = curses.tigetstr('bold')
norm = curses.tigetstr('sgr0')
cls = curses.tigetstr('clear')
cup = curses.tigetstr('cup')

write = sys.stdout.write
putp = curses.putp

def goto(row,column):
    putp(curses.tparm(cup,row,column))

def clear():
    putp(cls)
    
clear()
write("Enter your name: ")
name = input()

for row in [3,5,10,20]:
    goto(row, row+5)
    putp(bold)
    write(f'Hi there {name}')
    putp(norm)
    goto(row+1, row+6)
    write(f'Hi there {name}')

goto(24,0)    
write("Press enter to exit: ")
input()
clear()
                        
    
