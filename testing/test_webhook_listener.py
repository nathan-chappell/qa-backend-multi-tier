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

import aiohttp
from aiohttp import ClientSession
import common

from qa_backend.server.webhook_listener import WebhookListener

url = 'http://localhost:8083/webhook'

def run(ppid):
    webhook_filters = [
        lambda d: d.get('prop1') != 'attr1_',
    ]
    webhook_listener = WebhookListener(
            ppid, signal.BREAK, webhook_filters=webhook_filters
        )
    webhook_listener.run()

class TransformersMicro_TestQuery(unittest.TestCase):
    def setUp(self):
        self.url = url

    def test_activate(self):
        async def activate_webhook():
            body = {'prop1': 'attr1', 'prop2': 'attr2'}
            #await asyncio.sleep(2)
            async with session.post(self.url,json=body) as response:
                status = response.status
            return status
        status loop.run_until_complete(get_answer())
        self.assertEqual(status, 200)

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
        run()
        exit(0)

    multiprocessing.set_start_method('spawn')
    loop = asyncio.get_event_loop()
    log = logging.getLogger('server')

    session = ClientSession()
    # start server
    server_process = Process(target=run)
    server_process.start()
    print(f'SERVER PROCESS: {server_process.pid}')

    def cleanup():
        print('cleanup')
        loop.run_until_complete(session.close())
        os.kill(server_process.pid, signal.SIGTERM)

    atexit.register(cleanup)

    startup_successfull = loop.run_until_complete(wait_for_server())
    if not startup_successfull:
        raise RuntimeError("couldn't connect to server")

    context = """ Successful unit testing requires writing tests that would
    only fail in case of an actual error or requirement change. There are a
    few rules that help avoid writing fragile unit tests. These are tests that
    would fail due to an internal change in the software that does not affect
    the user.  Since the same developer that wrote the code and knows how the
    solution was implemented usually writes unit tests, it is difficult not to
    test the inner workings of how a feature was implemented. The problem is
    that implementation tends to change and the test will fail even if the
    result is the same.  """

    unittest.main()
