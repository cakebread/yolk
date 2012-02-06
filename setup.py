#!/usr/bin/python


from setuptools import setup

from yolk.__init__ import __version__ as VERSION



setup(name="yolk",
    license = "BSD License",
    version=VERSION,
    description="Command-line tool for querying PyPI and Python packages installed on your system.",
    long_description=open("README", "r").read(),
    maintainer="Rob Cakebread",
    author="Rob Cakebread",
    author_email="cakebread @ gmail",
    url="https://github.com/cakebread/yolk",
    keywords="PyPI setuptools cheeseshop distutils eggs package management",
    classifiers=["Development Status :: 4 - Beta",
                 "Intended Audience :: Developers",
                 "License :: OSI Approved :: BSD License",
                 "Programming Language :: Python",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 ],
    install_requires=["setuptools"],
    tests_require=["nose"],
    packages=['yolk', 'yolk.plugins'],
    package_dir={'yolk':'yolk'},
    entry_points={'console_scripts': ['yolk = yolk.cli:main',]},
    test_suite = 'nose.collector',
)

