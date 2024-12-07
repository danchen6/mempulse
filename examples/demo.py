import os
import sys
import uuid

import mempulse


def allocate_small():
    return [1] * (10 ** 5)

def allocate_large():
    x = [1] * (10 ** 5)
    y = [1] * (10 ** 6)
    z = [1] * (10 ** 7)
    return (x, y, z)

def allocate_uuids():
    result = []
    for _ in range(3 * 10 ** 5):
        value = str(uuid.uuid4())
        result.append(value)
    return result

def allocate_multi_levels():
    leaky_object = [None]
    def level_1():
        data = [x for x in range(10 ** 6)]
        return level_2(data)

    def level_2(data):
        data.extend([x * 2 for x in range(10 ** 5)])
        return level_3(data)

    def level_3(data):
        sliced_data = data[:10 ** 4]
        return level_4(sliced_data)

    def level_4(data):
        additional_data = {i: i**2 for i in range(10**4)}
        return level_5(data, additional_data)

    def level_5(data, additional_data):
        leaky_object[0] = (data, additional_data)
        return leaky_object
    return level_1()

def workload():
    a = allocate_small()
    b = allocate_large()
    del b
    c = allocate_uuids()
    d = allocate_multi_levels()
    return (a, c, d)

def main():
    trace_callback = lambda r: sys.stderr.write(mempulse.format_trace_result(r))
    trace_depth = int(os.getenv('MEMORY_TRACE_DEPTH', '1'))

    with mempulse.MemoryUsageTracer(
        result_callback=trace_callback,
        trace_depth=trace_depth,
    ):
        workload()

if __name__ == '__main__':
    main()
