

# pylint: disable-msg=C0301,W0613,W0612,R0201

"""

pypi.py
=======

Desc: Library for getting information about Python packages by querying
      The CheeseShop (PYPI a.k.a. Python Package Index).


Author: Rob Cakebread <gentoodev a t gmail.com>

License  : GNU General Public License Version 2

"""

__docformat__ = 'restructuredtext'

import xmlrpclib
import cPickle
import urllib2
import os
import sys

from yolk import __version__


XMLRPC = True
#Python >=2.5 has elementtree 
if sys.version_info[0] == 2 and sys.version_info[1] == 5:
    from xml.etree.ElementTree import parse
else:
    try:
        from cElementTree import parse
    except ImportError:
        try:
            from elementtree.ElementTree import parse
        except ImportError:
            #If there is absolutely no version of elementtree available
            #this disables reading RSS feed (-L option).
            XMLRPC = False

PYPI_SERVER = xmlrpclib.Server('http://cheeseshop.python.org/pypi')
PYPI_URL = 'http://www.python.org/pypi?:action=rss'
VERSION = __version__.VERSION


class CheeseShop:

    """Interface to Python Package Index"""

    def __init__(self):
        """init"""

        self.yolk_dir = self.get_yolk_dir()

    def get_rss(self):
        """Fetch last 20 package release items from PyPI RSS feed"""
        if not XMLRPC:
            print >> sys.stderr, "You need to install ElementTree to use -L"
            sys.exit(2)
        rss = {}
        request = urllib2.Request(PYPI_URL)
        request.add_header('User-Agent', "yolk/%s (Python-urllib)" % VERSION)
        root = parse(urllib2.urlopen(request)).getiterator()
        #Remove Cheeseshop header
        for i in range(5):
            del root[i]
        for element in root:
            if element.tag == "title":
                title = element.text
            elif element.tag == "description":
                if element.text:
                    rss[title] = element.text
                else:
                    rss[title] = "No description."
            elif element.tag == "pubDate":
                if element.text:
                    rss[title] = (rss[title], element.text)
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
                elif pkg_type == "binary" and \
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
    #Remove Source Forge cruft
    if "?modtime" in url:
        url = url.split("?")[0]
    #Remove MD5 checksum
    if "#md5=" in url:
        url = url.split("#")[0]

    if pkg_type == "all":
        return url

    if pkg_type == "source":
        valid_source_types = [".tgz", ".tar.gz", ".zip", ".tbz2", ".tar.bz2"]
        for extension in valid_source_types:
            if url.lower().endswith(extension):
                return url

    elif pkg_type == "binary":
        if url.lower().endswith(".egg") or url.lower().endswith(".exe"):
            return url

