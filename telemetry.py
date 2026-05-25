import time
import socket
import struct
import random
import pymem
import pymem.process

# --- SIMHUB C# TELEMETRY GENERATED CONSTANTS ---
GAME_SIGNATURE = 0x21ECBAA2
TELEMETRY_SIGNATURE = 0x370926DF
LAYOUT_MAJOR_VERSION = 1
LAYOUT_MINOR_VERSION = 0
EXPECTED_PACKET_LENGTH = 71

# Network configuration
SIMHUB_IP = "127.0.0.1"
SIMHUB_PORT = 20777

# --- CHEAT ENGINE POINTER CONFIGURATION ---
PROCESS_NAME = "wmn6r.exe"

# Shared base pointer for speed + RPM  (wmn6r.exe+1E5B5B0)
BASE_OFFSET_SPEED_RPM = 0x1E5B5B0
OFFSET_SPEED = 0xC90     # float  -> speed km/h
OFFSET_RPM   = 0xC8C     # float  -> engine RPM

# Controller gear: wmn6r.exe+1E5B4E8  (direct module offset, no sub-pointer)
BASE_OFFSET_GEAR_CTRL = 0x1E5B4E8   # int32 read directly at module_base + offset

# Automatic gear: raw static address 0x9AF61DA8 + offset 0x20
# NOTE: This is a raw 32-bit-style address. In a 64-bit process it may or may not
# be a valid VA depending on the game's memory layout. If reads fail consistently
# this value will stay None and the fallback gear will be used instead.
GEAR_AUTO_STATIC_ADDR = 0x9AF61DA8
OFFSET_GEAR_AUTO = 0x20             # int32 at (GEAR_AUTO_STATIC_ADDR + 0x20)


def get_pointer_address(pm, base_address, offsets):
    """
    Resolves a multi-level pointer chain in a 64-bit process.
    base_address  -- the static address to start from (already resolved to a VA)
    offsets       -- list of offsets; the final offset is added, not dereferenced
    Returns the final address, or None on any failure.
    """
    try:
        addr = pm.read_longlong(base_address)
        for offset in offsets:
            if offset == offsets[-1]:
                return addr + offset
            addr = pm.read_longlong(addr + offset)
    except Exception:
        return None


def read_gear_controller(pm, module_base):
    """
    Reads the controller gear as a signed int32 directly at
    module_base + BASE_OFFSET_GEAR_CTRL (no pointer dereference needed).
    Returns the int value, or None on failure.
    """
    try:
        addr = module_base + BASE_OFFSET_GEAR_CTRL
        return pm.read_int(addr)
    except Exception:
        return None


def read_gear_auto(pm):
    """
    Reads the automatic-transmission gear as a signed int32 from the
    raw static address GEAR_AUTO_STATIC_ADDR + OFFSET_GEAR_AUTO.
    Returns the int value, or None on failure.
    """
    try:
        return pm.read_int(GEAR_AUTO_STATIC_ADDR + OFFSET_GEAR_AUTO)
    except Exception:
        return None


def resolve_gear(gear_ctrl, gear_auto):
    """
    Gear selection logic:
      - If gear_auto is a valid, non-zero value use it (automatic transmission).
      - Otherwise fall back to gear_ctrl.
      - If both are unavailable default to 0 (Neutral).
    'Valid' for auto means the read succeeded (not None) and the value is non-zero,
    since a zero auto-gear typically means the field is unpopulated.
    """
    if gear_auto is not None and gear_auto != 0:
        return gear_auto
    if gear_ctrl is not None:
        return gear_ctrl
    return 0


def generate_uint64():
    """Generates a random 64-bit unsigned integer."""
    return random.randint(0, (2**64) - 1)


def format_gear_string(gear_val):
    """Encodes gear data into a fixed-size 8-byte null-terminated byte array."""
    if gear_val == -1:
        gear_str = "R"
    elif gear_val == 0:
        gear_str = "N"
    else:
        gear_str = str(gear_val)

    encoded = gear_str.encode('utf-8')
    if len(encoded) >= 8:
        encoded = encoded[:7]
    return encoded.ljust(8, b'\x00')


