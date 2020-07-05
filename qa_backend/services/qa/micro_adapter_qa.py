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
import attr

from .abstract_qa import QA
from .abstract_qa import QAQueryError
from qa_backend.util import ConfigurationError
from qa_backend.util import QAAnswer

log = logging.getLogger('qa')

def strip_leading_slash(path: str) -> str:
    if len(path) > 0:
        if path[0] == '/':
            return path[1:]
    return path

@attr.s(slots=True)
class MicroAdapterQAConfig:
    host: str = attr.ib(default='0.0.0.0')
    port: int = attr.ib(default=8081, converter=int)
    path: str = attr.ib(default='question',converter=strip_leading_slash)

    @property
    def url(self) -> str:
        return f'http://{self.host}:{self.port}/{self.path}'

class MicroAdapterQA(QA):
    session: ClientSession
    config: MicroAdapterQAConfig
    _requires_context = True

    def __init__(self, config: MicroAdapterQAConfig):
        log.info(f'creating MicroAdapterQA: {config}')
        self.config = config
        self.session = ClientSession()

    @staticmethod
    def from_config(config: MutableMapping[str,str]) -> 'MicroAdapterQA':
        log.info('creating MicroAdapterQA from config')
        log.debug(f"config:\n{config}")
        ma_config = MicroAdapterQAConfig(**config)
        return MicroAdapterQA(ma_config)

    async def query(self, question: str, **kwargs) -> List[QAAnswer]:
        log.info(f'[MicroAdapterQA] question: {question}')
        context = kwargs.get('context','')
        if context == '':
            raise QAQueryError("context required")
        if not isinstance(context, str):
            raise QAQueryError("context must be a string")
        body = {'question': question, 'context': context}
        log.info(f'about to query: {self.config.url}: {body}')
        async with self.session.post(self.config.url, json=body) as response:
            status = response.status
            log.info(f'got response: {response}')
            if status != 200:
                msg = f'got {status} from {self.config.url}: {response.reason}'
                raise QAQueryError(msg)
            try:
                resp_json = await response.json()
                if len(resp_json) == 0:
                    return []
                question = resp_json[0]['question']
                answer = resp_json[0]['answer']
                score = float(resp_json[0]['score'])
                return [QAAnswer(question, answer, score)]
            except JSONDecodeError as e:
                text = await response.text()
                msg = f"error decoding json:\n{self.config.url}\n{text}\n{str(e)}"
                raise QAQueryError(msg)
            except KeyError as e:
                raise QAQueryError(str(e))
            except ContentTypeError as e:
                raise QAQueryError(str(e))

    async def shutdown(self):
        log.info('shutting down MicroAdapterQA')
        if not self.session.closed:
            await self.session.close()
