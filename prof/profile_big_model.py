import cProfile
import montepy
import pstats

prof = cProfile.Profile()
prof.enable()

montepy.read_input("benchmark/big_model.imcnp")

stats = prof.create_stats()
stats.sort_stats(SortKey.CUMULATIVE, SortKey.TIME).print_stats(300, "montepy")
stats.sort_stats(SortKey.CUMULATIVE, SortKey.TIME).print_stats(100, "sly")
