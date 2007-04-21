#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""

setuptools_support
==================

License  : GNU General Public License Version 2

"""


from setuptools.package_index import PackageIndex
import pkg_resources

from yolk.pypi import filter_url


__docformat__ = 'restructuredtext'


class DownloadURI(Exception):

    """Hack to raise the value of the URI from PackageIndex"""

    def __init__(self, value):
        """init"""
        self.value = value

    def __str__(self):
        """Set value to URI"""
        return repr(self.value)

class MyPackageIndex(PackageIndex):

    """Over-ride methods so we can obtain the package's URI"""

    def _download_to(self, url, filename):
        """Raise exception so we immediately get url with no downloading"""
        raise DownloadURI(url)

    def download(self, spec, tmpdir="/tmp/spambar"):
        """Raise exception so we immediately get url with no downloading"""
        raise DownloadURI(spec)


def get_download_uri(file_type, package_name, version=None):
    """Use setuptools to search for a package's URI"""
    if version:
        pkg_spec = "%s==%s" % (package_name, version)
    else:
        pkg_spec = package_name
    req = pkg_resources.Requirement.parse(pkg_spec)
    pkg_index = MyPackageIndex()
    try:
        pkg_index.fetch_distribution(req, None)
    except DownloadURI, url:
        return filter_url(file_type, url.value)

