# git_es_database.py
"""
Combine a git and es database
"""

from asyncio import Lock
from typing import Optional, Iterable

from .abstract_database import DocId, Paragraph, QueryDatabase, acquire_lock
from .es_database import ElasticsearchDatabase
from .git_database import GitDatabase

from .database_error import DatabaseError
from .database_error import DatabaseCreateError, DatabaseUpdateError
from .database_error import DatabaseDeleteError, DatabaseReadError

class GitEsDatabase(QueryDatabase):
    git_database: GitDatabase
    es_database: ElasticsearchDatabase
    lock: Lock

    def __init__(
            self,
            git_database: GitDatabase,
            es_database: ElasticsearchDatabase,
            lock: Optional[Lock] = None
        ):
        self.git_database = git_database
        self.es_database = es_database
        if isinstance(lock, Lock):
            self.lock = lock
        else:
            self.lock = Lock()

    @acquire_lock
    async def create(
            self, 
            paragraph: Paragraph
        ) -> None:
        try:
            # when this fails, the paragraphs is not added to the directory
            await self.git_database.create(paragraph)
        except DatabaseCreateError:
            raise
        try:
            # when this fails, it must be removed from the git
            await self.es_database.create(paragraph)
        except DatabaseCreateError:
            # rollback
            await self.git_database.reset('@^')
            raise

    @acquire_lock
    async def read(
            self,
            doc_id: DocId
        ) -> Iterable[Paragraph]:
        # here we appeal only to the git_database
        return await self.git_database.read(doc_id)

    @acquire_lock
    async def update(
            self,
            paragraph: Paragraph
        ) -> None:
        try:
            # here we appeal only to the git_database
            await self.git_database.update(paragraph)
        except DatabaseUpdateError:
            raise
        try:
            await self.es_database.update(paragraph)
        except DatabaseUpdateError:
            await self.git_database.reset('@^')

    @acquire_lock
    async def delete(
            self,
            doc_id: DocId
        ) -> None:
        try:
            await self.git_database.delete(doc_id)
        except DatabaseDeleteError:
            raise
        try:
            await self.es_database.delete(doc_id)
        except DatabaseDeleteError:
            raise

    @acquire_lock
    async def pull(self) -> None:
        await self.git_database.pull(path)
        await self.es_database.pull(path)

    @acquire_lock
    async def query(
            self,
            query_string: str,
            size: int = 5
        ) -> Iterable[Paragraph]:
        return await self.es_database.query(query_string, size)
