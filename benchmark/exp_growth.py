import numpy as np
import io
from model_builder import create_problem
import cProfile
import pstats
from pstats import SortKey

def dump_stats(n_cells):
    pr = cProfile.Profile()
    pr.enable()
    create_problem(n_cells)
    pr.disable()
    pr.dump_stats("foo.prof")
    stats = pstats.Stats("foo.prof")
    stats.print_stats("append_renumber", 20)


def collect_samples():
    grid = np.geomspace(10, 10_000, 4)
    for n_cells in grid:
        n_cells = int(n_cells)
        print(f"****************** {n_cells} ***************")
        dump_stats(n_cells)

collect_samples()
