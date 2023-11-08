# 
# ordinance/core.py
# main functions called in driver
# 

from typing import (
    Dict,
    List,
    Optional,
    Any,
    Self,
    Callable
)

import os
import sys
import time
import threading
import asyncio
import importlib.util
import yaml
import yaml.parser

import ordinance.exceptions
import ordinance.ext.network
import ordinance.ext.plugin
import ordinance.ext.schedule
import ordinance.writer
import ordinance.util
import ordinance.thread


def _safe_load_config_path(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, 'r') as file:
            conf = yaml.safe_load(file.read())
    except FileNotFoundError:
        print(f"Config file {config_path} not found, creating...")
        with open(config_path, 'w') as file:
            file.write(
                ordinance.util.get_header(comment=
                "Ordnance v2\nWritten by: Kalamuwu\nGithub: https://github.com/Kalamuwu/\n\n" +
                "This is the Ordnance configuration file. Change these variables and flags to " +
                "change how Ordinance and its plugins behave.") +
                "\n---\n\n")
    except yaml.parser.ParserError as e:
        raise ordinance.exceptions.ConfigSyntaxError(path, e) from e
    return conf


def _resolve_import_name(name: str) -> str:
    """ Resolve relative import name to absolute import name """
    try:
        return importlib.util.resolve_name(name, None)
    except ImportError:
        raise ordinance.exceptions.PluginNotFound(name)


def _load_plugin_details(folder_name: str) -> Dict[str, str]:
    """
    Reads the `plugin.yaml` file for a given plugin name, and returns a dict containing the following information from it:
    :meth:`['name', 'description', 'author', 'version', 'qualified_name', 'entry_file', 'default_config]`
    """
    try:
        with open(f"extensions/{folder_name}/plugin.yaml", 'r') as file:
            conf = yaml.safe_load(file.read())
    except FileNotFoundError:
        raise ordinance.exceptions.PluginInvalid(f'Plugin {folder_name} has no plugin.yaml!')
    except yaml.parser.ParserError:
        raise ordinance.exceptions.PluginInvalid(f"Plugin {folder_name}/plugin.yaml is invalid YAML!")
    out = {}
    # copy necessary info while dropping unrecognized
    for keyname in ["name", "description", "author", "version", "qualified_name", "entry_file", "default_config"]:
        out[keyname] = conf.get(keyname, "")
        if not out[keyname]:
            print(f"Warning: plugin at folder {folder_name} missing key {keyname}")
    out['folder_name'] = folder_name
    return out


def _extract_entry_func(details: Dict[str, Any]) -> Callable:
    """
    Extracts the plugin class according to the given plugin details. See
    :meth:`_load_plugin_details` for what information is required. 
    """
    # get details
    qname = details['qualified_name']
    if 'entry_file' not in details:
        raise ordinance.exceptions.PluginNoDefinedEntryPointError(qname)
    # pull out and define module
    entry_file = details.pop('entry_file')
    folder_name = details.get('folder_name')  # we still need this! get, dont pop!
    resolved_name = importlib.util.resolve_name(f"extensions.{folder_name}.{entry_file}", None)
    spec = importlib.util.find_spec(resolved_name)
    if spec is None:  raise ordinance.exceptions.PluginNotFound(qname)
    # plugin spec found! register
    module = importlib.util.module_from_spec(spec)
    sys.modules[qname] = module
    try:  # attempt to load
        spec.loader.exec_module(module)
    except Exception as e:
        del sys.modules[qname]
        raise ordinance.exceptions.PluginLoadingFailed(f"Could not load plugin {qname}, error:", e=e)
    if not hasattr(module, 'setup'):
        del sys.modules[qname]
        raise ordinance.exceptions.PluginEntryPointNotFoundError(qname, entry_file)
    return module.setup


def _register_plugins(conf: Dict[str, Any]) -> Dict[str, ordinance.ext.plugin.OrdinancePlugin]:
    """ Returns a dictionary of enabled plugins' qnames as keys to that plugin's object. """
    plugins = {}
    for folder in os.listdir('extensions'):
        
        # check for reasons to skip
        if not os.path.isdir('extensions/'+folder):
            ordinance.writer.error(f"Skipping unknown file extensions/{folder}")
            continue
        if folder.endswith('disabled'):
            ordinance.writer.warn(f"Skipping disabled plugin extensions/{folder}/")
            continue
        
        # pull details from plugin.yaml
        try:
            details = _load_plugin_details(folder)
        except ordinance.exceptions.PluginInvalid:
            ordinance.writer.error(f"Plugin at folder {folder} is invalid!")
            continue
        except Exception as e:
            ordinance.writer.error(f"Could not load plugin at folder {folder}, with error: ", e)
            continue
        
        # check for conflicts
        qname = details['qualified_name']
        if qname in plugins:
            raise ordinance.exceptions.PluginAlreadyLoaded(qname)
        
        # initialize
        plugin_conf = ordinance.util.deep_merge(
            details.pop('default_config'),
            conf.get('plugin.'+qname, {}))
        try:
            entry_func = _extract_entry_func(details)
            plugins[qname] = entry_func(plugin_conf)
            plugins[qname].__metadata__ = details
            ordinance.ext.schedule._register(plugins[qname])
        except Exception as e:
            ordinance.writer.error(f"Could not load plugin {qname}, with error: ", e)
            del plugins[qname]
    
    return plugins


class Core:
    version = "1.0"

    def __init__(self, config_path: str, load_plugins: bool = True):
        # first and foremost -- check for root.
        ordinance.util.root_check()
        # read config from file
        self.config = _safe_load_config_path(config_path)
        # initialize and start writers
        ordinance.writer.initialize(self.config.get('writers', {}))
        # initialize plugins
        self.plugins = _register_plugins(self.config) if load_plugins else {}
        # initialize networking module
        ordinance.ext.network.initialize(self.config.get('core', {}))
        ordinance.ext.network._read_local_list()
        # initialize self
        self.running = False
        if not load_plugins: self.version += " (Safe Mode)"
        ordinance.writer.success(f"Initialized Ordinance Core v{self.version}")
    
    def run(self):
        self.running = True
        # fire startup event
        ordinance.writer.debug("Firing startup event.")
        ordinance.ext.schedule.fire_event(ordinance.ext.schedule.OrdinanceEvent.STARTUP)
        # start ticking schedulers
        ordinance.ext.schedule._start()
        # announce
        ordinance.writer.debug("Running with writers:", *ordinance.writer._enabled.keys())
        ordinance.writer.debug("Running with plugins:", *self.plugins.keys())
        ordinance.writer.success(f"=====\nOrdinance v{self.version} started.\n=====")
    
    def close(self):
        self.running = False
        ordinance.writer.info("Shutting down Ordinance...")
        # run plugin close() functions
        ordinance.ext.schedule.fire_event(ordinance.ext.schedule.OrdinanceEvent.SHUTDOWN)
        # stop scheduler thread
        ordinance.ext.schedule._close()
        # write white/blacklist database
        ordinance.ext.network._write_local_list()
        # close writers
        ordinance.writer._close()
        # announce
        print(f"Ordinance v{self.version} stopped.")
