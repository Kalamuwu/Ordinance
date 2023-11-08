import os

from typing import (
    Dict,
    Any
)

import ordinance.writer
import ordinance.ext.network   # load this now so plugins can use it
import ordinance.ext.schedule  # load this now so plugins can use it

class OrdinancePlugin:
    """ The base class that all plugins must inherit from. """
    def __init__(self, config: Dict[str, Any]):
        ordinance.writer.info(f"{self.__class__.__name__}: Initialized.")
