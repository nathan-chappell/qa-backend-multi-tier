"""
QA Server

Uses
* Git as a database backend,
* Elasticsearch as a search tool
* transformers for QA

"""

from abc import ABC, abstractmethod
# Sequence is used because it's type argument is covariant
from typing import MutableMapping, List, Union, Sequence

def check_config_keys(section: MutableMapping[str,str], keys: List[str]):
    key_set = set(section.keys())
    if not set(section.keys()) <= set(keys):
        unk_keys = key_set - set(keys)
        msg = f'Unknown keys in config: {", ".join(list(unk_keys))}'
        raise ValueError(msg)

class ConfigurationError(ValueError): pass

class Configurable(ABC):
    @staticmethod
    @abstractmethod
    def from_config(
            section: MutableMapping[str,str]
        ) -> Union['Configurable', Sequence['Configurable']]:
        ...

from .server.main_server import MainServer
