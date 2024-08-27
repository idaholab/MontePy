import montepy

import timeit
import tracemalloc

tracemalloc.start()
start = timeit.timeit()

problem = montepy.read_input("benchmark/big_model.imcnp")

stop = timeit.timeit()

print(f"Took {stop - start} seconds")
print(f"Memory usage report: {tracemalloc.get_traced_memory()}")
