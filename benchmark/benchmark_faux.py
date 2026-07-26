import montepy
import pandas as pd
from pathlib import Path
import os
import timeit

data = []

for path in Path("faux_models").glob("*.imcnp"):
    buffer = {"path": path, "size": os.path.getsize(path)}
    time = timeit.timeit(f"montepy.read_input('{path}')", number=1, globals=globals())
    buffer["time"] = time
    buffer["rate"] = buffer["size"] / time
    data.append(buffer)

data = pd.DataFrame(data)
data.to_pickle(f"fake_benchmark_{montepy.__version__}.pkl")
data.to_excel("faux_benchmark_{montepy.__version__}.xlsx")


