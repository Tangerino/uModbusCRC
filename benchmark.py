#!/usr/bin/env python3
"""
Modbus CRC16 Benchmark for ESP32
Compares modbus_crc module (with native optimization) vs pure Python implementation
"""

import gc
import sys

try:
    import utime as time
    IS_MICROPYTHON = True
except ImportError:
    import time
    IS_MICROPYTHON = False

try:
    from machine import freq
    ESP32 = True
except ImportError:
    ESP32 = False

# Import the modbus_crc module (may have @micropython.native optimization)
import modbus_crc


# Pure Python CRC implementation for comparison
def crc16_pure_python(data):
    """Pure Python Modbus CRC16 - for benchmark comparison"""
    # CRC16 Modbus table
    table = (
        0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
        0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
        0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
        0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
        0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
        0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
        0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
        0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
        0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
        0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
        0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
        0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
        0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
        0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
        0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
        0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
        0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
        0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
        0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
        0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
        0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
        0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
        0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
        0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
        0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
        0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
        0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
        0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
        0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
        0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
        0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
        0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040,
    )
    
    crc = 0xFFFF
    for byte in data:
        crc = (crc >> 8) ^ table[(crc ^ byte) & 0xFF]
    return bytes([crc & 0xFF, crc >> 8])


def format_time(microseconds):
    """Format time with appropriate units"""
    if microseconds < 1000:
        return f"{microseconds:.1f} µs"
    elif microseconds < 1000000:
        return f"{microseconds/1000:.2f} ms"
    else:
        return f"{microseconds/1000000:.2f} s"


def benchmark(func, data, iterations=1000):
    """Run benchmark and return time per operation in microseconds"""
    if IS_MICROPYTHON:
        gc.collect()
        start = time.ticks_us()
        for _ in range(iterations):
            _ = func(data)
        elapsed = time.ticks_diff(time.ticks_us(), start)
    else:
        start = time.perf_counter()
        for _ in range(iterations):
            _ = func(data)
        elapsed = (time.perf_counter() - start) * 1000000
    
    return elapsed / iterations


def main():
    """Run CRC benchmark"""
    print("=" * 80)
    print(" " * 25 + "MODBUS CRC16 BENCHMARK")
    print("=" * 80)
    
    # System info
    if ESP32:
        try:
            print(f"Platform: ESP32 @ {freq()/1000000:.0f} MHz")
        except:
            print("Platform: ESP32")
    elif IS_MICROPYTHON:
        print("Platform: MicroPython")
    else:
        print(f"Platform: CPython {sys.version.split()[0]}")
    
    if IS_MICROPYTHON:
        gc.collect()
        print(f"Free Memory: {gc.mem_free():,} bytes")
    
    # Check which implementation modbus_crc is using
    if hasattr(modbus_crc, '_HAS_NATIVE') and hasattr(modbus_crc, '_MP'):
        if modbus_crc._MP and modbus_crc._HAS_NATIVE:
            print("modbus_crc module: Using @micropython.native optimization ✓")
        elif modbus_crc._MP:
            print("modbus_crc module: MicroPython without native")
        else:
            print("modbus_crc module: CPython implementation")
    
    print("-" * 80)
    
    # Validate both produce same results
    test_data = b'\x01\x03\x00\x00\x00\x06'
    result1 = modbus_crc.crc16(test_data)
    result2 = crc16_pure_python(test_data)
    print(f"Validation test:")
    print(f"  modbus_crc.crc16(): {result1.hex()}")
    print(f"  pure_python_crc16(): {result2.hex()}")
    if result1 == result2:
        print("  ✓ Results match!\n")
    else:
        print("  ✗ Results differ!\n")
        return
    
    # Test data sizes
    test_sizes = [
        (6, "6 bytes"),
        (8, "8 bytes"),
        (32, "32 bytes"),
        (64, "64 bytes"),
        (256, "256 bytes"),
        (512, "512 bytes"),
        (1024, "1 KB"),
    ]
    
    print("=" * 80)
    print("PERFORMANCE COMPARISON")
    print("-" * 80)
    print(f"{'Data Size':<15} {'modbus_crc':<20} {'Pure Python':<20} {'Speedup':<10}")
    print("-" * 80)
    
    for size, label in test_sizes:
        # Create test data
        data = bytes(range(size % 256)) * (size // 256 + 1)
        data = data[:size]
        
        # Adjust iterations based on data size
        iterations = max(100, 10000 // (size + 1))
        
        # Benchmark modbus_crc
        time1_us = benchmark(modbus_crc.crc16, data, iterations)
        ops1 = 1000000 / time1_us
        
        # Benchmark pure Python
        time2_us = benchmark(crc16_pure_python, data, iterations)
        ops2 = 1000000 / time2_us
        
        # Calculate speedup
        speedup = time2_us / time1_us
        
        # Format results
        modbus_result = f"{format_time(time1_us)} ({ops1:.0f} ops/s)"
        python_result = f"{format_time(time2_us)} ({ops2:.0f} ops/s)"
        
        print(f"{label:<15} {modbus_result:<20} {python_result:<20} {speedup:>6.2f}x")
    
    print("-" * 80)
    
    # Summary statistics
    print("\nTHROUGHPUT COMPARISON (for 256 bytes)")
    print("-" * 80)
    
    data = bytes(range(256))
    iterations = 1000
    
    # modbus_crc throughput
    time1_us = benchmark(modbus_crc.crc16, data, iterations)
    throughput1 = (256 * 1000000 / time1_us) / 1024  # KB/s
    
    # Pure Python throughput
    time2_us = benchmark(crc16_pure_python, data, iterations)
    throughput2 = (256 * 1000000 / time2_us) / 1024  # KB/s
    
    print(f"modbus_crc module:  {throughput1:>8.1f} KB/s")
    print(f"Pure Python:        {throughput2:>8.1f} KB/s")
    print(f"Performance gain:   {(throughput1/throughput2 - 1)*100:>8.1f}%")
    
    print("\n" + "=" * 80)
    print("Benchmark completed!")
    
    if IS_MICROPYTHON and speedup > 1.5:
        print("\n✓ Native optimization is working! Significant speedup detected.")
    elif IS_MICROPYTHON:
        print("\n⚠ Native optimization may not be active. Check modbus_crc._HAS_NATIVE")


if __name__ == "__main__":
    main()
