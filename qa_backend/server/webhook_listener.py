# server/webhook_listener.py
"""
Listens for a webhook message, then fires a signal to notify someone else
"""

import os
from typing import Dict, Any, Protocol, List

import aiohttp
import aiohttp.web
from aiohttp.web import Request, Response

class WebhookFilter(Protocol):
    def __call__(self, message: Dict[str,Any]) -> bool:
        ...

class WebhookListener:
    notify_pid: int
    notify_sig: int
    host: str
    path: str
    port: int
    webhook_filters: List[WebhookFilter]
    def __init__(
            self, notify_pid: int, notify_sig: int,
            host: str = '0.0.0.0', path: str = '/webhook',
            port: int = 8083, webhook_filters: List[WebhookFilter] = [],
        ):
        self.host = host
        self.path = path
        self.port = port
        self.webhook_filters = webhook_filters

    async def webhook(self, request: Request) -> Response:
        body = await request.json()
        if all([webhook_filter(body) 
                for webhook_filter in self.webhook_filters]):
            os.kill(self.notify_pid, self.notify_sig)
        return Response()

    def run(self):
        app = web.Application()
        app.add_routes([
            web.get(self.path, self.webhook),
        ])
        web.run_app(app, host=self.host, port=self.port)

