#!/usr/bin/env python
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


def get_download_uri(package_name, version, source):
    """
    Use setuptools to search for a package's URI
    
    @returns: list of URI strings 
    """
    tmpdir = None
    force_scan = True
    develop_ok = False

    if version:
        pkg_spec = "%s==%s" % (package_name, version)
    else:
        pkg_spec = package_name
    req = pkg_resources.Requirement.parse(pkg_spec)
    pkg_index = MyPackageIndex()
    output = []
    try:
        pkg_index.fetch_distribution(req, tmpdir, force_scan, source, 
                develop_ok)
    except DownloadURI, url:
        #uri = filter_url(file_type, url.value)
        if url.value not in output:
            #Remove #egg=pkg-dev
            output.append(url.value.split("#")[0])
    return output
