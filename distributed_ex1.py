import numpy as np
import numba as cuda
import time

def add_cpu(a, b, c):
    start_time = time.time()
    for i in range(N):
        for j in range(N):
            c[i][j] = a[i][j] + b[i][j]
    end_time = time.time()
    execution_time = end_time - start_time
    return c, execution_time

@cuda.jit
def add_gpu(a, b):
    start_time = time.time()
    # Allocate memory on GPU
    d_a = cuda.to_device(a)
    d_b = cuda.to_device(b)
    d_c = cuda.device_array_like(a)

    # Configure 2D grid and block dimensions
    threadsperblock = (16, 16)
    blockspergrid_x = (a.shape[0] + threadsperblock[0] - 1) // threadsperblock[0]
    blockspergrid_y = (a.shape[1] + threadsperblock[1] - 1) // threadsperblock[1]
    blockspergrid = (blockspergrid_x, blockspergrid_y)

    # Call the kernel
    add_kernal[blockspergrid, threadsperblock](d_a, d_b, d_c)

    # Copy the result back to host
    c = d_c.copy_to_host()
    end_time = time.time()
    execution_time = end_time - start_time
    return c, execution_time


def add_kernal(a, b, c):
    row, col = cuda.grid(2)
    if row < c.shape[0] and col < c.shape[1]:
        c[row][col] = a[row][col] + b[row][col]



if __name__ == "__main__":
    N = 1000

    a = np.random.rand(N,N) # Create a random array of size N
    b = np.random.rand(N,N) # Create a random array of size N
    c = np.zeros((N,N)) # Create an array of zeros of size N

    # a[i][j] + b[i][j] = c[i][j] for all i,j in N

    print("Starting CPU computation")
    #Perform CPU computation
    cpu_result, cpu_execution = add_cpu(a, b, c)
    print("CPU Execution Time: ", cpu_execution, " seconds")

    print("Starting GPU computation")
    #Perform GPU computation
    gpu_result, gpu_execution = add_gpu(a, b)
    print("GPU Execution Time: ", gpu_execution, " seconds")

    print("Sometimes GPU is longer cause of the copy to and from the device.")
