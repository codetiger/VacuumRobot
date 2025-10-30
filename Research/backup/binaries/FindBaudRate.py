# Ghidra script to find baud rate configuration in AuxCtrl
# @category Analysis

from ghidra.program.model.symbol import SymbolType
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

def find_baud_references():
    """Find baud rate configuration"""

    print("=" * 80)
    print("Searching for Baud Rate Configuration")
    print("=" * 80)
    print()

    # Setup decompiler
    decompiler = DecompInterface()
    decompiler.openProgram(currentProgram)
    monitor = ConsoleTaskMonitor()

    # Common baud rate constants (as used by termios)
    BAUD_CONSTANTS = {
        0x0000: "B0",
        0x0001: "B50",
        0x0002: "B75",
        0x0003: "B110",
        0x0004: "B134",
        0x0005: "B150",
        0x0006: "B200",
        0x0007: "B300",
        0x0008: "B600",
        0x0009: "B1200",
        0x000A: "B1800",
        0x000B: "B2400",
        0x000C: "B4800",
        0x000D: "B9600",
        0x000E: "B19200",
        0x000F: "B38400",
        0x1001: "B57600",
        0x1002: "B115200",
        0x1003: "B230400",
        0x1004: "B460800",
    }

    # Search for setBaud function
    symbol_table = currentProgram.getSymbolTable()

    print("[1] Looking for setBaud/rateToBaud functions...")
    print()

    for symbol in symbol_table.getAllSymbols(True):
        name = symbol.getName()
        if 'Baud' in name or 'baud' in name:
            func = getFunctionAt(symbol.getAddress())
            if func:
                print(f"Found function: {name} at {symbol.getAddress()}")

                # Decompile and show
                results = decompiler.decompileFunction(func, 30, monitor)
                if results and results.decompileCompleted():
                    code = results.getDecompiledFunction().getC()
                    print(f"Code preview (first 500 chars):")
                    print(code[:500])
                    print()

    print()
    print("[2] Searching for baud rate constants...")
    print()

    # Search for references to common baud values
    for value, name in BAUD_CONSTANTS.items():
        # Search for this constant in the program
        addresses = currentProgram.getMemory().findBytes(
            currentProgram.getMinAddress(),
            bytearray([value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF]),
            None,
            True,
            monitor
        )

        if addresses:
            print(f"Found potential {name} (0x{value:04X}) constant at: {addresses}")

    print()
    print("[3] Looking for serial port initialization...")
    print()

    # Find functions that reference /dev/ttyS1
    listing = currentProgram.getListing()
    memory = currentProgram.getMemory()

    # Search for string "/dev/ttyS1"
    found = memory.findBytes(
        currentProgram.getMinAddress(),
        "/dev/ttyS1",
        None,
        True,
        monitor
    )

    if found:
        print(f"Found /dev/ttyS1 string at: {found}")

        # Find references to this string
        refs = getReferencesTo(found)
        for ref in refs:
            ref_addr = ref.getFromAddress()
            func = getFunctionContaining(ref_addr)
            if func:
                print(f"  Referenced by function: {func.getName()} at {ref_addr}")

                # Decompile this function
                results = decompiler.decompileFunction(func, 30, monitor)
                if results and results.decompileCompleted():
                    code = results.getDecompiledFunction().getC()

                    # Look for baud-related code
                    if 'baud' in code.lower() or 'rate' in code.lower():
                        print(f"  Function contains baud/rate configuration:")
                        print(code[:1000])
                        print()

    print()
    print("[4] Searching for cfsetispeed/cfsetospeed calls...")
    print()

    # These are standard termios functions for setting baud rate
    for func_name in ['cfsetispeed', 'cfsetospeed', 'tcsetattr', 'ioctl']:
        sym = symbol_table.getGlobalSymbol(None, func_name, None)
        if sym:
            print(f"Found {func_name} at {sym.getAddress()}")

            # Find all references
            refs = getReferencesTo(sym.getAddress())
            for ref in refs:
                ref_func = getFunctionContaining(ref.getFromAddress())
                if ref_func:
                    print(f"  Called from: {ref_func.getName()}")

if __name__ == '__main__':
    find_baud_references()
