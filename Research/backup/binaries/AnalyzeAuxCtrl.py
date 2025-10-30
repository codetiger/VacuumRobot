# Ghidra Python script to comprehensively analyze AuxCtrl binary
# @category: Analysis

from ghidra.program.flatapi import FlatProgramAPI
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

api = FlatProgramAPI(currentProgram)

print("=" * 100)
print("COMPREHENSIVE AUXCTRL BINARY ANALYSIS")
print("=" * 100)

# Initialize decompiler
decomp = DecompInterface()
decomp.openProgram(currentProgram)

# Get all functions
function_manager = currentProgram.getFunctionManager()
functions = function_manager.getFunctions(True)

# Target packet functions based on string analysis
target_packet_functions = [
    'packetHeartBeat',
    'packetMotorVelocity',
    'packetMotorSpeed',
    'packetBrushSpeed',
    'packetRollingSpeed',
    'packetBlowerSpeed',
    'packetLidarPower',
    'packetChargerPower',
    'packetCliffIRControl',
    'packetCliffIRDirection',
    'packetButtonLEDState',
    'packetWakeupAck',
    'packetResetErrorCode',
    'packetRequireSystemVersion',
    'packetSetIMUZero',
    'packetIMUCalibration',
    'packetIMUFactoryCalibrate',
    'packetIMUFactoryCalibrateState',
    'packetGeoMagnetismCalibrate',
    'packetGeoMagnetismCalibrateState',
    'packetMotorControlType',
    'packetRestartR16System',
    'packetStm32Sleep'
]

target_unpacket_functions = [
    'unpacketBool',
    'unpacketSensorMessage',
    'unpacketCRL200SSensorMessage',
    'unpacketCRL300SensorMessage',
    'unpacketSystemVersion',
    'unpacketDebug1',
    'unpacketErroCode'
]

target_protocol_functions = [
    'CRobotPacketSender',
    'CRobotPacketReceiver',
    'readSerialPacket',
    'processStateSYNC1',
    'processStateSYNC2',
    'processStateLength',
    'processStateAcquireData',
    'sendCommand',
    'sendBuf'
]

print("\n" + "="*100)
print("SECTION 1: PACKET BUILDING FUNCTIONS (A33 -> GD32)")
print("="*100)

packet_count = 0
for func in functions:
    fname = func.getName()
    for target in target_packet_functions:
        if target.lower() in fname.lower():
            packet_count += 1
            print("\n{:-<100}".format(""))
            print("Function {}: {}".format(packet_count, func.getName()))
            print("Address: 0x{:08x}".format(func.getEntryPoint().getOffset()))
            print("-"*100)

            # Decompile the function
            results = decomp.decompileFunction(func, 30, ConsoleTaskMonitor())
            if results and results.decompileCompleted():
                c_code = results.getDecompiledFunction().getC()
                print(c_code)
            else:
                print("  [Decompilation failed]")

            # Look for command ID candidates in assembly
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
                            if 0 <= val <= 0x30:  # Command IDs likely 0-48
                                command_candidates.add(val)
                    except Exception:
                        pass

            if command_candidates:
                candidates_sorted = sorted(list(command_candidates))
                print("\nPossible Command IDs: {}".format([hex(c) for c in candidates_sorted]))

            break

print("\n" + "="*100)
print("SECTION 2: PACKET PARSING FUNCTIONS (GD32 -> A33)")
print("="*100)

unpacket_count = 0
for func in functions:
    fname = func.getName()
    for target in target_unpacket_functions:
        if target.lower() in fname.lower():
            unpacket_count += 1
            print("\n{:-<100}".format(""))
            print("Function {}: {}".format(unpacket_count, func.getName()))
            print("Address: 0x{:08x}".format(func.getEntryPoint().getOffset()))
            print("-"*100)

            results = decomp.decompileFunction(func, 30, ConsoleTaskMonitor())
            if results and results.decompileCompleted():
                c_code = results.getDecompiledFunction().getC()
                # Print first 60 lines
                lines = c_code.split('\n')[:60]
                print('\n'.join(lines))
                if len(c_code.split('\n')) > 60:
                    print("\n[... {} more lines ...]".format(len(c_code.split('\n')) - 60))
            else:
                print("  [Decompilation failed]")
            break

print("\n" + "="*100)
print("SECTION 3: PROTOCOL STATE MACHINE FUNCTIONS")
print("="*100)

protocol_count = 0
for func in functions:
    fname = func.getName()
    for target in target_protocol_functions:
        if target.lower() in fname.lower():
            protocol_count += 1
            print("\n{:-<100}".format(""))
            print("Function {}: {}".format(protocol_count, func.getName()))
            print("Address: 0x{:08x}".format(func.getEntryPoint().getOffset()))
            print("-"*100)

            results = decomp.decompileFunction(func, 30, ConsoleTaskMonitor())
            if results and results.decompileCompleted():
                c_code = results.getDecompiledFunction().getC()
                # Print first 50 lines for protocol functions
                lines = c_code.split('\n')[:50]
                print('\n'.join(lines))
                if len(c_code.split('\n')) > 50:
                    print("\n[... {} more lines ...]".format(len(c_code.split('\n')) - 50))
            else:
                print("  [Decompilation failed]")
            break

print("\n" + "="*100)
print("SECTION 4: SEARCHING FOR COMMAND ID CONSTANTS")
print("="*100)

# Search for strings that mention command IDs
memory = currentProgram.getMemory()
address_factory = currentProgram.getAddressFactory()
listing = currentProgram.getListing()

# Look for error messages that reference command IDs
strings_list = []
for defined_str in listing.getDefinedData(True):
    if defined_str.hasStringValue():
        str_val = defined_str.getValue()
        if isinstance(str_val, str):
            if 'CMD_' in str_val or 'command' in str_val.lower():
                strings_list.append({
                    'address': defined_str.getAddress(),
                    'value': str_val
                })

print("\nFound {} command-related strings:".format(len(strings_list)))
for s in strings_list[:20]:  # Limit to 20
    print("  0x{:08x}: {}".format(s['address'].getOffset(), s['value']))

print("\n" + "="*100)
print("ANALYSIS COMPLETE")
print("="*100)
print("\nSummary:")
print("  - Packet building functions analyzed: {}".format(packet_count))
print("  - Packet parsing functions analyzed: {}".format(unpacket_count))
print("  - Protocol functions analyzed: {}".format(protocol_count))
print("  - Command-related strings found: {}".format(len(strings_list)))
