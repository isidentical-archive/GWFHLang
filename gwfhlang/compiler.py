from ast import literal_eval
from lark import Transformer
from gwfhlang.parser import get_parser
from arkhe.utils import create_instr
from arkhe.vm import TypeTable
from arkhe.controller import Arkhe
from arkhe.debugger import ADB
from itertools import chain
from textwrap import dedent


def arkhe_int(value):
    dc = value >> 8
    do = value - (dc << 8)
    return dc, do


def name(value):
    return list(map(ord, value))


COMP_MAP = {"==": "eq", "!=": "ne", ">": "gt", "<": "lt", ">=": "ge", "<=": "le"}
FACT_MAP = {"+": "add", "-": "sub", "*": "mul", "/": "truediv"}

"""
Register Reserves;
0, 1 => LOAD
26 => RVM
27, 28 => CCALL
29, 30, 31 => IF

0..31 => SYMREAD
"""


class Compiler(Transformer):
    def main(self, tokens):
        return list(chain.from_iterable(filter(lambda token: token, tokens)))

    def symset(self, tokens):
        sym, val = tokens
        pre, ops = self.load_value(val)

        loads = [
            *pre,
            *create_instr("load", 0, *name(sym), TypeTable.STR.value),
            *create_instr("load", 1, *ops),
        ]
        
        return [*loads, *create_instr("symset", 0, 1)]

    def comp(self, tokens):
        comp = COMP_MAP.get(tokens.pop(1).children[0].value)
        inst, regs = self.tbb(tokens)
        return 0, [*inst, *create_instr(comp, *regs)]

    def arith(self, tokens):
        fact = FACT_MAP.get(tokens.pop(1).children[0].value)
        inst, regs = self.tbb(tokens)
        return 26, [*inst, *create_instr(fact, *regs, 26)]
        
    def symread(self, *syms, **kwargs):
        start = kwargs.pop('start', 0)
        loads = [
            create_instr("load", n, *name(item), TypeTable.STR.value)
            for n, item in enumerate(syms, start)
        ]
        symreads = [create_instr("symread", n, n) for n in range(len(syms))]
        return list(chain.from_iterable([*loads, *symreads])), list(range(len(syms)))

    def if_stmt(self, tokens):
        if len(tokens) == 3:
            comp, suite, suite_else = tokens
            loads = [
                *create_instr("load", 29, *arkhe_int(len(suite))),
                *create_instr("load", 30, *arkhe_int(len(suite_else))),
                *create_instr("load", 31, *arkhe_int(0)),
            ]

            code = [
                *loads,
                *comp,
                *create_instr("jfe", 31),  # No jump
                *create_instr("jfn", 29),  # Jump amount of suite
                *suite,
                *create_instr("jfn", 31),
                *create_instr("jfe", 30),
                *suite_else,
            ]

        else:
            comp, suite = tokens
            loads = [
                *create_instr("load", 29, *arkhe_int(len(suite))),
                *create_instr("load", 30, *arkhe_int(0)),
            ]

            code = [
                *loads,
                *comp,
                *create_instr("jfe", 30),  # No jump
                *create_instr("jfn", 29),  # Jump amount of suite
                *suite,
            ]

        return code

    def suite(self, tokens):
        return list(chain.from_iterable(tokens))

    def load_value(self, val):
        if isinstance(val, list):
            t, pre = val
            if t:
                ops = [t, TypeTable.REG.value]
            else:
                ops = []
                
        else:    
            value = literal_eval(val)
            pre = []
            if val.type == "INT":
                ops = arkhe_int(value)
            elif val.type == "STR":
                ops = list(map(ord, value))
                ops.append(TypeTable.STR.value)
            elif val.type == "BYT":
                ops = list(map(ord, value.decode("utf8")))
                ops.append(TypeTable.BYT.value)
            
        return pre, ops
        
    def ccall(self, tokens):
        func, *args = tokens
        args, args_regs = self.symread(*args)

        return [
            *args,
            *create_instr("load", 27, *name(str(func)), TypeTable.STR.value),
            *create_instr("ccall", 27, *args_regs, 28),
        ]
    
    def tbb(self, tokens):
        inst = []
        regs = []
        for operand in tokens:
            next_free_reg = max(regs, default=-1) + 1
            if operand.type == 'SYM':
                read, reg = self.symread(str(operand), start=next_free_reg)
                inst.extend(read)
                regs.extend(reg)
            elif operand.type == 'STR' or operand.type == 'INT':
                _, read = self.load_value(operand)
                inst.extend(create_instr("load", next_free_reg, *read))
                regs.append(next_free_reg)
                
        return inst, regs
