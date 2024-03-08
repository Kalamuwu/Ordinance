import threading
import json
import os
import io

from os import PathLike
from typing import Dict, Tuple, Set, Union, Optional, Any



# module globals

LOCAL_DATABASE_HEADER = b"Ordinance local data storage file. Do not edit, or the data will be corrupted.\n---\n"

def parse_path(path: str) -> str:
    # ensure path is to a good file
    if os.path.exists(path):
        if not os.path.isfile(path):
            raise OSError(f"Path '{path}' exists, but is not a file!")
    else:
        # file doesn't exist. create it
        with open(path, 'wb') as file:
            file.write(LOCAL_DATABASE_HEADER)
    # all is good! return.
    return path


# base classes

class BaseKeyValDatabase:
    def __init__(self, path: str, name: Optional[str] = ""):
        self.__db: Dict[str, Any] = {}
        self.__name = name
        self.__lock = threading.Lock()
        self.__path = parse_path(path)
    
    @property
    def name(self) -> str: return self.__name
    
    # helper functions
    
    def __contains__(self, key: str) -> bool:
        try: value = self._value_type(value)
        except ValueError: raise TypeError("Value could not be type-casted to match database type")    
        with self.__lock:
            return key in self.__db
    
    def __len__(self) -> int:
        with self.__lock:
            return len(self.__db)
    
    def items(self):
        with self.__lock:
            for item in self.__db.items(): yield item
    
    def keys(self):
        with self.__lock:
            for key in self.__db.keys(): yield key
    
    def values(self):
        with self.__lock:
            for value in self.__db.values(): yield value
    
    def get(self, key: str, default: Optional[Any] = ...) -> Any:
        if not isinstance(key, str): raise TypeError("Key must be a str")
        with self.__lock:
            if key in self.__db: return self.__db[key]           # key found! return it
        if default is ...: raise KeyError(f"Unknown key {key}")  # key not found and default not specified
        try: return self._value_type(default)                    # key not found and default specified; type-cast default
        except ValueError: raise TypeError("Default could not be type-casted to match database value type")

    def set(self, key: str, value: Any) -> None:
        if not isinstance(key, str): raise TypeError("Key must be a str")
        with self.__lock:
            try: self.__db[key] = self._value_type(value)
            except ValueError: raise TypeError("Value could not be type-casted to match database type")
    
    def delete(self, key: str) -> None:
        if not isinstance(key, str): raise TypeError("Key must be a str")
        with self.__lock: del self.__db[key]
    
    def clear(self) -> None:
        with self.__lock:  self.__db = {}
    
    # file io wrappers

    def flush(self):
        with self.__lock:
            with open(self.__path, 'wb') as file:
                file.write(LOCAL_DATABASE_HEADER)
                self._serialize(file, self.__db)
    
    def read(self, _create_if_not_exists=True):
        if not os.path.exists(self.__path):
            if _create_if_not_exists:
                with open(self.__path, 'wb') as file:
                    file.write(LOCAL_DATABASE_HEADER)
            else:
                raise FileNotFoundError(self.__path)
            return
        with self.__lock:
            with open(self.__path, 'rb') as file:
                # check header
                data = file.read(len(LOCAL_DATABASE_HEADER))
                if data != LOCAL_DATABASE_HEADER:
                    raise OSError(f"Database file '{self.__path}' is corrupted!")
                self.__db = self._deserialize(file)

    # functions that must be defined by inherited classes

    def _serialize(  self, file: io.BufferedWriter, data: Dict[str, Any]) -> None:  raise NotImplementedError()
    def _deserialize(self, file: io.BufferedReader) ->    Dict[str, Any]:           raise NotImplementedError()
    def _value_type( self, value: Any) -> Any:                                      raise NotImplementedError()

