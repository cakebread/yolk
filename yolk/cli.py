#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Name: cli.py

Desc: Command-line tool for listing Python packages installed by setuptools,
      package metadata, package dependencies, and querying The Cheese Shop
      (PyPI) for Python package release information such as which installed
      packages have updates available.

Author: Rob Cakebread <gentoodev a t gmail.com>

License  : PSF (Python Software Foundation License)

"""

import sys
import optparse
import pkg_resources
import webbrowser

from yolk import __version__
from yolk.metadata import get_metadata
from yolk.yolklib import Distributions, get_highest_installed, get_highest_version
from yolk.pypi import CheeseShop


class Usage(Exception):

    """Usage exception"""

    def __init__(self, msg):
        print >> sys.stderr, "%s" % msg
        sys.exit(2)

#Functions for obtaining info about packages installed with setuptools
##############################################################################

def get_pkglist():
    """Return list of all pkg names"""
    dists = Distributions()
    pkgs = []
    for (dist, active) in dists.get_distributions("all"):
        if dist.project_name not in pkgs:
            pkgs.append(dist.project_name)
    return pkgs

def show_updates(package_name="", version=""):
    """Check installed packages for available updates on PyPI"""
    dists = Distributions()
    for pkg in get_pkglist():
        for (dist, active) in dists.get_distributions("all", pkg,
                get_highest_installed(pkg)):
            (pkg_name, versions) = PYPI.query_versions_pypi(dist.project_name, True)
            if versions:
                newest = get_highest_version(versions)
                if newest != dist.version:
                    #We may have newer than what PyPI knows about
                    if pkg_resources.parse_version(dist.version) < \
                            pkg_resources.parse_version(newest):
                        print " %s %s (%s)" % (pkg_name, dist.version, newest)

def show_distributions(show, pkg_name, version, show_metadata, fields):
    """Show list of installed activated OR non-activated packages"""

    dists = Distributions()
    results = None
    for (dist, active) in dists.get_distributions(show, pkg_name, 
            version):
        metadata = get_metadata(dist)
        print_metadata(show, metadata, active, show_metadata, fields)
        results = True
    if show == 'all' and results:
        print "Versions with '*' are non-active."


def print_metadata(show, metadata, active, show_metadata, fields):
    """Print out formatted metadata"""

    version = metadata['Version']

    #When showing all packages, note which are not active:

    if show == 'all' and not active:
        active = " *"
    else:
        active = ''

    print '%s (%s)%s' % (metadata['Name'], version, active)

    if fields:

        #Only show specific fields

        for field in metadata.keys():
            if field in fields:
                print '    %s: %s' % (field, metadata[field])
    elif show_metadata:

        #Print all available metadata fields

        for field in metadata.keys():
            if field != 'Name' and field != 'Summary':
                print '    %s: %s' % (field, metadata[field])
    else:

        #Default when listing packages
        if metadata.has_key('Summary'):
            print "    %s" % metadata['Summary']
    print 


def show_deps(pkg_ver):
    """Show dependencies for package(s)"""

    if not pkg_ver:
        msg = "I need at least a package name.\n" \
              "You can also specify a package name and version:\n" \
              "  yolk.py -d kid 0.8"
        raise Usage(msg)

    try:
        (pkg_name, ver) = pkg_ver[0].split('=')
    except ValueError:
        pkg_name = pkg_ver[0]
        ver = None

    pkgs = pkg_resources.Environment()

    if not len(pkgs[pkg_name]):
        print >> sys.stderr, "Can't find package for %s" % pkg_name
        sys.exit(2)

    for pkg in pkgs[pkg_name]:
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
            print >> sys.stderr, \
                "No dependency information was supplied with the package."
            sys.exit(2)


#PyPI functions
##############################################################################


def show_download_links(package_name, version, file_type):
    """Query PyPI for pkg download URI for a packge"""
    for url in PYPI.get_download_urls(package_name, version, file_type):
        print url


def browse_website(package_name, browser=None):
    """Launch web browser at project's homepage"""

    #Get verified name from pypi.

    (pypi_pkg_name, versions) = PYPI.query_versions_pypi(package_name)
    if len(versions):
        metadata = PYPI.release_data(pypi_pkg_name, versions[0])
        if metadata.has_key("home_page"):
            print "Launching browser: %s" % metadata["home_page"]
            if browser == 'konqueror':
                browser = webbrowser.Konqueror()
            else:
                browser = webbrowser.get()
            try:
                browser.open(metadata["home_page"], 2)
            except AttributeError:
                browser.open(metadata["home_page"], 2)
            return 

    print "No homepage URL found."


