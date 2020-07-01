# abstract_qa.py

from abc import ABC, abstractmethod
from typing import List, Optional
import logging

from . import QAAnswer
from qa_backend import Configurable

log = logging.getLogger('qa')

class QAQueryError(RuntimeError):
    message: str

    def __init__(self, message: str):
        self.message = message
        log.error(str(self))

    def __str__(self) -> str:
        cls = self.__class__.__name__
        return f'{cls}: {self.message}'

    def __repr__(self) -> str:
        return f'<{str(self)}>'

class QA(Configurable):
    _requires_context: bool

    @abstractmethod
    async def query(self, question: str, **kwargs) -> List[QAAnswer]:
        ...

    @property
    def requires_context(self) -> bool:
        return self._requires_context

    async def shutdown(self):
        ...
