# pylint: disable-msg=W0613,W0612,W0212,W0511,R0912,C0322,W0704
# W0511 = XXX (my own todo's)

"""

cli.py
======

Desc: Command-line tool for listing Python packages installed by setuptools,
      package metadata, package dependencies, and querying The Cheese Shop
      (PyPI) for Python package release information such as which installed
      packages have updates available.

Author: Rob Cakebread <gentoodev a t gmail.com>

License : GNU General Public License Version 2 (See COPYING)

"""

__docformat__ = 'restructuredtext'
__revision__ = '$Revision$'[11:-1].strip()

import pprint
import os
import sys
import optparse
import pkg_resources
import webbrowser
from distutils.sysconfig import get_python_lib
import logging
from urllib import urlretrieve
from urlparse import urlparse

from yolk import __version__
from yolk.metadata import get_metadata
from yolk.yolklib import get_highest_version, Distributions
from yolk.pypi import CheeseShop
from yolk.setuptools_support import get_download_uri
from yolk.plugins import load_plugins
from yolk.__init__ import __version__ as VERSION



class StdOut:
    """Filter stdout from specific modules"""
    def __init__(self, stream, modulenames):
        self.stdout = stream
        self.modulenames = modulenames

    def __getattr__(self, attribute):
        if not self.__dict__.has_key(attribute) or attribute == '__doc__':
            return getattr(self.stdout, attribute)
        return self.__dict__[attribute]

    def write(self, inline):
        if sys._getframe(1).f_globals.get('__name__') in self.modulenames:
            pass
        else:
            self.stdout.write(inline)

    def writelines(self, inline):
        for line in inlines:
            self.write(line)

#Squelch output from setuptools
sys.stdout = StdOut(sys.stdout, ['distutils.log'])
sys.stderr = StdOut(sys.stderr, ['distutils.log'])



#Functions for obtaining info about packages installed by setuptools
##############################################################################


def get_pkglist():
    """
    Return list of all installed packages

    Note: It returns one project name per pkg no matter how many versions
    of a particular package is installed
     
    @returns: list of project name strings for every installed pkg
    
    """

    dists = Distributions()
    projects = []
    for (dist, active) in dists.get_distributions("all"):
        if dist.project_name not in projects:
            projects.append(dist.project_name)
    return projects


def show_updates(package_name=""):
    """
    Check installed packages for available updates on PyPI

    @param package_name: optional package name to check; checks every
                         installed pacakge if none specified
    @type package_name: string

    @returns: None
    """
    pypi = CheeseShop()
    dists = Distributions()
    if package_name:
        #Check for a single package
        pkg_list = []
        pkg_list.append(package_name)
    else:
        #Check for every installed package
        pkg_list = get_pkglist()

    for pkg in pkg_list:
        for (dist, active) in dists.get_distributions("all", pkg,
                dists.get_highest_installed(pkg)):
            (project_name, versions) = \
                    pypi.query_versions_pypi(dist.project_name, True)
            if versions:

                #PyPI returns them in chronological order,
                #but who knows if its guaranteed in the API?
                #Make sure we grab the highest version:

                newest = get_highest_version(versions)
                if newest != dist.version:

                    #We may have newer than what PyPI knows about

                    if pkg_resources.parse_version(dist.version) < \
                        pkg_resources.parse_version(newest):
                        print " %s %s (%s)" % (project_name, dist.version,
                                newest)


def get_plugin(method, options):
    """
    Return plugin object if CLI option is activated and method exists

    @param method: name of plugin's method we're calling
    @type method: string

    @param options: opt_parser options
    @type options: list of opt_parser.parse_args

    @returns: list of plugins with `method`

    """
    all_plugins = []
    for entry_point in pkg_resources.iter_entry_points('yolk.plugins'):
        plugin_obj = entry_point.load()
        plugin = plugin_obj()
        plugin.configure(options, None)
        if plugin.enabled:
            if not hasattr(plugin, method):
                LOGGER.warn("Error: plugin has no method: %s" % method)
                plugin = None
            else:
                all_plugins.append(plugin)
    return all_plugins

