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


import inspect
import re
import pprint
import os
import sys
import optparse
import pkg_resources
import webbrowser
import logging
from distutils.sysconfig import get_python_lib
from urllib import urlretrieve
from urlparse import urlparse

from yolk.metadata import get_metadata
from yolk.yolklib import get_highest_version, Distributions
from yolk.pypi import CheeseShop
from yolk.setuptools_support import get_download_uri, get_pkglist
from yolk.plugins import load_plugins
from yolk.utils import run_command, command_successful
from yolk.__init__ import __version__ as VERSION



class StdOut:

    """
    Filter stdout or stderr from specific modules
    So far this is just used for pkg_resources
    """

    def __init__(self, stream, modulenames):
        self.stdout = stream
        #Modules to squelch
        self.modulenames = modulenames

    def __getattr__(self, attribute):
        if not self.__dict__.has_key(attribute) or attribute == '__doc__':
            return getattr(self.stdout, attribute)
        return self.__dict__[attribute]

    def write(self, inline):
        """
        Write a line to stdout if it isn't in a blacklist
        
        Try to get the name of the calling module to see if we want
        to filter it. If there is no calling module, use current
        frame in case there's a traceback before there is any calling module
        """
        frame = inspect.currentframe().f_back
        if frame:
            mod = frame.f_globals.get('__name__') 
        else:
            mod = sys._getframe(0).f_globals.get('__name__') 
        if not mod in self.modulenames:
            self.stdout.write(inline)

    def writelines(self, inline):
        """Write multiple lines"""
        for line in inline:
            self.write(line)