def show_pkg_metadata_pypi(package_name, version):
    """Show pkg metadata queried from PyPI"""

    if version:
        versions = [version]
    else:
        #If they don't specify version, show all.

        (package_name, versions) = PYPI.query_versions_pypi(package_name, None)

    for ver in versions:
        metadata = PYPI.release_data(package_name, ver)
        for key in metadata.keys():
            print "%s: %s" % (key, metadata[key])


def get_all_versions_pypi(package_name, use_cached_pkglist):
    """Fetch list of available versions for a package from The Cheese Shop"""

    (pypi_pkg_name, versions) = PYPI.query_versions_pypi(package_name, 
            use_cached_pkglist)

    #pypi_pkg_name may != package_name; it returns the name with correct case
    #i.e. You give beautifulsoup but PyPI knows it as BeautifulSoup

    if versions:
        print_pkg_versions(pypi_pkg_name, versions)
    else:
        print >> sys.stderr, "Nothing found on PyPI for %s" % \
            package_name
        sys.exit(2)

def parse_search_spec(spec):
    """Parse search args and return spec dict for PyPI"""

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
        raise Usage(usage)

    try:
        spec = (" ").join(spec)
        operator = 'AND'
        first = second = ''
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
        raise Usage(usage)
    return (spec, operator)


def pypi_search(spec):
    """Search PyPI by metadata keyword"""

    (spec, operator) = parse_search_spec(spec)
    for pkg in PYPI.search(spec, operator):
        if pkg['summary']:
            summary = pkg['summary'].encode('utf-8')
        else:
            summary = ''
        print "%s (%s):\n    %s\n" % (pkg['name'].encode('utf-8'), 
               pkg['version'], 
               summary)


def get_rss_feed():
    """Show last 20 package updates from PyPI RSS feed"""

    rss = PYPI.get_rss()
    for pkg in rss.keys():
        print "%s\n    %s\n" % (pkg, rss[pkg])


#Utility functions
##############################################################################

def parse_pkg_ver(args):
    """Return tuple with package_name and version from CLI args"""

    version = package = None
    if len(args) == 1:
        package = args[0]
    elif len(args) == 2:
        package = args[0]
        version = args[1]
    return (package, version)


def print_pkg_versions(package_name, versions):
    """Print list of versions available for a package"""

    for ver in versions:
        print "%s %s" % (package_name, ver)