def show_distributions(show, project_name, version, options):
    """
    Show list of installed activated OR non-activated packages
    @param show: type of pkgs to show (all, active or nonactive)
    @type show: string

    @param project_name: pkg_resources Distribution project name to query
    @type project_name: string

    @param version: pkg_resources Distribution version
    @type version: string

    @param options: opt_parser options
    @type options: list of opt_parser.parse_args

    @returns: None or 2 if error 
    """
    show_metadata = options.metadata
    fields = options.fields

    #Search for any plugins with active CLI options with add_column() method
    plugins = get_plugin("add_column", options)

    #Some locations show false positive for 'development' packages:
    ignores = ["/UNIONFS", "/KNOPPIX.IMG"]

    #Check if we're in a workingenv
    #See http://cheeseshop.python.org/pypi/workingenv.py
    workingenv = os.environ.get('WORKING_ENV')
    if workingenv:
        ignores.append(workingenv)

    dists = Distributions()
    results = None
    for (dist, active) in dists.get_distributions(show, project_name,
            version):
        metadata = get_metadata(dist)
        for prefix in ignores:
            if dist.location.startswith(prefix):
                dist.location = dist.location.replace(prefix, "")
        #Case-insensitve search because of Windows
        if dist.location.lower().startswith(get_python_lib().lower()):
            develop = ""
        else:
            develop = dist.location
        if metadata:
            add_column_text = ""
            for my_plugin in plugins:
                #See if package is 'owned' by a package manager such as
                #portage, apt, rpm etc.
                #add_column_text += my_plugin.add_column(filename) + " "
                add_column_text += my_plugin.add_column(dist) + " "
            print_metadata(metadata, develop, active, options, add_column_text)
        else:
            print dist + " has no metadata"
        results = True
    if not results and project_name:
        if version:
            pkg_spec = "%s==%s" % (project_name, version)
        else:
            pkg_spec = "%s" % project_name
        if show == "all":
            LOGGER.error("There are no versions of %s installed." % pkg_spec)
        else:
            LOGGER.error("There are no %s versions of %s installed." % \
                    (show, pkg_spec))
        return 2
    elif show == "all" and results and fields:
        print "Versions with '*' are non-active."
        print "Versions with '!' are deployed in development mode."


def print_metadata(metadata, develop, active, options, installed_by):
    """
    Print out formatted metadata
    @param metadata: package's metadata
    @type metadata:  pkg_resources Distribution obj

    @param develop: path to pkg if its deployed in development mode
    @type develop: string

    @param active: show if package is activated or not
    @type active: boolean

    @param options: opt_parser options
    @type options: list of opt_parser.parse_args

    @param installed_by: Shows if pkg was installed by a package manager other
                         than setuptools
    @type installed_by: string

    @returns: None
    
    """
    show_metadata = options.metadata
    fields = options.fields

    version = metadata['Version']

    #When showing all packages, note which are not active:

    if active:
        if fields:
            active_status = ""
        else:
            active_status = "active"
    else:
        if fields:
            active_status = "*"
        else:
            active_status = "non-active"
    if develop:
        if fields:
            development_status = "! (%s)" % develop
        else:
            development_status = "development (%s)" % develop
    else:
        development_status = installed_by
    status = "%s %s" % (active_status, development_status)
    if fields:
        print '%s (%s)%s %s' % (metadata['Name'], version, active_status,
                                development_status)
    else:

        # Need intelligent justification

        print metadata['Name'].ljust(15) + " - " + version.ljust(12) + \
            " - " + status
    if fields:

        #Only show specific fields

        for field in metadata.keys():
            if field in fields:
                print '    %s: %s' % (field, metadata[field])
        print
    elif show_metadata:

        #Print all available metadata fields

        for field in metadata.keys():
            if field != 'Name' and field != 'Summary':
                print '    %s: %s' % (field, metadata[field])



