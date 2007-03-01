
""" Nose unit tests """

__docformat__ = "restructuredtext"


def test_parse_pkg_ver():
    """Parse package version string"""
    assert "==" in "foo==1.0"
    assert "==" not in "foo"


