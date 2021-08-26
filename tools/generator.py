#!/usr/bin/env python3
"""
Tool to generate the is_prime source code for the interpreter bash script
"""

import os
from itertools import product
WIDTH = 120
DIR_PREFIX = 'src'
ALPHABET = ['0', '1', '#']


def clear():
    return '\x1b[2J'


def clear_line():
    return '\x1b[2K'


def copy_rect(top, left, bottom, right, targety, targetx):
    return f'\x1b[{top};{left};{bottom};{right};1;{targety};{targetx};1$v'


def mov_cursor(targety, targetx):
    return f'\x1b[{targety};{targetx}H'


def get_checksum(line):
    return f'\x1b[{line};1;{line};{WIDTH // 2};{line};{WIDTH // 2}*y'


def checksum(sym, idx):
    negsum = 0x10000 - ord(sym)
    return f'\x1bP{idx}!~{negsum:04X}\x1b\\'


def mov_right(line):
    ret = copy_rect(line, 2, line, WIDTH, line, 1)
    ret += mov_cursor(line, WIDTH) + '#'
    return ret


def mov_left(line):
    ret = copy_rect(line, 1, line, WIDTH - 1, line, 2)
    ret += mov_cursor(line, 1) + '#'
    return ret


def modify_band(line, sym, mov):
    sequence = mov_cursor(line, WIDTH // 2) + sym + mov_cursor(3, 1)
    if mov == 'L':
        sequence += mov_left(line)
    elif mov == 'R':
        sequence += mov_right(line)
    return sequence


def create_tapewriter(sym1, mov1, sym2, mov2):
    band_modification = modify_band(1, sym1, mov1) + modify_band(2, sym2, mov2)
    return band_modification + mov_cursor(3, 1) + (
            get_checksum(1) + get_checksum(2)
    )


def init_file(prompt):
    empty = '#' * WIDTH
    ret = (
            clear() +
            mov_cursor(1, 1) + empty +
            mov_cursor(2, 1) + empty +
            mov_cursor(3, 1) + prompt +
            mov_cursor(1, WIDTH // 2)
    )
    return ret


def post_init_file():
    return (
            mov_cursor(3, WIDTH // 2) + clear_line() + '^' +
            mov_cursor(3, 1) + get_checksum(1) + get_checksum(2)
    )


def send_message(msg):
    return (mov_cursor(3, 1) + f'{msg:30}'
            + mov_cursor(4, 1) + "Press ^C to close"
            + mov_cursor(5, 1))


class DTuring:
    def __init__(self, transitions, initial_state,
                 final_states, prompt=''):
        self.transitions = transitions.copy()
        self.states = list(self.transitions.keys())
        self.initial_state = initial_state
        self.final_states = final_states.copy()
        self.mono_states = {}
        self.mono_num = 0
        self.prompt = prompt
        self._add_invalid()
        self._combine_state_with_move()
        for state in self.states:
            print(state)
            print(len(list(self.transitions[state].keys())))

    def _add_invalid(self):
        if "invalid" not in self.states:
            self.states += ["invalid"]
        if "invalid" not in self.final_states:
            self.final_states["invalid"] = "Invalid State, halting"
        for state in self.states:
            if state not in self.transitions:
                self.transitions[state] = {}
            for sym in product(ALPHABET, ALPHABET):
                if sym not in self.transitions[state]:
                    self.transitions[state][sym] = (
                            "invalid", ('#', 'N'), ('#', 'N')
                    )

    def _combine_state_with_move(self):
        for (_, trans) in self.transitions.items():
            for (_, out) in trans.items():
                self.s_to_string(out)

    def _validate(self):
        trans_states = list(self.transitions.keys())
        trans_states.sort()
        self.states.sort()

    def s_to_string(self, s):
        if s not in self.mono_states:
            self.mono_states[s] = hex(self.mono_num)[2:]
            self.mono_num += 1
        return self.mono_states[s]

    def create_dirs(self):
        os.mkdir(f'{DIR_PREFIX}')
        with open(f'{DIR_PREFIX}/init', 'w') as initfile:
            initfile.write(init_file(self.prompt))
        with open(f'{DIR_PREFIX}/postinit', 'w') as postinitfile:
            postinitfile.write(post_init_file())
        for (_, monname) in self.mono_states.items():
            outpath = f'{DIR_PREFIX}/{monname}'
            os.mkdir(outpath)
        for ((state, change1, change2), monname) in self.mono_states.items():
            outpath = f'{DIR_PREFIX}/{monname}'
            self.create_symlinks(state, monname)
            self.create_tapewriter_file(outpath, state, change1, change2)

    def create_symlinks(self, state, name):
        if state in self.final_states:
            return

        for ((sym1, sym2), out) in self.transitions[state].items():
            print(f'{len(list(self.transitions[state].keys()))} - {state}')
            for checkname in [
                    checksum(sym1, 1) + checksum(sym2, 2),
                    checksum(sym2, 2) + checksum(sym1, 1)
                    ]:
                target = self.s_to_string(out)
                if state == self.initial_state:
                    try:
                        os.symlink(target, f'{DIR_PREFIX}/{checkname}')
                    except FileExistsError:
                        pass
                os.symlink(f'../{target}', f'{DIR_PREFIX}/{name}/{checkname}')

    def create_tapewriter_file(self, outpath, state, change1, change2):
        if state in self.final_states:
            tapewriter = send_message(self.final_states[state])
        else:
            (sym1, mov1) = change1
            (sym2, mov2) = change2
            tapewriter = create_tapewriter(sym1, mov1, sym2, mov2)
        with open(f'{outpath}/w', 'w') as outfile:
            outfile.write(tapewriter)


machine = DTuring(
    transitions={
        'clr0': {
            ('#', '#'): ('notprime', ('#', 'N'), ('#', 'N')),
            ('0', '#'): ('clr0', ('#', 'R'), ('#', 'N')),
            ('1', '#'): ('chk1', ('1', 'R'), ('1', 'L')),
        },
        'chk1': {
            ('#', '#'): ('notprime', ('#', 'N'), ('#', 'N')),
            ('0', '#'): ('chk2', ('0', 'R'), ('0', 'L')),
            ('1', '#'): ('chk2', ('1', 'R'), ('1', 'L')),
        },
        'chk2': {
            ('#', '#'): ('prime', ('#', 'R'), ('#', 'N')),
            ('0', '#'): ('movinit0', ('0', 'R'), ('0', 'L')),
            ('1', '#'): ('movinit1', ('1', 'R'), ('1', 'L')),
        },
        'movinit0': {
            ('#', '#'): ('notprime', ('#', 'R'), ('#', 'N')),
            ('0', '#'): ('movinit0', ('0', 'R'), ('0', 'L')),
            ('1', '#'): ('movinit1', ('1', 'R'), ('1', 'L')),
        },
        'movinit1': {
            ('#', '#'): ('initquot', ('#', 'R'), ('#', 'N')),
            ('0', '#'): ('movinit0', ('0', 'R'), ('0', 'L')),
            ('1', '#'): ('movinit1', ('1', 'R'), ('1', 'L')),
        },
        'initquot': {
            ('#', '#'): ('inc0', ('1', 'N'), ('#', 'R')),
        },
        'inc0': {
            ('#', '#'): ('prime', ('1', 'N'), ('#', 'N')),
            ('#', '0'): ('align', ('1', 'R'), ('0', 'R')),
            ('#', '1'): ('align', ('1', 'R'), ('1', 'R')),
            ('0', '#'): ('prime', ('0', 'N'), ('#', 'N')),
            ('0', '0'): ('al1', ('1', 'R'), ('0', 'R')),
            ('0', '1'): ('al1', ('1', 'R'), ('1', 'R')),
            ('1', '#'): ('prime', ('1', 'N'), ('#', 'N')),
            ('1', '0'): ('inc1', ('0', 'R'), ('0', 'R')),
            ('1', '1'): ('inc1', ('0', 'R'), ('1', 'R')),
        },
        'inc1': {
            ('#', '#'): ('inc0', ('#', 'N'), ('#', 'N')),
            ('#', '0'): ('inc0', ('#', 'N'), ('0', 'R')),
            ('#', '1'): ('inc0', ('#', 'N'), ('1', 'R')),
            ('0', '#'): ('prime', ('0', 'N'), ('#', 'N')),
            ('0', '0'): ('inc0', ('0', 'N'), ('0', 'R')),
            ('0', '1'): ('inc0', ('0', 'N'), ('1', 'R')),
            ('1', '#'): ('prime', ('1', 'N'), ('#', 'N')),
            ('1', '0'): ('inc0', ('1', 'N'), ('0', 'R')),
            ('1', '1'): ('inc0', ('1', 'N'), ('1', 'R')),
        },
        'al0': {
            ('#', '#'): ('dleq', ('#', 'L'), ('#', 'L')),
            ('#', '0'): ('align', ('#', 'N'), ('0', 'R')),
            ('#', '1'): ('align', ('#', 'N'), ('1', 'R')),
            ('0', '#'): ('prime', ('0', 'N'), ('#', 'N')),
            ('0', '0'): ('al1', ('0', 'R'), ('0', 'R')),
            ('0', '1'): ('al1', ('0', 'R'), ('1', 'R')),
            ('1', '#'): ('prime', ('1', 'N'), ('#', 'N')),
            ('1', '0'): ('al1', ('1', 'R'), ('0', 'R')),
            ('1', '1'): ('al1', ('1', 'R'), ('1', 'R')),
        },
        'al1': {
            ('#', '#'): ('dleq', ('#', 'L'), ('#', 'L')),
            ('#', '0'): ('align', ('#', 'N'), ('0', 'R')),
            ('#', '1'): ('align', ('#', 'N'), ('1', 'R')),
            ('0', '#'): ('prime', ('0', 'N'), ('#', 'N')),
            ('0', '0'): ('al0', ('0', 'N'), ('0', 'R')),
            ('0', '1'): ('al0', ('0', 'N'), ('1', 'R')),
            ('1', '#'): ('prime', ('1', 'N'), ('#', 'N')),
            ('1', '0'): ('al0', ('1', 'N'), ('0', 'R')),
            ('1', '1'): ('al0', ('1', 'N'), ('1', 'R')),
        },
        'align': {
            ('#', '#'): ('dleq', ('#', 'L'), ('#', 'L')),
            ('#', '0'): ('align', ('#', 'N'), ('0', 'R')),
            ('#', '1'): ('align', ('#', 'N'), ('1', 'R')),
            ('0', '0'): ('align', ('0', 'R'), ('0', 'R')),
            ('0', '1'): ('align', ('0', 'R'), ('1', 'R')),
            ('1', '0'): ('align', ('1', 'R'), ('0', 'R')),
            ('1', '1'): ('align', ('1', 'R'), ('1', 'R')),
        },
        'dleq': {
            ('#', '#'): ('notprime', ('#', 'N'), ('#', 'N')),
            ('#', '0'): ('sub0', ('#', 'R'), ('0', 'R')),
            ('#', '1'): ('sub0', ('#', 'R'), ('1', 'R')),
            ('0', '0'): ('dleq', ('0', 'L'), ('0', 'L')),
            ('0', '1'): ('dless', ('0', 'L'), ('1', 'L')),
            ('1', '0'): ('dskip0', ('1', 'L'), ('0', 'L')),
            ('1', '1'): ('dleq', ('1', 'L'), ('1', 'L')),
        },
        'dless': {
            ('#', '#'): ('copy0', ('#', 'L'), ('#', 'R')),
            ('#', '0'): ('sub0', ('#', 'R'), ('0', 'R')),
            ('#', '1'): ('sub0', ('#', 'R'), ('1', 'R')),
            ('0', '0'): ('dless', ('0', 'L'), ('0', 'L')),
            ('0', '1'): ('dless', ('0', 'L'), ('1', 'L')),
            ('1', '0'): ('dless', ('1', 'L'), ('0', 'L')),
            ('1', '1'): ('dless', ('1', 'L'), ('1', 'L')),
        },
        'dskip0': {
            ('#', '#'): ('copy0', ('#', 'L'), ('#', 'R')),
            ('#', '0'): ('dskip1', ('#', 'R'), ('0', 'R')),
            ('#', '1'): ('dskip1', ('#', 'R'), ('1', 'R')),
            ('0', '0'): ('dskip0', ('0', 'L'), ('0', 'L')),
            ('0', '1'): ('dskip0', ('0', 'L'), ('1', 'L')),
            ('1', '0'): ('dskip0', ('1', 'L'), ('0', 'L')),
            ('1', '1'): ('dskip0', ('1', 'L'), ('1', 'L')),
        },
        'dskip1': {
            ('#', '#'): ('shift', ('#', 'L'), ('#', 'L')),
            ('#', '0'): ('shift', ('#', 'L'), ('0', 'L')),
            ('#', '1'): ('shift', ('#', 'L'), ('1', 'L')),
            ('0', '0'): ('dskip1', ('0', 'R'), ('0', 'R')),
            ('0', '1'): ('dskip1', ('0', 'R'), ('1', 'R')),
            ('1', '0'): ('dskip1', ('1', 'R'), ('0', 'R')),
            ('1', '1'): ('dskip1', ('1', 'R'), ('1', 'R')),
        },
        'sub0': {
            ('#', '#'): ('shift', ('#', 'L'), ('#', 'L')),
            ('#', '0'): ('shift', ('#', 'L'), ('0', 'L')),
            ('#', '1'): ('shift', ('#', 'L'), ('1', 'L')),
            ('0', '0'): ('sub0', ('0', 'R'), ('0', 'R')),
            ('0', '1'): ('sub0', ('0', 'R'), ('1', 'R')),
            ('1', '0'): ('sub1', ('1', 'R'), ('1', 'R')),
            ('1', '1'): ('sub0', ('1', 'R'), ('0', 'R')),
        },
        'sub1': {
            ('#', '1'): ('shift', ('#', 'L'), ('0', 'L')),
            ('0', '0'): ('sub1', ('0', 'R'), ('1', 'R')),
            ('0', '1'): ('sub0', ('0', 'R'), ('0', 'R')),
            ('1', '0'): ('sub1', ('1', 'R'), ('0', 'R')),
            ('1', '1'): ('sub1', ('1', 'R'), ('1', 'R')),
        },
        'shift': {
            ('0', '0'): ('dleq', ('0', 'N'), ('0', 'L')),
            ('0', '1'): ('dless', ('0', 'N'), ('1', 'L')),
            ('1', '0'): ('dleq', ('1', 'N'), ('0', 'L')),
            ('1', '1'): ('dless', ('1', 'N'), ('1', 'L')),
        },
        'copy0': {
            ('#', '#'): ('copy1', ('#', 'R'), ('#', 'L')),
            ('0', '0'): ('copy0', ('0', 'L'), ('#', 'R')),
            ('0', '1'): ('copy0', ('0', 'L'), ('#', 'R')),
            ('1', '0'): ('copy0', ('1', 'L'), ('#', 'R')),
            ('1', '1'): ('copy0', ('1', 'L'), ('#', 'R')),
        },
        'copy1': {
            ('#', '#'): ('inc0', ('#', 'R'), ('#', 'R')),
            ('0', '#'): ('copy1', ('0', 'R'), ('0', 'L')),
            ('1', '#'): ('copy1', ('1', 'R'), ('1', 'L')),
        }
    },
    initial_state='clr0',
    final_states={
        'notprime': 'Number is not prime',
        'prime': 'Number is prime'
    },
    prompt='Please type your number in binary (<29 bits) and press enter'
)

machine.create_dirs()
