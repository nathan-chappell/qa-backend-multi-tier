# micro_adapter_qa.py
"""
Adapter for a transformers_micro endpoint
"""

import logging
from typing import List
from json.decoder import JSONDecodeError

import aiohttp.web as web
from aiohttp.web import Request, Response
from aiohttp import ClientSession, ContentTypeError

from .abstract_qa import QA, QAAnswer, QAQueryError
from . import complete_sentence

log = logging.getLogger('qa')

class MicroAdapter(QA):
    host: str
    port: int
    path: str
    session: ClientSession

    def __init__(self, host='localhost', port=8081, path='/question'):
        self._requires_context = True
        self.host = host
        self.port = port
        self.path = path
        self.session = ClientSession()
    
    @property
    def url(self) -> str:
        return f'http://{self.host}:{self.port}{self.path}'

    async def query(self, question: str, **kwargs) -> List[QAAnswer]:
        context = kwargs.get('context','')
        if context == '':
            raise QAQueryError("context required")
        body = {'question': question, 'context': context}
        async with self.session.post(url=self.url, json=body) as response:
            status = response.status
            if status != 200:
                msg = f'got {status} from {self.url}: {response.reason}'
                raise QAQueryError(msg)
            try:
                resp_json = await response.json()
                question = resp_json['question']
                answer = resp_json['answer']
                score = float(resp_json['score'])
                return [QAAnswer(question, answer, score)]
            except JSONDecodeError as e:
                text = await response.text()
                msg = f'error decoding json: {self.url}: {text}'
                raise QAQueryError(msg)
            except KeyError as e:
                raise QAQueryError(str(e))
            except ContentTypeError as e:
                raise QAQueryError(str(e))

    async def close(self):
        await self.session.close()
