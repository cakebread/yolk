#!/usr/bin/python

import sys

from setuptools import setup

from yolk import __version__


#ElementTree does not use setuptools in its setup.py. Because virtually every
#distro except Windows has an elementree package available already in their
#package system, we see if its installed and if so, don't add it to 
#install_requires, avoiding double-installation because setuptools can't find
#a version of it installed by distutils.


install_requires=["setuptools"]

#Python >=2.5 has elementtree 
if sys.version_info[0] == 2 and sys.version_info[1] == 5:
    #cElementTree is in stdlib, safe to add to install_requires
    install_requires.append("cElementTree")
else:
    #For Python <=2.4
    try:
        from elementtree.ElementTree import parse
    except ImportError:
        install_requires.append("cElementTree")

setup(name="yolk",
    license = "GPL-2",
    version=__version__.VERSION,
    description="Library and command-line tool for listing packages installed by setuptools, their metadata and dependencies and PyPI querying.",
    long_description=open("README", "r").read(),
    maintainer="Rob Cakebread",
    author="Rob Cakebread",
    author_email="gentoodev a t gmail . com",
    url="http://tools.assembla.com/yolk/",
    keywords="PyPI setuptools cheeseshop distutils eggs package management",
    classifiers=["Development Status :: 3 - Alpha",
                 "Intended Audience :: Developers",
                 "License :: OSI Approved :: GNU General Public License (GPL)",
                 "Programming Language :: Python",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 ],
    install_requires=install_requires,
    tests_require=["nose"],
    packages=['yolk', 'yolk.plugins'],
    package_dir={'yolk':'yolk'},
    entry_points={'console_scripts': ['yolk = yolk.cli:main',]},
    test_suite = 'nose.collector',
)

