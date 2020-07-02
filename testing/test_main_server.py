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
from typing import Dict, Any, Tuple
from configparser import ConfigParser, ExtendedInterpolation
from json.decoder import JSONDecodeError

import aiohttp
from aiohttp import ClientSession, ClientResponseError
from aiohttp.client_exceptions import ClientConnectorError

log = logging.getLogger('server')
loop = asyncio.get_event_loop()

from qa_backend.server.main_server import MainServer

context = """ Client session is the recommended interface for making HTTP requests.  Session encapsulates a connection pool (connector instance) and supports keepalives by default. Unless you are connecting to a large, unknown number of different servers over the lifetime of your application, it is suggested you use a single session for the lifetime of your application to benefit from connection pooling.  """
config_file = 'main_server.cfg'
config = ConfigParser(interpolation=ExtendedInterpolation())
config.read(config_file)

def run():
    log.info('running main server for testing...')
    main_server = MainServer('main_server.cfg')
    main_server.run()

def wait_for_connection(endpoint:str):
    session = ClientSession()
    try:
        async def _wait(count: int):
            while count >= 0:
                count -= 1
                try:
                    async with session.get(endpoint): ...
                except ClientConnectorError:
                    await asyncio.sleep(1)
                except ClientResponseError:
                    return True
                except Exception as e:
                    log.error(type(e))
                    log.error(str(e))
                else:
                    return True
        success = loop.run_until_complete(_wait(5))
    finally:
        loop.run_until_complete(session.close())
    if not success:
        raise ConnectionRefusedError()

def start_server_process():
    p = multiprocessing.Process(target=run)
    p.start()
    def kill_p():
        try:
            os.kill(p.pid, signal.SIGINT)
            p.join()
        except:
            ...
    atexit.register(kill_p)
    wait_for_connection('http://0.0.0.0:8080')
    wait_for_connection('http://0.0.0.0:8081')

def index_uri():
    host = config['qa server']['host']
    port = config['qa server'].getint('port')
    return f'http://{host}:{port}/index'

def delete_uri(docId):
    return f'{index_uri()}?docId={docId}'

def read_uri(docId):
    return f'{index_uri()}?docId={docId}'

update_test_doc = {
    'operation':'update',
    'docId': 'foo.txt',
    'text': 'this is an update test'
}

test_doc = {
    'operation':'create',
    'docId': 'foo.txt',
    'text': 'this is a test'
}

session: ClientSession

async def create_session():
    global session
    session = ClientSession()
    def close_session():
        loop.run_until_complete(session.close())
    atexit.register(close_session)

loop.run_until_complete(create_session())

def create_test_doc() -> int:
    async def _create():
        async with session.post(index_uri(),json=test_doc) as response:
            return response.status
    return loop.run_until_complete(_create())

def delete_test_doc() -> int:
    async def _delete():
        async with session.delete(delete_uri(test_doc['docId'])) as response:
            return response.status
    return loop.run_until_complete(_delete())

def update_test_doc() -> int:
    async def _update():
        async with session.post(index_uri(),json=update_test_doc) as response:
            return response.status
    return loop.run_until_complete(_update())

def read_test_doc() -> Tuple[int,Any]:
    async def _read():
        async with session.get(read_uri(test_doc['docId'])) as response:
            return response.status, await response.json()
    return loop.run_until_complete(_read())

class MainServer_CD(unittest.TestCase):
    def setUp(self):
        #self.session = ClientSession()
        ...

    def test_CD(self):
        c_status = create_test_doc()
        self.assertEqual(c_status, 200)
        d_status = delete_test_doc()
        self.assertEqual(d_status, 200)

    def test_CRD(self):
        c_status = create_test_doc()
        self.assertEqual(c_status, 200)
        r_status, r_body = read_test_doc()
        self.assertEqual(r_status, 200)
        self.assertEqual(len(r_body),1)
        self.assertEqual(r_body[0]['docId'],test_doc['docId'])
        self.assertEqual(r_body[0]['text'],test_doc['text'])
        d_status = delete_test_doc()
        self.assertEqual(d_status, 200)
    
    def tearDown(self):
        ...

if __name__ == '__main__':
    try:
        if sys.argv[1] == '-r':
            main_server = MainServer('main_server.cfg')
            main_server.run()
            exit(0)
    except IndexError:
        pass
    start_server_process()
    unittest.main(exit=False)

    print(f'killing self: {os.getpid()}')
    os.kill(os.getpid(),signal.SIGINT)
