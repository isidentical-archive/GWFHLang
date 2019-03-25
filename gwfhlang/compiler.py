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
    dc = (value >> 8)
    do = value - (dc << 8)
    return dc, do

def name(value):
    return list(map(ord, value))
    
COMP_MAP = {
    "==": "eq",
    "!=": "ne",
    ">": "gt",
    "<": "lt",
    ">=": "ge",
    "<=": "le"
}
"""
Register Reserves;
0, 1 => LOAD
27, 28 => CCALL
29, 30, 31 => IF

0..31 => SYMREAD
"""
class Compiler(Transformer):
    def main(self, tokens):
        return list(chain.from_iterable(filter(lambda token: token, tokens)))
        
    def symset(self, tokens):
        sym, val = tokens
        value = literal_eval(val)
        if val.type == 'INT':
            ops = arkhe_int(value)
        elif val.type == 'STR':
            ops = list(map(ord, value))
            ops.append(TypeTable.STR.value)
        elif val.type == 'BYT':
            ops = list(map(ord, value.decode('utf8')))
            ops.append(TypeTable.BYT.value)
            
        loads = [*create_instr("load", 0, *name(sym), TypeTable.STR.value),
                 *create_instr("load", 1, *ops)]
                 
        return [*loads, *create_instr("symset", 0, 1)]
    
    def comp(self, tokens):
        op1, comp, op2 = tokens
        comp = COMP_MAP.get(comp.children[0].value, "eq")
        
        read, regs = self.symread(op1, op2)
        return [*read, *create_instr(comp, *regs)]
        
    def symread(self, *syms):
        loads = [create_instr("load", n, *name(item), TypeTable.STR.value) for n, item in enumerate(syms)]
        symreads = [create_instr("symread", n, n) for n in range(len(syms))]
        return list(chain.from_iterable([*loads, *symreads])), list(range(len(syms)))
    
    def if_stmt(self, tokens):
        if len(tokens) == 3:
            comp, suite, suite_else = tokens
            loads = [*create_instr("load", 29, *arkhe_int(len(suite))),
                     *create_instr("load", 30, *arkhe_int(len(suite_else))),
                     *create_instr("load", 31, *arkhe_int(0))]
            
            code = [
                *loads,
                *comp,
                *create_instr('jfe', 31), # No jump
                *create_instr('jfn', 29), # Jump amount of suite
                *suite,
                *create_instr('jfn', 31),
                *create_instr('jfe', 30),
                *suite_else
            ]
        else:
            comp, suite = tokens
            loads = [*create_instr("load", 29, *arkhe_int(len(suite))),
                     *create_instr("load", 30, *arkhe_int(0))]
            
            code = [
                *loads,
                *comp,
                *create_instr('jfe', 30), # No jump
                *create_instr('jfn', 29), # Jump amount of suite
                *suite,
            ]
        
        return code

    def suite(self, tokens):
        return list(chain.from_iterable(tokens))
    
    def ccall(self, tokens):
        func, *args = tokens
        args, args_regs = self.symread(*args)
        
        return [*args, *create_instr("load", 27, *name(str(func)), TypeTable.STR.value), *create_instr("ccall", 27, *args_regs, 28)]
