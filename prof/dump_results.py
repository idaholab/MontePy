import pstats
from pstats import SortKey

stats = pstats.Stats("prof/combined.prof")
stats.sort_stats(SortKey.CUMULATIVE, SortKey.TIME).print_stats("montepy", 50)
stats.sort_stats(SortKey.CUMULATIVE, SortKey.TIME).print_stats("sly", 20)
