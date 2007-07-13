#!/usr/bin/python


from setuptools import setup

from yolk.__init__ import __version__ as VERSION



setup(name="yolk",
    license = "GPL-2",
    version=VERSION,
    description="Command-line tool for listing packages installed by setuptools, their metadata and dependencies and PyPI querying.",
    long_description=open("README", "r").read(),
    maintainer="Rob Cakebread",
    author="Rob Cakebread",
    author_email="gentoodev@gmail.com",
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

