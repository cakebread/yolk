#!/usr/bin/env python

from setuptools import setup



setup(name="yolk-portage",
    license="GPL-2",
    version="0.1",
    description="Plugin to show which Python packages were installed via Gentoo's Portage system.",
    long_description=open("README", "r").read(),
    maintainer="Rob Cakebread",
    author="Rob Cakebread",
    author_email="gentoodev a t gmail . com",
    url="http://tools.assembla.com/yolk/",
    keywords="Gentoo portage PyPI setuptools cheeseshop distutils eggs package management",
    classifiers=["Development Status :: 2 - Pre-Alpha",
                 "Intended Audience :: Developers",
                 "Programming Language :: Python",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 ],
    py_modules = ['yolk_portage'],
    entry_points = {
        'yolk.plugins': [
        'gentooplugin = yolk_portage:PackageManagerPlugin'
        ]
    },
    test_suite = 'nose.collector',
)

