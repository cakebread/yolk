#!/usr/bin/env python

from setuptools import setup


setup(name="yolk-acme",
    license="GPL-2",
    version="0.1",
    description="Plugin to show which Python packages were installed via the Acme Package Manger.",
    maintainer="Josefina Blo",
    author="Josefina Blo",
    author_email="josefina@josefinasdomain.com",
    url="http://tools.assembla.com/josplugin",
    keywords="PyPI setuptools cheeseshop distutils eggs package management",
    classifiers=["Development Status :: 2 - Pre-Alpha",
                 "Intended Audience :: Developers",
                 "Programming Language :: Python",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 ],
    py_modules = ['yolk_acme'],
    entry_points = {
        'yolk.plugins': [
        'acmeplugin = yolk_acme:PackageManagerPlugin'
        ]
    },
)

