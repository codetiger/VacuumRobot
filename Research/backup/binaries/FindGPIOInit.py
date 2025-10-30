# Ghidra script to find GPIO initialization and all GPIO pin numbers
# @category Analysis

from ghidra.program.model.symbol import SymbolType
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.program.model.listing import CodeUnit

def find_gpio_init():
    """Find GPIO initialization code and extract GPIO pin numbers"""

    print("=" * 80)
    print("GPIO Initialization Analysis")
    print("=" * 80)
    print()

    # Setup decompiler
    decompiler = DecompInterface()
    decompiler.openProgram(currentProgram)
    monitor = ConsoleTaskMonitor()

    symbol_table = currentProgram.getSymbolTable()

    # Find all CGpioControl related functions
    gpio_functions = []

    for symbol in symbol_table.getAllSymbols(True):
        name = symbol.getName()
        if 'CGpioControl' in name or 'Gpio' in name:
            func = getFunctionAt(symbol.getAddress())
            if func:
                gpio_functions.append((name, func))

    print(f"[1] Found {len(gpio_functions)} GPIO-related functions")
    print()

    # Decompile each
    for name, func in gpio_functions:
        print("=" * 80)
        print(f"Function: {name}")
        print(f"Address: {func.getEntryPoint()}")
        print("=" * 80)

        results = decompiler.decompileFunction(func, 90, monitor)
        if results and results.decompileCompleted():
            code = results.getDecompiledFunction().getC()
            print(code)
            print()

            # Look for numeric constants that might be GPIO numbers
            if any(keyword in code for keyword in ['GpioInit', 'GpioExport', 'CGpioControl']):
                print("  ⚠️  This function likely contains GPIO pin numbers!")
                print()
        else:
            print("  Failed to decompile")
            print()

    print()
    print("[2] Searching for numeric constant 233 (0xE9 - gpio233)...")
    print()

    # Search for references to 233
    listing = currentProgram.getListing()
    min_addr = currentProgram.getMinAddress()
    max_addr = currentProgram.getMaxAddress()

    # Search for the value 233 (0xE9)
    found_addresses = []
    addr = min_addr
    while addr and addr.compareTo(max_addr) < 0:
        try:
            # Try to get instruction or data at this address
            instr = listing.getInstructionAt(addr)
            if instr:
                # Check operands for value 233
                for i in range(instr.getNumOperands()):
                    try:
                        scalar = instr.getScalar(i)
                        if scalar and scalar.getValue() == 233:
                            found_addresses.append(addr)
                            print(f"Found reference to 233 at {addr}")
                            print(f"  Instruction: {instr}")

                            # Find containing function
                            func = getFunctionContaining(addr)
                            if func:
                                print(f"  In function: {func.getName()}")
                            print()
                            break
                    except:
                        pass

            addr = addr.add(2)  # ARM instructions are 2-byte aligned minimum
        except:
            addr = addr.add(2)
            continue

    print()
    print(f"[3] Found {len(found_addresses)} references to GPIO 233")
    print()

    # Decompile functions containing these references
    if found_addresses:
        print("[4] Decompiling functions with GPIO 233 references...")
        print()

        for addr in found_addresses[:5]:  # Limit to first 5
            func = getFunctionContaining(addr)
            if func:
                print("=" * 80)
                print(f"Function: {func.getName()} at {func.getEntryPoint()}")
                print("=" * 80)

                results = decompiler.decompileFunction(func, 90, monitor)
                if results and results.decompileCompleted():
                    code = results.getDecompiledFunction().getC()
                    print(code)
                    print()

if __name__ == '__main__':
    find_gpio_init()
