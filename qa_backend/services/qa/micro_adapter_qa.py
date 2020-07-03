# micro_adapter_qa.py
"""
Adapter for a transformers_micro endpoint
"""

from json.decoder import JSONDecodeError
from typing import List
from typing import MutableMapping
import logging

from aiohttp import ClientSession
from aiohttp import ContentTypeError

from .abstract_qa import QA
from .abstract_qa import QAQueryError
from qa_backend.util import ConfigurationError
from qa_backend.util import QAAnswer
from qa_backend.util import check_config_keys

log = logging.getLogger('qa')

class MicroAdapterQA(QA):
    host: str
    port: int
    path: str
    session: ClientSession

    def __init__(self, host='localhost', port=8081, path='/question'):
        self._requires_context = True
        self.host = host
        self.port = port
        self.path = path
        log.info('created MicroAdapterQA: {self.url}')
        self.session = ClientSession()

    @staticmethod
    def from_config(config: MutableMapping[str,str]) -> 'MicroAdapterQA':
        check_config_keys(config, ['host','port','path'])
        log.info('creating MicroAdapterQA from config')
        log.debug(f"config:\n{config}")
        try:
            host = str(config.get('host','localhost'))
            port = int(config.get('port', 8081))
            path = str(config.get('path','/question'))
            return MicroAdapterQA(host,port,path)
        except ValueError as e:
            msg = 'Error in config: {str(e)}'
            log.error(msg)
            raise ConfigurationError(msg)

    @property
    def url(self) -> str:
        return f'http://{self.host}:{self.port}{self.path}'

    async def query(self, question: str, **kwargs) -> List[QAAnswer]:
        log.debug('[MicroAdapterQA] question: {question}')
        context = kwargs.get('context','')
        if context == '':
            raise QAQueryError("context required")
        if not isinstance(context, str):
            raise QAQueryError("context must be a string")
        body = {'question': question, 'context': context}
        log.debug(f'about to query: {body}')
        async with self.session.post(url=self.url, json=body) as response:
            status = response.status
            log.debug('got response: {response}')
            if status != 200:
                msg = f'got {status} from {self.url}: {response.reason}'
                raise QAQueryError(msg)
            try:
                resp_json = await response.json()
                question = resp_json[0]['question']
                answer = resp_json[0]['answer']
                score = float(resp_json[0]['score'])
                return [QAAnswer(question, answer, score)]
            except JSONDecodeError as e:
                text = await response.text()
                msg = f"error decoding json:\n{self.url}\n{text}\n{str(e)}"
                raise QAQueryError(msg)
            except KeyError as e:
                raise QAQueryError(str(e))
            except ContentTypeError as e:
                raise QAQueryError(str(e))

    async def shutdown(self):
        log.info('shutting down MicroAdapterQA')
        if not self.session.closed:
            await self.session.close()
