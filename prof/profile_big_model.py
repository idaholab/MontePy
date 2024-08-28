import cProfile
import montepy
import pstats

stats = cProfile.run(
    'montepy.read_input("benchmark/big_model.imcnp")',
    "prof/big.prof",
    sort=pstats.SortKey.CUMULATIVE,
)

stats = pstats.Stats("prof/big.prof")
stats.sort_stats(pstats.SortKey.CUMULATIVE, pstats.SortKey.TIME).print_stats(
    "montepy", 70
)
stats.sort_stats(pstats.SortKey.CUMULATIVE, pstats.SortKey.TIME).print_stats("sly", 20)
