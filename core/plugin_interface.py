import os
import sys
import yaml
import yaml.parser
import importlib.util
import datetime
import time

import ordinance.schedule
import ordinance.exceptions
import ordinance.plugin
import ordinance.writer

from typing import Set, Tuple, Dict, Any


valid_qname_chars = "abcdefghijklmnopqrstuvwxyz0123456789.-_+"

recognized_metadata_keys = ['name', 'author', 'description', 'version']

def deep_merge(dict1: dict, dict2: dict) -> dict:
    """
    Merges two dicts. If keys are conflicting, dict2 is preferred.
    
    Credit to milanboers on GitHub for this function:
    https://gist.github.com/milanboers/a8bb8b81b1c3fb3eb86ee2d9ea4bd5b2
    """
    def _val(v1, v2):
        if isinstance(v1, dict) and isinstance(v2, dict):
            return deep_merge(v1, v2)
        return v2 or v1
    return {k: _val(dict1.get(k), dict2.get(k)) for k in dict1.keys() | dict2.keys()}


def fetch_all_qnames() -> Set[str]:
    """ Fetches the names of all plugins in the extensions folder. """
    path = os.path.abspath('extensions')
    if not (os.path.exists(path) and os.path.isdir(path)):
        raise FileNotFoundError(path)
    valid_qnames = set()
    skipped = set()
    for fname in os.listdir(path):
        if fname == 'disabled':
            ordinance.writer.debug(f"'disabled' folder found, skipping it.")
        elif not all(c in valid_qname_chars for c in fname):
            ordinance.writer.warn(f"Skipping bad plugin qname '{fname}'. Plugin qnames can only contain " +
                                   "lowercase a-z, 0-9, and any characters from [+-_] (not including the brackets).")
        elif fname in valid_qnames:
            ordinance.writer.warn(f"Multiple plugins defined for qname '{fname}', skipping all.")
            valid_qnames.remove(fname)
        else:
            valid_qnames.add(fname)
    return valid_qnames


# module load stages


def load_plugin_yaml(qname: str) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    # try loading the plugin.yaml config file
    try:
        with open(f"extensions/{qname}/plugin.yaml", 'r') as file:
            conf = yaml.safe_load(file.read())
    except FileNotFoundError:
        raise ordinance.exceptions.PluginInvalid(f'Plugin {qname} has no plugin.yaml')
    except yaml.parser.ParserError:
        raise ordinance.exceptions.PluginInvalid(f"Plugin {qname}/plugin.yaml is invalid YAML")
    # ensure there's an entry point defined
    if "entry_file" not in conf:
        raise ordinance.exceptions.PluginNoDefinedEntryPointError(qname)
    entry_file = conf["entry_file"]
    # copy recognized metadata
    meta = {}
    for keyname in recognized_metadata_keys:
        meta[keyname] = conf.get(keyname, None)
        if meta[keyname] is None:
            ordinance.writer.debug(f"config for plugin {qname} has no attribute {keyname}")
    # extract default config if it exists
    default_conf = conf.get("default_config", {})
    # return gathered information
    return (entry_file, meta, default_conf)


def load_module_from_file(qname: str, entry_file: str):
    # resolve module name
    try:
        resolved_name = importlib.util.resolve_name(f"extensions.{qname}.{entry_file}", None)
        spec = importlib.util.find_spec(resolved_name)
        module = importlib.util.module_from_spec(spec)
    except Exception as e:
        raise ordinance.exceptions.PluginLoadingFailed(f"Could not load plugin {qname}, error extracting module:", e=e)
    # attempt to load
    try:
        sys.modules[qname] = module
        spec.loader.exec_module(module)
    except Exception as e:
        del sys.modules[qname]
        raise ordinance.exceptions.PluginLoadingFailed(f"Could not load plugin {qname}, error executing module:", e=e)
    # all went well :)
    return module


def define_plugin_from_module(qname: str, module) -> ordinance.plugin.OrdinancePlugin:
    # there's a setup function, right?
    if not hasattr(module, 'setup'):
        raise ordinance.exceptions.PluginEntryPointNotFoundError(qname, entry_file)
    try:
        plug_cls = module.setup()
    except Exception as e:
        raise ordinance.exceptions.PluginLoadingFailed(f"Could not load plugin {qname}, error during setup function:", e=e)
    # ensure setup function returned a plugin class
    if not isinstance(plug_cls, type):
        raise ordinance.exceptions.PluginInvalid(f"Object returned from plugin {qname} setup() is not a class")
    if not issubclass(plug_cls, ordinance.plugin.OrdinancePlugin):
        raise ordinance.exceptions.PluginInvalid(f"Plugin qname {qname} setup() didn't return a class that inherits from OrdinancePlugin")
    # yippee!
    return plug_cls


# plugin preinit functions


def write_metadata(plugin_cls: type, qname: str, meta: Dict[str, str]) -> None:
    for key,val in [
        ('__qname__', qname),
        ('__metadata__', meta),
        ('__running__', False)
    ]:
        if hasattr(plugin_cls, key):
            raise ordinance.exceptions.PluginInvalid(f"Key {key} cannot exist on plugin")
        setattr(plugin_cls, key, val)


def extract_scheduler_funcs(plugin_cls: type) -> Dict[str, Any]:
    schedules = {}
    for name,method in plugin_cls.__dict__.items():
        if isinstance(method, ordinance.schedule.ScheduledFunction):
            if name in schedules:
                ordinance.writer.warn(f"Duplicate scheduled method name {name} on plugin")
            schedules[name] = method
    return schedules


def extract_command_funcs(plugin_cls: type) -> Dict[str, Any]:
    commands = {}
    for name,method in plugin_cls.__dict__.items():
        if hasattr(method, '__ordinance_commands'):
            commands[name] = method.__ordinance_commands
    return commands


# module teardown functions


...
