

'''

Name: yolklib.py

Desc: Library for getting information about Python packages installed by
      setuptools, package metadata, package dependencies, and querying
      The CheeseShop (PYPI) for Python package release information.


Author: Rob Cakebread <gentoodev a t gmail.com>

License  : PSF (Python Software Foundation License)

'''

import pkg_resources



class Distributions:

    def __init__(self):

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
            for p in self.environment[dist.project_name]:
                if ver == p.version:
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

