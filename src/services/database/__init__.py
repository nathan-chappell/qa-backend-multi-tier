"""
Abstract database requires basic CRUD functionality:
"""

from abc import ABC
from typing import Iterable
import logging
import sys
from traceback import format_tb

from .. import Paragraph, DocId

log = logging.getLogger('database')

class DatabaseError(RuntimeError):
    message: str
    operation: str

    def __init__(self, message: str, operation: str):
        self.message = message
        self.operation = operation
        log.error(self)
        log.debug(''.join(format_tb(sys.exc_info()[2],limit=5)))

    @classmethod
    def __init_subclass__(cls: type, operation: str) -> None:
        def init(self, message: str):
            super().__init__(operation, message)
        cls.__init__ = init

    def __str__(self) -> str:
        cls = self.__class__.__name__
        op = self.operation
        msg = self.message
        return f'{cls}: [{op}]: {msg}'

    def __repr__(self) -> str:
        return f'<{str(self)}>'

class DatabaseCreateError(DatabaseError, operation='Create'): ...
class DatabaseReadError(DatabaseError, operation='Read'): ...
class DatabaseUpdateError(DatabaseError, operation='Update'): ...
class DatabaseDeleteError(DatabaseError, operation='Delete'): ...

class Database(ABC):
    @abstractmethod
    async def create(
            self, 
            paragraphs: Paragraph
        ) -> None:
        ...

    # returns an iterable for handling wildcards / not found
    @abstractmethod
    async def read(
            self,
            doc_id: DocId
        ) -> Iterable[Paragraph]:
        ...

    @abstractmethod
    async def update(
            self,
            doc_id: DocId,
            paragraph: Paragraph
        ) -> None:
        ...

    @abstractmethod
    async def delete(
            self,
            doc_ids: DocId
        ) -> None:
        ...

class QueryDatabase(ABC, Database):
    @abstractmethod
    async def query(
            self,
            query_string: str
        ) -> Iterable[Paragraph]
        ...
