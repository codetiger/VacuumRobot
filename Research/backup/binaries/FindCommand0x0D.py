# Ghidra script to find command 0x0D and analyze packetR16Power
# @category: Analysis

from ghidra.program.flatapi import FlatProgramAPI
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

api = FlatProgramAPI(currentProgram)

print("=" * 100)
print("SEARCHING FOR COMMAND 0x0D AND MISSING FUNCTIONS")
print("=" * 100)

# Initialize decompiler
decomp = DecompInterface()
decomp.openProgram(currentProgram)

# Get all functions
function_manager = currentProgram.getFunctionManager()
functions = function_manager.getFunctions(True)

# Search for packetR16Power
print("\n" + "="*100)
print("SEARCHING FOR: packetR16Power")
print("="*100)

for func in functions:
    fname = func.getName()
    if 'packetR16Power' in fname.lower() or 'r16power' in fname.lower():
        print("\n{:-<100}".format(""))
        print("Function: {}".format(func.getName()))
        print("Address: 0x{:08x}".format(func.getEntryPoint().getOffset()))
        print("-"*100)

        # Decompile the function
        results = decomp.decompileFunction(func, 30, ConsoleTaskMonitor())
        if results and results.decompileCompleted():
            c_code = results.getDecompiledFunction().getC()
            print(c_code)
        else:
            print("  [Decompilation failed]")

        # Look for command ID in assembly
        listing = currentProgram.getListing()
        instructions = listing.getInstructions(func.getBody(), True)
        command_candidates = set()
        count = 0
        for inst in instructions:
            count += 1
            if count > 25:
                break
            for i in range(inst.getNumOperands()):
                try:
                    scalar = inst.getScalar(i)
                    if scalar:
                        val = scalar.getValue()
                        if 0 <= val <= 0x30:
                            command_candidates.add(val)
                except Exception:
                    pass

        if command_candidates:
            candidates_sorted = sorted(list(command_candidates))
            print("\nPossible Command IDs: {}".format([hex(c) for c in candidates_sorted]))

# Search for any function that might use 0x0D
print("\n" + "="*100)
print("SEARCHING FOR FUNCTIONS WITH COMMAND ID 0x0D")
print("="*100)

found_0x0d = []
for func in functions:
    fname = func.getName()
    if 'packet' in fname.lower() and 'Message' in fname:
        listing = currentProgram.getListing()
        instructions = listing.getInstructions(func.getBody(), True)

        count = 0
        for inst in instructions:
            count += 1
            if count > 30:
                break
            for i in range(inst.getNumOperands()):
                try:
                    scalar = inst.getScalar(i)
                    if scalar and scalar.getValue() == 0x0D:
                        found_0x0d.append({
                            'func': func,
                            'addr': func.getEntryPoint().getOffset()
                        })
                        break
                except Exception:
                    pass

if found_0x0d:
    print("\nFound {} functions with 0x0D:".format(len(found_0x0d)))
    for item in found_0x0d:
        func = item['func']
        print("\n{:-<100}".format(""))
        print("Function: {}".format(func.getName()))
        print("Address: 0x{:08x}".format(item['addr']))
        print("-"*100)

        results = decomp.decompileFunction(func, 30, ConsoleTaskMonitor())
        if results and results.decompileCompleted():
            c_code = results.getDecompiledFunction().getC()
            print(c_code)
else:
    print("\nNo functions found with literal 0x0D in first 30 instructions")

# Search for all packet functions we might have missed
print("\n" + "="*100)
print("ALL PACKET BUILDING FUNCTIONS (COMPREHENSIVE)")
print("="*100)

packet_funcs = []
for func in functions:
    fname = func.getName()
    if 'CSerialMessagePacket::packet' in fname:
        listing = currentProgram.getListing()
        instructions = listing.getInstructions(func.getBody(), True)

        # Get command ID from first CRobotPacket::CRobotPacket call
        cmd_id = None
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
                        if 0 <= val <= 0xFF and val != 0 and val != 4 and val != 8:
                            if cmd_id is None or (val > 3 and val < 0x100):
                                cmd_id = val
                except Exception:
                    pass

        packet_funcs.append({
            'name': fname,
            'addr': func.getEntryPoint().getOffset(),
            'cmd_id': cmd_id
        })

# Sort by command ID
packet_funcs_sorted = sorted(packet_funcs, key=lambda x: x['cmd_id'] if x['cmd_id'] else 0xFF)

print("\nFound {} packet functions:".format(len(packet_funcs_sorted)))
print("\n{:<60} | {:>10} | {}".format("Function", "Address", "Cmd ID"))
print("-" * 100)
for pf in packet_funcs_sorted:
    cmd_str = "0x{:02X}".format(pf['cmd_id']) if pf['cmd_id'] is not None else "Unknown"
    short_name = pf['name'].split('::')[-1] if '::' in pf['name'] else pf['name']
    print("{:<60} | 0x{:08X} | {}".format(short_name, pf['addr'], cmd_str))

print("\n" + "="*100)
print("ANALYSIS COMPLETE")
print("="*100)
