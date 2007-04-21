

# pylint: disable-msg=C0301,W0613,W0612

'''

yolklib.py
==========

Desc: Library for getting information about Python packages installed by
      setuptools, package metadata, package dependencies, and querying
      The CheeseShop (PYPI) for Python package release information.


Author: Rob Cakebread <gentoodev a t gmail.com>

License  : GNU General Public License Version 2

'''

__docformat__ = 'restructuredtext'

import pkg_resources



class Distributions:

    """Helper class for pkg_resources"""

    def __init__(self):
        """init"""

        self.environment = pkg_resources.Environment()
        self.working_set = pkg_resources.WorkingSet()

    def query_activated(self, dist):
        """Return True if distribution is active"""
        if dist in self.working_set:
            return True

    def get_distributions(self, show, pkg_name="", version=""):
        """List installed packages"""
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
        """Return list of alphabetized packages"""
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
        """Return list of Distributions"""

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
        """Return case-sensitive package name given any-case package name"""
        if len(self.environment[package_name]):
            return self.environment[package_name][0].project_name
        else:
            return


def get_highest_installed(project_name):
    """Return highest version of installed package"""
    return pkg_resources.require(project_name)[0].version


def get_highest_version(versions):
    """Given list of versions returns highest available version for a package"""
    #Used to sort versions returned from PyPI
    sorted_versions = []
    for ver in versions:
        sorted_versions.append((pkg_resources.parse_version(ver), ver))

    sorted_versions.reverse()
    return sorted_versions[0][1]