def show_deps(pkg_ver):
    """
    Show dependencies for package(s)

    @param pkg_ver: setuptools pkgspec (e.g. kid>=0.8)
    @type pkg_ver: string
    
    @returns: None or 2 if error 
    """

    if not pkg_ver:
        msg = \
            '''I need at least a package name.
You can also specify a package name and version:
  yolk -d kid==0.8'''
        LOGGER.error(msg)
        return 2

    try:
        (project_name, ver) = pkg_ver[0].split('=')
    except ValueError:
        project_name = pkg_ver[0]
        ver = None

    pkgs = pkg_resources.Environment()

    if not len(pkgs[project_name]):
        LOGGER.error("Can't find package for %s" % project_name)
        return 2

    for pkg in pkgs[project_name]:
        if not ver:
            print pkg.project_name, pkg.version

        #XXX accessing protected member. Find better way.

        i = len(pkg._dep_map.values()[0])
        if i:
            while i:
                if not ver or ver and pkg.version == ver:
                    if ver and i == len(pkg._dep_map.values()[0]):
                        print pkg.project_name, pkg.version
                    print "  " + str(pkg._dep_map.values()[0][i - 1])
                i -= 1
        else:
            LOGGER.error(\
                    "No dependency information was supplied with the package.")
            return 2


#PyPI functions
##############################################################################


def show_download_links(pkg_name, version, file_type):
    """
    Query PyPI for pkg download URI for a packge

    @param pkg_name: pkg_resources Distribution project name to query
    @type pkg_name: string

    @param version: pkg_resources Distribution version
    @type version: string

    @param file_type: svn, source, binary, all (show all 3)
    @param file_type: string

    @returns: None
    
    """
    source = True

    if file_type == "svn":
        version = "dev"
        print_download_uri(pkg_name, version, source)
    elif file_type == "source":
        print_download_uri(pkg_name, version, source)
    elif file_type == "binary":
        source = False
        print_download_uri(pkg_name, version, source)
    elif file_type == "all":
        #Search for source, binary and svn
        source = True
        print_download_uri(pkg_name, version, source)
        source = False
        print_download_uri(pkg_name, version, source)
        source = True
        print_download_uri(pkg_name, version, source)

def fetch(pkg_name, version, directory, file_type="source"):
    """
    Download a package

    @param pkg_name: pkg_resources Distribution project name to query
    @type pkg_name: string

    @param version: pkg_resources Distribution version
    @type version: string

    @param file_type: svn, source, binary, all (use any available)
    @param file_type: string

    @returns: None
    
    """

    if file_type == "svn":
        version = "dev"
        source = True
        svn_uri = get_download_uri(pkg_name, version, source)[0]
        if svn_uri:
            directory = pkg_name + "_svn"
            fetch_svn(svn_uri, directory)
            return
        else:
            LOGGER.error("ERROR: No subversion repository found for %s" % pkg_name)
            sys.exit(2)
    elif file_type == "source":
        source = True
    elif file_type == "binary":
        source = False

    uri = get_download_uri(pkg_name, version, source)[0]

    if uri:
        fetch_uri(pkg_name, version, directory, uri)
    else:
        LOGGER.error("No URI found for package: %s %s" % (pkg_name, version))
        return 2

def fetch_uri(pkg_name, version, directory, uri):
    """
    Use ``urllib.urlretrieve`` to download package to file in sandbox dir.
    """
    filename = os.path.basename(urlparse(uri).path)
    if os.path.exists(filename):
        LOGGER.error("ERROR: File exists: " + filename)
        sys.exit(2)

    try:
        downloaded_filename, headers = urlretrieve(uri, filename)
        print "Downloaded ./" + filename
    except IOError, e:
        LOGGER.error("Error downloading package %s from URL %s"  % (filename, uri))
        LOGGER.error(str(e))
        sys.exit(2)

    if headers.gettype() in ["text/html"]:
        f = open(downloaded_filename)
        if re.search("404 Not Found", "".join(f.readlines())):
            f.close()
            LOGGER.error("Got '404 Not Found' error while trying to download package ... exiting")
            sys.exit(2)
        f.close()


