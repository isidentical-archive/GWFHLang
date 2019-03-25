from pathlib import Path
from lark import Lark
from lark.indenter import Indenter

class GWFHIndenter(Indenter):
    NL_type = '_NEWLINE'
    OPEN_PAREN_types = ['LPAR', 'LSQB', 'LBRACE']
    CLOSE_PAREN_types = ['RPAR', 'RSQB', 'RBRACE']
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 4

def get_parser():
    return Lark.open("grammar.lark", parser="lalr", rel_to=__file__, postlex=GWFHIndenter(), start="main")

if __name__ == '__main__':
    parser = get_parser()
    code = """
    name = "batuhan"
    born = 2003
    """
    tree = parser.parse(code)
