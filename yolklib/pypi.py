

"""

Name: pypi.py

Desc: Library for getting information about Python packages by querying
      The CheeseShop (PYPI a.k.a. Python Package Index).


Author: Rob Cakebread <gentoodev a t gmail.com>

License  : PSF (Python Software Foundation License)

"""

import xmlrpclib
import cPickle
import urllib2
import os
import sys

import __version__

#XXX celementree is part of the stdlib in Python 2.5 but it uses a different
#namespace. Add check for it before this:
try:
    from cElementTree import parse
except ImportError:
    from elementtree.ElementTree import parse

PYPI_SERVER = xmlrpclib.Server('http://cheeseshop.python.org/pypi')
PYPI_URL = 'http://www.python.org/pypi?:action=rss'
VERSION = __version__.VERSION


class CheeseShop:

    """Interface to Python Package Index"""

    def __init__(self):

        self.yolk_dir = self.get_yolk_dir()

    def get_rss(self):
        """Fetch last 20 package release items from PyPI RSS feed"""
        rss = {}
        request = urllib2.Request(PYPI_URL)
        request.add_header('User-Agent', "yolk/%s (Python-urllib)" % VERSION)
        root = parse(urllib2.urlopen(request)).getiterator()
        #XXX It'd be nicer if we did a reverse chronological sort. 
        for element in root:
            if element.tag == "title":
                if not element.text.startswith("Cheese Shop recent updates"):
                    title = element.text
            elif element.tag == "description":
                if element.text:
                    if not element.text.startswith("Updates to the Python Cheese Shop"):
                        rss[title] = element.text
                        element.clear()
        return rss

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
        return cPickle.load(open(pickle_file, "r"))

    def store_pkg_list(self):
        """Cache master list of package names from PYPI"""

        package_list = self.list_packages()
        pickle_file = '%s/package_list.pkl' % self.yolk_dir
        cPickle.dump(package_list, open(pickle_file, "w"))

    def search(self, spec, operator):
        '''Query PYPI via XMLRPC interface using search spec'''
        return PYPI_SERVER.search(spec, operator.lower())

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
            #XXX Raises xmlrpclib.Fault if you give non-existant version
            #Could this be server bug?
            sys.exit(2)

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
                elif pkg_type == "binary" and \
                        urls['packagetype'].startswith("bdist"):
                    all_urls.append(urls['url'])
                elif pkg_type == "all":
                    #All
                    all_urls.append(urls['url'])

            #Try the package's metadata directly in case there's nothing
            #returned by XML-RPC's release_urls()

            if metadata.has_key('download_url') and \
                    metadata['download_url'] != "UNKNOWN":
                if metadata['download_url'] not in all_urls:
                    if pkg_type != "all":
                        url = _filter_urls(pkg_type, metadata['download_url'])
                        if url:
                            all_urls.append(url)
        return all_urls
        
def _filter_urls(pkg_type, url):
    """Returns list of URL's of specified file type"""

    if pkg_type == "source":
        valid_source_types = ["tgz", "tar.gz", "zip", "bz2", "tar.bz2"]
        for extension in valid_source_types:
            if url.lower().endswith(extension):
                return url

    elif pkg_type == "binary":
        for url in all_urls:
            if url.lower().endswith("egg") or url.lower().endswith("exe"):
                return url

