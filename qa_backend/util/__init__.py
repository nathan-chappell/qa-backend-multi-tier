# util/__init__.py
"""
Various utilities for the qa backend
"""

# Sequence is used because it's type argument is covariant

from abc import ABC
from abc import abstractmethod
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

from .logging_ import set_all_loglevels
from .serialization import JsonRepresentation
from .serialization import Paragraph
from .serialization import QAAnswer

log = logging.getLogger('util')

def exception_to_dict(exception: Exception, log_error=False) -> Dict[str,Any]:
    """Convert an exception into a dict for JSON response."""
    if log_error:
        log.error(f'converting exception: {str(exception)}')
        if os.environ.get('PRINT_TB'):
            log.error(format_tb(sys.exc_info()[2]))
    return {'error_type': type(exception).__name__, 'message': str(exception)}

class ConfigurationError(ValueError): pass

class Configurable(ABC):
    """Abstraction for classes which may be constructed from config section"""
    @staticmethod
    @abstractmethod
    def from_config(
            section: MutableMapping[str,str]
        ) -> Union['Configurable', Sequence['Configurable']]:
        ...

def check_config_keys(section: MutableMapping[str,str], keys: List[str]):
    key_set = set(section.keys())
    if not set(section.keys()) <= set(keys):
        unk_keys = key_set - set(keys)
        msg = f'Unknown keys in config: {", ".join(list(unk_keys))}'
        raise ValueError(msg)

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

