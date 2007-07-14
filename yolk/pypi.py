

# pylint: disable-msg=C0301,W0613,W0612,R0201

"""

pypi.py
=======

Desc: Library for getting information about Python packages by querying
      The CheeseShop (PYPI a.k.a. Python Package Index).


Author: Rob Cakebread <gentoodev@gmail.com>

License  : GNU General Public License Version 2

"""

__docformat__ = 'restructuredtext'

import xmlrpclib
import cPickle
import os
import time


PYPI_SERVER = xmlrpclib.Server('http://cheeseshop.python.org/pypi')


class CheeseShop:

    """Interface to Python Package Index"""

    def __init__(self):
        """init"""
        self.yolk_dir = self.get_yolk_dir()

    def query_versions_pypi(self, package_name, use_cached_pkglist=None):
        """Fetch list of available versions for a package from The CheeseShop"""

        versions = self.package_releases(package_name)
        if not versions:

            #The search failed, maybe they used the wrong case.
            #Check entire list of packages using case-insensitive search.

            if use_cached_pkglist:
                package_list = self.query_cached_package_list()
            else:

                #Download package list from PYPI

                package_list = self.list_packages()
            for pypi_pkg in package_list:
                if pypi_pkg.lower() == package_name.lower():
                    versions = self.package_releases(pypi_pkg)
                    package_name = pypi_pkg
                    break
        return (package_name, versions)

    def get_yolk_dir(self):
        """Return location we store config files and data"""
        app_data_dir = "%s/.yolk" % os.path.expanduser("~")
        if not os.path.exists(app_data_dir):
            os.mkdir(app_data_dir)
        return app_data_dir

    def query_cached_package_list(self):
        """Return list of pickled package names from PYPI"""

        pickle_file = '%s/package_list.pkl' % self.yolk_dir
        if not os.path.exists(pickle_file):
            self.store_pkg_list()
        return cPickle.load(open(pickle_file, "r"))

    def store_pkg_list(self):
        """Cache master list of package names from PYPI"""

        package_list = self.list_packages()
        pickle_file = '%s/package_list.pkl' % self.yolk_dir
        cPickle.dump(package_list, open(pickle_file, "w"))

    def search(self, spec, operator):
        '''Query PYPI via XMLRPC interface using search spec'''
        return PYPI_SERVER.search(spec, operator.lower())
    
    def changelog(self, hours):
        '''Query PYPI via XMLRPC interface using search spec'''
        return PYPI_SERVER.changelog(get_seconds(hours))

    def updated_releases(self, hours):
        '''Query PYPI via XMLRPC interface using search spec'''
        return PYPI_SERVER.updated_releases(get_seconds(hours))

    def list_packages(self):
        """Query PYPI via XMLRPC interface for a a list of all package names"""

        return PYPI_SERVER.list_packages()

    def release_urls(self, package_name, version):
        """Query PYPI via XMLRPC interface for a pkg's available versions"""

        return PYPI_SERVER.release_urls(package_name, version)

    def release_data(self, package_name, version):
        """Query PYPI via XMLRPC interface for a pkg's metadata"""
        try:
            return PYPI_SERVER.release_data(package_name, version)
        except xmlrpclib.Fault:
            #XXX Raises xmlrpclib. Fault if you give non-existant version
            #Could this be server bug?
            return

    def package_releases(self, package_name):
        """Query PYPI via XMLRPC interface for a pkg's available versions"""

        return PYPI_SERVER.package_releases(package_name)

    def get_download_urls(self, package_name, version="", pkg_type="all"):
        """Query PyPI for pkg download URI for a packge"""

        if version:
            versions = [version]
        else:

            #If they don't specify version, show em all.

            (package_name, versions) = self.query_versions_pypi(package_name, 
                    None)

        all_urls = []
        for ver in versions:
            metadata = self.release_data(package_name, ver)
            for urls in self.release_urls(package_name, ver):
                if pkg_type == "source" and urls['packagetype'] == "sdist":
                    all_urls.append(urls['url'])
                elif pkg_type == "egg" and \
                        urls['packagetype'].startswith("bdist"):
                    all_urls.append(urls['url'])
                elif pkg_type == "all":
                    #All
                    all_urls.append(urls['url'])

            #Try the package's metadata directly in case there's nothing
            #returned by XML-RPC's release_urls()
            if metadata and metadata.has_key('download_url') and \
                        metadata['download_url'] != "UNKNOWN" and \
                        metadata['download_url'] != None:
                if metadata['download_url'] not in all_urls:
                    if pkg_type != "all":
                        url = filter_url(pkg_type, metadata['download_url'])
                        if url:
                            all_urls.append(url)
        return all_urls
        
def filter_url(pkg_type, url):
    """Returns URL of specified file type, else None"""
    bad_stuff = ["?modtime", "#md5="]
    for junk in bad_stuff:
        if junk in url:
            url = url.split(junk)[0]
            break

    #pkg_spec==dev (svn)
    if url.endswith("-dev"):
        url = url.split("#egg=")[0]

    if pkg_type == "all":
        return url

    if pkg_type == "source":
        valid_source_types = [".tgz", ".tar.gz", ".zip", ".tbz2", ".tar.bz2"]
        for extension in valid_source_types:
            if url.lower().endswith(extension):
                return url

    elif pkg_type == "egg":
        if url.lower().endswith(".egg"):
            return url

def get_seconds(hours):
    """
    Get number of seconds since epoc from now - hours

    @param hours: Number of hours back in time we are checking
    @type hours: int

    Return integer for number of seconds for hours

    """
    return int(time.time() - (60 * 60) * hours)

