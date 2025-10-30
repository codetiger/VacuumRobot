# Ghidra script to find response command handlers (GD32 -> A33)
# @category: Analysis

from ghidra.program.flatapi import FlatProgramAPI
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

api = FlatProgramAPI(currentProgram)

print("=" * 100)
print("ANALYZING RESPONSE COMMAND HANDLERS")
print("=" * 100)

decomp = DecompInterface()
decomp.openProgram(currentProgram)

function_manager = currentProgram.getFunctionManager()
functions = function_manager.getFunctions(True)

# Find the main packet handling/switch function
print("\nSearching for main packet handler with switch statement...")

handler_funcs = []
for func in functions:
    fname = func.getName()
    if 'handle' in fname.lower() and ('packet' in fname.lower() or 'message' in fname.lower() or 'sensor' in fname.lower()):
        handler_funcs.append(func)

print("\nFound {} potential handler functions:".format(len(handler_funcs)))
for func in handler_funcs:
    print("  - {} at 0x{:08x}".format(func.getName(), func.getEntryPoint().getOffset()))

# Decompile the handlers to find switch statements
print("\n" + "="*100)
print("DECOMPILING PACKET HANDLERS")
print("="*100)

for func in handler_funcs[:5]:  # Analyze first 5 handlers
    print("\n{:-<100}".format(""))
    print("Function: {}".format(func.getName()))
    print("Address: 0x{:08x}".format(func.getEntryPoint().getOffset()))
    print("-"*100)

    results = decomp.decompileFunction(func, 30, ConsoleTaskMonitor())
    if results and results.decompileCompleted():
        c_code = results.getDecompiledFunction().getC()
        # Print first 100 lines to see switch statements
        lines = c_code.split('\n')[:100]
        print('\n'.join(lines))
        if len(c_code.split('\n')) > 100:
            print("\n[... {} more lines ...]".format(len(c_code.split('\n')) - 100))
    else:
        print("  [Decompilation failed]")

# Search for functions that read packet ID and compare values
print("\n" + "="*100)
print("SEARCHING FOR PACKET ID COMPARISONS")
print("="*100)

# Look for getPacketID function calls
listing = currentProgram.getListing()
for func in functions:
    fname = func.getName()

    # Skip if not a likely message handler
    if not any(x in fname.lower() for x in ['handle', 'process', 'receive', 'parse']):
        continue

    # Look for comparisons with small constants (command IDs)
    instructions = listing.getInstructions(func.getBody(), True)
    cmd_comparisons = []

    count = 0
    for inst in instructions:
        count += 1
        if count > 200:  # Check more instructions for handlers
            break

        # Look for CMP instructions with immediate values
        mnemonic = inst.getMnemonicString()
        if mnemonic in ['cmp', 'CMP']:
            for i in range(inst.getNumOperands()):
                try:
                    scalar = inst.getScalar(i)
                    if scalar:
                        val = scalar.getValue()
                        if 0 <= val <= 0x20:  # Likely command IDs 0-32
                            cmd_comparisons.append(val)
                except Exception:
                    pass

    if cmd_comparisons:
        unique_cmds = sorted(set(cmd_comparisons))
        if len(unique_cmds) >= 3:  # Only show functions with multiple command checks
            print("\n{}: {}".format(func.getName(), [hex(c) for c in unique_cmds]))

print("\n" + "="*100)
print("COMPLETE")
print("="*100)
