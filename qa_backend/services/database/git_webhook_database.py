# git_webhook_database.py
"""
A GitDatabase which spawns a webhook listener.
When the listener gets triggered, the database does a pull and fires an event
"""

from typing import Optional
from asyncio import Lock

from .git_database import GitDatabase

class GitWebhookDatabase(GitDatabase):
    def __init__(
            self, git_dir: str, lock: Optional[Lock] = None,
            host='0.0.0.0', port=8082
        ):
        super().__init__(git_dir, lock)
    