def fetch_svn(svn_uri, directory):
    """
    Fetch subversion repository

    """
    if os.path.exists(directory):
        LOGGER.error("ERROR: Checkout directory exists - %s" % directory)
        sys.exit(2)
    try:
        os.mkdir(directory)
    except OSError, e:
        LOGGER.error("ERROR: " + str(e))
        sys.exit(2)
    cwd = os.path.realpath(os.curdir)
    os.chdir(directory)
    print "Doing subversion checkout for %s" % svn_uri
    os.system("/usr/bin/svn co %s" % svn_uri)
    os.chdir(cwd)

def print_download_uri(pkg_name, version, source):
    """
    @param pkg_name: pkg_resources Distribution project name to query
    @type pkg_name: string

    @param version: pkg_resources Distribution version
    @type version: string

    @param source: download source or binary
    @type source: boolean

    @returns: None

    """
    url = None
    #Use setuptools monkey-patch to grab url
    for url in get_download_uri(pkg_name, version, source):
        if url:
            print "%s" % url

def browse_website(pkg_name, browser=None):
    """
    Launch web browser at project's homepage
    
    @param pkg_name: pkg_resources Distribution project name
    @type pkg_name: string

    @param browser: name of web browser to use if not system default    
    @type browser: string

    @returns None
    """

    pypi = CheeseShop()
    #Get verified name from pypi.

    (pypi_project_name, versions) = pypi.query_versions_pypi(pkg_name)
    if len(versions):
        metadata = pypi.release_data(pypi_project_name, versions[0])
        if metadata.has_key("home_page"):
            print "Launching browser: %s" % metadata["home_page"]
            if browser == 'konqueror':
                browser = webbrowser.Konqueror()
            else:
                browser = webbrowser.get()
                browser.open(metadata["home_page"], 2)
            return

    print "No homepage URL found."


def show_pkg_metadata_pypi(pkg_name, version, fields):
    """
    Show pkg metadata queried from PyPI

    @param pkg_name: pkg_resources Distribution project name to query
    @type pkg_name: string

    @param version: pkg_resources Distribution version
    @type version: string

    @param fields: particular fields to show or "" for all
    @type fields: string
    
    @returns: None or 2 if error 
    
    """
    pypi = CheeseShop()
    (pypi_project_name, versions) = \
            pypi.query_versions_pypi(pkg_name, False)
    if version and version in versions:
        metadata = pypi.release_data(pypi_project_name, version)
    else:
        #Give highest version
        metadata = pypi.release_data(pypi_project_name, versions[0])

    if metadata:
        for key in metadata.keys():
            if not fields or (fields and fields==key):
                print "%s: %s" % (key, metadata[key])
    else:
        LOGGER.error(\
                "I'm afraid we have no %s at The Cheese Shop. \
                \nPerhaps a little red Leicester?" % pkg_name)
        return 2


def get_all_versions_pypi(pkg_name, my_version, use_cached_pkglist=False):
    """
    Fetch list of available versions for a package from The Cheese Shop

    @param pkg_name: pkg_resources Distribution project name to query
    @type pkg_name: string

    @param my_version: pkg_resources Distribution version
    @type my_version: string

    @param use_cached_pkglist: use a pkg list stored on disk to avoid network
                               usage
    @type use_cached_pkglist: boolean

    @returns: None or 2 if false
    """
    pypi = CheeseShop()
    (pypi_project_name, versions) = \
            pypi.query_versions_pypi(pkg_name, use_cached_pkglist)

    #pypi_project_name may != pkg_name
    #it returns the name with correct case
    #i.e. You give beautifulsoup but PyPI knows it as BeautifulSoup
    if my_version:
        spec = "%s==%s" % (pkg_name, my_version)
    else:
        spec = pkg_name

    if versions and my_version in versions:
        print_pkg_versions(pypi_project_name, [my_version])
    elif not my_version:
        print_pkg_versions(pypi_project_name, versions)
    else:
        LOGGER.error(\
                "I'm afraid we have no %s at The Cheese Shop. \
                \nPerhaps a little red Leicester?" % spec)
        return 2


