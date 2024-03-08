from typing import Dict, Any

import ordinance.plugin

class TemplatePlugin(ordinance.plugin.OrdinancePlugin):
    """ A template plugin. """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.very_important_message = "Hello, Ordinance!"


# behold, the Great Setup Function - fortold
# by the incredible prophet Plugin Dot Yaml
def setup():
    return TemplatePlugin
