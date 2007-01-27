#!/usr/bin/python

from setuptools import setup

from yolklib import __version__

setup(name="yolk",
    license = "PSF",
    version=__version__.version,
    description="Library and CLI tool for listing installed eggs, their metadata and dependencies and PYPI querying.",
    long_description="Command-line tool and library for information about Python packages installed by setuptools, and querying of The Cheese Shop (Python Package Index).",
    maintainer="Rob Cakebread",
    author="Rob Cakebread",
    author_email="gentoodev a t gmail . com",
    url="http://tools.assembla.com/yolk/",
    keywords="PyPI setuptools cheeseshop distutils eggs package management",
    classifiers=["Development Status :: 2 - Pre-Alpha",
                 "Intended Audience :: Developers",
                 "License :: OSI Approved :: Python Software Foundation License",
                 "Programming Language :: Python",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 ],
    py_modules=["yolklib/pypi", "yolklib/metadata", "yolklib/yolklib", "yolklib/__init__", "yolklib/__version__"],
    packages=['yolklib',],
    package_dir={'yolklib':''},
    scripts=['yolk.py',],
)

