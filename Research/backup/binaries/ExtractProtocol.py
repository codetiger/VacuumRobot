# Ghidra Python script to extract packet protocol information
# @category: Analysis

from ghidra.program.model.listing import CodeUnit
from ghidra.program.model.symbol import SymbolType
from ghidra.program.flatapi import FlatProgramAPI

api = FlatProgramAPI(currentProgram)

print("=" * 80)
print("EXTRACTING PACKET PROTOCOL INFORMATION")
print("=" * 80)

# Get all defined functions
function_manager = currentProgram.getFunctionManager()
functions = function_manager.getFunctions(True)  # True = forward order

packet_functions = []
for func in functions:
    name = func.getName()
    if 'packet' in name.lower() or 'Packet' in name:
        packet_functions.append(func)

print("\nFound {} packet-related functions".format(len(packet_functions)))

# Analyze each packet function
print("\n" + "=" * 80)
print("PACKET FUNCTION ANALYSIS")
print("=" * 80)

for func in packet_functions[:50]:  # Limit to first 50
    print("\n{} at 0x{:08x}".format(func.getName(), func.getEntryPoint().getOffset()))

    # Get the first few instructions
    listing = currentProgram.getListing()
    instructions = listing.getInstructions(func.getBody(), True)

    # Look for immediate values (potential command IDs)
    imm_values = []
    count = 0
    for inst in instructions:
        count += 1
        if count > 30:  # Only check first 30 instructions
            break

        # Check scalar operands for command ID candidates
        for i in range(inst.getNumOperands()):
            # Check if operand is a scalar (immediate value)
            try:
                scalar = inst.getScalar(i)
                if scalar is not None:
                    value = scalar.getValue()
                    if 0 <= value <= 255:  # Command IDs are likely single bytes
                        imm_values.append(hex(value))
            except:
                pass

    if imm_values:
        print("  Immediate values: {}".format(', '.join(set(imm_values))))

print("\n" + "=" * 80)
print("SEARCHING FOR COMMAND ID TABLES")
print("=" * 80)

# Search for data arrays that might be command ID tables
memory = currentProgram.getMemory()
data_iterator = listing.getDefinedData(True)

for data in data_iterator:
    if data.isArray():
        array = data
        if array.getNumElements() > 5 and array.getNumElements() < 100:
            # Check if it looks like a command table
            name = data.getLabel()
            if name and ('command' in name.lower() or 'packet' in name.lower()):
                print("\nFound potential command table: {} at 0x{:08x}".format(
                    name, data.getAddress().getOffset()))
                print("  Array size: {} elements".format(array.getNumElements()))

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)