def setup_opt_parser():
    """Setup the optparser"""

    usage = "usage: %prog [options] <package_name> <version>"
    opt_parser = optparse.OptionParser(usage=usage)
    opt_parser.add_option("-v", "--version", action='store_true', dest=
                          "version", default=False, help=
                          "Show yolk version and exit.")

    group_local = optparse.OptionGroup(opt_parser, 
            "Query installed Python packages", 
            "The following options show information about Python packages installed by setuptools. Activated packages are normal packages on sys.path that can be imported. Non-activated packages need 'pkg_resources.require()' before they can be imported, such as packages installed with 'easy_install --multi-version'")

    group_local.add_option("-l", "--list", action='store_true', dest=
                           'all', default=False, help=
                           "List all packages installed by setuptools.")

    group_local.add_option("-a", "--activated", action='store_true', 
                           dest="active", default=False, help=
                           'List only activated packages installed by ' +
                           'setuptools.')

    group_local.add_option("-n", "--non-activated", action='store_true', 
                           dest="nonactive", default=False, help=
                           'List only non-activated packages installed by ' +
                           'setuptools.')

    group_local.add_option("-m", "--metadata", action='store_true', dest=
                           "metadata", default=False, help=
                           'Show all metadata for packages installed by ' +
                           'setuptools (use with -l -a or -n)')

    group_local.add_option("-f", "--fields", action="store", dest=
                           "fields", default=False, help=
                           'Show specific metadata fields. ' +
                           '(use with -l -a or -n)')

    group_local.add_option("-d", "--depends", action='store_true', dest=
                           "depends", default=False, help=
                           "Show dependencies for a package installed by " + 
                           "setuptools if they are available. " + 
                           '(use with -l -a or -n)')

    group_pypi = optparse.OptionGroup(opt_parser, 
            "PyPI (Cheese Shop) options", 
            "The following options query the Python Package Index:")

    group_pypi.add_option("-C", "--use-cached-pkglist", action=
                          'store_true', dest="use_cached_pkglist", 
                          default=False, help=
                          "Use cached package list instead of querying PyPI " + 
                          "(Use -F to force retrieving list.)")

    group_pypi.add_option("-D", "--download-links", action='store_true', 
                          dest="download_links", default=False, help=
                          "Show download URL's for package listed on PyPI. ")

    group_pypi.add_option("-F", "--fetch-package-list", action=
                          'store_true', dest="fetch_package_list", 
                          default=False, help=
                          "Fetch and cache list of packages from PyPI.")

    group_pypi.add_option("-H", "--browse-homepage", action='store_true', 
                          dest="browse_website", default=False, help=
                          "Launch web browser at home page for package.")

    group_pypi.add_option("-L", "--latest", action='store_true', dest=
                          "rss_feed", default=False, help=
                          "Show last 20 updates on PyPI.")

    group_pypi.add_option("-M", "--query-metadata", action='store_true', 
                          dest="query_metadata_pypi", default=False, 
                          help=
                          "Show metadata for a package listed on PyPI.")

    group_pypi.add_option("-S", "--search", action='store_true', dest=
                          "search", default=False, help=
                          "Search PyPI by spec and operator.")

    group_pypi.add_option("-T", "--file-type", action='store', dest=
                          "file_type", default="all", help=
                          "You may specify 'source', 'egg' or 'all' when using -D.")

    group_pypi.add_option("-U", "--show-updates", action='store_true', dest=
                          "show_updates", default=False, help=
                          "Check PyPI for updates on packages.")

    group_pypi.add_option("-V", "--versions-available", action=
                          'store_true', dest="versions_available", 
                          default=False, help=
                          "Show available versions for given package " + 
                          "listeded on PyPI.")
    opt_parser.add_option_group(group_local)
    opt_parser.add_option_group(group_pypi)
    return opt_parser


def main():
    """Main function"""

    opt_parser = setup_opt_parser()
    (options, remaining_args) = opt_parser.parse_args()

    def usage(msg=""):
        """Print optparse help msg plus an optional additional msg"""
        opt_parser.print_help()
        if msg:
            print >> sys.stderr, "%s" % msg
        sys.exit(2)

    if not options.search and (len(sys.argv) == 1 or len(remaining_args) > 2):
        usage()

    (package, version) = parse_pkg_ver(remaining_args)

    if options.search:
        pypi_search(remaining_args)

    elif options.version:
        print "Version %s" % __version__.VERSION
    elif options.depends:
        show_deps(remaining_args)
    elif options.all:
        if options.active or options.nonactive:
            usage("Choose either -l, -n or -a, not combinations of those.")
        show_distributions('all', package, version, options.metadata, 
                           options.fields)
    elif options.active:
        if options.all or options.nonactive:
            usage("Choose either -l, -n or -a, not combinations of those.")

        show_distributions("active", package, version, options.metadata, 
                           options.fields)
    elif options.nonactive:
        if options.active or options.all:
            usage("Choose either -l, -n or -a, not combinations of those.")
        show_distributions("nonactive", package, version, options.metadata, 
                           options.fields)

    elif options.versions_available:
        get_all_versions_pypi(package, options.use_cached_pkglist)
    elif options.browse_website:
        browse_website(package)
    elif options.fetch_package_list:
        PYPI.store_pkg_list()
    elif options.download_links:
        show_download_links(package, version, options.file_type)
    elif options.rss_feed:
        get_rss_feed()
    elif options.show_updates:
        show_updates(package, version)
    elif options.query_metadata_pypi:
        show_pkg_metadata_pypi(package, version)
    else:
        usage()


PYPI = CheeseShop()

if __name__ == "__main__":
    main()

