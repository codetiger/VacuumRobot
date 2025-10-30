# Ghidra script to find CRC calculation in AuxCtrl
# @category Analysis

from ghidra.program.model.symbol import SymbolType
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

def find_crc_functions():
    """Find CRC calculation functions"""

    print("=" * 80)
    print("Searching for CRC Calculation Functions")
    print("=" * 80)
    print()

    # Setup decompiler
    decompiler = DecompInterface()
    decompiler.openProgram(currentProgram)
    monitor = ConsoleTaskMonitor()

    # Search for CRC-related functions
    symbol_table = currentProgram.getSymbolTable()

    print("[1] Looking for CRC/checksum functions...")
    print()

    target_functions = [
        'calcCheckSum',
        'verifyCheckSum',
        'CRobotPacket',
    ]

    for symbol in symbol_table.getAllSymbols(True):
        name = symbol.getName()

        # Check if this is a CRC-related function
        is_target = any(target in name for target in target_functions)

        if is_target and 'Robot' in name:
            func = getFunctionAt(symbol.getAddress())
            if func:
                print("=" * 80)
                print(f"Function: {name}")
                print(f"Address: {symbol.getAddress()}")
                print("=" * 80)
                print()

                # Decompile and show full code
                results = decompiler.decompileFunction(func, 60, monitor)
                if results and results.decompileCompleted():
                    code = results.getDecompiledFunction().getC()
                    print(code)
                    print()
                else:
                    print("Failed to decompile")
                    print()

    print()
    print("[2] Searching for CRC error message references...")
    print()

    # Find the "crc check is wrong" string
    listing = currentProgram.getListing()
    memory = currentProgram.getMemory()

    search_str = "crc check is wrong"
    found = memory.findBytes(
        currentProgram.getMinAddress(),
        search_str,
        None,
        True,
        monitor
    )

    if found:
        print(f"Found error message at: {found}")
        print()

        # Find references to this string
        refs = getReferencesTo(found)
        for ref in refs:
            ref_addr = ref.getFromAddress()
            func = getFunctionContaining(ref_addr)
            if func:
                print("=" * 80)
                print(f"Error message used in: {func.getName()}")
                print(f"At address: {ref_addr}")
                print("=" * 80)
                print()

                # Decompile this function
                results = decompiler.decompileFunction(func, 60, monitor)
                if results and results.decompileCompleted():
                    code = results.getDecompiledFunction().getC()
                    print(code)
                    print()

if __name__ == '__main__':
    find_crc_functions()
