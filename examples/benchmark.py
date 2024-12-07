import argparse
import gc
import sys
import time

import numpy as np

from demo import (
    allocate_small,
    allocate_large,
    allocate_uuids,
    allocate_multi_levels,
)

def numpy_cpu_bound():
    for _ in range(10 ** 3):
        a = np.random.rand(10 ** 4)
        b = np.random.rand(10 ** 4)
        c = a * b
        s = np.sum(c)
        m = np.mean(c)

def numpy_large_data():
    data = np.random.rand(10**7, 10)
    result = data.mean(axis=0)
    return result

def workload():
    t0 = time.time()
    _ = allocate_small()
    _ = allocate_large()
    t = allocate_uuids()
    del t
    _ = numpy_cpu_bound()
    _ = numpy_large_data()
    gc.collect()
    _ = allocate_multi_levels()
    t1 = time.time()
    print('Elapsed: {:.2f} seconds'.format(t1 - t0))

# ------------------------------------------------------------------------------

def run_mempulse():
    import mempulse  # pip install mempulse[psutil]
    callback = lambda r: sys.stderr.write(mempulse.format_trace_result(r))
    with mempulse.MemoryUsageTracer(callback, 1):
        workload()

def run_mempulse_c():
    import mempulse  # pip install mempulse
    callback = lambda r: sys.stderr.write(mempulse.format_trace_result(r))
    with mempulse.cMemoryUsageTracer(callback, 1):
        workload()

def run_tracemalloc():
    import tracemalloc  # built-in for Python >= 3.4
    tracemalloc.start()
    workload()
    snapshot = tracemalloc.take_snapshot()
    for stat in snapshot.statistics('lineno')[:10]:
        print(stat)

def run_memory_profiler():
    import memory_profiler  # pip install memory_profiler
    memory_profiler.profile(workload)()

def main():
    parser = argparse.ArgumentParser(description='Benchmark memory tracer')
    parser.add_argument('--tracer', choices=['mempulse', 'mempulse_c', 'tracemalloc', 'memory_profiler'])
    args = parser.parse_args()

    print('Running with "{}"'.format(args.tracer))
    {
        'mempulse': run_mempulse,
        'mempulse_c': run_mempulse_c,
        'tracemalloc': run_tracemalloc,
        'memory_profiler': run_memory_profiler,
    }.get(args.tracer, workload)()


if __name__ == '__main__':
    main()
