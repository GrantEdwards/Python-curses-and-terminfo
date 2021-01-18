#!/usr/bin/python3

import os,ctypes,sys,curses

libc = ctypes.CDLL(None, use_errno=True)
stdout = ctypes.c_void_p.in_dll(libc, 'stdout')

curses.setupterm()

bold = curses.tigetstr('bold')
norm = curses.tigetstr('sgr0')
cls = curses.tigetstr('clear')
cup = curses.tigetstr('cup')

write = sys.stdout.write

def putp(s):
    sys.stdout.flush()
    curses.putp(s)
    libc.fflush(stdout)

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
