# Ghidra script to find command IDs by analyzing packet functions
# @category: Analysis

from ghidra.program.flatapi import FlatProgramAPI

api = FlatProgramAPI(currentProgram)

print("=" * 80)
print("SEARCHING FOR PACKET COMMAND FUNCTIONS")
print("=" * 80)

# Known packet command function names from strings analysis
target_functions = [
    'packetHeartBeat',
    'packetMotorVelocity',
    'packetMotorSpeed',
    'packetBrushSpeed',
    'packetRollingSpeed',
    'packetBlowerSpeed',
    'packetLidarPower',
    'packetChargerPower',
    'packetCliffIRControl',
    'packetButtonLEDState',
    'packetWakeupAck',
    'packetResetErrorCode',
    'packetRequireSystemVersion'
]

# Get all functions
function_manager = currentProgram.getFunctionManager()
functions = function_manager.getFunctions(True)

# Search for each target function
found_functions = {}
for func in functions:
    fname = func.getName()
    for target in target_functions:
        if target.lower() in fname.lower():
            found_functions[target] = func
            break

print("\nFound {} of {} target functions".format(len(found_functions), len(target_functions)))

# Analyze each found function
listing = currentProgram.getListing()

for func_name in sorted(found_functions.keys()):
    func = found_functions[func_name]
    print("\n" + "=" * 80)
    print("Function: {} at 0x{:08x}".format(func.getName(), func.getEntryPoint().getOffset()))
    print("=" * 80)

    # Decompile the function
    from ghidra.app.decompiler import DecompInterface
    from ghidra.util.task import ConsoleTaskMonitor

    decomp = DecompInterface()
    decomp.openProgram(currentProgram)
    results = decomp.decompileFunction(func, 30, ConsoleTaskMonitor())

    if results and results.decompileCompleted():
        c_code = results.getDecompiledFunction().getC()
        # Print first 40 lines
        lines = c_code.split('\n')[:40]
        for line in lines:
            print(line)
    else:
        print("  (Decompilation failed)")

    # Also look for small immediate values in first instructions
    instructions = listing.getInstructions(func.getBody(), True)
    command_candidates = []
    count = 0
    for inst in instructions:
        count += 1
        if count > 20:
            break
        for i in range(inst.getNumOperands()):
            try:
                scalar = inst.getScalar(i)
                if scalar:
                    val = scalar.getValue()
                    if 0 <= val <= 0x20:  # Command IDs likely 0-32
                        command_candidates.append("0x{:02x}".format(val))
            except:
                pass

    if command_candidates:
        unique = list(set(command_candidates))
        unique.sort()
        print("\n  Small immediate values (possible command IDs): {}".format(", ".join(unique)))

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)
