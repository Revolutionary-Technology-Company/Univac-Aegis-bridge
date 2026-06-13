import socket
import struct
import time
import numpy as np
from numba import njit, prange
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

@njit(parallel=True, fastmath=True)
def generate_fuzzing_matrices(num_samples, fault_injection_rate):
    payloads = np.zeros(num_samples * 4, dtype=np.uint32)
    for i in prange(num_samples):
        base_idx = i * 4
        az = np.uint32(15000 + (i % 100)) 
        el = np.uint32(8000 + (i % 50))
        trig = np.uint32(0) 
        crc = az ^ el ^ trig
        
        if i % fault_injection_rate == 0:
            crc = crc ^ np.uint32(0x0000FFFF)
        elif i % (fault_injection_rate + 1) == 0:
            az = az + np.uint32(10000) 
            
        payloads[base_idx]     = az
        payloads[base_idx + 1] = el
        payloads[base_idx + 2] = trig
        payloads[base_idx + 3] = crc
    return payloads

def packet_blaster_worker(worker_id, ip, port, byte_buffer, num_packets):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576) 
    struct_format = '>4I' 
    start_time = time.time()
    packets_sent = 0
    
    for i in range(num_packets):
        base_idx = i * 4
        data = struct.pack(struct_format, byte_buffer[base_idx], byte_buffer[base_idx+1], 
                           byte_buffer[base_idx+2], byte_buffer[base_idx+3])
        sock.sendto(data, (ip, port))
        packets_sent += 1
        
    duration = time.time() - start_time
    print(f"[Worker {worker_id}] Transmitted {packets_sent:,} packets in {duration:.2f}s")
    sock.close()

if __name__ == '__main__':
    TARGET_IP = "127.0.0.1"
    TARGET_PORT = 5006
    TOTAL_PACKETS = 10_000_000 
    CORRUPTION_RATE = 50_000 
    CORES = multiprocessing.cpu_count()
    
    print(f"[*] Initializing Numba JIT...")
    start_compile = time.time()
    raw_payloads = generate_fuzzing_matrices(TOTAL_PACKETS, CORRUPTION_RATE)
    print(f"[*] 10M Matrices generated via @njit in {time.time() - start_compile:.3f}s")
    
    chunk_size = TOTAL_PACKETS // CORES
    print(f"[*] Spawning {CORES} simultaneous OS network threads...")
    
    with ProcessPoolExecutor(max_workers=CORES) as executor:
        for core in range(CORES):
            start_slice = (core * chunk_size) * 4
            end_slice = start_slice + (chunk_size * 4)
            executor.submit(packet_blaster_worker, core, TARGET_IP, TARGET_PORT, 
                            raw_payloads[start_slice:end_slice], chunk_size)
