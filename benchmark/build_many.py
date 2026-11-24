from concurrent import futures
import itertools as it
import model_builder
import numpy as np
from pathlib import Path


def build_model(n_cells, index):
    path = Path("faux_models") / f"fake_model_{n_cells}_{index:03d}.imcnp"
    if path.exists():
        return n_cells, index
    problem = model_builder.create_problem(n_cells)
    problem.write_problem(
        Path("faux_models") / f"fake_model_{n_cells}_{index:03d}.imcnp"
    )
    return n_cells, index


prods = np.array(
    list(it.product(np.geomspace(10, 500_000, 20, dtype="int"), range(30)))
)
with futures.ProcessPoolExecutor() as executor:
    for args in executor.map(build_model, prods[:, 0], prods[:, 1]):
        if args[1] % 10 == 0:
            print(args)
