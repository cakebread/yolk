
'''

yolklib.py
==========

Desc: Library for getting information about Python packages installed by
      setuptools, package metadata, package dependencies, and querying
      The CheeseShop (PYPI) for Python package release information.


Author: Rob Cakebread <cakebread @ gmail>

License  : BSD (See COPYING)

'''

__docformat__ = 'restructuredtext'

import pkg_resources



class Distributions(object):

    """Helper class for pkg_resources"""

    def __init__(self):
        """init"""

        self.environment = pkg_resources.Environment()
        self.working_set = pkg_resources.WorkingSet()

    def query_activated(self, dist):
        """
        Return True if distribution is active
        Return Falsee if distribution is non-active

        @param dist: pkg_resources Distribution object

        @returns: True or False

        """
        if dist in self.working_set:
            return True
        else:
            return False

    def get_distributions(self, show, pkg_name="", version=""):
        """
        Yield installed packages

        @param show: Type of package(s) to show; active, non-active or all
        @type show: string: "active", "non-active", "all"

        @param pkg_name: PyPI project name
        @type pkg_name: string

        @param version: project's PyPI version
        @type version: string

        @returns: yields tuples of distribution and True or False depending
                  on active state. e.g. (dist, True)

        """
        #pylint: disable-msg=W0612
        #'name' is a placeholder for the sorted list
        for name, dist in self.get_alpha(show, pkg_name, version):
            ver = dist.version
            for package in self.environment[dist.project_name]:
                if ver == package.version:
                    if show == "nonactive" and dist not in self.working_set:
                        yield (dist, self.query_activated(dist))
                    elif show == "active" and dist in self.working_set:
                        yield (dist, self.query_activated(dist))
                    elif show == "all":
                        yield (dist, self.query_activated(dist))

    def get_alpha(self, show, pkg_name="", version=""):
        """
        Return list of alphabetized packages

        @param pkg_name: PyPI project name
        @type pkg_name: string

        @param version: project's PyPI version
        @type version: string

        @returns: Alphabetized list of tuples. Each tuple contains
                  a string and a pkg_resources Distribution object.
                  The string is the project name + version.

        """
        alpha_list = []
        for dist in self.get_packages(show):
            if pkg_name and dist.project_name != pkg_name:
                #Only checking for a single package name
                pass
            elif version and dist.version != version:
                #Only checking for a single version of a package
                pass
            else:
                alpha_list.append((dist.project_name + dist.version, dist))
        alpha_list.sort()
        return alpha_list

    def get_packages(self, show):
        """
        Return list of Distributions filtered by active status or all

        @param show: Type of package(s) to show; active, non-active or all
        @type show: string: "active", "non-active", "all"

        @returns: list of pkg_resources Distribution objects
        """


        if show == 'nonactive' or show == "all":
            all_packages = []
            for package in self.environment:
                #There may be multiple versions of same packages
                for i in range(len(self.environment[package])):
                    if self.environment[package][i]:
                        all_packages.append(self.environment[package][i])
            return all_packages
        else:
            # Only activated packages
            return self.working_set

    def case_sensitive_name(self, package_name):
        """
        Return case-sensitive package name given any-case package name

        @param project_name: PyPI project name
        @type project_name: string

        """
        if len(self.environment[package_name]):
            return self.environment[package_name][0].project_name

    def get_highest_installed(self, project_name):
        """
        Return highest version of installed package

        @param project_name: PyPI project name
        @type project_name: string

        @return: string of highest installed version

        """
        return self.environment[project_name][0].version


def get_highest_version(versions):
    """
    Returns highest available version for a package in a list of versions
    Uses pkg_resources to parse the versions

    @param versions: List of PyPI package versions
    @type versions: List of strings

    @returns: string of a PyPI package version


    """
    sorted_versions = []
    for ver in versions:
        sorted_versions.append((pkg_resources.parse_version(ver), ver))

    sorted_versions = sorted(sorted_versions)
    sorted_versions.reverse()
    return sorted_versions[0][1]

