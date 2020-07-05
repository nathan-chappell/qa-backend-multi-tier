# util/__init__.py
"""
Various utilities for the qa backend
"""

# Sequence is used because it's type argument is covariant

from abc import ABC
from abc import abstractmethod
from configparser import ConfigParser
from traceback import format_tb
from typing import Any
from typing import Dict
from typing import List
from typing import MutableMapping
from typing import Sequence
from typing import Union
import logging
import os
import sys

from .api_error import APIError
from .api_error import exception_middleware
from .from_request import JsonCrudOperation
from .from_request import JsonQuestion
from .from_request import JsonQuestionOptionalContext
from .logging_ import set_all_loglevels
from .serialization import JsonRepresentation
from .serialization import Paragraph
from .serialization import QAAnswer

log = logging.getLogger('util')

def convert_bool(arg: Union[str,bool]) -> bool:
    if isinstance(arg, bool):
        return arg
    elif isinstance(arg, str):
        p = ConfigParser()
        p.read_string(f"[-]\narg={arg}")
        return p['-'].getboolean('arg')
    else:
        raise RuntimeError('Unreachable')

class ConfigurationError(ValueError):
    def __init__(self, message: str):
        super().__init__(message)
        log.error(message)

class Configurable(ABC):
    """Abstraction for classes which may be constructed from config section"""
    def __init__(self, **kwargs):
        assert False and "Don't instantiate this class"

    @classmethod
    def from_config(
            cls,
            section: MutableMapping[str,str]
        ) -> Union['Configurable', Sequence['Configurable']]:
        return cls(**section)

def complete_sentence(context: str, start: int, end: int) -> str:
    """Turn the span into a complete sentence."""
    log.info(f'original span: {context[start:end+1]}')
    # note: the original span my point to a space after a full-stop.
    _start = context.rfind('.',0,start) + 1
    while context[end].isspace(): end -= 1
    if context[end] == '.':
        _end = end
    else:
        _end = context.find('.',end)
        if _end == -1:
            _end = len(context)
    return context[_start:_end].strip() + '.'

