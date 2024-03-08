# 
# ordinance/core.py
# main functions called in driver
# 

from typing import (
    Dict,
    List,
    Set,
    Optional,
    Any,
    Self,
    Callable
)

import os
import sys
import datetime
import time
import threading
import asyncio
import yaml
import json
import yaml.parser
import http.server

import core.existing_writers
import core.api_server
import core.plugin_interface
import core.schedule_interface
import core.network_interface

import ordinance.exceptions
import ordinance.network
import ordinance.plugin
import ordinance.schedule
import ordinance.util

VERSION = "4.0"

default_config_yaml = f"""# 
# Ordinance v{VERSION}
# Written by: Kalamuwu
# Github: https://github.com/Kalamuwu/Ordinance
# 
# This is the Ordinance configuration file. Change these variables and flags to
# change how Ordinance and its plugins behave.
# 

---

core:
  scheduler_tick: 30

api:
  http_server:
    interface:
    port:

writers:
  enabled:
    - stdout
    - logfile
  logfile:
    files:
      - path: logs/debug.log
        mask: 0b1111111
      - path: logs/standard.log
        mask: 0b1111110
      - path: logs/important.log
        mask: 0b1110000
"""

def _safe_load_config_path(config_path: str, _make_if_missing: bool = True) -> Dict[str, Any]:
    try:
        with open(config_path, 'r') as file:
            conf = yaml.safe_load(file.read())
        if conf is None: return {}
        else: return conf
    except FileNotFoundError:
        default = yaml.safe_load(default_config_yaml)
        if _make_if_missing:
            print(f"Config file {config_path} not found, creating with default...")
            with open(config_path, 'w') as file:
                file.write(default_config_yaml)
        else: print(f"Config file {config_path} not found, using default.")
        return default_config_yaml
    except yaml.parser.ParserError as e:
        raise ordinance.exceptions.ConfigSyntaxError(path, e) from e


def async_join_threads(threads: List[threading.Thread], timeout: Optional[float] = None) -> List[threading.Thread]:
    try:
        loop = asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    async def join_one(th):
        th.join(timeout)
    async def join_all():
        await asyncio.gather(*[
            join_one(th) for th in threads
        ], return_exceptions=True)
    loop.run_until_complete(join_all())
    loop.stop(); loop.close()
    return [th for th in threads if th.is_alive()]


