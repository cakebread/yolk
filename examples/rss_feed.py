#!/usr/bin/python

import urllib
import os

from cElementTree import iterparse

import sys

try:
    from yolklib.pypi import CheeseShop
except:
    sys.path.insert(0, os.getcwd())
    from yolklib.pypi import CheeseShop


PYPI_URL = 'http://www.python.org/pypi?:action=rss'


def get_pkg_ver(pv, add_quotes=True):
    """Return package name and version"""
    n = len(pv.split())
    if n == 2:
        #Normal package_name 1.0
        pkg_name, ver = pv.split()
    else:
        parts = pv.split()
        ver = parts[-1:]
        if add_quotes:
            pkg_name = "'%s'" % " ".join(parts[:-1])
        else:
            pkg_name = "%s" % " ".join(parts[:-1])
    return pkg_name, ver

def test_api(pypi_xml):
    failed = 0
    failed_msgs =[]
    for event, elem in iterparse(pypi_xml):
        if elem.tag == "title":
            if not elem.text.startswith('Cheese Shop recent updates'):
                pkg_name, ver = get_pkg_ver(elem.text, False)
                (pypi_pkg_name, versions) = PyPI.query_versions_pypi(pkg_name, True)
                try:
                    assert versions[0] == ver
                    print "Testing %s... passed" % elem.text
                except:
                    failed += 1
                    failed_msgs.append("%s %s" % (pkg_name, versions))
                    print "Testing %s... failed" % elem.text

    print "%s tests failed." % failed
    for msg in failed_msgs:
        print "\t%s" % msg

def test_cli(pypi_xml):
    #Fetch master list of package names so we can use cache
    os.system('./yolk.py -F')
    for event, elem in iterparse(pypi_xml):
        if elem.tag == "title":
            if not elem.text.startswith('Cheese Shop recent updates'):
                print "Testing %s..." % elem.text
                pkg_name, ver = get_pkg_ver(elem.text)
                os.system('./yolk.py -V %s' % pkg_name)
                os.system('./yolk.py -C -D %s %s' % (pkg_name, ver))
            elem.clear()

test_cli(urllib.urlopen(PYPI_URL))
PyPI = CheeseShop()
test_api(urllib.urlopen(PYPI_URL))
