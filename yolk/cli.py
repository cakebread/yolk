#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable-msg=C0301,W0613,W0612

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
from distutils.sysconfig import get_python_lib

from yolk import __version__
from yolk.metadata import get_metadata
from yolk.yolklib import Distributions, get_highest_version
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
                dists.get_highest_installed(pkg)):
            (project_name, versions) = \
                    PYPI.query_versions_pypi(dist.project_name, True)
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


def show_distributions(show, project_name, version, show_metadata,
                       fields):
    """Show list of installed activated OR non-activated packages"""

    #When using unionfs in livecd's such as Knoppix we remove prefixes
    #otherwise all packages show as development

    ignores = ["/UNIONFS", "/KNOPPIX.IMG"]
    dists = Distributions()
    results = None
    for (dist, active) in dists.get_distributions(show, project_name,
            version):
        metadata = get_metadata(dist)
        for ignore in ignores:
            if dist.location.startswith(ignore):
                dist.location = dist.location.replace(ignore, "")
        if dist.location.startswith(get_python_lib()):
            develop = ""
        else:
            develop = dist.location
        if metadata:
            print_metadata(metadata, develop, active,
                           show_metadata, fields)
        else:
            print dist + " has no metadata"
        results = True
    if show == "all" and results and fields:
        print "Versions with '*' are non-active."
        print "Versions with '!' are deployed in development mode."


def print_metadata(metadata, develop, active, show_metadata,
                   fields):
    """Print out formatted metadata"""

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
        development_status = ""
    status = "%s %s" % (active_status, development_status)
    if fields:
        print '%s (%s)%s %s' % (metadata['Name'], version, active_status,
                                development_status)
    else:

        #XXX Need intelligent justification

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
    """Show dependencies for package(s)"""

    if not pkg_ver:
        msg = \
            '''I need at least a package name.
You can also specify a package name and version:
  yolk -d kid==0.8'''
        raise Usage(msg)

    try:
        (project_name, ver) = pkg_ver[0].split('=')
    except ValueError:
        project_name = pkg_ver[0]
        ver = None

    pkgs = pkg_resources.Environment()

    if not len(pkgs[project_name]):
        print >> sys.stderr, "Can't find package for %s" % project_name
        sys.exit(2)

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

    (pypi_project_name, versions) = PYPI.query_versions_pypi(package_name)
    if len(versions):
        metadata = PYPI.release_data(pypi_project_name, versions[0])
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

        (package_name, versions) = PYPI.query_versions_pypi(package_name,
                None)

    for ver in versions:
        metadata = PYPI.release_data(package_name, ver)
        for key in metadata.keys():
            print "%s: %s" % (key, metadata[key])


def get_all_versions_pypi(package_name, use_cached_pkglist=False):
    """Fetch list of available versions for a package from The Cheese Shop"""

    (pypi_project_name, versions) = \
            PYPI.query_versions_pypi(package_name, use_cached_pkglist)

    #pypi_project_name may != package_name; it returns the name with correct case
    #i.e. You give beautifulsoup but PyPI knows it as BeautifulSoup

    if versions:
        print_pkg_versions(pypi_project_name, versions)
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
        raise Usage(usage)
    return (spec, operator)


def pypi_search(arg, spec):
    """Search PyPI by metadata keyword
    e.g. yolk -S name=yolk
    """

    spec.insert(0, arg.strip())
    (spec, operator) = parse_search_spec(spec)
    for pkg in PYPI.search(spec, operator):
        if pkg['summary']:
            summary = pkg['summary'].encode('utf-8')
        else:
            summary = ""
        print """%s (%s):
    %s
""" % (pkg['name'].encode('utf-8'), pkg["version"],
                summary)


def get_rss_feed():
    """Show last 20 package updates from PyPI RSS feed"""

    rss = PYPI.get_rss()
    for pkg in rss.keys():
        print """%s
    %s
""" % (pkg, rss[pkg])


#Utility functions
##############################################################################


def parse_pkg_ver(package_spec):
    """Return tuple with package_name and version from CLI args"""

    arg_str = ("").join(package_spec)
    if "==" not in arg_str:

        #No version specified

        package_name = arg_str
        version = None
    else:
        (package_name, version) = arg_str.split("==")
        package_name = package_name.strip()
        version = version.strip()
    return (package_name, version)


def print_pkg_versions(package_name, versions):
    """Print list of versions available for a package"""

    for ver in versions:
        print "%s %s" % (package_name, ver)


