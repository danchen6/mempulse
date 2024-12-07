'''
Copyright (c) 2024, Dan Chen

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
import warnings
import sys
from collections import OrderedDict

try:
    import psutil
except ImportError:
    psutil = None

try:
    import resource
    get_peak_rss_via_resource_pkg = (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 0)
except (ImportError, OSError):
    get_peak_rss_via_resource_pkg = False


_g_trace_enabled = False


class MemoryUsageTracer(object):
    def __init__(self, result_callback, trace_depth=1):
        # TODO: validate arguments
        self.result_callback = result_callback
        self.trace_depth = trace_depth

        self.current_depth = 0
        self.line_records = OrderedDict()  # (id(f_code), line_num) -> (filename, func_name, uss_bytes, swap_bytes, peak_rss_bytes)
        self.original_trace_func = None
        self.psutil_proc = None

    def _collect_memory_usage(self):
        self.psutil_proc = self.psutil_proc or psutil.Process()
        mem_info = self.psutil_proc.memory_full_info()
        uss_bytes = getattr(mem_info, 'uss', -1)
        swap_bytes = getattr(mem_info, 'swap', -1)
        peak_rss_bytes = -1
        try:
            if get_peak_rss_via_resource_pkg:
                # on macOS `ru_maxrss` comes in bytes, while on Linux it comes in KiB
                k = 1024 if sys.platform != 'darwin' else 1
                peak_rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * k
            else:
                peak_rss_bytes = getattr(mem_info, 'peak_wset', -1)  # Windows-only
        except Exception:
            pass
        return (uss_bytes, swap_bytes, peak_rss_bytes)

    def __enter__(self):
        global _g_trace_enabled
        if _g_trace_enabled:
            raise RuntimeError('Cannot start trace when a trace is already running')

        if psutil is None:
            warnings.warn('\n'.join([
                'Package `psutil` is required by mempulse.MemoryUsageTracer.',
                'Install with `pip install mempulse[psutil]`, or switch to mempulse.cMemoryUsageTracer if you are on Linux.'
            ]))
            return

        is_memory_info_available = (self._collect_memory_usage()[0] > 0)
        if not is_memory_info_available:
            warnings.warn('Cannot start trace because required memory information is not available')
            return

        if self.trace_depth < 1:
            return

        self.current_depth = 0
        self.original_trace_func = sys.gettrace()
        sys.settrace(self.trace_func)
        _g_trace_enabled = True

    def __exit__(self, exc_type, exc_value, traceback):  # pylint: disable=unused-argument
        global _g_trace_enabled
        if not _g_trace_enabled:
            return

        sys.settrace(self.original_trace_func)
        self.original_trace_func = None
        _g_trace_enabled = False
        self.result_callback(self.line_records.values())

    def trace_func(self, frame, event, arg):  # pylint: disable=unused-argument
        if event == 'call':
            if self.current_depth < self.trace_depth:
                self.current_depth += 1
                return self.trace_func
            return

        if event == 'return':
            self.current_depth -= 1
            return

        if event == 'line':
            f_code = frame.f_code
            line_num = frame.f_lineno
            key = (id(f_code), line_num)
            if key not in self.line_records:
                filename = f_code.co_filename
                func_name = f_code.co_name
                uss_bytes, swap_bytes, peak_rss_bytes = self._collect_memory_usage()
                value = (filename, line_num, func_name, uss_bytes, swap_bytes, peak_rss_bytes)
                self.line_records[key] = value
