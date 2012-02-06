#!/usr/bin/env python
# pylint: disable-msg=W0231,R0904


"""

setuptools_support
==================

License  : BSD (See COPYING)

"""


from yolk.yolklib import Distributions

from setuptools.package_index import PackageIndex
import pkg_resources


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


def get_download_uri(package_name, version, source, index_url=None):

    """
    Use setuptools to search for a package's URI

    @returns: URI string
    """
    tmpdir = None
    force_scan = True
    develop_ok = False
    if not index_url:
        index_url = 'http://cheeseshop.python.org/pypi'

    if version:
        pkg_spec = "%s==%s" % (package_name, version)
    else:
        pkg_spec = package_name
    req = pkg_resources.Requirement.parse(pkg_spec)
    pkg_index = MyPackageIndex(index_url)
    try:
        pkg_index.fetch_distribution(req, tmpdir, force_scan, source,
                develop_ok)
    except DownloadURI, url:
        #Remove #egg=pkg-dev
        clean_url = url.value.split("#")[0]
        #If setuptools is asked for an egg and there isn't one, it will
        #return source if available, which we don't want.
        if not source and not clean_url.endswith(".egg") and \
                not clean_url.endswith(".EGG"):
            return
        else:
            return clean_url

def get_pkglist():
    """
    Return list of all installed packages

    Note: It returns one project name per pkg no matter how many versions
    of a particular package is installed

    @returns: list of project name strings for every installed pkg

    """

    dists = Distributions()
    projects = []
    for (dist, _active) in dists.get_distributions("all"):
        if dist.project_name not in projects:
            projects.append(dist.project_name)
    return projects

