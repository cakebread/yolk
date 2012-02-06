yolk 0.4.2
==========

.. contents::

Installation
------------

You can install yolk with ``pip install yolk`` or via your distro's package manager, if available.

As of 0.0.7 yolk is in Gentoo's Portage tree as dev-python/yolk and a plugin for Portage named dev-python/yolk-portage. The portage plugin shows you which Python packages were installed via Portage and which were installed directly with pip (or easy_install). Check out that plugin and make one for your favorite distro. It's a great way to find Python cruft.


Summary
-------

Yolk is a Python tool for obtaining information about installed Python packages and querying packages avilable on PyPI (Python Package Index). 

You can see which packages are active, non-active or in development mode and show you which have newer versions available by querying PyPI. 

Usage Examples::

    $ yolk -l
         List all installed Python packages

    $ yolk -a 
         List only the activated packages installed (Activated packages are normal packages on sys.path you can import) 

    $ yolk -n 
         List only the non-activated (--multi-version) packages installed 
         
    $ yolk -l -f License,Author nose==1.0
         Show the license and author for version 1.0 of the package `nose`

    $ yolk --entry-map nose
         Show entry map for the nose package

    $ yolk --entry-points nose.plugins
         Show all setuptools entry points for nose.plugins


These options query PyPI::

    $ yolk -U pkg_name
         Shows if an update for pkg_name is available by querying PyPI

    $ yolk -U
         Checks PyPI to see if any installed Python packages have updates available.

    $ yolk -F Paste
         Download source tarball for latest version of Paste to your current directory

    $ yolk -F Paste -T svn
         Do a subversion checkout for Paste to a directory named Paste_svn in your current directory.

    $ yolk -L 2
         Show list of CheeseShop releases in the last two hours

    $ yolk -C 2
         Show detailed list of changes in the CheeseShop in the last two hours

    $ yolk -M Paste==1.0 
         Show all the metadata for Paste version 1.0 

    $ yolk -M Paste 
         Show all the metadata for the latest version of Paste listed on PyPi

    $ yolk -D cheesecake 
         Show all (source, egg, svn) URL's for the latest version of cheesecake packages

     $ yolk -T source -D cheesecake 
         Show only source code releases for cheesecake 

     $ yolk -H twisted 
         Launches your web browser at Twisted's home page 


Tips and Tricks
---------------

 * Use yolk inside your virtualenv to see which packages are installed.

 * Upgrade all installed Python packages:


  {{{Warning: You only want to do this inside a virtualenv. If you're using Linux, use your package manager to install Python packages globally whenever possible.

     $ pip install -U `yolk -U | awk '{print $1}'`
}}}


Changes
-------
**0.4.2**: Fix for -C when an integer isn't supplied
           
           Fix for --entry-map from Jesus Rivero (Neurogeek) neurogeek@gentoo.org. Thanks, Jesus!
		
		   Switch to BSD license from GPL-2


**0.4.1**: Fix for -f fields
           
           Add check for integer with -L


**0.4.0**: Added http proxy support for XML-RPC
            
           Added case-insensitive search for -f

           Non-existent packages with -S no longer show entire index (bug was with PyPI)

           Fixed exception when package has no metadata


**0.3.0**: Added -C and -L options for new PyPI XML-RPC methods `changelog` and `updated_releases`

           Always check package name cache on disk before querying PyPi to see if a package exists and has proper case.

           Added -F option to download source, egg or subversion checkouts.

           Removed -L RSS feed option because the new `updated_releases` XML-RPC method is much nicer

           Fixed '-D -T egg' so it won't return source if no egg is available

           Major refactoring.

           Removed dependency on elementtree 

           
**0.2.0**: Added 'svn' type for -T

           A kablillion bug fixes


**0.1.0**: You can now use -f with -M

           More accurate URL's with -D using pip

           Ability to check for a single package with -U

           Uses std Python logging module

           Fixed bug so we have correct exit codes


**0.0.7**: New options: --entry-map and -entry-points
           
           Improved results with --download-links

           New plugin system. First plugin available: yolk-portage
           for Gentoo Linux.

           -v option is now --version

           -v is now a new option: --verbose

           Many bug fixes.


**0.0.6**: Fix Windows problem which showed all pkgs in develop mode
           on some systems.

           Fix bad interpreter shebang in rss_feed.py example

           Start using nose unit tests from setup.py

           Use restructuredtext in docstrings


**0.0.5**: Show packages installed in 'development' mode.

           Improved output of -l, -n and -a. You can get the previous (<=0.0.4)
           output by adding '-f Summary'

           More sanity checking for various options.

           Don't throw exception if there is no package metadata


**0.0.4**: Added -U option to query PyPI for new versions of packages you have 
           installed

Requirements
------------

* setuptools (Distribute preferred)

* elementtree (For RSS feed option extra_requires [RSS]) (included in Python >=2.5)

