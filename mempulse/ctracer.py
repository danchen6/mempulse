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

from .ext import tracer


_g_trace_enabled = None

class cMemoryUsageTracer():
    def __init__(self, result_callback, trace_depth=1):
        # TODO: validate arguments
        self.result_callback = result_callback
        self.trace_depth = trace_depth

        self.original_trace_func = None

    def __enter__(self):
        global _g_trace_enabled
        if not sys.platform.startswith('linux'):
            raise RuntimeError('cMemoryUsageTracer is only available on Linux')

        if not tracer.check_support():
            warnings.warn('Cannot start trace because required memory information is not available')
            return

        if self.trace_depth < 1:
            return

        self.original_trace_func = sys.gettrace()
        tracer.start_trace(self.trace_depth)
        _g_trace_enabled = True

    def __exit__(self, exc_type, exc_value, traceback):  # pylint: disable=unused-argument
        global _g_trace_enabled
        if not _g_trace_enabled:
            return

        result = tracer.stop_trace()
        sys.settrace(self.original_trace_func)
        _g_trace_enabled = False
        self.result_callback(result)
