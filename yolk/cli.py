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
from xmlrpclib import Fault as XMLRPCFault
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

        #Squelch output from setuptools
        #Add future offenders to this list.
        shut_up = ['distutils.log']
        sys.stdout = StdOut(sys.stdout, shut_up)
        sys.stderr = StdOut(sys.stderr, shut_up)
        self.pypi = None

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

    def set_log_level(self):
        """
        Set log level according to command-line options

        @returns: logger object
        """

        if self.options.debug:
            self.logger.setLevel(logging.DEBUG)
        elif self.options.quiet:
            self.logger.setLevel(logging.ERROR)
        else:
            self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler())
        return self.logger

    def run(self):
        """
        Perform actions based on CLI options
        
        @returns: status code
        """
        opt_parser = setup_opt_parser()
        (self.options, remaining_args) = opt_parser.parse_args()
        logger = self.set_log_level()

        pkg_spec = validate_pypi_opts(opt_parser)
        if not pkg_spec:
            pkg_spec = remaining_args
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
        if self.options.depends or self.options.all or \
                self.options.active or self.options.nonactive  or \
                (self.options.show_updates and pkg_spec):
            want_installed = True
        else:
            want_installed = False
        if not want_installed or self.options.show_updates:
            self.pypi = CheeseShop(self.options.debug)
            #XXX: We should return 2 here if we couldn't create xmlrpc server
        if pkg_spec:
            (self.project_name, self.version, self.all_versions) = \
                    self.parse_pkg_ver(pkg_spec, want_installed)
            if want_installed and not self.project_name:
                logger.error("%s is not installed." % pkg_spec[0])
                return 2

        if self.options.search:
            status = self.pypi_search(pkg_spec)
        elif self.options.changelog:
            status = self.show_pypi_changelog(self.options.changelog)
        elif self.options.releases:
            status = self.show_pypi_releases(self.options.releases)
        elif self.options.fetch:
            directory = "."
            status = self.fetch(directory)
        elif self.options.version:
            print "yolk version %s (rev. %s)" % (VERSION, __revision__)
            status = 0
        elif self.options.depends:
            status = self.show_deps()
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
            status = self.get_all_versions_pypi()
        elif self.options.browse_website:
            status = self.browse_website()
        elif self.options.download_links:
            status = self.show_download_links()
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
        dists = Distributions()
        if self.project_name:
            #Check for a single package
            pkg_list = [self.project_name]
        else:
            #Check for every installed package
            pkg_list = get_pkglist()
        found = None
        for pkg in pkg_list:
            for (dist, active) in dists.get_distributions("all", pkg,
                    dists.get_highest_installed(pkg)):
                (project_name, versions) = \
                        self.pypi.query_versions_pypi(dist.project_name)
                if versions:

                    #PyPI returns them in chronological order,
                    #but who knows if its guaranteed in the API?
                    #Make sure we grab the highest version:

                    newest = get_highest_version(versions)
                    if newest != dist.version:

                        #We may have newer than what PyPI knows about

                        if pkg_resources.parse_version(dist.version) < \
                            pkg_resources.parse_version(newest):
                            found = True
                            print " %s %s (%s)" % (project_name, dist.version,
                                    newest)
        if not found:
            self.logger.info("You have the latest version.")
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

    def show_deps(self):
        """
        Show dependencies for package(s)

        @param pkg_ver: setuptools pkgspec (e.g. kid>=0.8)
        @type pkg_ver: string
        
        @returns: None or 2 if error 
        """

        pkgs = pkg_resources.Environment()

        for pkg in pkgs[self.project_name]:
            if not self.version:
                print pkg.project_name, pkg.version

            i = len(pkg._dep_map.values()[0])
            if i:
                while i:
                    if not self.version or self.version and \
                            pkg.version == self.version:
                        if self.version and i == len(pkg._dep_map.values()[0]):
                            print pkg.project_name, pkg.version
                        print "  " + str(pkg._dep_map.values()[0][i - 1])
                    i -= 1
            else:
                self.logger.info(\
                    "No dependency information was supplied with the package.")
        return 0

    def show_pypi_changelog(self, hours):
        """
        Show detailed PyPI ChangeLog for the last `hours`

        @param hours: Number of `hours` to check back
        @type hours: string

        @returns: 1 if failed to retrieve from XML-RPC server

        """
        try:
            changelog = self.pypi.changelog(int(hours))
        except XMLRPCFault, err_msg:
            self.logger.error(err_msg)
            self.logger.error("ERROR: Couldn't retrieve changelog.")
            return 1

        last_pkg = ''
        for entry in changelog:
            pkg = entry[0]
            if pkg != last_pkg:
                print "%s %s\n\t%s" % (entry[0], entry[1], entry[3])
                last_pkg = pkg
            else:
                print "\t%s" % entry[3]
         
        return 0

    def show_pypi_releases(self, hours):
        """
        Show PyPI releases for last the `hours`

        @param hours: Number of `hours` to check back
        @type hours: string

        @returns: 1 if failed to retrieve from XML-RPC server

        """
        try:
            latest_releases = self.pypi.updated_releases(int(hours))
        except XMLRPCFault, err_msg:
            self.logger.error(err_msg)
            self.logger.error("ERROR: Couldn't retrieve latest releases.")
            return 1

        for release in latest_releases:
            print "%s %s" % (release[0], release[1])
        return 0

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
                version = self.all_versions[0]
        if self.options.file_type == "all":
            #Search for source, egg, and svn
            self.print_download_uri(version, True)
            self.print_download_uri(version, False)
            self.print_download_uri("dev", True, True)
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
        if svn or version == "dev":
            pkg_type = "subversion"
            source = True
        elif source:
            pkg_type = "source"
        else:
            pkg_type = "egg"

        #Use setuptools monkey-patch to grab url
        url = get_download_uri(self.project_name, version, source)
        if url:
            print "%s" % url
        else:
            self.logger.info("No download URL found for %s" % pkg_type)

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
                    "dev", True)
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

        uri = get_download_uri(self.project_name, self.version, source)
        if uri:
            self.fetch_uri(directory, uri)
        else:
            self.logger.error("No %s URI found for package: %s " % \
                    (self.options.file_type, self.project_name))
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
        self.logger.info("Doing subversion checkout for %s" % svn_uri)
        status, output = run_command("/usr/bin/svn co %s" % svn_uri)
        self.logger.info(output)
        os.chdir(cwd)
        self.logger.info("subversion checkout is in directory './%s'" \
                % directory)

    def browse_website(self, browser=None):
        """
        Launch web browser at project's homepage

        @returns None
        """
        if len(self.all_versions):
            metadata = self.pypi.release_data(self.project_name, \
                    self.all_versions[0])
            self.logger.debug("DEBUG: browser: %s" % browser)
            if metadata.has_key("home_page"):
                self.logger.info("Launching browser: %s" \
                        % metadata["home_page"])
                if browser == 'konqueror':
                    browser = webbrowser.Konqueror()
                else:
                    browser = webbrowser.get()
                    browser.open(metadata["home_page"], 2)
                return

        self.logger.error("No homepage URL found.")


    def show_pkg_metadata_pypi(self):
        """
        Show pkg metadata queried from PyPI

        @returns: None or 2 if error 
        
        """
        if self.version and self.version in self.all_versions:
            metadata = self.pypi.release_data(self.project_name, self.version)
        else:
            #Give highest version
            metadata = self.pypi.release_data(self.project_name, \
                    self.all_versions[0])

        if metadata:
            for key in metadata.keys():
                if not self.options.fields or (self.options.fields and \
                        self.options.fields==key):
                    print "%s: %s" % (key, metadata[key])
        return 0

    def get_all_versions_pypi(self):
        """
        Query PyPI for a particular version or all versions of a package

        @returns: 0 if version(s) found or 1 if none found
        """

        if self.version:
            spec = "%s==%s" % (self.project_name, self.version)
        else:
            spec = self.project_name

        if self.all_versions and self.version in self.all_versions:
            print_pkg_versions(self.project_name, [self.version])
            return 0
        elif not self.version and self.all_versions:
            print_pkg_versions(self.project_name, self.all_versions)
            return 0
        else:
            if self.version:
                self.logger.error("No pacakge found for version %s" \
                        % self.version)
            else:
                self.logger.error("No pacakge found for %s" % self.project_name)
            return 1

    def parse_search_spec(self, spec):
        """
        Parse search args and return spec dict for PyPI
        * Owwww, my eyes!. Re-write this.

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
       
        spec examples:
          ["name=yolk"]
          ["license=GPL"]
          ["name=yolk", "AND", "license=GPL"]

        @returns: None


        """
        #Add remainging cli arguments to options.search
        search_arg = self.options.search
        spec.insert(0, search_arg.strip())

        (spec, operator) = self.parse_search_spec(spec)
        if not spec:
            return 2
        for pkg in self.pypi.search(spec, operator):
            if pkg['summary']:
                summary = pkg['summary'].encode('utf-8')
            else:
                summary = ""
            print """%s (%s):
        %s
    """ % (pkg['name'].encode('utf-8'), pkg["version"],
                    summary)


    def show_entry_map(self):
        """
        Show entry map for a package
        
        @param dist: package
        @param type: srting
        
        @returns: None or 2 if error
        """
        pprinter = pprint.PrettyPrinter()
        try:
            pprinter.pprint(pkg_resources.get_entry_map(self.options.entry_map))
            return 0
        except pkg_resources.DistributionNotFound:
            self.logger.error("Distribution not found: %s" \
                    % self.options.entry_map)
            return 2

    def show_entry_points(self):
        """
        Show entry points for a module
        
        @returns: None or 2 if error
        
        """
        found = False
        for entry_point in \
                pkg_resources.iter_entry_points(self.options.entry_points):
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
            self.logger.error("No entry points found for %s" \
                    % self.options.entry_points)
            return 2

    def parse_pkg_ver(self, package_spec, want_installed):
        """
        Return tuple with project_name and version from CLI args
        If the user gave the wrong case for the project name, this corrects it

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
            (project_name, all_versions) = \
                    self.pypi.query_versions_pypi(project_name)

            if not len(all_versions):
                self.logger.error("I'm afraid we have no %s at The Cheese Shop. Perhaps a little Red Leicester?" % project_name)
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

    opt_parser.add_option("--debug", action='store_true', dest=
                          "debug", default=False, help=
                          "Show debugging information.")

    opt_parser.add_option("-q", "--quiet", action='store_true', dest=
                          "quiet", default=False, help=
                          "Show less output.")
    group_local = optparse.OptionGroup(opt_parser,
            "Query installed Python packages",
            "The following options show information about installed Python packages. Activated packages are normal packages on sys.path that can be imported. Non-activated packages need 'pkg_resources.require()' before they can be imported, such as packages installed with 'easy_install --multi-version'. PKG_SPEC can be either a package name or package name and version e.g. Paste==0.9")

    group_local.add_option("-l", "--list", action='store_true', dest=
                           "all", default=False, help=
                           "List all Python packages installed by distutils or setuptools. Use PKG_SPEC to narrow results.")

    group_local.add_option("-a", "--activated", action='store_true',
                           dest="active", default=False, help=
                           'List activated packages installed by distutils or ' +
                           'setuptools. Use PKG_SPEC to narrow results.')

    group_local.add_option("-n", "--non-activated", action='store_true',
                           dest="nonactive", default=False, help=
                           'List non-activated packages installed by distutils or ' +
                           'setuptools. Use PKG_SPEC to narrow results.')

    group_local.add_option("-m", "--metadata", action='store_true', dest=
                           "metadata", default=False, help=
                           'Show all metadata for packages installed by ' +
                           'setuptools (use with -l -a or -n)')

    group_local.add_option("-f", "--fields", action="store", dest=
                           "fields", default=False, help=
                           'Show specific metadata fields. ' +
                           '(use with -m or -M)')

    group_local.add_option("-d", "--depends", action='store', dest=
                           "depends", metavar='PKG_SPEC',
                           help= "Show dependencies for a package installed by " +
                           "setuptools if they are available.")

    group_local.add_option("--entry-points", action='store',
                           dest="entry_points", default=False, help=
                           'List entry points for a module. e.g. --entry-points nose.plugins',
                            metavar="MODULE")

    group_local.add_option("--entry-map", action='store',
                           dest="entry_map", default=False, help=
                           'List entry map for a package. e.g. --entry-map yolk',
                           metavar="PACKAGE_NAME")
    group_pypi = optparse.OptionGroup(opt_parser,
            "PyPI (Cheese Shop) options",
            "The following options query the Python Package Index:")

    group_pypi.add_option("-C", "--changelog", action='store',
                          dest="changelog", metavar='HOURS',
                          default=False, help=
                          "Show detailed ChangeLog for PyPI for last n hours. ")

    group_pypi.add_option("-D", "--download-links", action='store',
                          metavar="PKG_SPEC", dest="download_links",
                          default=False, help=
                          "Show download URL's for package listed on PyPI. Use with -T to specify egg, source etc.")

    group_pypi.add_option("-F", "--fetch-package", action='store',
                          metavar="PKG_SPEC", dest="fetch",
                          default=False, help=
                          "Download package source or egg. You can specify a file type with -T")

    group_pypi.add_option("-H", "--browse-homepage", action='store',
                          metavar="PKG_SPEC", dest="browse_website",
                          default=False, help=
                          "Launch web browser at home page for package.")

    group_pypi.add_option("-L", "--latest-releases", action='store',
                          dest="releases", metavar="HOURS",
                          default=False, help=
                          "Show PyPI releases for last n hours. ")

    group_pypi.add_option("-M", "--query-metadata", action='store',
                          dest="query_metadata_pypi", default=False,
                          metavar="PKG_SPEC", help=
                          "Show metadata for a package listed on PyPI. Use -f to show particular fields.")

    group_pypi.add_option("-S", "", action="store", dest="search",
                          default=False, help=
                          "Search PyPI by spec and optional AND/OR operator.",
                          metavar='SEARCH_SPEC <AND/OR SEARCH_SPEC>')

    group_pypi.add_option("-T", "--file-type", action="store", dest=
                          "file_type", default="all", help=
                          "You may specify 'source', 'egg', 'svn' or 'all' when using -D.")

    group_pypi.add_option("-U", "--show-updates", action='store_true',
                          dest="show_updates", metavar='<PKG_NAME>',
                          default=False, help= 
                          "Check PyPI for updates on package(s).")

    group_pypi.add_option("-V", "--versions-available", action=
                          'store', dest="versions_available",
                          default=False, metavar='PKG_SPEC',
                          help="Show available versions for given package " +
                          "listed on PyPI.")
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

def print_pkg_versions(project_name, versions):
    """
    Print list of versions available for a package

    @returns: None

    """
    for ver in versions:
        print "%s %s" % (project_name, ver)

def validate_pypi_opts(opt_parser):
    """
    Check parse options that require pkg_spec

    @returns: pkg_spec
    
    """

    (options, remaining_args) = opt_parser.parse_args()
    options_pkg_specs = [ options.versions_available, 
            options.query_metadata_pypi,
            options.download_links,
            options.browse_website,
            options.fetch,
            options.depends,
            ]
    for pkg_spec in options_pkg_specs:
        if pkg_spec:
            return pkg_spec


def main():
    """
    Let's do it.
    """
    my_yolk = Yolk()
    my_yolk.run()

if __name__ == "__main__":
    sys.exit(main())