def parse_search_spec(spec):
    """
    Parse search args and return spec dict for PyPI


    @param spec: Cheese Shop package search spec
                 e.g.
                 name=Cheetah
                 license=ZPL
                 license=ZPL AND name=Cheetah
    @type spec: string
    
    @returns:  
    """

    usage = \
        """You can search PyPI by the following:
 name 
 version 
 author 
 author_email 
 maintainer 
 maintainer_email 
 home_page 
 license 
 summary 
 description 
 keywords 
 platform 
 download_url
 
 e.g. yolk -S name=Cheetah
      yolk -S name=yolk AND license=PSF
      """

    if not spec:
        LOGGER.error(usage)
        return (None, None)

    try:
        spec = (" ").join(spec)
        operator = 'AND'
        first = second = ""
        if " AND " in spec:
            (first, second) = spec.split('AND')
        elif " OR " in spec:
            (first, second) = spec.split('OR')
            operator = 'OR'
        else:
            first = spec
        (key1, term1) = first.split('=')
        key1 = key1.strip()
        if second:
            (key2, term2) = second.split('=')
            key2 = key2.strip()

        spec = {}
        spec[key1] = term1
        if second:
            spec[key2] = term2
    except:
        LOGGER.error(usage)
        spec = operator = None
    return (spec, operator)


def pypi_search(spec):
    """
    Search PyPI by metadata keyword
    e.g. yolk -S name=yolk AND license=GPL

    @param spec: Cheese Shop search spec
    @type spec: list of strings
    
    spec could like like any of these:
      ["name=yolk"]
      ["license=GPL"]
      ["name=yolk", "AND", "license=GPL"]

    @returns: None


    """
    pypi = CheeseShop()

    (spec, operator) = parse_search_spec(spec)
    if not spec:
        return 2
    for pkg in pypi.search(spec, operator):
        if pkg['summary']:
            summary = pkg['summary'].encode('utf-8')
        else:
            summary = ""
        print """%s (%s):
    %s
""" % (pkg['name'].encode('utf-8'), pkg["version"],
                summary)


def get_rss_feed():
    """
    Show last 20 package updates from PyPI RSS feed
    
    @returns: None
    
    """

    pypi = CheeseShop()
    rss = pypi.get_rss()
    items = []
    for pkg in rss.keys():
        date = rss[pkg][1][:10]
        #Show packages grouped by date released
        if not date in items:
            items.append(date)
            print date
        print "  %s - %s" % (pkg, rss[pkg][0])

#Utility functions
##############################################################################


def parse_pkg_ver(package_spec, installed):
    """
    Return tuple with package_name and version from CLI args

    @param package_spec:
    @type package_spec:
    
    @param installed: whether package is installed or not
    @type installed: boolean

    @returns: tuple(pkg_name, version) 
    
    """

    arg_str = ("").join(package_spec)
    if "==" not in arg_str:

        #No version specified

        package_name = arg_str
        version = None
    else:
        (package_name, version) = arg_str.split("==")
        package_name = package_name.strip()
        version = version.strip()
    if installed:
        #Find proper case for package name
        dists = Distributions()
        package_name = dists.case_sensitive_name(package_name)
    return (package_name, version)

def print_pkg_versions(pkg_name, versions):
    """
    Print list of versions available for a package

    @param pkg_name: pkg_resources Distribution project name to query
    @type pkg_name: string

    @param version: pkg_resources Distribution version
    @type version: string

    @returns: None

    """

    for ver in versions:
        print "%s %s" % (pkg_name, ver)

def validate_pypi_opts(opt_parser):
    """
    Check for sane pkg_spec parse options

    @returns: True if sane, False if insane
    
    """

    (options, remaining_args) = opt_parser.parse_args()
    if options.versions_available or options.query_metadata_pypi or \
        options.download_links or options.browse_website:
        if not remaining_args:
            usage = \
                """You must specify a package spec
Examples:
  PackageName
  PackageName==2.0"""
            LOGGER.error(usage)
            return False
        else:
            return True
    return True


def show_entry_map(dist):
    """
    Show entry map for a distribution
    
    @param dist: `Distribution`
    @param type: pkg_resources Distribution object
    
    @returns: None or 2 if error
    """
    pprinter = pprint.PrettyPrinter()
    try:
        pprinter.pprint(pkg_resources.get_entry_map(dist))
    except pkg_resources.DistributionNotFound:
        LOGGER.error("Distribution not found: %s" % dist)
        return 2

