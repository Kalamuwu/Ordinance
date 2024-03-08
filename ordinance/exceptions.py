# 
# ordinance/exceptions.py
# 
# the Ordinance exception tree, grouped by parent via 80-wide dash comments 
# 

import traceback
from typing import Coroutine


class OrdinanceError(Exception):
    """ Any exception that stems from Ordinance. """
    def __init__(self, message: str, e: Exception = None):
        if e is not None:
            before = f" {str(type(e))[8:-2]}"
            tb = traceback.format_exc()
            super().__init__(f"{before}\n{message}{tb}\n")
        else: super().__init__(str(message))

class NotRootException(Exception):
    """ Ordinance must be run as root. """
    def __init__(self):
        super().__init__("[!] Ordinance must be run as root.")

# -----------------------------------------------------------------------------

class ConfigError(OrdinanceError):
    """ Base class for configuration errors. """

class ConfigNotFound(ConfigError):
    """ Configuration file could not be found."""
    def __init__(self, config_path: str):
        super().__init__(f"Config {config_path} could not be found!")

class ConfigManagerNotInitialized:
    """ Configuration manager has not been initialized with the config. """
    def __init__(self):
        super().__init__("ConfigManager has not yet been initialized!")

class ConfigSyntaxError(ConfigError):
    """ Configuration file could not be parsed. """
    def __init__(self, config_path: str, e: Exception):
        super().__init__(f"Could not parse config {config_path}, with exception:", e)

class UnknownConfigKey(ConfigError):
    """ Parser found a configuration key that does not belong to Ordinance or any plugins. """

class InvalidConfigValue(ConfigError):
    """ Parser found an invalid configuration value. """

class RequiredConfigKeyNotFound(ConfigError):
    """ A configuration variable marked as required was not found in the configuration file. """

class ConfigKeyAlreadyExists(ConfigError):
    """ Could not add this configuration key, because it already exists. """

# -----------------------------------------------------------------------------

class PluginError(OrdinanceError):
    """ Base class for plugin errors. """

class PluginNotFound(PluginError):
    """ Requested plugin could not be found. """
    def __init__(self, plugin_name: str):
        super().__init__(f"Plugin {plugin_name} count not be found!")

class PluginNotLoaded(PluginError):
    """ Requested plugin has not yet been loaded. """
    def __init__(self, plugin_name: str):
        super().__init__(f"Plugin {plugin_name} not yet loaded!")

class PluginAlreadyLoaded(PluginError):
    """ Attempted to load a plugin that is already loaded. """
    def __init__(self, plugin_name: str):
        super().__init__(f"Plugin {plugin_name} already loaded!")

class PluginRunning(PluginError):
    """ Attempted to do some action to a running plugin that can only be done once the plugin is stopped. """
    def __init__(self, plugin_name: str):
        super().__init__(f"Plugin {plugin_name} is running! Plugin must be stopped before doing this!")

class PluginLoadingFailed(PluginError):
    """ Base class for errors while attempting to load a plugin. """

class PluginInvalid(PluginLoadingFailed):
    """ Plugin folder or structure is invalid. """

class PluginNoDefinedEntryPointError(PluginLoadingFailed):
    """ No entry point could be found in this plugin's plugin.yaml file. """
    def __init__(self, plugin_name: str):
        super().__init__(f"No entry class defined for plugin {plugin_name}!")

class PluginEntryPointNotFoundError(PluginLoadingFailed):
    """ Entry point defined in this plugin's plugin.yaml file could not be found. """
    def __init__(self, plugin_name: str, entry_file_name: str):
        super().__init__(f"No function 'setup' could be found in file {entry_file_name} for plugin {plugin_name}!")

# -----------------------------------------------------------------------------

class SchedulerError(OrdinanceError):
    """ Base class for scheduler errors. """

class CouldNotRunScheduledFunc(SchedulerError):
    """ Could not run the scheduled function. """
    def __init__(self, name: str):
        super().__init__(f"Could not run scheduled function {name}")

class CouldNotRunEventFunc(SchedulerError):
    """ Could not run the event function. """
    def __init__(self, name: str):
        super().__init__(f"Could not run event function {name}")

class NotAnOrdinanceCoro(SchedulerError):
    """ Given function is not registered as a scheduled or event function. """
    def __init__(self, func_name: str):
        super().__init__(f"Callable with name {func_name} is not an OrdinanceFunc.")

# -----------------------------------------------------------------------------

class WriterException(OrdinanceError):
    """ Base class for writer errors. """

class WriterNotInitialized(WriterException):
    """ Global writer isn't initialized yet. """
    def __init__(self):
        super().__init__(f"Global writer hasn't been initialized yet!")

class WriterNotFound(WriterException):
    """ Writer type given not known. """
    def __init__(self, writer_name: str):
        super().__init__(f"Unknown writer type {writer_name}")

class WriterAlreadyEnabled(WriterException):
    """ Tried to enable a writer that was already enabled. """
    def __init__(self, writer_name: str):
        super().__init__(f"Writer {writer_name} is already enabled!")

class WriterAlreadyDisabled(WriterException):
    """ Tried to disable a writer that was already disabled. """
    def __init__(self, writer_name: str):
        super().__init__(f"Writer {writer_name} is already disabled!")

# -----------------------------------------------------------------------------

class NetworkException(OrdinanceError):
    """ Base class for network errors. """

class IPInvalid(NetworkException):
    """ IP given is not a valid IP. """
    def __init__(self, ip: str):
        super().__init__(f"Given IP '{ip}' is not a valid IP!")

class CantBanIP(NetworkException):
    """ Couldn't ban specified IP. """
    def __init__(self, ip: str, e: Exception):
        super().__init__(f"Couldn't ban IP {ip}", e=e)

class IPWhitelisted(NetworkException):
    """ Tried to blacklist a whitelisted IP. """
    def __init__(self, ip: str):
        super().__init__(f"Tried to blacklist a whitelisted IP {ip}")

class IPBlacklisted(NetworkException):
    """ Tried to whitelist a blacklisted IP. """
    def __init__(self, ip: str):
        super().__init__(f"Tried to whitelist a blacklisted IP {ip}")

class IPNotBlacklisted(NetworkException):
    """ Tried to un-blacklist a not blacklisted IP. """
    def __init__(self, ip: str):
        super().__init__(f"Tried to un-blacklist a not blacklisted IP {ip}")

class IPNotWhitelisted(NetworkException):
    """ Tried to un-whitelist a not whitelisted IP. """
    def __init__(self, ip: str):
        super().__init__(f"Tried to un-whitelist a not whitelisted IP {ip}")

# -----------------------------------------------------------------------------