def validate_pypi_opts(opt_parser):
    """Check for sane parse options"""

    (options, remaining_args) = opt_parser.parse_args()
    if options.versions_available or options.query_metadata_pypi or \
        options.download_links or options.browse_website:
        if not remaining_args:
            raise Usage, \
                """You must specify a package spec
Examples:
  PackageName
  PackageName==2.0"""


def setup_opt_parser():
    """Setup the optparser"""

    usage = "usage: %prog [options]"
    opt_parser = optparse.OptionParser(usage=usage)

    opt_parser.add_option("-v", "--version", action='store_true', dest=
                          "version", default=False, help=
                          "Show yolk version and exit.")

    group_local = optparse.OptionGroup(opt_parser,
            "Query installed Python packages",
            "The following options show information about Python packages installed by setuptools. Activated packages are normal packages on sys.path that can be imported. Non-activated packages need 'pkg_resources.require()' before they can be imported, such as packages installed with 'easy_install --multi-version'")

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
                           '(use with -l -a or -n)')

    group_local.add_option("-d", "--depends", action='store_true', dest=
                           "depends", default=False, help=
                           "Show dependencies for a package installed by " +
                           "setuptools if they are available. (Use with PKG_SPEC)")

    group_pypi = optparse.OptionGroup(opt_parser,
            "PyPI (Cheese Shop) options",
            "The following options query the Python Package Index:")

    group_pypi.add_option("-D", "--download-links", action='store_true',
                          metavar="PKG_SPEC", dest="download_links",
                          default=False, help=
                          "Show download URL's for package listed on PyPI. (Use with PKG_SPEC)")

    group_pypi.add_option("-H", "--browse-homepage", action='store_true',
                          metavar="PKG_SPEC", dest="browse_website",
                          default=False, help=
                          "Launch web browser at home page for package. (Use with PKG_SPEC)")

    group_pypi.add_option("-L", "--latest", action='store_true', dest=
                          "rss_feed", default=False, help=
                          "Show last 20 updates on PyPI.")

    group_pypi.add_option("-M", "--query-metadata", action='store_true',
                          dest="query_metadata_pypi", default=False,
                          metavar="PKG_SPEC", help=
                          "Show metadata for a package listed on PyPI. (Use with PKG_SPEC)")

    group_pypi.add_option("-S", "", action="store", dest="search",
                          default=False, help=
                          "Search PyPI by spec and optional AND/OR operator.",
                          metavar='SEARCH_SPEC <AND/OR SEARCH_SPEC>')

    group_pypi.add_option("-T", "--file-type", action="store", dest=
                          "file_type", default="all", help=
                          "You may specify 'source', 'binary' or 'all' when using -D.")

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
    return opt_parser


def main():
    """Main function"""

    opt_parser = setup_opt_parser()
    (options, remaining_args) = opt_parser.parse_args()

    validate_pypi_opts(opt_parser)
    if not options.search and (len(sys.argv) == 1 or len(remaining_args) >
                               2):
        opt_parser.print_help()
        sys.exit(2)

    if remaining_args:
        (package, version) = parse_pkg_ver(remaining_args)
    else:
        package = version = None
    if options.search:
        pypi_search(options.search, remaining_args)
    elif options.version:

        print "Version %s" % __version__.VERSION
    elif options.depends:
        show_deps(remaining_args)
    elif options.all:
        if options.active or options.nonactive:
            opt_parser.error("Choose either -l, -n or -a, not combinations of those.")
        show_distributions("all", package, version, options.metadata,
                           options.fields)
    elif options.active:
        if options.all or options.nonactive:
            opt_parser.error("Choose either -l, -n or -a, not combinations of those.")

        show_distributions("active", package, version, options.metadata,
                           options.fields)
    elif options.nonactive:
        if options.active or options.all:
            opt_parser.error("Choose either -l, -n or -a, not combinations of those.")
        show_distributions("nonactive", package, version, options.metadata,
                           options.fields)
    elif options.versions_available:

        get_all_versions_pypi(package, False)
    elif options.browse_website:
        browse_website(package)
    elif options.download_links:
        show_download_links(package, version, options.file_type)
    elif options.rss_feed:
        get_rss_feed()
    elif options.show_updates:
        show_updates(package, version)
    elif options.query_metadata_pypi:
        show_pkg_metadata_pypi(package, version)
    else:
        opt_parser.print_help()
        sys.exit(2)


PYPI = CheeseShop()

if __name__ == "__main__":
    main()