class BaseDataset:
    def __init__(self, path: str, name: Optional[str] = ""):
        self.__db: Set[Any] = set()
        self.__name = name
        self.__lock = threading.Lock()
        self.__path = parse_path(path)
    
    @property
    def name(self) -> str: return self.__name
    
    # builtin functions
    
    def __contains__(self, value: Any) -> bool:
        try: value = self._value_type(value)
        except ValueError: raise TypeError("Value could not be type-casted to match database type")    
        with self.__lock:
            return value in self.__db
    
    def __len__(self) -> int:
        with self.__lock:
            return len(self.__db)
    
    # helper functions
    
    def iter(self):
        with self.__lock:
            for item in self.__db: yield item
    
    def add(self, value: Any) -> None:
        try: value = self._value_type(value)
        except ValueError: raise TypeError("Value could not be type-casted to match database type")
        with self.__lock:
            self.__db.add(value)
    
    def delete(self, value: Any) -> None:
        try: value = self._value_type(value)
        except ValueError: raise TypeError("Value could not be type-casted to match database type")
        with self.__lock:
            self.__db.remove(value)
    
    def update_to(self, values: set) -> None:
        typed = set()
        for value in values:
            try: value = self._value_type(value)
            except ValueError: raise TypeError("Value could not be type-casted to match database type")
            else: typed.add(value)
        with self.__lock:
            self.__db = typed
    
    def clear(self) -> None:
        with self.__lock:
            self.__db.clear()
    
    # standard set operations
    
    def intersection(self, other: set) -> set:
        """
        Returns a set containing all items in BOTH this set and set `other`.
        """
        typed = set()
        with self.__lock:
            for value in other:
                try: value = self._value_type(value)
                except ValueError: raise TypeError("Value could not be type-casted to match database type")
                if value in self.__db: typed.add(value)
        return typed
    
    def union(self, other: set) -> set:
        """
        Returns a set containing all items in EITHER this set or set `other`.
        """
        typed = set()
        with self.__lock:
            for value in other:
                try: value = self._value_type(value)
                except ValueError: raise TypeError("Value could not be type-casted to match database type")
                typed.add(value)
            return typed + self.__db
    
    def diff(self, other: set) -> Tuple[set, set]:
        """
        Returns a tuple (a, b) where:
            a   is items that are unique to set `other`, and
            b   is items that are unique to this set.
        """
        typed = set()
        for value in other:
            try: value = self._value_type(value)
            except ValueError: raise TypeError("Value could not be type-casted to match database type")
            else: typed.add(value)
        with self.__lock:
            return (typed - self.__db, self.__db - typed)
    
    # file io wrappers

    def flush(self):
        with self.__lock:
            with open(self.__path, 'wb') as file:
                file.write(LOCAL_DATABASE_HEADER)
                self._serialize(file, self.__db)
    
    def read(self, _create_if_not_exists=True):
        if not os.path.exists(self.__path):
            if _create_if_not_exists:
                with open(self.__path, 'wb') as file:
                    file.write(LOCAL_DATABASE_HEADER)
            else:
                raise FileNotFoundError(self.__path)
            return
        with self.__lock:
            with open(self.__path, 'rb') as file:
                # check header
                data = file.read(len(LOCAL_DATABASE_HEADER))
                if data != LOCAL_DATABASE_HEADER:
                    raise OSError(f"Database file '{self.__path}' is corrupted!")
                self.__db = self._deserialize(file)

    # functions that must be defined by inherited classes

    def _serialize(  self, file: io.BufferedWriter, data: Set[Any]) -> None:  raise NotImplementedError()
    def _deserialize(self, file: io.BufferedReader) ->    Set[Any]:           raise NotImplementedError()
    def _value_type( self, value: Any) -> Any:                                raise NotImplementedError()



# predefined database types

class IntDatabase(BaseKeyValDatabase):
    """
    Stores (key, value) (`str`, `int`) pairs.
    Inherits from :class:`ordinance.database.BaseKeyValDatabase`.
    
    Data in the file is laid out as follows:

    ```
    eight bytes
    containing
    the num of
    k+v entries        one such entry
    .----|----. .------------|------------.
    AA ..... AA BB BB CC....CC DD EE....EE [more entries]-->
    ```
    Each entry consists of:
    
    `BB BB`     Two bytes for the length of this key\n
    `CC....CC`  N bytes, decoded in utf-8 to produce the string key\n
    `DD`        One byte for the length of this value\n
    `EE....EE`  N bytes for the value itself
    """
    def _serialize(self, file: io.BufferedWriter, data: Dict[str, int]) -> None:
        num_entries = len(data)
        file.write(num_entries.to_bytes(8))
        for k,v in data.items():
            k = k.encode(); v = v.to_bytes(2)
            file.write( len(k).to_bytes(4) ); file.write( k )
            file.write( len(v).to_bytes(1) ); file.write( v )
    
    def _deserialize(self, file: io.BufferedReader) -> Dict[str, int]:
        out = {}
        def read_n(n: int):
            data = file.read(n)
            if len(data) != n: raise ValueError()
            return data
        num_entries = int.from_bytes(file.read(8))
        for i in range(num_entries):
            keysize = int.from_bytes(read_n(2))
            key     =                read_n(keysize).decode()
            valsize = int.from_bytes(read_n(1))
            val     = int.from_bytes(read_n(valsize))
            out[key] = val
        return out
    
    def _value_type(self, value: Any) -> Any:
        try: return int(value)
        except: raise ValueError()

