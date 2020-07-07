# abstract_database.py
"""
Abstract database requires basic CRUD functionality:
"""

from abc import abstractmethod
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Coroutine
from typing import Iterable
from typing import List
import functools
import logging

from .database_error import *
from qa_backend.util import Configurable
from qa_backend.util import Paragraph

log = logging.getLogger('database')

DocId = str

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
        ) -> List[Paragraph]:
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
            size: int,
            qid: str = ''
        ) -> Iterable[Paragraph]:
        ...
