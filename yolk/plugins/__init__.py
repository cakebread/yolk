
# pylint: disable-msg=W0142,C0103

"""Writing Plugins
---------------

yolk supports setuptools_ entry point plugins.

There are two basic rules for plugins:

 * Plugin classes should subclass `yolk.plugins.Plugin`_.
 * Plugins may implement any of the methods described in the class
   PluginInterface in yolk.plugins.base. Please note that this class is for
   documentary purposes only; plugins may not subclass PluginInterface.

.. _setuptools: http://peak.telecommunity.com/DevCenter/setuptools
.. _yolk.plugins.Plugin: http://tools.assembla.com/yolk
   
Registering
===========

For yolk to find a plugin, it must be part of a package that uses
setuptools, and the plugin must be included in the entry points defined
in the setup.py for the package::

  setup(name='Some plugin',
        ...
        entry_points = {
            'yolk.plugins': [
                'someplugin = someplugin:SomePlugin'
                ]
            },
        ...
        )

Once the package is installed with install or develop, yolk will be able
to load the plugin.

Defining options
================

All plugins must implement the methods ``add_options(self, parser, env)``
and ``configure(self, options, conf)``. Subclasses of yolk.plugins.Plugin
that want the standard options should call the superclass methods.

yolk uses optparse.OptionParser from the standard library to parse
arguments. A plugin's ``add_options()`` method receives a parser
instance. It's good form for a plugin to use that instance only to add
additional arguments that take only long arguments (--like-this). Most
of yolk's built-in arguments get their default value from an environment
variable. This is a good practice because it allows options to be
utilized when run through some other means than the yolktests script.

A plugin's ``configure()`` method receives the parsed ``OptionParser`` options 
object, as well as the current config object. Plugins should configure their
behavior based on the user-selected settings, and may raise exceptions
if the configured behavior is nonsensical.

Logging
=======

yolk uses the logging classes from the standard library. To enable users
to view debug messages easily, plugins should use ``logging.getLogger()`` to
acquire a logger in the ``yolk.plugins`` namespace.

"""

import logging
import pkg_resources
from warnings import warn
from yolk.plugins.base import Plugin

#LOG = logging.getLogger(__name__)

def call_plugins(plugins, method, *arg, **kw):
    """Call all method on plugins in list, that define it, with provided
    arguments. The first response that is not None is returned.
    """
    for plug in plugins:
        func = getattr(plug, method, None)
        if func is None:
            continue
        #LOG.debug("call plugin %s: %s", plug.name, method)
        result = func(*arg, **kw)
        if result is not None:
            return result
    return None
        
def load_plugins(builtin=True, others=True):
    """Load plugins, either builtin, others, or both.
    """
    for entry_point in pkg_resources.iter_entry_points('yolk.plugins'):
        #LOG.debug("load plugin %s" % entry_point)
        try:
            plugin = entry_point.load()
        except KeyboardInterrupt:
            raise
        except Exception, err_msg:
            # never want a plugin load to exit yolk
            # but we can't log here because the logger is not yet
            # configured
            warn("Unable to load plugin %s: %s" % \
                    (entry_point, err_msg), RuntimeWarning)
            continue
        if plugin.__module__.startswith('yolk.plugins'):
            if builtin:
                yield plugin
        elif others:
            yield plugin