class Core:
    def __init__(self,
        config_path: str,
        safe_mode: Optional[bool] = False,
        load_plugins: Optional[bool] = True,
        do_api_server: Optional[bool] = True
    ):
        # preliminary safe mode condition checking
        if safe_mode:
            load_plugins = False
            do_api_server = False
        
        # read config from file
        self.__config = _safe_load_config_path(config_path)
        
        # initialize writers
        core.existing_writers.add_known_writers()
        writer_configs = self.__config.get('writers', {})
        enabled_writers = writer_configs.get('enabled', [])
        for writer in enabled_writers:
            this_writer_config = writer_configs.get(writer, {})
            try: ordinance.writer.enable(writer, this_writer_config)
            except ordinance.exceptions.WriterNotFound:
                warning = f"Unknown writer type '{writer}' in config writers.enabled"
                ordinance.writer.warn(warning)
                if writer == 'stdout': print(warning)  # just in case
            except Exception as e:
                error = f"Error enabling writer '{writer}'"
                ordinance.writer.error(error)
                ordinance.writer.error(e)
                if writer == 'stdout':  # just in case
                    print(error)
                    print(e)
        
        # initialize networking module
        core.network_interface.read_dbs()
        core.network_interface.setup_iptables()

        # initialize plugins list
        all_qnames = core.plugin_interface.fetch_all_qnames()
        self.__plugins: Dict[str, ordinance.plugin.OrdinancePlugin] = \
            { qname: None for qname in all_qnames }
        self.__schedules: Dict[str, Dict[str, ordinance.schedule.ScheduledFunction]] = \
            { qname: {} for qname in all_qnames }
        self.__commands: Dict[str, Dict[str, ...]] = \
            { qname: {} for qname in all_qnames }
        if load_plugins:
            for qname in self.__plugins.keys():
                try: self.plugin_load(qname)
                except Exception as e:
                    warning = f"Unknown writer type '{writer}' in config writers.enabled"
                    ordinance.writer.warn(warning)
        
        # initialize scheduler stuffs
        sched_tick = self.__config.get('core', {}).get('scheduler_tick', 30)
        ordinance.writer.debug(f"Using scheduler tick = {sched_tick}")
        sched_subtick = self.__config.get('core', {}).get('scheduler_subtick', 5)
        ordinance.writer.debug(f"Using scheduler subtick = {sched_subtick}")
        self.__scheduler_thread = threading.Thread(
            target=self._scheduler_loop, args=(sched_tick, sched_subtick,),
            name='Ordinance-scheduler')
        self._scheduler_should_run = True
        self.__scheduler_thread.start()
        
        # initialize api server stuffs
        core.api_server.ApiRequestHandler._core_ref = self
        api_config = self.__config.get('api', {})
        http_server_config = api_config.get('http_server', None)
        if http_server_config is None: do_api_server = False
        http_server_interface = http_server_config.get('interface', None)
        http_server_port = http_server_config.get('port', None)
        self.__api_server = core.api_server.ApiServer(bind=(http_server_interface, http_server_port), poll_interval=1.0)
        if do_api_server: self.__api_server.start()
        
        # announce start
        global VERSION
        self.__core_running = True
        if safe_mode: VERSION += " (Safe Mode)"
        ordinance.writer.debug("Running with plugins:", *self.__plugins.keys())
        ordinance.writer.debug("Running with writers:", *ordinance.writer.get_enabled())
        ordinance.writer.success(f"Initialized Ordinance Core v{VERSION}")
    
    
    def stop(self):
        if not self.__core_running:
            raise Exception("Already stopped")
        
        # announce stop
        ordinance.writer.debug("Stopping plugins:", *self.__plugins.keys())
        ordinance.writer.debug("Stopping writers:", *ordinance.writer.get_enabled())

        # stop webserver stuffs
        self.__api_server.stop()
        
        # ensure scheduler and plugins are stopped
        self._scheduler_should_run = False
        self.__scheduler_thread.join()
        
        # stop networking module
        ordinance.network.blacklist.flush()
        ordinance.network.whitelist.flush()
        
        # stop writers module
        for writer in ordinance.writer.get_enabled():
            ordinance.writer.disable(writer)
        
        # destruct core
        self.__core_running = False
        global VERSION
        print(f"Stopped Ordinance Core v{VERSION}")


    # two interfaces, <Core>.running and <Core>.is_running() -- they do the same thing
    @property
    def    running(self) -> bool: return self.__core_running
    def is_running(self) -> bool: return self.__core_running


    def plugin_load(self, qname: str) -> None:
        ordinance.writer.debug(f"considering qname {qname} for load...")
        if qname not in self.__plugins.keys():
            raise ordinance.exceptions.PluginNotFound(qname)
        if self.__plugins[qname] is not None:
            raise ordinance.exceptions.PluginAlreadyLoaded(qname)
        
        try:
            ordinance.writer.debug(f"qname {qname} in good state for load; loading plugin information...")
            entry_file, meta, default_conf = core.plugin_interface.load_plugin_yaml(qname)
            
            ordinance.writer.debug(f"loading plugin module...")
            module = core.plugin_interface.load_module_from_file(qname, entry_file)
            
            ordinance.writer.debug(f"defining plugin class from module...")
            plugin_class = core.plugin_interface.define_plugin_from_module(qname, module)

            ordinance.writer.debug(f"doing plugin preinit...")
            core.plugin_interface.write_metadata(plugin_class, qname, meta)
            scheds = core.plugin_interface.extract_scheduler_funcs(plugin_class)
            cmds = core.plugin_interface.extract_command_funcs(plugin_class)

            ordinance.writer.debug(f"creating plugin object...")
            conf_from_main = self.__config.get('plugin.'+qname, {})
            conf = core.plugin_interface.deep_merge(default_conf, conf_from_main)
            plugin = plugin_class(conf)
        
        except Exception as e:
            ordinance.writer.debug(f"plugin {qname} load failed. error:")
            ordinance.writer.debug(e)
            ordinance.writer.error(f"Plugin {qname} load failed, with error:", repr(e))
        
        else:
            ordinance.writer.debug(f"all ok. saving plugin {qname}.")
            ordinance.writer.success(f"Loaded plugin {qname}")
            self.__plugins[qname] = plugin
            self.__schedules[qname] = scheds
            self.__commands[qname] = cmds


    def plugin_unload(self, qname: str) -> None:
        ordinance.writer.debug(f"considering qname {qname} for unload...")
        if qname not in self.__plugins:
            raise ordinance.exceptions.PluginNotFound(qname)
        if self.__plugins[qname] is None:
            raise ordinance.exceptions.PluginAlreadyLoaded(qname)
        
        try:
            ordinance.writer.debug(f"qname {qname} in good state for unload; doing predel...")
            #TODO when scheds and cmds are saved, unregister them here

            ordinance.writer.debug(f"removing module from sys.modules[]...")
            del sys.modules[qname]
        
        except Exception as e:
            ordinance.writer.debug(f"plugin {qname} unload failed. error:")
            ordinance.writer.debug(e)
            ordinance.writer.error(f"Plugin {qname} unload failed, with error:", repr(e))
            ordinance.writer.info(f"[!] plugin is in undefined state. removing anyways. [!]")
        
        else:
            ordinance.writer.debug(f"all ok. removing plugin {qname}.")
        
        finally:
            ordinance.writer.success(f"Unloaded plugin {qname}")
            # from what I can tell, setting active references to None and del'ing
            # an object do the same thing from the gc's perspective (minus
            # deallocating the name; with setting to None, the name persists, but
            # the underlying object is still destroyed). regardless, from the gc's
            # perspective, this shouldn't leak. (hopefully.)
            self.__plugins[qname] = None
            self.__schedules[qname] = None
            self.__commands[qname] = None
    

    def is_known_plugin(self, qname: str) -> bool:
        return qname in self.__plugins
    

    def _scheduler_loop(self, tick_interval: float, poll_subtick: float):
        ordinance.writer.debug("Started scheduler thread.")
        localtz = core.schedule_interface.local_tz()
        scheduler_start = datetime.datetime.now(tz=localtz)
        active_threads: List[threading.Thread] = []
        granularity = tick_interval/2
        subtick_start = time.time()
        elapsed_subtick_time = 0

        while self._scheduler_should_run:
            #ordinance.writer.debug("Doing scheduler subtick")
            subtick_this = time.time()
            elapsed_subtick_time = (subtick_this - subtick_start)
            if elapsed_subtick_time <= tick_interval:
                # not time for a full tick yet
                time.sleep(poll_subtick)
                continue
            # time for scheduler tick!
            #ordinance.writer.debug("Doing scheduler tick")
            
            tick_start = time.time()
            time_now = datetime.datetime.now(tz=localtz)
            total_elapsed = time_now - scheduler_start
            active_threads = [th for th in active_threads if th.is_alive()]

            def calendar_filter(trigger):
                return core.schedule_interface.calendar_trigger_should_run(
                    trigger, time_now, granularity=granularity)

            def delay_filter(trigger):
                return core.schedule_interface.delay_trigger_should_run(
                    trigger, total_elapsed, granularity=granularity)

            def periodic_filter(trigger):
                return core.schedule_interface.periodic_trigger_should_run(
                    trigger, total_elapsed, granularity=granularity)
            
            for plugin_name,scheduled_funcs in self.__schedules.items():
                plugin_instance = self.__plugins[plugin_name]
                for sched_name,sched in scheduled_funcs.items():
                    for trig in sched._get_triggers():
                        if ( isinstance(trig, ordinance.schedule.CalendarTrigger) and calendar_filter(trig) ) \
                        or ( isinstance(trig, ordinance.schedule.DelayTrigger)    and delay_filter(trig)    ) \
                        or ( isinstance(trig, ordinance.schedule.PeriodicTrigger) and periodic_filter(trig) ) :
                            ordinance.writer.info(f"Firing trigger '{trig.id}', of sched '{sched.name}', daemonic={trig.daemonic}")
                            active_threads.append(sched(plugin_instance, trig.daemonic))
            tick_stop = time.time()
            tick_elapsed = tick_stop - tick_start
            #ordinance.writer.debug(f"Finished scheduler tick. Took {tick_elapsed:.4f} seconds")
            time.sleep(poll_subtick - tick_elapsed)
        
        # teardown
        ordinance.writer.debug(f"Scheduler noticed shutdown. Closing {len(active_threads)} active threads.")
        if len(active_threads):
            ordinance.writer.info(f"Some threads still active. Joining with timeout 5s...")
            active_threads = async_join_threads(active_threads, timeout=5.0)
        
        if len(active_threads):
            ordinance.writer.info(f"Some threads did not finish within 5 seconds. Destroying.")

        ordinance.writer.info(f"Scheduler stopped.")
        ordinance.writer.debug("Stopped scheduler thread.")


    def command(self, cmd: str) -> None:
        # handle simple commands
        if   cmd == 'stop': return self.stop()
        elif cmd == 'status':
            return ordinance.writer.info(f"Plugins: {', '.join(self.__plugins.keys())}\n" + \
                                         f"Writers: {', '.join(ordinance.writer.get_enabled())}")
        # handle plugin commands
        cmd = cmd.split()
        if len(cmd) == 1:
            return ordinance.writer.error(f"Unknown command {cmd[0]}")


    # http api server stuffs
    
    def _apiserver_status_single_plugin(self, qname: str):
        plugin = self.__plugins[qname]
        sched_dict = self.__schedules[qname]
        return {
            'qname': qname,
            'metadata': {
                'name': plugin.name,
                'description': plugin.description,
                'author': plugin.author,
                'version': plugin.version,
            },
            'schedules': [
                {
                    'name': sched_name,
                    'triggers': [ {
                        'id': trig.id,
                        'type': schedule_interface.get_type_string(trig),
                        'data': trig.__dict__
                    } for trig in sched._get_triggers() ]
                } for sched_name, sched in sched_dict.items()
            ],
            # 'commands': [
            #     #TODO
            # ]
        }
    
    def _apiserver_plugins(self):
        return [ {
            'qname': qname,
            'status': 'unloaded' if plugin is None else 'running'
        } for qname,plugin in self.__plugins.items() ],
    
    def _apiserver_writers(self):
        enabled = ordinance.writer.get_enabled()
        return  [ {
            'name': name,
            'status': 'enabled' if name in enabled else 'disabled'
        } for name in ordinance.writer.get_known() ]

    def _apiserver_status(self):
        enabled = ordinance.writer.get_enabled()
        return {
            'plugins': self._apiserver_plugins(),
            'writers': self._apiserver_writers()
        }
