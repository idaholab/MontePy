import gc
import montepy

import time
import tracemalloc

FAIL_THRESHOLD = 30

tracemalloc.start()
start = time.time()

problem = montepy.read_input("benchmark/big_model.imcnp")

stop = time.time()

print(f"Took {stop - start} seconds")
print(f"Memory usage report: {tracemalloc.get_traced_memory()[0]/1024/1024} MB")
del problem
gc.collect()
print(f"Memory usage report after GC: {tracemalloc.get_traced_memory()[0]/1024/1024} MB")

if (stop - start) > FAIL_THRESHOLD:
    raise RuntimeError(
        f"Benchmark took too long to complete. It must be faster than: {FAIL_THRESHOLD} s."
    )