def main():
    print(f"Waiting for {PROCESS_NAME} to start...")
    pm = None

    while not pm:
        try:
            pm = pymem.Pymem(PROCESS_NAME)
            print(f"Successfully hooked into {PROCESS_NAME}!")
        except pymem.exception.ProcessNotFound:
            time.sleep(1)
        except Exception as e:
            print(f"Error attaching to process: {e}")
            time.sleep(1)

    try:
        module = pymem.process.module_from_name(pm.process_handle, PROCESS_NAME)
        module_base = module.lpBaseOfDll
        print(f"Module Base Address found: {hex(module_base)}")
    except Exception as e:
        print(f"Failed to find module base: {e}")
        return

    # Pre-compute the static base used by the speed/RPM pointer chain
    static_base_speed_rpm = module_base + BASE_OFFSET_SPEED_RPM

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Initialize session constants
    emitter_instance_id = generate_uint64()
    session_id = generate_uint64()
    packets_counter = 0
    session_time_seconds = 0.0

    print(f"Streaming {EXPECTED_PACKET_LENGTH}-byte telemetry packets to SimHub at {SIMHUB_IP}:{SIMHUB_PORT}")
    print("Press Ctrl+C to stop.")

    last_time = time.perf_counter()

    while True:
        try:
            current_time = time.perf_counter()
            dt = current_time - last_time
            if dt < 0:
                dt = 0
            last_time = current_time

            # Increment dynamic session properties
            session_time_seconds += dt
            packets_counter += 1

            # ----------------------------------------------------------------
            # SPEED  (wmn6r.exe+1E5B5B0 -> +C90)
            # ----------------------------------------------------------------
            addr_speed = get_pointer_address(pm, static_base_speed_rpm, [OFFSET_SPEED])
            speed_kmh = 0.0
            if addr_speed:
                try:
                    speed_kmh = pm.read_float(addr_speed)
                except pymem.exception.MemoryReadError:
                    pass

            # ----------------------------------------------------------------
            # RPM  (wmn6r.exe+1E5B5B0 -> +C8C)
            # ----------------------------------------------------------------
            addr_rpm = get_pointer_address(pm, static_base_speed_rpm, [OFFSET_RPM])
            engine_rpm = 0.0
            if addr_rpm:
                try:
                    engine_rpm = pm.read_float(addr_rpm)
                except pymem.exception.MemoryReadError:
                    pass

            # ----------------------------------------------------------------
            # GEAR  – controller then auto, with fallback logic
            # ----------------------------------------------------------------
            gear_ctrl = read_gear_controller(pm, module_base)
            gear_auto = read_gear_auto(pm)
            gear_value = resolve_gear(gear_ctrl, gear_auto)
            gear_bytes = format_gear_string(gear_value)

            # Fixed header flags
            packet_id = 0
            is_session_running = 1
            is_session_paused = 0
            is_replay = 0
            is_user_in_control = 1
            is_ai_in_control = 0
            is_spectator = 0
            physics_discontinuity_counter = 0

            # --- STRUCT PACKING MAP (= forces strict Pack=1 alignment matching C# layout) ---
            # Layout: 4+4+2+2+8+1+8+1+1+8+1+1+1+1+8+4 + 4+4+8 = Exactly 71 Bytes
            packet_format = '= I I H H Q B Q B B Q B B B B d I f f 8s'

            data_packet = struct.pack(
                packet_format,
                GAME_SIGNATURE,                 # uint32
                TELEMETRY_SIGNATURE,            # uint32
                LAYOUT_MAJOR_VERSION,           # uint16
                LAYOUT_MINOR_VERSION,           # uint16
                emitter_instance_id,            # uint64
                packet_id,                      # uint8
                packets_counter,                # uint64
                is_session_running,             # uint8
                is_session_paused,              # uint8
                session_id,                     # uint64
                is_replay,                      # uint8
                is_user_in_control,             # uint8
                is_ai_in_control,               # uint8
                is_spectator,                   # uint8
                session_time_seconds,           # double
                physics_discontinuity_counter,  # uint32
                speed_kmh,                      # float
                engine_rpm,                     # float
                gear_bytes                      # 8-byte array string
            )

            sock.sendto(data_packet, (SIMHUB_IP, SIMHUB_PORT))

            # ~60 Hz frequency cycle
            time.sleep(0.015)

        except KeyboardInterrupt:
            print("\nStopping bridge.")
            break
        except Exception as e:
            print(f"Error packing or sending packet: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
