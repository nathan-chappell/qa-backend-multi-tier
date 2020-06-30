# server/webhook_listener.py
"""
Listens for a webhook message, then fires a signal to notify someone else
"""

import os
from typing import Dict, Any, List
from json.decoder import JSONDecodeError
import logging

from typing_extensions import Protocol

import aiohttp
import aiohttp.web as web
from aiohttp.web import Request, Response

log = logging.getLogger('server')

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
        log.info(f'notify_pid: {notify_pid}, notify_sig: {notify_sig}')
        self.notify_pid = notify_pid
        self.notify_sig = notify_sig
        self.host = host
        self.path = path
        self.port = port
        self.webhook_filters = webhook_filters

    async def webhook(self, request: Request) -> Response:
        log.info(f'webhook: {request}')
        try:
            body = await request.json()
            res = [webhook_filter(body) 
                    for webhook_filter in self.webhook_filters]
            log.info(res)
            if all([webhook_filter(body) 
                    for webhook_filter in self.webhook_filters]):
                log.info(f'kill: {self.notify_pid}, {self.notify_sig}')
                os.kill(self.notify_pid, self.notify_sig)
            return Response()
        except JSONDecodeError as e:
            log.error(str(e))
            return Response(text=str(e), status=400)
        except Exception as e:
            log.error(str(e))
            return Response(text=str(e), status=500)

    def run(self):
        app = web.Application()
        app.add_routes([
            web.post(self.path, self.webhook),
        ])
        web.run_app(app, host=self.host, port=self.port)

