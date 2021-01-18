#!/usr/bin/python3

import ctypes,sys,curses,re

curses.setupterm()

def tigetstr(name):
    seq = curses.tigetstr(name)
    return re.sub(b'\$<[0-9.]+[\*/]{0,2}>', b'', seq)

bold = tigetstr('bold').decode('ascii')
norm = tigetstr('sgr0').decode('ascii')
cls = tigetstr('clear').decode('ascii')
cup = curses.tigetstr('cup')

write = sys.stdout.write

def goto(row,column):
    write(curses.tparm(cup,row,column).decode('ascii'))

def clear():
    write(cls)
    
clear()
write("Enter your name: ")
name = input()

for row in [3,5,10,20]:
    goto(row, row+5)
    write(f'{bold}Hi there {name}{norm}')
    goto(row+1, row+6)
    write(f'Hi there {name}')

goto(24,0)    
write("Press enter to exit: ")
input()
clear()


        

                        
    
