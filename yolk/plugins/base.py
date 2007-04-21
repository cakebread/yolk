
# pylint: disable-msg=W0201,W0511
#XXX Attribute 'conf' defined outside __init__

"""

Base plugin class
This is not needed yet, see working plugins in examples directory.

"""


import textwrap

class Plugin(object):
    """Base class for yolk plugins. It's not necessary to subclass this
    class to create a plugin; however, all plugins must implement
    `add_options(self, parser)` and `configure(self, options,
    conf)`, and must have the attributes `enabled` and `name`.

    Plugins should not be enabled by default.

    Subclassing Plugin will give your plugin some friendly default
    behavior:

      * A --with-$name option will be added to the command line
        interface to enable the plugin. The plugin class's docstring
        will be used as the help for this option.
      * The plugin will not be enabled unless this option is selected by
        the user.    
    """
    enabled = False
    enable_opt = None
    name = None

    def __init__(self):
        if self.name is None:
            self.name = self.__class__.__name__.lower()
        if self.enable_opt is None:
            self.enable_opt = "enable_plugin_%s" % self.name
            
    def add_options(self, parser):
        """Add command-line options for this plugin.

        The base plugin class adds --with-$name by default, used to enable the
        plugin. 
        """
        parser.add_option("--with-%s" % self.name,
                          action="store_true",
                          dest=self.enable_opt,
                          help="Enable plugin %s: %s" %
                          (self.__class__.__name__, self.help())
                          )

    def configure(self, options, conf):
        """Configure the plugin and system, based on selected options.

        The base plugin class sets the plugin to enabled if the enable option
        for the plugin (self.enable_opt) is true.
        """
        self.conf = conf
        if hasattr(options, self.enable_opt):
            self.enabled = getattr(options, self.enable_opt)

    def help(self):
        """Return help for this plugin. This will be output as the help
        section of the --with-$name option that enables the plugin.
        """
        if self.__class__.__doc__:
            # doc sections are often indented; compress the spaces
            return textwrap.dedent(self.__class__.__doc__)
        return "(no help available)"


