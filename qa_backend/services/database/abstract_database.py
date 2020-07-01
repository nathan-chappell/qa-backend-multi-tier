# abstract_database.py
"""
Abstract database requires basic CRUD functionality:
"""

from abc import ABC, abstractmethod
from typing import Iterable, Callable, Coroutine, Any
import functools
import logging

from qa_backend import Configurable
from .. import Paragraph, DocId

AsyncMethod = Callable[..., Coroutine[Any,Any,Any]]

log = logging.getLogger('database')

def acquire_lock(f: AsyncMethod) -> AsyncMethod:
    @functools.wraps(f)
    async def wrapped(self, *args, **kwargs):
        log.warn('not acquiring lock')
        #await self.lock.acquire()
        result = await f(self, *args, **kwargs)
        #self.lock.release()
        return result
    return wrapped

class Database(Configurable):
    @abstractmethod
    async def create(
            self, 
            paragraph: Paragraph
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
            paragraph: Paragraph
        ) -> None:
        ...

    @abstractmethod
    async def delete(
            self,
            doc_id: DocId
        ) -> None:
        ...

    async def shutdown(self):
        pass

class QueryDatabase(Database):
    @abstractmethod
    async def query(
            self,
            query_string: str,
            size: int
        ) -> Iterable[Paragraph]:
        ...
