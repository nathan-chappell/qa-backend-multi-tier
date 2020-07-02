# test_main_server.py

import multiprocessing
import sys
sys.path.append('..')
import logging
import atexit
import os
import signal
import unittest
import asyncio

import aiohttp
from aiohttp import ClientSession

log = logging.getLogger('server')
loop = asyncio.get_event_loop()

from qa_backend.server.main_server import MainServer

context = """ Client session is the recommended interface for making HTTP requests.  Session encapsulates a connection pool (connector instance) and supports keepalives by default. Unless you are connecting to a large, unknown number of different servers over the lifetime of your application, it is suggested you use a single session for the lifetime of your application to benefit from connection pooling.  """

def run():
    log.info('running main server for testing...')
    main_server = MainServer('main_server.cfg')
    main_server.run()

def start_server_process():
    p = multiprocessing.Process(target=run)
    p.start()
    atexit.register(lambda : os.kill(p.pid, signal.SIGINT) and p.join())

class MainServer_TestApi(unittest.TestCase):
    def setUp(self):
        self.session = ClientSession()

    async def _run_create(self) -> int:
        async with self.session.post(
                    'http://localhost/index',
                    json=body
                ) as response:
            return response.status

    async def _run_read(self) -> Dict[str,Any]:
        async with self.session.get(
                'http://localhost/index?docId=foo.txt'
            ) as response:
            return = await response.json()

    def test_create(self):
        body = {'docId':'foo.txt', 'text': context}
        status = loop.run_until_complete(self._run_create())
        self.assertEqual(status, 200)

    def test_read(self):
        respone = loop.run_until_complete(self._run_read())
        self.assertEqual(len(body),1)
        self.assertEqual(body[0]['docId'], 'foo.txt')
        status = loop.run_until_complete(run_test())
        self.assertEqual(status, 200)

    def test_update(self):
        ...

    def test_delete(self):
        ...

    def tearDown(self):
        loop.run_until_complete(self.session.close())

if __name__ == '__main__':
    start_server_process()
