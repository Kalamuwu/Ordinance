# Ordinance

The Swiss-army-knife of honeypot and monitoring tools. Based loosely on [BinaryDefense's Artillery](https://github.com/binarydefense/artillery).

## Table of Contents
  1. **[Usage](#1-usage)** - General usage, configuration files, etc
  2. **[Core](#2-core)** - Ordinance Core
  3. **[Plugins](#3-plugins)** - Ordinance's plugin system
  4. **[Writers](#4-writers)** - Outputs of various kinds
  5. **[Scheduler](#5-scheduler)** - Ordinance's scheduling system
  6. **[Network utilities](#6-network-utilities)** - Ordinance networking framework

<br>

# 1. Usage

Ordinance is meant to be a set-and-forget tool. Set up the configuration, enable autostarting, and let it monitor and protect in the background while you work.

More specifically, Ordinance is a plugin manager and loader, that exposes certain functionality and modules helpful for creating passive defense tools like honeypots or monitors.

## Configuration

The configuration file is located at `config.yaml`. It is formatted according to standard YAML rules:
```yaml
myconfigvar: true
myotherconfigvar: [1, 2, 3]

plugin.myplugin:
  myvar: 2
  mothervar: 3

plugin.myotherplugin:
  mystring: 'Hello, Ordinance!'
```

Any standard YAML will be valid, and this config will also be checked by Ordinance according to the [plugins](#3-plugins) it is running.

# 2. Core

Ordinance Core is the backbone of Ordinance, and represents Ordinance as an object. It handles configuration, plugin initialization, managing scheduler and writer background threads, firing of events, and more.

## Core Configuration

The following keys must be present, to configure how Ordinance Core runs:
```yaml
auto_update:
  auto_update_ordinance: false
  interval_days: 14

core:
  create_startup_systemd_service: true
  issue_iptables_ban_comment: True

writers:
  enabled:
    email: false
    logfile: false
    notif: false
    stdout: false
    syslog: false
```

For more about the `writers` key, see section **[4. Writers](#4-writers)**.

## Auto-update

Ordinance can be configured to automatically check for new updates and download/install them if necessary. ***TODO this isn't functioning yet, enabling has no effect***

## Core section

The `core` section of the base `config.yaml` is dedicated to miscellaneous configurations for Ordinance Core. As of now, only two keys are there, `create_startup_systemd_service` and `issue_iptables_ban_comment`. The former of the two keys controls whether or not Ordinance should create a `systemd` service that will start Ordinance in the background when the computer is started. The latter of the two keys controls whether or not Ordinance, when it blacklists an IP address on iptables, should attach a comment to the blacklist entry. 

***TODO `create_startup_systemd_service` isn't functioning yet, enabling has no effect***

<br>

# 3. Plugins

A core feature that raises Ordinance above Artillery is its use of **plugins**. Ordinance Core is mainly a plugin manager; it doesn't do much on its own.

## Plugin structure

Any folder found in the `plugins` folder will be assumed to be a plugin, and Ordinance will attempt to attach it as such. Each plugin, to be valid, must contain a `plugin.yaml` config in its folder. (Plugins can have as many other files or subfolders in their folder as they like, but all _require_ a `plugin.yaml`). Plugins must also expose a class that inherits from `ordinance.ext.plugin.OrdinancePlugin`, that the `plugin.yaml` points to (see **Plugins > Configuration** for more about that pointing):

```python
import asyncio
from ordinance.ext import plugin, schedule
from ordinance import writer

class MyPlugin(plugin.OrdinancePlugin):
    def __init__(self, conf: Dict[str, Any]):           # 1
        self.myvar = conf['myvar']
        # ...
        writer.info("Example plugin: Initialized.")
    
    @schedule.run_periodically(minutes=30)              # 2
    async def my_half_hour_func(self):
        await asyncio.sleep(1)
        self.my_function()
        writer.debug("Example plugin: triggered!")
    
    def my_function(self, some_arg):                    # 3
        do_something()


def setup(conf): return MyPlugin(conf)                  # 4
```

## Plugin phases

### 1. Plugin init

```python
class MyPlugin(plugin.OrdinancePlugin):
    def __init__(self, conf: Dict[str, Any]):
        pass
```

The first step in a plugin's life cycle is instantiation (see **Plugins > Plugin Phases > Module setup function** for how plugins actually *get* to the instantiation phase. It's put last, however, because it's a minor detail compared to the plugin functionality details.)

Plugins are instantiated **synchronously**, so best practice is to extract any configuration variables from the given config and save them as instance variables, and don't yet do any processing or operating. This part is pretty basic.

Heavy-lifting for the setup of plugins should be done in an `async` function with the decorator `@schedule.run_at_startup()` -- see section [**5. Scheduler**](#5-scheduler) for more.

### 2. Scheduled functions

Plugins can schedule certain functions to fire at certain times of day, on a certain time interval, or on certain events. This is one such example. See [**5. Scheduler**](#5-scheduler) for more.

### 3. Other functions

Marker \#3 in the example plugin shown way above is next to a custom function. That's not the limit. Go ham.

Plugins can add as many other functions as they want. Do what you want. It's your plugin. Add other classes, other files, other functions. Whatever. Go wild.

### 4. Module setup function

```python
def setup(conf): return MyPlugin(conf)
```

The dictionary object passed to this `setup` function will be the entry specified in the base `config.yaml` merged with the default config specified in the plugin's `plugin.yaml` (see section **Plugins > Plugin configuration**). It is on the plugin to validate or otherwise manipulate the config. If this function raises an error, Ordinance will not proceed with initializing this plugin, and will raise this error to the user.

The point of this function is simply to return an `ordinance.ext.plugin.OrdinancePlugin` object. Don't use it to do any actual processing, like starting threads, opening files, etc. Save that for **Scheduler > Event-based functions > Startup**.

## Plugin configuration

Plugins are configured with a `plugin.yaml` file in their directory. This file tells all about the plugin; metadata, entry point, etc. This file is a little less flexible than the base `config.yaml`, as certain keys are required:

```yaml
qualified_name: myplugin
entry_file: main

default_config: ...
```

This is the bare minimum required for a `plugin.yaml` file. This tells Ordinance to register this plugin under the qualified name `myplugin`, and to look for the main `setup()` function in the file `main.py`. Note the `default_config` key; see **Plugins > Parsed config** and **Plugins > Default config** for more.

More keys can be configured for metadata:

```yaml
# 
# My plugin -- a test plugin.
# 

---

name: My Testing Plugin
description: Metadata can be attached to plugins with these four keys.
author: Kalamuwu
version: 1.0.0

qualified_name: myplugin
entry_file: main

default_config: ...
```

Comments are allowed, and will be skipped, according to YAML syntax. The four additional keys `name`, `description`, `author`, and `version` are all considered metadata, and don't have much of an effect on Ordinance or the plugin initialization process.

## Parsed config

Any valid YAML will be passed to the plugin in the `config` argument of `setup.py` during initialization:
```yaml
plugin.myplugin:
  mynumber: 621
  mylist: [a, b, c]
  myotherlist:
    - xyz
    - 6
    - mynestedobject:
        mynestedvalue: 4.6
        myothernestedvalue: Hello, Ordinance!
  mystring: Greetings, from Ordinance!
```
For the above configuration, the plugin defined with `qualified_name: myplugin` will receive the following configuration:
```python
{
    'mynumber': 621,
    'mylist': ['a', 'b', 'c'],
    'myotherlist': ['xyz', 6,
        {
            'mynestedobject': {
                'mynestedvalue': 4.6,
                'myothernestedvalue': 'Hello, Ordinance!'
            }
        }
    ],
    'mystring': 'Greetings, from Ordinance!'
}
```

Anything defined in the base `config.yaml` for the plugin will be passed in this `config` object. Note that this will be merged with the plugin's default config; **keys in the base `config.yaml` will override keys in the plugin's default config.**

Plugins are not required to be listed in `config.yaml` to run; if a plugin can run without any configuration variables, it will still be added to and run by Ordinance.

## Default config

Inside their `plugin.yaml` file, as we've seen before, plugins must include a default config. This is the object that will be merged with the configuration object defined in the base `config.yaml`. For example:
```yaml
# myplugin's plugin.yaml
...
default_config:
  myvar: 6
  myothervar: Hello!
```
```yaml
# base config.yaml
...
plugin.myplugin:
  myvar: 8
  mythirdvar: Hey!
```

For these two configurations, the plugin will receive:
```json
{
    "myvar": 8,
    "myothervar": "Hello!",
    "mythirdvar": "Hey!"
}
```

As you can see, the plugin's default config will be merged with the config given in the base `config.yaml`. Unique keys from both files will be aggregated, and any clashing keys will be overriden by the value given in the base `config.yaml`.

<br>

# 4. Writers

The `writers` module is how Ordinance communicates with the user. By default, there are different levels of logging; `debug`, `info`, `success`, `warn`, `error`, `critical`, and `alert`. Each of these corresponds to a unique need:

- `ordinance.writer.debug()`: Debug messages; unimportant for most people.
- `ordinance.writer.info()`: Informational messages that might be useful to update the user with, such as a confirmation of plugin initialization, etc.
- `ordinance.writer.success()`: This should be used for successful bans, blocks, updates, etc.
- `ordinance.writer.warn()`: Warn messages should be about things that aren't mission-critical, but are still important to know about for the user, such as a url 404'ing or a scheduled run taking a little too long.
- `ordinance.writer.error()`: Error messages -- invalid config keys, a command failed, etc. Should be for errors that **don't** stop the plugin from running, but rather stop the plugin from doing some action.
- `ordinance.writer.critical()`: Mission-critical failures. For example: a required config key wasn't found, so the plugin cannot start. Should be for errors that **do** stop the plugin from running or operating.
- `ordinance.writer.alert()`: Special high-criticality messages that the user needs to know about -- an attacker was blocked, a watched folder changed, a bruteforce attempt was observed, etc.

All of these functions exist in the module scope of the module `ordinance.writer`, and should be called as such, for example `ordinance.writer.info("Hello, Ordinance!")`. Note that all of these functions can take as many or as few args as you pass to it; similar to `print`, they will be aggregated together into one string before writing. For example:
```python
myvar = "MyPlugin"
ordinance.writer.info("Hello from", myvar)
```

There are different types of writers, each operating in different ways. These writers are:

- `email`: Successes, errors, criticals, and alerts will be queued up and sent to a specified email address every `n` minutes.
- `logfile`: Given paths and masks will be used for different log files. These masks are bitmasks, each bit right-to-left corresponding to criticalities top-to-bottom in the list above. For example, the mask `0b1110000` means write alerts, criticals, and errors to the corresponding file, and the mask `0b0000011` means write only debugs and infos to the corresponding file.
- `notif`: This writer sends popup notifications via `notify2` to the user. This is useful if you're running Ordinance as a pseudo-daemon or in the background on a machine that you use with a desktop environment.
- `stdout`: Writes to the standard output, stdout. It can be useful to disable this if you are running Ordinance as a pseudo-daemon, or in the background.
- `syslog`: Writes to the syslog, usually the file that `journalctl` reads.

These can all be configured and enabled/disabled in the base `config.yaml` file. These writers all operate in the background, in a separate thread. Plugins do not need to worry about which writer they are writing to, but rather call `ordinance.writer.<function>` to write to them all, and let each individual writer handle itself. In this case, `<function>` corresponds to the functions listed in the above list, before the writer type list, e.x. `ordinance.writer.info()` or `ordinance.writer.alert()`.

<br>

# 5. Scheduler

The `ordinance.ext.schedule` module is for plugins to schedule functions to run at certain events or times. This is achieved through decorators above these functions. Any scheduled function must be an `async` function, and must take a single argument, `self`.  Do note that the scheduled functions must be on a class that derives from `ordinance.ext.plugin.OrdinancePlugin`.

## Event-based functions

Plugin functions can be scheduled to fire at various events. As of now, there are only two events, startup and shutdown.

### Startup

```python
    @schedule.run_at_startup()
    async def my_setup_func(self):
        pass
```

*This* is where you can start to do heavy lifting for setting up the plugin. Once all the plugins have been instantiated, they all _concurrently_ run any functions marked with the `schedule.OrdinanceEvent.STARTUP` flag. These functions will be started AND stopped before the scheduler starts ticking -- meaning you can be sure that this function will be run before any other scheduled functions. This way, no race conditions will occur, such as a scheduled function writing to a handle that a startup function hasn't had a chance to open yet.

As all plugins are concurrently set up, it's best practice to throw in `await asyncio.sleep(0)` throughout the function to split up blocking code and let the other plugins have a chance to run. Don't be a dick and hog the event loop.

Any exceptions raised by this function will be collected and sent to `ordinance.writer.error`, however the plugins' scheduled functions will still be ran. To cancel these scheduled functions, call `ordinance.ext.schedule.cancel(fhash)` where `fhash` is the result of `hash(func)` for whatever `func` you which to cancel.

### Shutdown

Some plugins will need to do certain actions before destruction, like `join()`ing a thread, closing a server, or saving a file.

```python
    @scheduler.run_at_shutdown
    async def my_close_func(self):
        pass
```

This is the function to do such things. This function is called asyncronously and concurrently among the plugins when the `ordinance.core.Core` is destructed. Again, same rules apply as startup functions, be considerate and call `asyncio.sleep(0)` to space out expensive blocking calls and let the other plugins have some event loop time. Again, similar to startup functions, the scheduler will stop ticking before this function is called. You can be sure that no scheduled functions will be in the middle of running when this function is called, meaning there will be no race conditions between e.x. a scheduled function writing to a handle and a shutdown function closing that handle.

## Time-based functions

Two time-based functions exist, for scheduling a function to run periodically at a set interval, and for scheduling a function to run once a day at a certain time.

```python
    @schedule.run_periodically(minutes=30)
    async def my_half_hour_func(self):
        writer.info("This runs every half hour!")
```

```python
    @schedule.run_daily_at(hour=6, minute=45)
    async def my_daily_func(self):
        writer.info("This runs every day at 6:45AM!")
```

Functions can be scheduled to be run, either with `run_periodically` to run a function at some time interval, or `run_daily_at` if you want the function to be run at a certain time every day.

## Stacking and combining decorators

Decorators can be stacked, as many as you need, like follows:

```python
    @schedule.run_periodically(hours=2)
    @schedule.run_periodically(hours=7)
    @schedule.run_daily_at(hour=0, minute=0, second=0)
    @schedule.run_at_startup()
    async def my_func(self): pass
```

<br>

# 6. Network utilities

TODO
