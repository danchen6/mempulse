mempulse
========

Tiny yet effective Python memory profiler/tracer.  With minimized overhead with the C extension, `mempulse` gives you a holistic view of what's eating memory in your Python applications, on development and on production environments.

This package supports both `Python 2.7` and `Python >= 3.3` (tested with `Python 3.13`).


Install
-------

Install from [PyPI](https://pypi.org/project/mempulse/):
```
# Python-based `mempulse.MemoryUsageTracer` (depends on `psutil`, for Linux, macOS, Windows)
pip install mempulse[psutil]

# C-based `mempulse.cMemoryUsageTracer` (Linux only)
pip install mempulse
```

Install from source:
```
pip install setuptools
pip install .[psutil]
```


How to Use
----------

Choose appropriate "tracing depth" (which slightly affects the overhead) then wrap the function you'd like to profile with a `with` statement:
```python
import os
import sys
import mempulse

def application():
    callback = lambda r: sys.stderr.write(mempulse.format_trace_result(r))
    trace_depth = int(os.getenv('MEMORY_TRACE_DEPTH', '1')) # `0` disables tracing
    with mempulse.cMemoryUsageTracer(callback, trace_depth):
        the_workload()
```

Leavning the `with` scope will summarize line-by-line memory stats like belw:
```
Callsite         Method Name               USS   Swap       Peak RSS
--------------------------------------------------------------------
benchmark.py:53  run_mempulse_c     26,525,696      0     28,057,600
benchmark.py:29  workload           26,525,696      0     28,057,600
benchmark.py:30  workload           26,525,696      0     28,057,600
benchmark.py:31  workload           27,328,512      0     28,860,416
benchmark.py:32  workload          115,335,168      0    117,530,624
benchmark.py:33  workload          147,431,424      0    148,926,464
benchmark.py:34  workload          117,096,448      0    148,926,464
benchmark.py:35  workload           34,779,136      0    148,926,464
benchmark.py:36  workload           34,779,136      0    836,354,048
benchmark.py:37  workload           34,779,136      0    836,354,048
benchmark.py:38  workload           44,900,352      0    836,354,048
benchmark.py:39  workload           44,900,352      0    836,354,048
benchmark.py:52  run_mempulse_c     44,900,352      0    836,354,048
```


Benchmark
---------

Running benchmark program `examples/benchmark.py` with Python 3.11 on macOS (with 8-core Intel Core i9 @ 3.6GHz) here showcases that `mempulse` outperforms similar tools such as [`memory_profiler`](https://pypi.org/project/memory-profiler/), and [`tracemalloc`](https://docs.python.org/3/library/tracemalloc.html), in terms of overhead:

| Tracer                        | Execution Time in Average | Overhead |
|-------------------------------|---------------------------|----------|
| - (without tracer)            |                     2.26s |        - |
| `mempulse.cMemoryUsageTracer` |                     3.40s |   50.44% |
| `mempulse.MemoryUsageTracer`  |                     3.62s |   60.18% |
| `memory_profiler`             |                     8.31s |  268.58% |
| `tracemalloc`                 |                    11.02s |  387.61% |


Limitations
-----------

* Interoperability: `mempulse` sets trace function though `sys.settrace()` (or `PyEval_SetStrace()`), therefore it cannot be used with other tracers (such as [Coverage.py](https://github.com/nedbat/coveragepy)) at the same time.
* Concurrency: `mempulse` traces current thread only.  Functions run with other threads will not show in line-by-line trace records.


License
-------
* This `mempulse` software is released under [3-Clause BSD License](https://opensource.org/license/bsd-3-clause).
* The file `mempulse/ext/uthash.h` comes from [uthash](https://troydhanson.github.io/uthash/) which is under [BSD revised](https://troydhanson.github.io/uthash/license.html) license.
