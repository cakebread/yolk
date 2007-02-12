#!/usr/bin/python

from setuptools import setup, find_packages

from lib import __version__


setup(name="yolk",
    license = "PSF",
    version=__version__.VERSION,
    description="Library and command-line tool for listing installed packages, their metadata and dependencies and PyPI querying.",
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
    packages=['yolk'],
    package_dir={'yolk':'lib'},
    entry_points={'console_scripts': ['yolk = yolk.cli:main',]},
)

