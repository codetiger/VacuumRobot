# Ghidra script to analyze GPIO and STM32 control in AuxCtrl
# @category Analysis

from ghidra.program.model.symbol import SymbolType
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

def analyze_gpio_control():
    """Analyze GPIO control and STM32 initialization functions"""

    print("=" * 80)
    print("GPIO and STM32 Control Analysis")
    print("=" * 80)
    print()

    # Setup decompiler
    decompiler = DecompInterface()
    decompiler.openProgram(currentProgram)
    monitor = ConsoleTaskMonitor()

    # Functions of interest
    target_functions = [
        'CGpioControl',
        'GpioInit',
        'GpioSetDirection',
        'enableStm32ReceiveData',
        'getStm32ReceiveData',
        'packetStm32Sleep',
        'main',
    ]

    symbol_table = currentProgram.getSymbolTable()

    print("[1] Analyzing GPIO and STM32 control functions...")
    print()

    for symbol in symbol_table.getAllSymbols(True):
        name = symbol.getName()

        # Check if this matches our targets
        is_target = any(target in name for target in target_functions)

        if is_target:
            func = getFunctionAt(symbol.getAddress())
            if func:
                print("=" * 80)
                print(f"Function: {name}")
                print(f"Address: {symbol.getAddress()}")
                print("=" * 80)
                print()

                # Decompile and show full code
                results = decompiler.decompileFunction(func, 90, monitor)
                if results and results.decompileCompleted():
                    code = results.getDecompiledFunction().getC()
                    print(code)
                    print()
                else:
                    print("Failed to decompile")
                    print()

    print()
    print("[2] Searching for /dev/ device access...")
    print()

    # Find references to device paths
    devices = ['/dev/ttyS1', '/dev/ttyS3', '/dev/ttyS0']
    listing = currentProgram.getListing()
    memory = currentProgram.getMemory()

    for dev in devices:
        found = memory.findBytes(
            currentProgram.getMinAddress(),
            dev,
            None,
            True,
            monitor
        )

        if found:
            print(f"Found '{dev}' at: {found}")
            print()

            # Find references
            refs = getReferencesTo(found)
            for ref in refs:
                ref_addr = ref.getFromAddress()
                func = getFunctionContaining(ref_addr)
                if func:
                    print(f"  Used in function: {func.getName()} at {ref_addr}")

                    # Decompile this function
                    results = decompiler.decompileFunction(func, 90, monitor)
                    if results and results.decompileCompleted():
                        code = results.getDecompiledFunction().getC()
                        # Show snippet around the device path
                        if dev in code:
                            print(f"  Code excerpt:")
                            for line in code.split('\n'):
                                if 'ttyS' in line or 'open' in line or 'ioctl' in line:
                                    print(f"    {line}")
                    print()

    print()
    print("[3] Searching for ioctl calls...")
    print()

    # Find ioctl function calls
    for symbol in symbol_table.getAllSymbols(True):
        if 'ioctl' in symbol.getName().lower():
            print(f"Found ioctl-related symbol: {symbol.getName()} at {symbol.getAddress()}")

            # Find all calls to this function
            refs = getReferencesTo(symbol.getAddress())
            for ref in refs:
                ref_func = getFunctionContaining(ref.getFromAddress())
                if ref_func:
                    print(f"  Called from: {ref_func.getName()}")

if __name__ == '__main__':
    analyze_gpio_control()
