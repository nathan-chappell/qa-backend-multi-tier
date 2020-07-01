# git_webhook_database.py
"""
A GitDatabase which spawns a webhook listener.
When the listener gets triggered, the database does a pull and fires an event
"""

from typing import Optional, List, Callable, Coroutine, Any, MutableMapping
from asyncio import Lock
import asyncio
import multiprocessing
import os
import signal

from qa_backend import check_config_keys, ConfigurationError
from .git_database import GitDatabase
from qa_backend.server.webhook_listener import WebhookListener

class GitWebhookDatabase(GitDatabase):
    processes: List[multiprocessing.Process]
    futures: List[asyncio.Future]
    webhook_listener: WebhookListener
    flash_callbacks: List[Callable[[],Coroutine[Any,Any,None]]]

    def __init__(
            self, git_dir: str, lock: Optional[Lock] = None,
            host='0.0.0.0', path='/webhook', port=8082, start_listener=True
        ):
        super().__init__(git_dir, lock)
        self.processes = []
        self.futures = []
        self.flash_callbacks = []
        self.webhook_listener = WebhookListener(
                os.getpid(), signal.SIGUSR1, host, path, port
            )
        if start_listener:
            self.start_listener()

    @staticmethod
    def from_config(
            config: MutableMapping[str,str]
        ) -> 'GitWebhookDatabase':
        check_config_keys(config, ['git dir', 'host', 'path', 'port'])
        try:
            git_dir = config['git dir']
            host = str(config.get('host','0.0.0.0'))
            port = int(config.get('port', 8082))
            path = str(config.get('path','/webhook'))
            return GitWebhookDatabase(git_dir,host=host,path=path,port=port)
        except ValueError as e:
            raise ConfigurationError(str(e))

    def add_callback(self, callback: Callable[[],Coroutine[Any,Any,None]]):
        self.flash_callbacks.append(callback)

    def start_listener(self):
        p = multiprocessing.Process(target=self.webhook_listener.run)
        self.processes.append(p)
        p.start()

    def kill_all_processes(self):
        for process in self.processes: 
            if process.is_alive():
                os.kill(signal.SIGINT, process.pid)
                process.terminate()
            process.join()

    def cancel_all_futures(self):
        # TODO: something smarter
        for future in self.futures:
            future.cancel()

    async def shutdown(self):
        self.kill_all_processes()
        self.cancel_all_futures()
        await asyncio.tasks.gather(*self.futures)

    async def flash_db(self):
        await self.reset()
        await self.pull()
        for callback in self.flash_callbacks:
            loop.create_task(callback())

    def handle_listener(self, signum, frame):
        loop = asyncio.get_event_loop()
        # don't wait here, we'll deadlock for sure
        task = loop.create_task(self.flash_db())
        self.futures.append(task)

    def __del__(self):
        self.kill_all_processes()
        self.cancel_all_futures()
