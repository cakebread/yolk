#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable-msg=W0231,R0904


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
    if not file_type:
        #Give them source by default
        dist_type = [True]
    elif file_type == "source":
        dist_type = [True]
    elif file_type == "binary":
        dist_type = [False]
    elif file_type == "all":
        #Binary and source
        dist_type = [True, False]

    if version:
        pkg_spec = "%s==%s" % (package_name, version)
    else:
        pkg_spec = package_name
    req = pkg_resources.Requirement.parse(pkg_spec)
    pkg_index = MyPackageIndex()
    output = []
    for dist in dist_type:
        try:
            pkg_index.fetch_distribution(req, None, True, dist)
        except DownloadURI, url:
            output.append(filter_url(file_type, url.value))
    return output
