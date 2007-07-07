#!/usr/bin/python


from setuptools import setup

from yolk import __version__


#ElementTree does not use setuptools in its setup.py. Because virtually every
#distro except Windows has an elementree package available already in their
#package system, we see if its installed and if so, don't add it to 
#install_requires, avoiding double-installation because setuptools can't find
#a version of it installed by distutils.


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
    install_requires=["setuptools"],
    extras_require={'RSS': ["cElementTree"],},
    tests_require=["nose"],
    packages=['yolk', 'yolk.plugins'],
    package_dir={'yolk':'yolk'},
    entry_points={'console_scripts': ['yolk = yolk.cli:main',]},
    test_suite = 'nose.collector',
)