class Yolk(object):

    """
    Main class for yolk
    """

    def __init__(self):
        #PyPI project name with proper case
        self.project_name = ""
        #PyPI project version 
        self.version = ""
        #List of all versions not hidden on PyPI
        self.all_versions = []
        self.options = None
        self.logger = logging.getLogger("yolk")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler())
        self.logger.setLevel(logging.DEBUG)

        #Squelch output from setuptools
        #Add future offenders to this list.
        shut_up = ['distutils.log']
        sys.stdout = StdOut(sys.stdout, shut_up)
        sys.stderr = StdOut(sys.stderr, shut_up)

    def get_plugin(self, method):
        """
        Return plugin object if CLI option is activated and method exists

        @param method: name of plugin's method we're calling
        @type method: string

        @returns: list of plugins with `method`

        """
        all_plugins = []
        for entry_point in pkg_resources.iter_entry_points('yolk.plugins'):
            plugin_obj = entry_point.load()
            plugin = plugin_obj()
            plugin.configure(self.options, None)
            if plugin.enabled:
                if not hasattr(plugin, method):
                    self.logger.warn("Error: plugin has no method: %s" % method)
                    plugin = None
                else:
                    all_plugins.append(plugin)
        return all_plugins

    def run(self):
        """
        Perform actions based on CLI options
        
        @returns: status code
        """
        opt_parser = setup_opt_parser()
        (self.options, remaining_args) = opt_parser.parse_args()

        if not self.validate_pypi_opts(opt_parser):
            return 2
        if not self.options.search and (len(sys.argv) == 1 or\
                len(remaining_args) > 2):
            opt_parser.print_help()
            return 2

        if self.options.entry_points:
            return self.show_entry_points()
        if self.options.entry_map:
            return self.show_entry_map()

        #Options that depend on querying installed packages, not PyPI.
        #We find the proper case for package names if they are installed,
        #otherwise PyPI returns the correct case.
        if self.options.depends or self.options.all or self.options.active \
                or self.options.nonactive  or \
                (self.options.show_updates and remaining_args):
            want_installed = True
        else:
            want_installed = False
        if remaining_args:
            (self.project_name, self.version, self.all_versions) = \
                    self.parse_pkg_ver(remaining_args, want_installed)
            if want_installed and not self.project_name:
                print >> sys.stderr, "%s is not installed." % remaining_args[0]
                return 2

        if self.options.search:
            #Add remainging cli arguments to options.search
            spec = remaining_args
            search_arg = self.options.search
            spec.insert(0, search_arg.strip())
            status = self.pypi_search(spec)
        elif self.options.fetch:
            directory = "."
            status = self.fetch(directory)
        elif self.options.version:
            print "yolk version %s (rev. %s)" % (VERSION, __revision__)
            status = 0
        elif self.options.depends:
            status = self.show_deps(remaining_args)
        elif self.options.all:
            if self.options.active or self.options.nonactive:
                opt_parser.error("Choose either -l, -n or -a")
            status = self.show_distributions("all")
        elif self.options.active:
            if self.options.all or self.options.nonactive:
                opt_parser.error("Choose either -l, -n or -a")
            status = self.show_distributions("active")
        elif self.options.nonactive:
            if self.options.active or self.options.all:
                opt_parser.error("Choose either -l, -n or -a")
            status = self.show_distributions("nonactive")
        elif self.options.versions_available:
            status = self.get_all_versions_pypi(False)
        elif self.options.browse_website:
            status = self.browse_website()
        elif self.options.download_links:
            status = self.show_download_links()
        elif self.options.rss_feed:
            status = get_rss_feed()
        elif self.options.show_updates:
            status = self.show_updates()
        elif self.options.query_metadata_pypi:
            status = self.show_pkg_metadata_pypi()
        else:
            opt_parser.print_help()
            status = 2

    def show_updates(self):
        """
        Check installed packages for available updates on PyPI

        @param project_name: optional package name to check; checks every
                             installed pacakge if none specified
        @type project_name: string

        @returns: None
        """
        pypi = CheeseShop()
        dists = Distributions()
        if self.project_name:
            #Check for a single package
            pkg_list = [self.project_name]
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
        return 0


    def show_distributions(self, show):
        """
        Show list of installed activated OR non-activated packages

        @param show: type of pkgs to show (all, active or nonactive)
        @type show: string

        @returns: None or 2 if error 
        """
        show_metadata = self.options.metadata

        #Search for any plugins with active CLI options with add_column() method
        plugins = self.get_plugin("add_column")

        #Some locations show false positive for 'development' packages:
        ignores = ["/UNIONFS", "/KNOPPIX.IMG"]

        #Check if we're in a workingenv
        #See http://cheeseshop.python.org/pypi/workingenv.py
        workingenv = os.environ.get('WORKING_ENV')
        if workingenv:
            ignores.append(workingenv)

        dists = Distributions()
        results = None
        for (dist, active) in dists.get_distributions(show, self.project_name,
                self.version):
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
                self.print_metadata(metadata, develop, active, add_column_text)
            else:
                print dist + " has no metadata"
            results = True
        if not results and self.project_name:
            if self.version:
                pkg_spec = "%s==%s" % (self.project_name, self.version)
            else:
                pkg_spec = "%s" % self.project_name
            if show == "all":
                self.logger.error("There are no versions of %s installed." \
                        % pkg_spec)
            else:
                self.logger.error("There are no %s versions of %s installed." \
                        % \
                        (show, pkg_spec))
            return 2
        elif show == "all" and results and self.options.fields:
            print "Versions with '*' are non-active."
            print "Versions with '!' are deployed in development mode."


    def print_metadata(self, metadata, develop, active, installed_by):
        """
        Print out formatted metadata
        @param metadata: package's metadata
        @type metadata:  pkg_resources Distribution obj

        @param develop: path to pkg if its deployed in development mode
        @type develop: string

        @param active: show if package is activated or not
        @type active: boolean

        @param installed_by: Shows if pkg was installed by a package manager other
                             than setuptools
        @type installed_by: string

        @returns: None
        
        """
        show_metadata = self.options.metadata
        fields = self.options.fields

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

    def show_deps(self, pkg_ver):
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
            self.logger.error(msg)
            return 2

        try:
            (project_name, ver) = pkg_ver[0].split('=')
        except ValueError:
            project_name = pkg_ver[0]
            ver = None

        pkgs = pkg_resources.Environment()

        if not len(pkgs[project_name]):
            self.logger.error("Can't find package for %s" % self.project_name)
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
                self.logger.error(\
                    "No dependency information was supplied with the package.")
                return 2


    def show_download_links(self):
        """
        Query PyPI for pkg download URI for a packge

        @returns: None
        
        """
        #In case they specify version as 'dev' instead of using -T svn,
        #don't show three svn URI's
        if self.options.file_type == "all" and self.version == "dev":
            self.options.file_type = "svn"

        if self.options.file_type == "svn":
            version = "dev"
        else:
            if self.version:
                version = self.version
            else:
                #version = get_highest_version(self.all_versions)
                version = self.all_versions[0]
        if self.options.file_type == "all":
            #Search for source, egg, and svn
            self.print_download_uri(version, True)
            self.print_download_uri(version, False)
            self.print_download_uri("dev", False, True)
        else:
            if self.options.file_type == "source":
                source = True
            else:
                source = False
            self.print_download_uri(version, source)
        return 0

    def print_download_uri(self, version, source, svn=False):
        """
        @param source: download source or egg
        @type source: boolean

        @returns: None

        """

        url = None
        #Use setuptools monkey-patch to grab url
        for url in get_download_uri(self.project_name, version, source):
            if url:
                print "%s" % url

    def fetch(self, directory):
        """
        Download a package

        @returns: None
        
        """
        #Default type to download
        source = True

        if self.options.file_type == "svn":
            version = "dev"
            svn_uri = get_download_uri(self.project_name, \
                    self.version, source)[0]
            if svn_uri:
                directory = self.project_name + "_svn"
                self.fetch_svn(svn_uri, directory)
                return
            else:
                self.logger.error(\
                    "ERROR: No subversion repository found for %s" % \
                    self.project_name)
                sys.exit(2)
        elif self.options.file_type == "source":
            source = True
        elif self.options.file_type == "egg":
            source = False

        uri = get_download_uri(self.project_name, self.version, source)[0]

        if uri:
            self.fetch_uri(directory, uri)
        else:
            self.logger.error("No URI found for package: %s %s" % \
                    (self.project_name, self.version))
            return 2

    def fetch_uri(self, directory, uri):
        """
        Use ``urllib.urlretrieve`` to download package to file in sandbox dir.
        """
        filename = os.path.basename(urlparse(uri).path)
        if os.path.exists(filename):
            self.logger.error("ERROR: File exists: " + filename)
            sys.exit(2)

        try:
            downloaded_filename, headers = urlretrieve(uri, filename)
            print "Downloaded ./" + filename
        except IOError, err_msg:
            self.logger.error("Error downloading package %s from URL %s"  \
                    % (filename, uri))
            self.logger.error(str(err_msg))
            sys.exit(2)

        if headers.gettype() in ["text/html"]:
            dfile = open(downloaded_filename)
            if re.search("404 Not Found", "".join(dfile.readlines())):
                dfile.close()
                self.logger.error("'404 Not Found' error")
                sys.exit(2)
            dfile.close()


    def fetch_svn(self, svn_uri, directory):
        """
        Fetch subversion repository

        """
        if not command_successful("svn --version"):
            self.logger.error("ERROR: Do you have subversion installed?")
            sys.exit(2)
        if os.path.exists(directory):
            self.logger.error("ERROR: Checkout directory exists - %s" \
                    % directory)
            sys.exit(2)
        try:
            os.mkdir(directory)
        except OSError, err_msg:
            self.logger.error("ERROR: " + str(err_msg))
            sys.exit(2)
        cwd = os.path.realpath(os.curdir)
        os.chdir(directory)
        print "Doing subversion checkout for %s" % svn_uri
        status, output = run_command("/usr/bin/svn co %s" % svn_uri)
        print output
        os.chdir(cwd)

    def browse_website(self, browser=None):
        """
        Launch web browser at project's homepage

        @returns None
        """
        pypi = CheeseShop()
        if len(self.all_versions):
            metadata = pypi.release_data(self.project_name, self.all_versions[0])
            if metadata.has_key("home_page"):
                print "Launching browser: %s" % metadata["home_page"]
                if browser == 'konqueror':
                    browser = webbrowser.Konqueror()
                else:
                    browser = webbrowser.get()
                    browser.open(metadata["home_page"], 2)
                return

        print "No homepage URL found."


    def show_pkg_metadata_pypi(self):
        """
        Show pkg metadata queried from PyPI

        @returns: None or 2 if error 
        
        """
        pypi = CheeseShop()
        if self.version and self.version in self.all_versions:
            metadata = pypi.release_data(self.project_name, self.version)
        else:
            #Give highest version
            metadata = pypi.release_data(self.project_name, self.all_versions[0])

        if metadata:
            for key in metadata.keys():
                if not self.options.fields or (self.options.fields and \
                        self.options.fields==key):
                    print "%s: %s" % (key, metadata[key])

    def get_all_versions_pypi(self, my_version, use_cached_pkglist=False):
        """
        Fetch list of available versions for a package from The Cheese Shop

        @param my_version: pkg_resources Distribution version
        @type my_version: string

        @param use_cached_pkglist: use a pkg list stored on disk to avoid network
                                   usage
        @type use_cached_pkglist: boolean

        @returns: None or 2 if false
        """

        if my_version:
            spec = "%s==%s" % (self.project_name, my_version)
        else:
            spec = self.project_name

        if self.all_versions and my_version in self.all_versions:
            print_pkg_versions(self.project_name, [my_version])
        elif not my_version and self.all_versions:
            print_pkg_versions(self.project_name, self.all_versions)

    def parse_search_spec(self, spec):
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
            self.logger.error(usage)
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
            self.logger.error(usage)
            spec = operator = None
        return (spec, operator)


    def pypi_search(self, spec):
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

        (spec, operator) = self.parse_search_spec(spec)
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


    def validate_pypi_opts(self, opt_parser):
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
                self.logger.error(usage)
                return False
            else:
                return True
        return True


    def show_entry_map(self, dist):
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
            self.logger.error("Distribution not found: %s" % dist)
            return 2

    def show_entry_points(self, module):
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
            self.logger.error("No entry points found for %s" % module)
            return 2

    def parse_pkg_ver(self, package_spec, want_installed):
        """
        Return tuple with project_name and version from CLI args

        @param package_spec:
        @type package_spec:
        
        @param want_installed: whether package we want is installed or not
        @type want_installed: boolean

        @returns: tuple(project_name, version) 
        
        """
        all_versions = []

        arg_str = ("").join(package_spec)
        if "==" not in arg_str:

            #No version specified

            project_name = arg_str
            version = None
        else:
            (project_name, version) = arg_str.split("==")
            project_name = project_name.strip()
            version = version.strip()
        #Find proper case for package name
        if want_installed:
            dists = Distributions()
            project_name = dists.case_sensitive_name(project_name)
        else:
            pypi = CheeseShop()
            (project_name, all_versions) = \
                    pypi.query_versions_pypi(project_name, False)

            if not len(all_versions):
                self.logger.error("I'm afraid we have no %s at The Cheese Shop. \
                        \nPerhaps a little red Leicester?" % project_name)
                sys.exit(2)
        return (project_name, version, all_versions)

def setup_opt_parser():
    """
    Setup the optparser

    @returns: opt_parser.OptionParser
    
    """
    #pylint: disable-msg=C0301
    #line too long

    usage = "usage: %prog [options]"
    opt_parser = optparse.OptionParser(usage=usage)

    opt_parser.add_option("--version", action='store_true', dest=
                          "version", default=False, help=
                          "Show yolk version and exit.")

    opt_parser.add_option("-v", "--verbose", action='store_true', dest=
                          "verbose", default=False, help=
                          "Be more verbose.")
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
                          "file_type", default="all", help=
                          "You may specify 'source', 'egg', 'svn' or 'all' when using -D.")

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

def get_rss_feed():
    """
    Show last 20 package updates from PyPI RSS feed
    
    @returns: 0
    
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
    return 0

def print_pkg_versions(project_name, versions):
    """
    Print list of versions available for a package

    @returns: None

    """
    for ver in versions:
        print "%s %s" % (project_name, ver)

def main():
    """
    Let's do it.
    """
    my_yolk = Yolk()
    my_yolk.run()

if __name__ == "__main__":
    sys.exit(main())