class StringDatabase(BaseKeyValDatabase):
    """
    Stores (key, value) pairs where both key and value are strings.
    Inherits from :class:`ordinance.database.BaseKeyValDatabase`.
    
    Data in the file is laid out as follows:

    ```
    eight bytes
    containing
    the num of
    k+v entries         one such entry
    .----|----. .-------------|-------------.
    AA ..... AA BB BB CC....CC DD DD EE....EE [more entries]-->
    ```
    Each entry consists of:
    
    `BB BB`     Two bytes for the length of this key\n
    `CC....CC`  N bytes, decoded in utf-8 to produce the string key\n
    `DD DD`     Two bytes for the length of this value\n
    `EE....EE`  N bytes, decoded in utf-8 to produce the string value
    """
    def _serialize(self, file: io.BufferedWriter, data: Dict[str, str]) -> None:
        num_entries = len(data)
        file.write(num_entries.to_bytes(8))
        for k,v in data.items():
            k = k.encode(); v = v.encode()
            file.write( len(k).to_bytes(2) ); file.write( k )
            file.write( len(v).to_bytes(2) ); file.write( v )
    
    def _deserialize(self, file: io.BufferedReader) -> Dict[str, str]:
        out = {}
        def read_n(n: int):
            data = file.read(n)
            if len(data) != n: raise ValueError()
            return data
        num_entries = int.from_bytes(file.read(8))
        for i in range(num_entries):
            keysize = int.from_bytes(read_n(2))
            key     =                read_n(keysize).decode()
            valsize = int.from_bytes(read_n(2))
            val     =                read_n(valsize).decode()
            out[key] = val
        return out
    
    def _value_type(self, value: Any) -> Any:
        try: return str(value)
        except: raise ValueError()

