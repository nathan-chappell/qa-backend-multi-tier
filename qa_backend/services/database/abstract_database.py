# abstract_database.py
"""
Abstract database requires basic CRUD functionality:
"""

from abc import ABC, abstractmethod
from typing import Iterable, Callable, Coroutine, Any, List
import functools
import logging
from pathlib import Path

from qa_backend import Configurable
from .. import Paragraph, DocId
from .database_error import *

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
            docId: DocId
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
            docId: DocId
        ) -> None:
        ...

    async def shutdown(self):
        pass

    async def get_all(self) -> List[Paragraph]:
        pass

    # TODO: test, add to api
    async def add_directory(self, directory_name):
        directory_path = Path(directory_name)
        if not directory_path.exists():
            msg = f'{directory_name} does not exist'
            raise DatabaseCreateError(msg)
        paths = directory_path.glob('*.txt')
        for path in paths:
            log.debug(f'adding path: {path}')
            with open(path) as file:
                text = file.read()
            try:
                await self.create(Paragraph(path.name, text))
            except DatabaseAlreadyExistsError as e:
                msg = f'{path.name} alread exists'
                log.info(msg)

    # TODO: test, add to api
    async def dump_to_directory(self, directory_path: Path):
        all_paragraphs = await self.get_all()
        for paragraph in all_paragraphs:
            with open(directory_path / paragraph.docId,'w') as file:
                file.write(paragraph.text)

class QueryDatabase(Database):
    @abstractmethod
    async def query(
            self,
            query_string: str,
            size: int
        ) -> Iterable[Paragraph]:
        ...