def show_entry_points(module):
    """
    Show entry points for a module
    
    @param module: module name
    @type type: string

    @returns: None or 2 if error
    
    """
    found = False
    for entry_point in pkg_resources.iter_entry_points(module):
        found = True
        try:
            plugin = entry_point.load()
            print plugin.__module__
            print "   %s" % entry_point
            if plugin.__doc__:
                print plugin.__doc__
            print
        except ImportError:
            pass
    if not found:
        LOGGER.error("No entry points found for %s" % module)
        return 2

def setup_opt_parser():
    """
    Setup the optparser

    @returns: opt_parser.OptionParser
    
    """

    usage = "usage: %prog [options]"
    opt_parser = optparse.OptionParser(usage=usage)

    opt_parser.add_option("--version", action='store_true', dest=
                          "version", default=False, help=
                          "Show yolk version and exit.")

    opt_parser.add_option("-v", "--verbose", action='store_true', dest=
                          "verbose", default=False, help=
                          "Be more verbose.")
    #pylint: disable-msg=C0301
    #line too long
    group_local = optparse.OptionGroup(opt_parser,
            "Query installed Python packages",
            "The following options show information about installed Python packages. Activated packages are normal packages on sys.path that can be imported. Non-activated packages need 'pkg_resources.require()' before they can be imported, such as packages installed with 'easy_install --multi-version'. PKG_SPEC can be either a package name or package name and version e.g. Paste==0.9")

    group_local.add_option("-l", "--list", action='store_true', dest=
                           "all", default=False, help=
                           "List packages installed by setuptools. Use PKG_SPEC to narrow results.")

    group_local.add_option("-a", "--activated", action='store_true',
                           dest="active", default=False, help=
                           'List activated packages installed by ' +
                           'setuptools. Use PKG_SPEC to narrow results.')

    group_local.add_option("-n", "--non-activated", action='store_true',
                           dest="nonactive", default=False, help=
                           'List non-activated packages installed by ' +
                           'setuptools. Use PKG_SPEC to narrow results.')

    group_local.add_option("-m", "--metadata", action='store_true', dest=
                           "metadata", default=False, help=
                           'Show all metadata for packages installed by ' +
                           'setuptools (use with -l -a or -n)')

    group_local.add_option("-f", "--fields", action="store", dest=
                           "fields", default=False, help=
                           'Show specific metadata fields. ' +
                           '(use with -m or -M)')

    group_local.add_option("-d", "--depends", action='store_true', dest=
                           "depends", default=False, help=
                           "Show dependencies for a package installed by " +
                           "setuptools if they are available. (Use with PKG_SPEC)")

    group_local.add_option("--entry-points", action='store',
                           dest="entry_points", default=False, help=
                           'List entry points for a module. e.g. --entry-points yolk.plugins',
                            metavar="MODULE")

    group_local.add_option("--entry-map", action='store',
                           dest="entry_map", default=False, help=
                           'List entry map for a distribution. e.g. --entry-map yolk',
                           metavar="PACKAGE_NAME")
    group_pypi = optparse.OptionGroup(opt_parser,
            "PyPI (Cheese Shop) options",
            "The following options query the Python Package Index:")

    group_pypi.add_option("-D", "--download-links", action='store_true',
                          metavar="PKG_SPEC", dest="download_links",
                          default=False, help=
                          "Show download URL's for package listed on PyPI. (Use with PKG_SPEC)")

    group_pypi.add_option("-F", "--fetch-package", action='store_true',
                          metavar="PKG_SPEC", dest="fetch",
                          default=False, help=
                          "Download package source or egg. You can specify type with -T (Use with PKG_SPEC)")

    group_pypi.add_option("-H", "--browse-homepage", action='store_true',
                          metavar="PKG_SPEC", dest="browse_website",
                          default=False, help=
                          "Launch web browser at home page for package. (Use with PKG_SPEC)")

    group_pypi.add_option("-L", "--latest", action='store_true', dest=
                          "rss_feed", default=False, help=
                          "Show last 20 releases on PyPI.")

    group_pypi.add_option("-M", "--query-metadata", action='store_true',
                          dest="query_metadata_pypi", default=False,
                          metavar="PKG_SPEC", help=
                          "Show metadata for a package listed on PyPI. Use -f to show particular fields. (Use with PKG_SPEC)")

    group_pypi.add_option("-S", "", action="store", dest="search",
                          default=False, help=
                          "Search PyPI by spec and optional AND/OR operator.",
                          metavar='SEARCH_SPEC <AND/OR SEARCH_SPEC>')

    group_pypi.add_option("-T", "--file-type", action="store", dest=
                          "file_type", default="source", help=
                          "You may specify 'source', 'binary', 'svn' or 'all' when using -D.")

    group_pypi.add_option("-U", "--show-updates", action='store_true',
                          dest="show_updates", default=False, help=
                          "Check PyPI for updates on packages.")

    group_pypi.add_option("-V", "--versions-available", action=
                          'store_true', dest="versions_available",
                          default=False, help=
                          "Show available versions for given package " +
                          "listed on PyPI. (Use with PKG_NAME)")
    opt_parser.add_option_group(group_local)
    opt_parser.add_option_group(group_pypi)
    # add opts from plugins
    all_plugins = []
    for plugcls in load_plugins(others=True):
        plug = plugcls()
        try:
            plug.add_options(opt_parser)
        except AttributeError:
            pass

    return opt_parser


