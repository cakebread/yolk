#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

yolk_acme

This is a plugin for acme, the package manager for Acme Linux.
It provides information for packages installed by Acme.

--acme used with -l, -a or -n will show you if the packages
were installed by Acme.


"""

__docformat__ = 'restructuredtext'

import os
from distutils.sysconfig import get_python_lib
from commands import getstatusoutput


class PackageManagerPlugin:

    """Class for finding pkgs installed by external package manager"""

    #This is the name of the external package manager
    #This will become a new yolk option: --acme
    name = "acme"

    enabled = False
    enable_opt = None

    def __init__(self):
        if self.name is None:
            self.name = self.__class__.__name__.lower()
        if self.enable_opt is None:
            self.enable_opt = "enable_plugin_%s" % self.name
            
    def add_options(self, parser):
        """Add plugin's options to yolk"""
        parser.add_option('--%s' % self.name, action='store_true', 
                dest=self.enable_opt,
                help="Show which packages are installed via the " +
                     " %s package manager. Use with -l" % self.name)

    def configure(self, options, conf):
        """Configure the plugin and system, based on selected options.

        The base plugin class sets the plugin to enabled if the enable option
        for the plugin (self.enableOpt) is true.
        """
        self.conf = conf
        if hasattr(options, self.enable_opt):
            self.enabled = getattr(options, self.enable_opt)

    def add_column(self, dist):
        """
        Add column of text to output of -l, -n or -a
        Text will be appended to normal output.
        e.g.
        normal output:
        java-config     - 2.0.31       - active
        
        Using plugin with add_column:
        java-config     - 2.0.31       - active YOUR EXTRA TEXT
        """
        return self.package_manager_owns(dist)

    def package_manager_owns(self, dist):
        """
        Returns True if package manager 'owns' file
        Returns False if package manager does not 'own' file

        There is currently no way to determine if distutils or
        setuptools installed a package. A future feature of setuptools
        will make a package manifest which can be checked.
           
        'filename' must be the full path to file

        """
        #Installed by distutils/setuptools or external package manager?
        #If location is in site-packages dir, check for .egg-info file
        if dist.location.lower() == get_python_lib().lower():
            filename = os.path.join(dist.location, dist.egg_name() + ".egg-info")
        else:
            filename = dist.location

        status, output = getstatusoutput("/usr/bin/acmefile -q %s" % filename)
        #status == 0 (file was installed by Acme)
        #status == 256 (file was not installed by Acme)
        if status == 0:
            return self.name
        else:
            return ""


