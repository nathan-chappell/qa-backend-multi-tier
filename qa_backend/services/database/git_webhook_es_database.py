# git_webhook_es_database.py
"""
similar to git_es, but when the webhook listener fires it reindexes everything
in elasticsearch
"""

from typing import Optional, Coroutine, Any
from asyncio import Lock

from .es_database import ElasticsearchDatabase
from .git_es_database import GitEsDatabase
from .git_webhook_database import GitWebhookDatabase

class GitWebhookEsDatabase(GitEsDatabase):
    def __init__(
            self,
            git_webhook_database: GitWebhookDatabase,
            es_database: ElasticsearchDatabase,
            lock: Optional[Lock] = None
        ):
        git_webhook_database.add_callback(self.reindex)
        super().__init__(git_webhook_database, es_database, lock)

    async def reindex(self) -> None:
        #loop.run_until_complete(self.lock
        self.es_database.initialize(erase_if_exists=True)
        paragraphs = await self.git_database.read('*')
        for paragraph in paragraphs:
            await self.es_database.create(paragraph)