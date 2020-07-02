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
from pprint import pprint, pformat

import aiohttp
from aiohttp import ClientSession, ClientResponseError
from aiohttp.client_exceptions import ClientConnectorError
from elasticsearch import Elasticsearch

log = logging.getLogger('testing')
loop = asyncio.get_event_loop()
es = Elasticsearch()

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
                    #log.error(str(e))
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
        print('[[KILL P]]')
        try:
            os.kill(p.pid, signal.SIGINT)
            print('[[SIGINT SENT]]')
            p.join(5)
            if p.is_alive():
                os.kill(p.pid, signal.SIGKILL)
                print('[[SIGKILL SENT]]')
            print('[[JOINED]]')
        except:
            print('[[EXCEPTION]]')
    atexit.register(kill_p)
    wait_for_connection('http://0.0.0.0:8080')
    wait_for_connection('http://0.0.0.0:8081')

def get_host():
    host = config['qa server']['host']
    port = config['qa server'].getint('port')
    return f'http://{host}:{port}'

def question_uri():
    return f'{get_host()}/question'

def index_uri():
    return f'{get_host()}/index'

def delete_uri(docId):
    return f'{index_uri()}?docId={docId}'

def read_uri(docId):
    return f'{index_uri()}?docId={docId}'

test_doc_updated = {
    'operation':'update',
    'docId': 'foo.txt',
    'text': 'this is an update test'
}

test_doc = {
    'operation':'create',
    'docId': 'foo.txt',
    'text': 'this is a test'
}

context = """
Each Hypertext Transfer Protocol (HTTP) message is either a request or a
response. A server listens on a connection for a request, parses each message
received, interprets the message semantics in relation to the identified
request target, and responds to that request with one or more response
messages. A client constructs request messages to communicate specific
intentions, examines received responses to see if the intentions were carried
out, and determines how to interpret the results. This document defines
HTTP/1.1 request and response semantics in terms of the architecture defined
in [RFC7230]. HTTP provides a uniform interface for interacting with a
resource (Section 2), regardless of its type, nature , or implementation, via
the manipulation and transfer of representations ( Section 3).
"""
session: ClientSession

async def create_session():
    global session
    session = ClientSession()
    def close_session():
        loop.run_until_complete(session.close())
    atexit.register(close_session)

loop.run_until_complete(create_session())

def create_context() -> int:
    async def _create():
        body = {'operation':'create', 'docId':'context.txt', 'text':context}
        async with session.post(index_uri(),json=body) as response:
            status = response.status
            for i in range(5):
                if es.exists(index='test-index', id='context.txt'):
                    return status
                else:
                    await asyncio.sleep(1)
            raise RuntimeError('Context not created on time!')
    return loop.run_until_complete(_create())

def delete_context() -> int:
    async def _delete():
        async with session.delete(delete_uri('context.txt')) as response:
            return response.status
    return loop.run_until_complete(_delete())

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
        async with session.post(index_uri(),json=test_doc_updated) as response:
            return response.status
    return loop.run_until_complete(_update())

def read_test_doc() -> Tuple[int,Any]:
    async def _read():
        async with session.get(read_uri(test_doc['docId'])) as response:
            return response.status, await response.json()
    return loop.run_until_complete(_read())

def answer_question(question) -> Tuple[int,Any]:
    async def _answer_question():
        body = {'question': question}
        async with session.post(question_uri(),json=body) as response:
            return response.status, await response.json()
    return loop.run_until_complete(_answer_question())

def check_body(body, doc) -> bool:
    return all([len(body) == 1,
               body[0]['docId'] == doc['docId'],
               body[0]['text'] == doc['text']])

class MainServer_CRUD(unittest.TestCase):
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
        self.assertTrue(check_body(r_body, test_doc))
        d_status = delete_test_doc()
        self.assertEqual(d_status, 200)

    def test_CRUD(self):
        c_status = create_test_doc()
        self.assertEqual(c_status, 200)
        r_status, r_body = read_test_doc()
        self.assertEqual(r_status, 200)
        self.assertTrue(check_body(r_body, test_doc))
        u_status = update_test_doc()
        self.assertEqual(u_status, 200)
        r_status, r_body = read_test_doc()
        self.assertEqual(r_status, 200)
        self.assertTrue(check_body(r_body, test_doc_updated))
        d_status = delete_test_doc()
        self.assertEqual(d_status, 200)

class MainServer_QA(unittest.TestCase):
    def test_RegexQA(self):
        question = 'do you think that jelena is happy?'
        status, answers = answer_question(question)
        self.assertEqual(status, 200)
        #log.info(pformat(answers,indent=2))
        log.info(answers['chosen_answer'])

    def test_MicroQA(self):
        c_status = create_context()
        self.assertEqual(c_status, 200)
        question = 'what is http?'
        qa_status, answers = answer_question(question)
        self.assertEqual(qa_status, 200)
        #log.info(pformat(answers,indent=2))
        log.info(answers['chosen_answer'])
        d_status = delete_context()
        self.assertEqual(d_status, 200)

if __name__ == '__main__':
    try:
        if sys.argv[1] == '-r':
            main_server = MainServer('main_server.cfg')
            main_server.run()
            exit(0)
    except IndexError:
        pass
    start_server_process()
    #unittest.main(exit=False)
    #def int_self():
        #log.info('INT SELF')
        #os.kill(os.getpid(),signal.SIGINT)
    #atexit.register(int_self)
    unittest.main()

    #print(f'killing self: {os.getpid()}')
    #os.kill(os.getpid(),signal.SIGINT)
