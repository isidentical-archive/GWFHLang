from gwfhlang.parser import get_parser
from gwfhlang.compiler import Compiler
from arkhe.controller import Arkhe
from arkhe.debugger import ADB

def main(file, mode="normal"):
    parser = get_parser()
    compiler = Compiler()
    with open(file) as f:
        content = f.read()
    
    code = compiler.transform(parser.parse(content))
    vm = Arkhe(code)
    if mode.lower().startswith('d'):
        adb = ADB()
        adb.vm = vm
        adb.run()
    else:
        vm.eval()

if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
