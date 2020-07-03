# test_tranformers_micro.py

from aiohttp import ClientConnectionError
from multiprocessing import Process
import asyncio
import atexit
import logging
import multiprocessing
import os
import signal
import sys
import unittest

from aiohttp import ClientSession

sys.path.append('..')

from qa_backend.server import TransformersMicro

def run():
    transformers_micro = TransformersMicro()
    transformers_micro.run()

class TransformersMicro_TestQuery(unittest.TestCase):
    def setUp(self):
        self.url = f'http://localhost:8081/question'

    def test_answer(self):
        async def get_answer():
            body = {'question': 'what are fragile unit tests?',
                    'context': context}
            await asyncio.sleep(2)
            async with session.post(self.url,json=body) as response:
                status = response.status
                response_body = await response.json()
            return status, response_body
        status, response_body = loop.run_until_complete(get_answer())
        self.assertEqual(status, 200)
        self.assertEqual(set(response_body[0].keys()), 
                         set(['question','answer','score']))
        log.info(response_body)

    def test_api_error(self):
        async def bad_method():
            async with session.get(self.url) as response:
                return response.status
        status = loop.run_until_complete(bad_method())
        log.info(f'[STATUS]: {status}')
        self.assertEqual(status // 100, 4)

async def wait_for_server(seconds: int = 10) -> bool:
    count = 0
    while count < seconds:
        count += 1
        try:
            async with session.get('http://localhost:8081'):
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
