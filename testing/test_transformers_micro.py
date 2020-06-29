# test_tranformers_micro.py

from multiprocessing import Process
import signal
import asyncio
import logging
import unittest
import os

import aiohttp
from aiohttp import ClientSession
import fix_path
from qa_backend.server.transformers_micro import run

if __name__ == '__main__':
    run()
    exit(0)

loop = asyncio.get_event_loop()
session = ClientSession()
log = logging.getLogger('server')

# start server
server_process = Process(target=run)
server_process.start()
print(f'SERVER PROCESS: {server_process.pid}')

context = """
Successful unit testing requires writing tests that would only fail in case of an actual error or requirement change. There are a few rules that help avoid writing fragile unit tests. These are tests that would fail due to an internal change in the software that does not affect the user.

Since the same developer that wrote the code and knows how the solution was implemented usually writes unit tests, it is difficult not to test the inner workings of how a feature was implemented. The problem is that implementation tends to change and the test will fail even if the result is the same.
"""

class TransformersMicro_TestQuery(unittest.TestCase):
    def setUp(self):
        self.host = 'localhost'
        self.port = 8081

    def test_answer(self):
        print('-- here --')
        async def get_answer():
            body = {'question': 'what are fragile unit tests?',
                    'context': context}
            url = f'http://{self.host}:{self.port}/question'
            await asyncio.sleep(2)
            print('-- here ---')
            async with session.post(url,json=body) as response:
                print('__-- here ---')
                status = response.status
                response_body = await response.json()
            return status, response_body
        status, response_body = loop.run_until_complete(get_answer())
        self.assertEqual(status, 200)
        self.assertEqual(set(response_body.keys()), 
                         set(['question','answer','score']))
        log.info(response_body)
        print('-- here ----')

if __name__ == '__main__':
    print('here 0')
    unittest.main()
    print('here')
    os.kill(server_process.pid, signal.SIGTERM)
    print('sent kill')
    loop.run_until_complete(session.close())
    # stop server
