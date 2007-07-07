

""" yolk.cli.py Nose unit tests """

from yolk.cli import *

__docformat__ = "restructuredtext"


def test_parse_pkg_ver():
    """Parse package version string"""
    assert parse_pkg_ver("zxxvzx==1.0", True) == (None, "1.0")
    assert parse_pkg_ver("zxxvzx==1.0", False) == ("zxxvzx", "1.0")

