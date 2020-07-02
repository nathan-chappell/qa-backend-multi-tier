# __init__.py
"""
Question Answer interfaces and implementations
"""

import logging

log = logging.getLogger('qa')

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

from .. import QAAnswer
from .abstract_qa import QA
from .abstract_qa import QAQueryError
from .transformers_qa import TransformersQA
from .regex_qa import RegexQA
from .micro_adapter_qa import MicroAdapter

