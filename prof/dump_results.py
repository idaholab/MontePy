import pstats
from pstats import SortKey

stats = pstats.Stats("prof/combined.prof")
stats.sort_stats(SortKey.CUMULATIVE, SortKey.TIME).print_stats(300, "montepy/montepy")
stats.sort_stats(SortKey.CUMULATIVE, SortKey.TIME).print_stats(100, "sly")
