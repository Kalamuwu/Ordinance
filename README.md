# Ordinance v4.1

The Swiss-army-knife of honeypot and monitoring tools.

*NOTE: Docs might not yet be completely up-to-date with version 4.1. Most of it should be, though.*

## Table of Contents
  1. **[Usage](#1-usage)** - General usage, configuration files, etc
  2. **[Core](#2-core)** - Ordinance Core
  3. **[Plugins](#3-plugins)** - Ordinance's plugin system
  4. **[Writers](#4-writers)** - Outputs of various kinds
  5. **[Scheduler](#5-scheduler)** - Ordinance's scheduling system
  6. **[Databases](#6-databases)** - Built-in file-syncing databases and datasets
  7. **[Network utilities](#7-network-utilities)** - Ordinance networking framework

<br>

# 1. Usage

Ordinance is meant to be a set-and-forget tool. Set up the configuration, enable autostarting, and let it monitor and protect in the background while you work.

More specifically, Ordinance is a plugin manager and loader, that exposes certain functionality and modules helpful for creating passive defense tools like honeypots or file system monitors. (Note: A few plugins can be found at the [Ordinance-plugins](https://github.com/Kalamuwu/Ordinance-plugins) repo!)

## Requirements

Note that ordinance has one required dependency; `pyyaml`.

There are, however, more dependencies if you wish to use the built-in notifications or journalctl writer (more on those in section 4); `notify2`, `dbus-python`, and `systemd-python`.

Plugins will come with their own requirements and dependencies.

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

A core feature that raises Ordinance above Artillery is its use of **plugins**. Ordinance Core is mainly a plugin manager; it doesn't do much on its own. This is where plugins come in.

## Plugin structure

Any folder found in the `plugins` folder will be assumed to be a plugin, and Ordinance will attempt to attach it as such. Each plugin, to be valid, must contain a `plugin.yaml` config in its folder. (Plugins can have as many other files or subfolders in their folder as they like, but all _require_ a `plugin.yaml`). Plugins must also expose a class that inherits from `ordinance.plugin.OrdinancePlugin`, that the `plugin.yaml` points to (see **Plugins > Configuration** for more about that pointing):

```python
from ordinance import plugin, schedule
from ordinance import writer

class MyPlugin(plugin.OrdinancePlugin):
    def __init__(self, conf: Dict[str, Any]):           # 1
        self.myvar = conf['myvar']
        # ...
        writer.info("Example plugin: Initialized.")
    
    @schedule.run_periodically(minutes=30)              # 2
    def my_half_hour_func(self):
        self.my_function()
        writer.debug("Example plugin: triggered!")
    
    def my_function(self, some_arg):                    # 3
        do_something()


def setup(): return MyPlugin                            # 4
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

Heavy-lifting for the setup of plugins should be done in a function with the decorator `@schedule.run_at_plugin_start()` -- see section [**5. Scheduler**](#5-scheduler) for more.

### 2. Scheduled functions

Plugins can schedule certain functions to fire at certain times of day, on a certain time interval, or on certain events. This is one such example. See [**5. Scheduler**](#5-scheduler) for more.

### 3. Other functions

Marker \#3 in the example plugin shown way above is next to a custom function. That's not the limit. Go ham.

Plugins can add as many other functions as they want. Do what you want. It's your plugin. Add other classes, other files, other functions. Whatever. Go wild.

### 4. Module setup function

```python
def setup(): return MyPlugin
```

The dictionary object passed to this `setup` function will be the entry specified in the base `config.yaml` merged with the default config specified in the plugin's `plugin.yaml` (see section **Plugins > Plugin configuration**). It is on the plugin to validate or otherwise manipulate the config. If this function raises an error, Ordinance will not proceed with initializing this plugin, and will raise this error to the user.

The point of this function is simply to return a descendant of the `ordinance.plugin.OrdinancePlugin` class. Don't use it to do any actual processing, like starting threads, opening files, etc. Save that for **Scheduler > Event-based functions > Startup**.

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

The `ordinance.schedule` module is for plugins to schedule functions to run at certain events or times. This is achieved through decorators above these functions. Any scheduled function must take a single argument, `self`.  Do note that the scheduled functions must be on a class that derives from `ordinance.plugin.OrdinancePlugin` for them to take effect.

## Event-based functions

Plugin functions can be scheduled to fire at various events. As of now, there are only two events, plugin start and plugin stop.

### Startup

```python
    @schedule.run_at_plugin_start()
    def my_setup_func(self):
        pass
```

*This* is where you can start to do heavy lifting for setting up the plugin. Once all the plugins have been instantiated, they all _concurrently_ run any functions marked with the `schedule.OrdinanceEvent.PLUGIN_START` flag. These functions will be started when the scheduler starts ticking; however, you cannot be sure that this function will be run before any other scheduled functions. This function gets no special treatment, and will be treated the same as any other event-driven function -- meaning other functions may run *before* or *during* this event. Be wary of race conditions.

### Shutdown

Some plugins will need to do certain actions before destruction, like `join()`ing a thread, closing a server, or saving a file.

```python
    @scheduler.run_at_plugin_stop()
    def my_close_func(self):
        pass
```

This is the function to do such things. This function is called concurrently among the plugins when the `ordinance.core.Core` is destructed. Again, similar to startup functions, the scheduler will not stop ticking before this function is called. You cannot be sure that no scheduled functions will be in the middle of running when this function is called. Again, be wary of race conditions.

## Time-based functions

Time-based scheduler functions exist, for scheduling a function to run periodically at a set interval, and for scheduling a function to run once a day at a certain time.

```python
    @schedule.run_periodically(minutes=30)
    def my_half_hour_func(self):
        writer.info("This runs every half hour!")
```

```python
    @schedule.run_daily_at(hour=6, minute=45)
    def my_daily_func(self):
        writer.info("This runs every day at 6:45AM!")
```

Functions can be scheduled to be run, either with `run_periodically` to run a function at some time interval, or `run_daily_at` if you want the function to be run at a certain time every day.

## Stacking and combining decorators

Decorators can be stacked, as many as you need, like follows:

```python
    @schedule.run_periodically(hours=2)
    @schedule.run_periodically(hours=7)
    @schedule.run_daily_at(hour=0, minute=0, second=0)
    @schedule.run_at_plugin_start()
    def my_func(self): pass
```

<br>

# 6. Databases

There are two "models" of data storages, storing different "kinds" of data; however, both types are synced to files on the disk with `flush()` and `read()`. Any classes derived from `ordinance.database.BaseKeyValueDatabase` is a key-value type storage, similar to python's `dict`, and any classes derived from `ordinance.database.BaseDataset` is a list of unique entries, similar to python's `set`.


## Thread safety
Note that these data storages are thread-safe. All database and dataset actions acquire an underlying `threading.Lock`. This is to ensure data stores are compatible with plugins utilizing the `ordinance.schedule` module's scheduled and event-triggered method decorators.

## File IO

Both data storage models have similar methods for syncing and writing to its underlying file:
```python
database = ordinance.database.StringDatabase('my_string_db')
dataset = ordinance.database.StringDataset('my_string_ds')

database.read()
database.flush()

dataset.read()
dataset.flush()
```

## Python built-in methods

Both data storage models also have built-in python methods for ease of use:
```python
database.set('my_key', '10')
dataset.add('10')

print(len(database))  # 1
print(len(dataset))   # 1

print('my_key' in database)     # True
print('other_key' in database)  # False

print('10' in database)  # False -- this isn't a key!
print('10' in dataset)   # True
```

## Type casting

Values, if not of the correct type, will attempt to be type casted:
```python
database = ordinance.database.StringDatabase(...)
database.set('some_key', 10)
database.get('some_key')  # returns '10'
```
If type-casting fails, a `TypeError` will be raised:
```python
database = ordinance.database.IntDatabase(...)
database.set('some_key', 'some_string')
# TypeError: Value could not be type-casted to match database type
```

## Databases

Key-value databases have strings for keys and some given type for values. They are simple to create; for example, to create a database of strings:
```python
database = ordinance.database.StringDatabase(...)
```

Adding, overwriting, and deleting information is simple:
```python
database.set('my_key', 'my_key_value')
database.set('my_other_key', 'my_other_key_value')

print(database.get('my_key'))  # 'my_key_value'

print(len(database))  # 2
database.delete('my_other_key')
print(len(database))  # 1
```

Note that keys must be strings. Values must be the associated type, or be type-castable to that type.

Key-value databases contain the following methods for modifying key/value pairs:
- `get(key, default=None)`: Gets the value associated with the given key.
- `set(key, value)`: Sets the given key to the given value.
- `delete(key)`: Deletes the given key.
- `clear()`: Clears all key/value pairs.

Key-value databases also have the following iterators, which function similar to python's `dict` iterator methods:
- `keys()`: Iterates over database keys.
- `values()`: Iterates over database values.
- `items()`: Iterates over the database, yeilding a tuple `Tuple(key, value)` each iteration.

## Datasets

Datasets are similar to databases in some ways, but differ in that they are simple sets of data, rather than key-value stores. They are similar to python's `set` in that they are of no specific order and can only contain a certain value once. They are also simple to define; for example, a string dataset:
```python
dataset = ordinance.dataset.StringDataset(...)
```

Datasets have similar methods for data manipulation as a python `set`:
```python
dataset.add('google.com')
dataset.add('youtube.com')
dataset.add('github.com')

print('google.com' in dataset)  # True
dataset.remove('google.com')
print('google.com' in dataset)  # False
```

Note that all values added, deleted, or checked will be type-casted.

Datasets contain the following methods for modifying values:
- `add(value)`: Adds the value to this dataset.
- `delete(value)`: Removes the value from this dataset.
- `clear()`: Clears all values.

The entire dataset can be replaced with the `update_to` method. This clears all values and replaces them with the values in the given set. Note that all the values in the new set are type-casted accordingly:
```python
dataset = ordinance.database.StringDataset(...)
dataset.add(10)  # type-casted to '10'

other_set = set()
other_set.add(20)  # kept as integer

dataset.update_to(other_set)  # all values are type-casted here!
print(list(dataset.iter()))  # ['20']
```

Key-value databases also have one iterator:
- `iter()`: Iterates over the dataset, returning a value each iteration.

Datasets also allow for simple set operations, with a few differences. **Note that arguments passed to these functions must be of type python `set`, and not `ordinance.database.BaseDataset`**:
- `intersection(set)`: Returns a set containing any items in BOTH this dataset and the given set.
- `union(set)`: Returns a set containing any items in EITHER this dataset or the given set.
- `diff(set)`: Returns a tuple `(a, b)` where `a` is a set containing any items unique to the given set, and `b` is a set containing any items unique to this dataset.

## Custom Data Storages

Ordinance allows for custom implementations of both `ordinance.database.BaseKeyValueDatabase` and `ordinance.database.BaseDataset`. To create this, you must override three functions: `_serialize`, `_deserialize`, and `_value_type`. These define how the database or dataset is written to disk, read from the disk, and how values are type-casted.

For demonstration purposes, let's review the source code to the `StringDatabase` class. This class functions with both `key` and `value` being strings. It stores its data on the disk by first storing the number of entries, as an 8-bit integer, and then each key-value pair. Each key and each value is written first as a two-byte integer for that key or value's length, and then the key/value encoded in utf-8. If that doesn't make sense, the source code below might. *Note that this source code is much simplified from, and more annotated than, the original source code for the `StringDatabase` class. Integrity checks, length checks, and checksums are missing, and should probably be implemented in custom databases and datasets to ensure the data is not corrupted, and to ensure the data isn't for some other type of database or dataset.*

For the `_serialize` method, a file handler is given to the method, as well as a static copy of the database/dataset data:
```python
def _serialize(self, file: io.BufferedWriter, data: Dict[str, str]) -> None:
    num_entries = len(data)
    file.write(num_entries.to_bytes(8))
    for k,v in data.items():
        # encode key and value to bytes
        k = k.encode()
        v = v.encode()
        # write the key -- two bytes for length, n bytes for key
        file.write( len(k).to_bytes(2) )
        file.write( k )
        # write the value -- two bytes for length, n bytes for value
        file.write( len(v).to_bytes(2) )
        file.write( v )
```

Similarly, for the `_deserialize` method, a file handler is given to the method, and the method returns the deserialized data:
```python
def _deserialize(self, file: io.BufferedReader) -> Dict[str, str]:
    out = {}
    num_entries = int.from_bytes(file.read(8))
    for i in range(num_entries):
        # read the key -- two bytes for length, n bytes for key
        keysize = int.from_bytes(file.read(2))
        key = file.read(keysize)
        # read the value -- two bytes for length, n bytes for value
        valsize = int.from_bytes(file.read(2))
        val = file.read(valsize)
        # decode and store this key/value pair
        key = key.decode()
        val = val.decode()
        out[key] = val
    return out
```

Finally, for the `_value_type` method, a value is passed to the method, and the method returns the correctly-typed value. If the value is invalid, or cannot be type-casted, a `ValueError` should be raised:
```python
def _value_type(self, value: Any) -> Any:
    try: return str(value)
    except: raise ValueError()
```

That's all there is to defining a custom database or dataset. It can then be used like any other `ordinance.database` class.
```python
from ordinance.database import BaseKeyValueDatabase, BaseDataset

class MyDatabase(BaseKeyValueDatabase):
    def _serialize(...): ...
    def _deserialize(...): ...
    def _value_type(...): ...

class MyDataset(BaseDataset):
    def _serialize(...): ...
    def _deserialize(...): ...
    def _value_type(...): ...

db = MyDatabase(...)
db.set(...)
# ...etc

ds = MyDataset(...)
ds.add(...)
# ...etc
```

Note that for `_serialize` and `_deserialize`, the file index will not be at 0; there is a special header on all Ordinance database and dataset files to ensure any random file isn't loaded as data, but only a proper data storage file. This header also warns the user against modifying the file, lest the data be corrupted.

# 7. Network utilities

The `ordinance.network` module contains a few networking utilities, like IP address manipulation and global black+whitelists.

## IPv4 address manipulation

This module contains the following helper methods for manipulating IPv4 addresses:
- `clean_ip(ip)`: Cleans the given IPv4 address.
- `is_addr_within_network(ip, net)`: Returns a boolean value indicating if the given address is within the given network.
- `is_valid_ipv4(ip)`: Returns a boolean value indicating if the given address is a valid IPv4 address.
- `ip_to_int(ip)`: Returns the integer encoding of the given IPv4 address.
- `int_to_ip(iip)`: Returns the dotted string encoding (e.x. `'127.0.0.1'`) of the given integer-encoded address.

## IPv6 address manipulation

Not implemented yet. Check back soon.

## Global blacklist/whitelist

Ordinance has a built-in global blacklist and whitelist that plugins can utilize. This is as simple as operating on `ordinance.network.blacklist` or `ordinance.network.whitelist`:
```python
ordinance.network.whitelist.add('127.0.0.1')
```
The global blacklist can then be flushed to iptables (and, accordingly so, take effect on the host system) with the `ordinance.network.flush_blacklist_to_iptables()` method, explained below. This flushing is not done every time an address is added or removed to improve efficiency with adding or removing large sets of addresses, like with, for example, a remote known bad address list, such as [BinaryDefense's banlist](https://www.binarydefense.com/banlist.txt).

## IPtables interfaces

This module also contains the following IPtables interfaces:
- `create_iptables_rule(rule_type, port_type, port)`: Creates an iptables rule corresponding to the given arguments. Can be an `ACCEPT`, `DROP`, or `REJECT` rule, corresponding to a `tcp` or `udp` port.
- `delete_iptables_rule(rule_type, port_type, port)`: Deletes an iptables rule corresponding to the given arguments. Same limitations apply as above.
- `flush_blacklist_to_iptables()`: Flushes the global blacklist (see above) to iptables. Note that this operates via ipset, rather than a long list of iptables rules, for efficiency.

## IPv4 Dataset class

The `ordinance.network` module also defines a dataset (inheriting from `ordinance.database.BaseDataset`) that can more efficiently store IPv4 addresses on the disk. This is what `ordinance.network.blacklist` and `ordinance.network.whitelist` are instances of.
```python
print(
  isinstance(ordinance.network.blacklist, ordinance.network.IPv4Dataset),
  isinstance(ordinance.network.whitelist, ordinance.network.IPv4Dataset))
# True True
```
Note that given IP addresses will be type-casted to their integer versions. This is important for the `iter()` method -- all addresses will be in their integer-encoded variant. This does, however, mean that both integer-encoded and string-encoded IPv4 addresses can be used for all other methods:
```python
my_ip_list = ordinance.network.IPv4Dataset(...)

my_ip_list.add('127.0.0.1')
print('127.0.0.1' in my_ip_list)  # True
print('127.0.0.2' in my_ip_list)  # False

# note that the integer-encoded variant of '127.0.0.1' is 2130706433, or 0x7F000001
print(0x7F000001 in my_ip_list)  # True
print(0x7F000002 in my_ip_list)  # False

# important! iter() uses integer-encoded versions of addresses!
print(list(my_ip_list.iter()))  # [2130706433]
```
Using an `ordinance.network.IPv4Dataset` rather than, say, an `ordinance.database.StringDataset` results in a very large space improvement on the disk as well as in memory. In the worst-case scenario, `StringDataset` uses up to 17 bytes per address, whereas `IPv4Dataset` only uses 4 bytes -- less than 24% of the original required space.

## IPv6 Dataset class

Not implemented yet. Check back soon.