class BoolDatabase(BaseKeyValDatabase):
    """
    Stores (key, value) (`str`, `bool`) pairs.
    Inherits from :class:`ordinance.database.BaseKeyValDatabase`.
    
    Data in the file is laid out as follows:

    ```
    eight bytes
    containing
    the num of     one such
    k+v entries     entry
    .----|----. .-----|------.
    AA ..... AA BB BB CC....CC [more entries ...] [packed_values]
    ```
    Each entry consists of:
    
    `BB BB`     Two bytes for the length of this key\n
    `CC....CC`  N bytes, decoded in utf-8 to produce the string key

    Bytes are then read from the file, and each is decomposed into 8 bits. This
    set of bits is then read as bools for the LAST eight keys, and this
    repeats until no more keys are stored.
    """
    def __reverse_byte(self, n: int) -> int:
        out = 0
        for i in range(8):
            out |= ((n >> (7-i)) & 1) << i
        return out
    
    def _serialize(self, file: io.BufferedWriter, data: Dict[str, bool]) -> None:
        num_entries = len(data)
        file.write(num_entries.to_bytes(8))
        # write keys
        for k in data.keys():
            k = k.encode()
            file.write( len(k).to_bytes(2) ); file.write( k )
        # pack vals
        packed = 0
        for v in data.values():
            packed <<= 1
            packed |= v
        # pad to integer multiple of byte width
        if r:=num_entries%8:
            packed <<= 8 - r
            num_entries += r
        # write packed vals
        file.write(packed.to_bytes(num_entries//8))
    
    def _deserialize(self, file: io.BufferedReader) -> Dict[str, bool]:
        keys = []
        def read_n(n: int):
            data = file.read(n)
            if len(data) != n: raise ValueError()
            return data
        num_entries = int.from_bytes(read_n(8))
        # read keys
        for i in range(num_entries):
            keysize = int.from_bytes(read_n(2))
            key = read_n(keysize).decode()
            keys.append(key)
        # read vals
        r = num_entries%8
        packed = int.from_bytes(file.read( (num_entries+r) // 8 ))
        packed >>= r  # undo to-multiple-integer-of-full-byte padding
        # assign vals to keys
        out = {}
        for i in range(num_entries):
            out[keys.pop()] = bool( packed & 1 )
            packed >>= 1
        return out
    
    def _value_type(self, value: Any) -> Any:
        try: return bool(value)
        except: raise ValueError()

class BytesDatabase(BaseKeyValDatabase):
    """
    Stores (key, value) (`str`, `bytes`) pairs.
    Inherits from :class:`ordinance.database.BaseKeyValDatabase`.
    
    Data in the file is laid out as follows:

    ```
    eight bytes
    containing
    the num of
    k+v entries         one such entry
    .----|----. .-------------|-------------.
    AA ..... AA BB BB CC....CC DD DD EE....EE [more entries]-->
    ```
    Each entry consists of:
    
    `BB BB`     Two bytes for the length of this key\n
    `CC....CC`  N bytes, decoded in utf-8 to produce the string key\n
    `DD DD`     Two bytes for the length of this value\n
    `EE....EE`  N bytes for the value itself
    """
    def _serialize(self, file: io.BufferedWriter, data: Dict[str, bytes]) -> None:
        num_entries = len(data)
        file.write(num_entries.to_bytes(8))
        for k,v in data.items():
            k = k.encode()
            file.write( len(k).to_bytes(2) ); file.write( k )
            file.write( len(v).to_bytes(2) ); file.write( v )
    
    def _deserialize(self, file: io.BufferedReader) -> Dict[str, bytes]:
        out = {}
        def read_n(n: int):
            data = file.read(n)
            if len(data) != n: raise ValueError()
            return data
        num_entries = int.from_bytes(file.read(8))
        for i in range(num_entries):
            keysize = int.from_bytes(read_n(2))
            key     =                read_n(keysize).decode()
            valsize = int.from_bytes(read_n(2))
            val     =                read_n(valsize)
            out[key] = val
        return out
    
    def _value_type(self, value: Any) -> Any:
        try:
            if value is None:              return b''
            elif isinstance(value, bytes): return value
            elif isinstance(value, str):   return value.encode()
            elif isinstance(value, int):
                # this one needs special handling -- calc number of bytes
                # needed to store this number, for any arbitrarily large number
                n = value.bit_length()
                r = n%8
                if r: n += 8-r
                return value.to_bytes( n // 8 )
        except: raise ValueError()




# predefined datalist types

class IntDataset(BaseDataset):
    """
    Stores a set of unique integers.
    Inherits from :class:`ordinance.database.BaseDataset`.
    
    Data in the file is laid out as follows:

    ```
    eight bytes
    containing
    the num of    one such
      entries      entry
    .----|----. .----|----.
    AA ..... AA BB CC....CC [more entries]-->
    ```
    Each entry consists of:
    
    `BB`        One byte for the length of this value\n
    `CC....CC`  N bytes for the value itself
    """
    def _serialize(self, file: io.BufferedWriter, data: Set[int]) -> None:
        num_entries = len(data)
        file.write(num_entries.to_bytes(8))
        for v in data:
            v = v.to_bytes(4)
            file.write( len(v).to_bytes(1) ); file.write( v )
    
    def _deserialize(self, file: io.BufferedReader) -> Set[int]:
        out = set()
        def read_n(n: int):
            data = file.read(n)
            if len(data) != n: raise ValueError()
            return data
        num_entries = int.from_bytes(file.read(8))
        for i in range(num_entries):
            valsize = int.from_bytes(read_n(1))
            val     = int.from_bytes(read_n(valsize))
            out.add(val)
        return out
    
    def _value_type(self, value: Any) -> Any:
        try: return int(value)
        except: raise ValueError()

class StringDataset(BaseDataset):
    """
    Stores a set of unique strings.
    Inherits from :class:`ordinance.database.BaseDataset`.
    
    Data in the file is laid out as follows:

    ```
    eight bytes
    containing
    the num of
      entries      one such entry
    .----|----. .---------|--------.
    AA ..... AA BB BB BB BB CC....CC [more entries]-->
    ```
    Each entry consists of:
    
    `BB BB BB BB`  Four bytes for the length of this value\n
    `CC....CC`     N bytes, decoded in utf-8 to produce the string value
    """
    def _serialize(self, file: io.BufferedWriter, data: Set[str]) -> None:
        num_entries = len(data)
        file.write(num_entries.to_bytes(8))
        for v in data:
            v = v.encode()
            file.write( len(v).to_bytes(4) ); file.write( v )
    
    def _deserialize(self, file: io.BufferedReader) -> Set[str]:
        out = set()
        def read_n(n: int):
            data = file.read(n)
            if len(data) != n: raise ValueError()
            return data
        num_entries = int.from_bytes(file.read(8))
        for i in range(num_entries):
            valsize = int.from_bytes(read_n(4))
            val = read_n(valsize).decode()
            out[key] = val
        return out
    
    def _value_type(self, value: Any) -> Any:
        try: return str(value)
        except: raise ValueError()

