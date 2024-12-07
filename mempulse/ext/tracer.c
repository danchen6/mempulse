/*
Copyright (c) 2024, Dan Chen

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/
#include <stdio.h>
#include <stdbool.h>
#include <sys/resource.h>

#include <Python.h>
#include <frameobject.h>  // Python 2.7 needs this explicit import


#include "uthash.h"


struct RecordKey {
    PyCodeObject *code;
    int line_num;
};


struct Record {
    struct RecordKey key;
    char const *filename;
    char const *func_name;
    int line_num;
    uint64_t uss_bytes;
    uint64_t swap_bytes;
    uint64_t peak_rss_bytes;
    UT_hash_handle hh;
};


unsigned key_hash(struct RecordKey *k)
{
    return (unsigned)k->code + (unsigned)k->line_num;
}


bool key_equal(struct RecordKey *a, struct RecordKey *b)
{
    return (a->code == b->code) && (a->line_num == b->line_num);
}


#undef HASH_FUNCTION
#undef HASH_KEYCMP
#define HASH_FUNCTION(s, len, hashv) (hashv) = key_hash((struct RecordKey*) s)
#define HASH_KEYCMP(a, b, len) (!key_equal((struct RecordKey*) a, (struct RecordKey*) b))


static int g_trace_enabled = 0;
static int g_trace_depth = 0;
static int g_current_depth = 0;
static struct Record *g_line_records = NULL;


static int read_smaps_rollup(uint64_t *p_uss_bytes, uint64_t *p_swap_bytes)
{
    if (!p_uss_bytes || !p_swap_bytes) {
        return -1;
    }

    FILE *f = fopen("/proc/self/smaps_rollup", "r");
    if (!f) {
        return -2;
    }

    char buf[256];
    uint64_t uss_bytes = 0, swap_bytes = -1;
    while (fgets(buf, sizeof(buf), f)) {
        if (strncmp(buf, "Private_", 8) == 0) {
            uint64_t value = 0;
            if (sscanf(buf, "%*s %lu", &value) == 1) {
                uss_bytes += (value * 1024);
            }
        }
        else if (strncmp(buf, "Swap:", 5) == 0) {
            uint64_t value = 0;
            if (sscanf(buf, "%*s %lu", &value) == 1) {
                swap_bytes = (value * 1024);
            }
        }
    }

    fclose(f);
    *p_uss_bytes = uss_bytes;
    *p_swap_bytes = swap_bytes;
    return (uss_bytes ? 0 : -3);
}

static int get_rusage(uint64_t *p_peak_rss_bytes)
{
    if (!p_peak_rss_bytes) {
        return -1;
    }

    struct rusage usage;
    int ret = getrusage(RUSAGE_SELF, &usage);
    if (ret != 0) {
        return -2;
    }

    *p_peak_rss_bytes = usage.ru_maxrss * 1024;
    return 0;
}



static int trace_func(PyObject *obj, PyFrameObject *frame, int what, PyObject *arg)
{
    switch (what) {
    case PyTrace_CALL:
        g_current_depth += 1;
        if (g_current_depth > g_trace_depth) {
            #if (PY_MAJOR_VERSION >= 3) && (PY_MINOR_VERSION >= 7) && (PY_MINOR_VERSION < 11)
                // disable local tracing for inner scopes deeper than configured depth.
                //
                // however, after Python 3.11 the `f_trace_lines` attribute is not public,
                // and calling PyObject_SetAttrString() seems to be more expansive than disabling local trace
                // ref. https://docs.python.org/3/whatsnew/3.11.html#pyframeobject-3-11-hiding
                //
                // PyObject_SetAttrString((PyObject*) frame, "f_trace_lines", Py_False);
                frame->f_trace = NULL;
                frame->f_trace_lines = 0;
            #endif
        }
        break;
    case PyTrace_RETURN:
        if (g_current_depth > 0) {
            g_current_depth -= 1;
        }
        break;
    case PyTrace_LINE:
        if (g_current_depth <= g_trace_depth) {
            #if PY_MAJOR_VERSION >= 3
                #if PY_MINOR_VERSION >= 9
                    PyCodeObject *code = PyFrame_GetCode(frame);
                #else // Python 3.8 and earlier
                    PyCodeObject *code = frame->f_code;
                #endif
                int const line_num = PyFrame_GetLineNumber(frame);
                char const *filename = PyUnicode_AsUTF8(code->co_filename);
                char const *func_name = PyUnicode_AsUTF8(code->co_name);
            #else // Python 2.7
                PyCodeObject *code = frame->f_code;
                int const line_num = frame->f_lineno;
                char const *filename = PyString_AsString(code->co_filename);
                char const *func_name = PyString_AsString(code->co_name);
            #endif

            struct RecordKey key = {
                .code = code,
                .line_num = line_num,
            };

            struct Record *r = NULL;
            HASH_FIND(hh, g_line_records, &key, sizeof(struct RecordKey), r);
            if (r == NULL) {
                uint64_t uss_bytes = -1, swap_bytes = -1, peak_rss_bytes = -1;
                read_smaps_rollup(&uss_bytes, &swap_bytes);
                get_rusage(&peak_rss_bytes);

                r = malloc(sizeof(struct Record));
                r->key = key;
                r->filename = strdup(filename);
                r->func_name = strdup(func_name);
                r->line_num = line_num;
                r->uss_bytes = uss_bytes;
                r->swap_bytes = swap_bytes;
                r->peak_rss_bytes = peak_rss_bytes;
                HASH_ADD(hh, g_line_records, key, sizeof(struct RecordKey), r);
            }
        }
        break;
    }
    return 0;
}


static PyObject* start_trace(PyObject *self, PyObject *args)
{
    int trace_depth;
    if (!PyArg_ParseTuple(args, "i", &trace_depth)) {
        return NULL;
    }

    if (g_trace_enabled > 0) {
        PyErr_SetString(PyExc_RuntimeError, "Cannot start trace when a trace is already running");
        return NULL;
    }

    g_trace_depth = trace_depth;
    g_current_depth = 0;

    PyGILState_STATE gstate = PyGILState_Ensure();
    PyEval_SetTrace(trace_func, NULL);
    PyGILState_Release(gstate);
    g_trace_enabled = 1;

    Py_RETURN_NONE;
}


static PyObject* stop_trace()
{
    if (g_trace_enabled < 1) {
        PyErr_SetString(PyExc_RuntimeError, "Cannot stop trace when a trace is not running");
        return NULL;
    }

    PyGILState_STATE gstate = PyGILState_Ensure();
    PyEval_SetTrace(NULL, NULL);
    PyGILState_Release(gstate);
    g_trace_enabled = 0;

    // TODO: better error handling
    PyObject *records = PyList_New(0);
    struct Record *r, *tmp;
    HASH_ITER(hh, g_line_records, r, tmp) {
        // tuple: (filename, line_num, func_name, uss_bytes, swap_bytes, peak_rss_bytes)
        PyObject *filename = PyUnicode_FromString(r->filename);
        PyObject *line_num = PyLong_FromLong(r->line_num);
        PyObject *func_name = PyUnicode_FromString(r->func_name);
        PyObject *uss_bytes = PyLong_FromUnsignedLongLong(r->uss_bytes);
        PyObject *swap_bytes = PyLong_FromUnsignedLongLong(r->swap_bytes);
        PyObject *peak_rss_bytes = PyLong_FromUnsignedLongLong(r->peak_rss_bytes);

        PyObject *tuple = PyTuple_Pack(6, filename, line_num, func_name, uss_bytes, swap_bytes, peak_rss_bytes);
        Py_DECREF(filename);  // transfer ownership to the tuple
        Py_DECREF(line_num);  // transfer ownership to the tuple
        Py_DECREF(func_name);  // transfer ownership to the tuple
        Py_DECREF(uss_bytes);  // transfer ownership to the tuple
        Py_DECREF(swap_bytes);  // transfer ownership to the tuple
        Py_DECREF(peak_rss_bytes);  // transfer ownership to the tuple

        PyList_Append(records, tuple);
        Py_DECREF(tuple);  // transfer ownership to the list

        HASH_DEL(g_line_records, r);
        free((void*) r->filename);
        free((void*) r->func_name);
        free(r);
    }
    g_line_records = NULL;
    return records;
}


static PyObject* check_support()
{
    uint64_t uss_bytes, swap_bytes;
    int ret = read_smaps_rollup(&uss_bytes, &swap_bytes);
    if (ret < 0) {
        Py_RETURN_FALSE;
    }
    Py_RETURN_TRUE;
}


static PyMethodDef module_methods[] = {
    {
        "start_trace", (PyCFunction) start_trace, METH_VARARGS,
        "Start tracing"
    },
    {
        "stop_trace", (PyCFunction) stop_trace, METH_NOARGS,
        "Stop tracing"
    },
    {
        "check_support", (PyCFunction) check_support, METH_NOARGS,
        "Check whether current environment is supported"
    },
    {
        NULL
    },
};


#if PY_MAJOR_VERSION >= 3

    static struct PyModuleDef module = {
        PyModuleDef_HEAD_INIT,
        .m_name = "tracer",
        .m_doc = "Extension for mempulse memory usage tracer",
        .m_size = -1,
        .m_methods = module_methods,
    };

    PyMODINIT_FUNC PyInit_tracer()
    {
        return PyModule_Create(&module);
    }

#else // Python 2

    PyMODINIT_FUNC inittracer()
    {
        Py_InitModule3(
            "tracer",
            module_methods,
            "Extension for mempulse memory usage tracer"
        );
    }

#endif