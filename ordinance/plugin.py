from typing import Dict, List, Optional, Any

import ordinance.writer
import ordinance.network   # load this now so plugins can use it
import ordinance.schedule  # load this now so plugins can use it
import ordinance.database  # load this now so plugins can use it

class OrdinancePlugin:
    """ The base class that all plugins must inherit from. """
    def __init__(self, config: Dict[str, Any]):
        # this init function is meant to be overridden. if not needed, then by
        # default, just output that this plugin has been inited.
        ordinance.writer.info(f"{self.name}: Initialized.")


    # the following functions use variables defined during plugin preinit, so
    # the type checker might complain.


    # metadata functions
    
    # note that this defines both <plugin>.metavar and <plugin>.get_metavar()
    # forms, for better interop with developer styles/preferences. both forms
    # function the same, and return the same information. they are, for all
    # intents and purposes, indentical.
    # also note that metadata is filled in during plugin preinit; see the
    # core.plugins_interface module for how this works. From a plugin's
    # perspective, this metadata is present as a class variable by the time
    # __init__ is called.

    @property
    def qname(self) -> str:
        """ Returns the qname for this plugin. """
        return self.__class__.__qname__
    def get_qname(self) -> str:
        """ Returns the qname for this plugin. """
        return self.qname
    
    @property
    def name(self) -> str:
        """ Returns the name of this plugin, as defined in the `plugins.yaml` file. Returns the qname of this plugin if name is not defined. """
        return self.__class__.__metadata__.get('name', self.__qname__)
    def get_name(self) -> str:
        """ Returns the name of this plugin, as defined in the `plugins.yaml` file. Returns the qname of this plugin if name is not defined. """
        return self.name
    
    @property
    def author(self) -> str:
        """ Returns the author of this plugin, as defined in the `plugins.yaml` file. Returns :const:`None` if not defined. """
        return self.__class__.__metadata__.get('author', None)
    def get_author(self) -> str:
        """ Returns the author of this plugin, as defined in the `plugins.yaml` file. Returns :const:`None` if not defined. """
        return self.author
    
    @property
    def description(self) -> str:
        """ Returns the description of this plugin, as defined in the `plugins.yaml` file. Returns :const:`None` if not defined. """
        return self.__class__.__metadata__.get('description', None)
    def get_description(self) -> str:
        """ Returns the description of this plugin, as defined in the `plugins.yaml` file. Returns :const:`None` if not defined. """
        return self.description
    
    @property
    def version(self) -> str:
        """ Returns the version of this plugin, as defined in the `plugins.yaml` file. Returns :const:`None` if not defined. """
        return self.__class__.__metadata__.get('version', None)
    def get_version(self) -> str:
        """ Returns the version of this plugin, as defined in the `plugins.yaml` file. Returns :const:`None` if not defined. """
        return self.version

    

    # def fire_command(self, command: str, args: List[str]) -> None:
    #     """ Fires a command attached to this plugin. """
    #     if command not in self.__ordinance_commands:
    #         raise Exception() #TODO
    #     raise NotImplementedError()


    # def get_local_path(self, filename: Optional[str] = None):
    #     """
    #     Returns the path to a given file :attr:`filename` in the plugin folder.
    #     If :attr:`filename` is blank, returns the path to the plugin folder.\n
    #     This function is useful for, say, local static databases; for example,
    #     a file containing a list of known configuration vulnerabilities, that
    #     won't need to change.\n
    #     For databases that DO need to change and other file-based storage
    #     mediums, see :class:`ordinance.database` and its associated classes.
    #     """
    #     #path = os.path.dirname(os.path.abspath(__file__))
    #     #if filename: path = os.path.join(path, filename)
    #     #return path
    #     raise NotImplementedError()
