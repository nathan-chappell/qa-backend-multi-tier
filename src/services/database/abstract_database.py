# abstract_database.py
"""
Abstract database requires basic CRUD functionality:
"""

from abc import ABC, abstractmethod
from typing import Iterable

from .. import Paragraph, DocId

class Database(ABC):
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

class QueryDatabase(Database):
    @abstractmethod
    async def query(
            self,
            query_string: str,
            size: int
        ) -> Iterable[Paragraph]:
        ...
