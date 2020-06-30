# test_webhook_listener.py

import multiprocessing
from multiprocessing import Process
import signal
import asyncio
from aiohttp import ClientConnectionError
import logging
import unittest
import os
import atexit
import sys
import time
import json

import aiohttp
from aiohttp import ClientSession
import common

from qa_backend.server.webhook_listener import WebhookListener

log = logging.getLogger('server')

url = 'http://localhost:8083/webhook'
class ExpectedHandler(Exception): ...
class UnExpectedHandler(Exception): ...

def expected_handler(signum,frame):
    log.info('EXPECTED HANDLER')
    raise ExpectedHandler()

def unexpected_handler(signum,frame):
    log.info('UNEXPECTED HANDLER')
    raise UnExpectedHandler()

def run(ppid):
    webhook_filters = [
        lambda d: d.get('prop1') != 'attr1_',
    ]
    webhook_listener = WebhookListener(
            ppid, signal.SIGUSR1, webhook_filters=webhook_filters
        )
    webhook_listener.run()

class WebhookListener_TestActivation(unittest.TestCase):
    def setUp(self):
        self.url = url

    def test_activate(self):
        log.info('test_activate')
        signal.signal(signal.SIGUSR1, expected_handler)
        async def activate_webhook():
            body = {'prop1': 'attr1'}
            async with session.post(self.url,json=body) as response:
                log.info(response)
                status = response.status
            return status
        with self.assertRaises(ExpectedHandler):
            status = loop.run_until_complete(activate_webhook())
            time.sleep(5)

    def test_filter(self):
        log.info('test_filter')
        signal.signal(signal.SIGUSR1, unexpected_handler)
        async def activate_webhook():
            body = {'prop1': 'attr1_'}
            async with session.post(self.url,json=body) as response:
                status = response.status
            return status
        try:
            status = loop.run_until_complete(activate_webhook())
            time.sleep(5)
        except UnExpectedHandler:
            self.fail('unexpected_handler raise')

async def wait_for_server(seconds: int = 10) -> bool:
    count = 0
    while count < seconds:
        count += 1
        try:
            async with session.get(url):
                return True
        except ClientConnectionError:
            await asyncio.sleep(1)
    return False

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-r':
        run(os.getpid())
        exit(0)

    multiprocessing.set_start_method('spawn')
    loop = asyncio.get_event_loop()
    log = logging.getLogger('server')

    session = ClientSession()
    # start server
    server_process = Process(target=run,args=(os.getpid(),))
    server_process.start()
    log.info(f'SERVER PROCESS: {server_process.pid}')
    log.info(f'MY PROCESS: {os.getpid()}')

    def cleanup():
        log.info('cleanup')
        loop.run_until_complete(session.close())
        os.kill(server_process.pid, signal.SIGTERM)

    atexit.register(cleanup)

    startup_successfull = loop.run_until_complete(wait_for_server())
    if not startup_successfull:
        raise RuntimeError("couldn't connect to server")

    unittest.main()
