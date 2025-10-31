import gc

import time
import tracemalloc

tracemalloc.start()

import montepy

FAIL_THRESHOLD = 90
MEMORY_FRACTION = 0.50

starting_mem = tracemalloc.get_traced_memory()[0]
print(f"starting memory with montepy. {starting_mem/1024/1024} MB")
start = time.time()

problem = montepy.read_input("benchmark/big_model.imcnp")

stop = time.time()

problem_mem = tracemalloc.get_traced_memory()[0]
print(f"Took {stop - start} seconds")
print(f"Memory usage report: {problem_mem/1024/1024} MB")
del problem
gc.collect()
ending_mem = tracemalloc.get_traced_memory()[0]
print(f"Memory usage report after GC: {ending_mem/1024/1024} MB")

if (stop - start) > FAIL_THRESHOLD:
    raise RuntimeError(
        f"Benchmark took too long to complete. It must be faster than: {FAIL_THRESHOLD} s."
    )

prob_gc_mem = problem_mem - ending_mem
prob_actual_mem = problem_mem - starting_mem
gc_ratio = prob_gc_mem / prob_actual_mem
print(f"{gc_ratio:.2%} of the problem's memory was garbage collected.")
if (prob_gc_mem / prob_actual_mem) < MEMORY_FRACTION:
    raise RuntimeError(
        f"Benchmark had too many memory leaks. Only {gc_ratio:.2%} of the memory was collected."
    )
