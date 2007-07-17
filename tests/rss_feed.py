#!/usr/bin/env python

"""
Some basic tests of the command-line and API using the PyPI RSS feed of recent
updates.

Known issues: Package names with spaces will show as a fail.

"""

__docformat__ = 'restructuredtext'

import urllib
import os
import sys


if sys.version_info[0] == 2 and sys.version_info[1] == 5:
    #Python >=2.5 has elementtree 
    from xml.etree.cElementTree import iterparse
else:
    try:
        #Python <2.5 has elementtree as 3rd party module
        from cElementTree import iterparse
    except ImportError:
        print "You need to install cElementTree"
        sys.exit(2)




from yolk.pypi import CheeseShop

PYPI_URL = 'http://www.python.org/pypi?:action=rss'


def get_pkg_ver(pv, add_quotes=True):
    """Return package name and version"""
    #XXX Fix package names with spaces bug.
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
    """Basic API tests"""
    print "Testing API"""
    skipped = 0
    skipped_msgs = []
    failed = 0
    failed_msgs = []
    for event, elem in iterparse(pypi_xml):
        if elem.tag == "title":
            if not elem.text.startswith('Cheese Shop recent updates'):
                pkg_name, ver = get_pkg_ver(elem.text, False)
                (pypi_pkg_name, versions) = PyPI.query_versions_pypi(pkg_name)
                if " " in pypi_pkg_name:
                    skipped +=1
                    failed_msgs.append("%s %s" \
                            % (pkg_name, "- space in project name"))
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
    print "%s tests skipped." % skipped
    for msg in skipped_msgs:
        print "\t%s" % msg

def test_cli(pypi_xml):
    """Test the command-line tool"""
    print "Testing CLI"
    for event, elem in iterparse(pypi_xml):
        if elem.tag == "title":
            if not elem.text.startswith('Cheese Shop recent updates'):
                print "Testing %s..." % elem.text
                pkg_name, ver = get_pkg_ver(elem.text)
                if " " in pkg_name:
                    print "Space in package name, skipping: %s" % pkg_name
                else:
                    os.system("yolk -V '%s'" % pkg_name)
                    os.system("yolk -D %s==%s" % (pkg_name, ver))
            elem.clear()

test_cli(urllib.urlopen(PYPI_URL))
PyPI = CheeseShop()
test_api(urllib.urlopen(PYPI_URL))