def main():
    """
    Parse options and perform actions
    
    @returns: 2 if error for sys.exit
    """

    opt_parser = setup_opt_parser()
    (options, remaining_args) = opt_parser.parse_args()

    if not validate_pypi_opts(opt_parser):
        return 2
    if not options.search and (len(sys.argv) == 1 or len(remaining_args) >
                               2):
        opt_parser.print_help()
        return 2

    if options.entry_points:
        return show_entry_points(options.entry_points)
    if options.entry_map:
        return show_entry_map(options.entry_map)

    #Options that depend on querying installed packages, not PyPI.
    #We find the proper case for package names if they are installed,
    #otherwise PyPI returns the correct case.
    if options.depends or options.all or options.active or options.nonactive \
            or (options.show_updates and remaining_args):
        want_installed = True
    else:
        want_installed = False
    if remaining_args:
        (package, version) = parse_pkg_ver(remaining_args, want_installed)
        if want_installed and not package:
            LOGGER.error("%s is not installed." % remaining_args[0])
            return 2
    else:
        package = version = None

    if options.search:
        #Add remainging cli arguments to options.search
        spec = remaining_args
        search_arg = options.search
        spec.insert(0, search_arg.strip())
        return pypi_search(spec)
    elif options.fetch:
        directory = "."
        return fetch(package, version, directory, options.file_type)
    elif options.version:
        print "yolk version %s (rev. %s)" % (VERSION, __revision__)
        return
    elif options.depends:
        return show_deps(remaining_args)
    elif options.all:
        if options.active or options.nonactive:
            opt_parser.error("Choose either -l, -n or -a")
        return show_distributions("all", package, version, options)
    elif options.active:
        if options.all or options.nonactive:
            opt_parser.error("Choose either -l, -n or -a")
        return show_distributions("active", package, version, options)
    elif options.nonactive:
        if options.active or options.all:
            opt_parser.error("Choose either -l, -n or -a")
        return show_distributions("nonactive", package, version, options)
    elif options.versions_available:
        return get_all_versions_pypi(package, version, False)
    elif options.browse_website:
        return browse_website(package)
    elif options.download_links:
        return show_download_links(package, version, options.file_type)
    elif options.rss_feed:
        return get_rss_feed()
    elif options.show_updates:
        return show_updates(package)
    elif options.query_metadata_pypi:
        return show_pkg_metadata_pypi(package, version, options.fields)
    else:
        opt_parser.print_help()
        return 2

LOGGER = logging.getLogger("yolk")
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.DEBUG)

if __name__ == "__main__":
    sys.exit(main())

