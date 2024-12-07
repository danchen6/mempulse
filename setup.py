import os
import sys

from setuptools import setup, Extension


readme_md_content = None
with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
    readme_md_content = f.read()

extensions = []
if sys.platform.startswith('linux'):
    extensions.append(Extension(
        name='mempulse.ext.tracer',
        sources=['mempulse/ext/tracer.c'],
        include_dirs=['/mempulse/ext'],
        extra_compile_args=['-Wno-pointer-to-int-cast'],
    ))

setup(
    name="mempulse",
    version="0.6.4",
    description="Tiny yet effective Python memory profiler/tracer",
    author="Dan Chen",
    author_email="danchen666666@gmail.com",
    url='https://github.com/danchen6/mempulse',
    long_description=readme_md_content,
    long_description_content_type="text/markdown",
    license='3-Clause BSD License',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: C',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development',
        'Topic :: Software Development :: Debuggers',
        'Topic :: Utilities',
    ],
    packages=['mempulse', 'mempulse.ext'],
    ext_modules=extensions,
    install_requires=[],
    extras_require={
        'psutil': [
            'psutil==6.1.0',
        ],
    }
)
