# transformer_micro.py
"""
Microservice exposing transformer_qa.
Making pytorch work async in python is probably more trouble than it's worth,
so this is a good compromise
"""

from json.decoder import JSONDecodeError
from traceback import print_tb
from typing import Any
from typing import Dict
from typing import MutableMapping
from typing import Optional
import logging
import os
import sys

from aiohttp.web import Request # type: ignore
from aiohttp.web import Response # type: ignore
from aiohttp.web_middlewares import _Handler # type: ignore
from aiohttp.web import HTTPClientError
import aiohttp.web as web # type: ignore

from .api_error import APIError
from .api_error import exception_middleware
from .api_error import get_json_body
from qa_backend.services.qa import TransformersQA
from qa_backend.util import Configurable
from qa_backend.util import ConfigurationError
from qa_backend.util import check_config_keys
from qa_backend.util import exception_to_dict

log = logging.getLogger('server')

class TransformersMicro(Configurable):
    host: str
    port: int
    transformer_qa: TransformersQA
    transformer_qa_kwargs: Mapping[str,Union[int,bool,str]]

    def __init__(
            self, host: str = '0.0.0.0', port: int = 8081,
            transformer_qa: Optional[TransformersQA] = None,
            transformer_qa_kwargs: Optional[Mapping[str,Union[int,bool,str]]],
            #model_name: Optional[str] = None, 
            #use_gpu: bool = False,
            #device: int = -1,
        ):
        self.host = host
        self.port = port
        #self.model_name = model_name
        #self.use_gpu = use_gpu
        #self.device = device
        if isinstance(transformer_qa, TransformersQA):
            self.transformer_qa = transformer_qa
        else:
            self.transformer_qa_kwargs = transformer_qa_kwargs
        log.info(f'initialized TransformersMicro: {str(self)}')

    def __str__(self) -> str:
        return f'{self.url}, {self._info}'

    @property
    def url(self) -> str:
        return f'http://{self.host}:{self.port}'

    @property
    def _info(self) -> str:
        return f'<{self.model_name},use_gpu:{self.use_gpu},{self.device}>'

    # TODO: support model_name
    @staticmethod
    def from_config(config: MutableMapping[str,str]) -> 'TransformersMicro':
        log.info('creating TransformersMicro from config')
        log.debug(f"config:\n{config}")
        check_config_keys(
            config, ['host','port','model name','use gpu','device']
        )
        try:
            host = str(config.get('host','0.0.0.0'))
            port = int(config.get('port', 8081))
            use_gpu = config.get('use gpu')
            device = config.get('device')
            return TransformersMicro(host,port)
        except ValueError as e:
            raise ConfigurationError(str(e))

    async def answer_question(self, request: Request) -> Response:
        log.debug('answering question')
        json_fmt = {'question':str, 'context':str}
        body = await get_json_body(request, json_fmt)
        log.debug(f'body: {body}')
        question = body['question']
        context = body['context']
        # QAQueryError will pass to middleware
        answer = await self.transformer_qa.query(question, context=context)
        log.debug(f'micro got answer: {answer}')
        return web.json_response(text=repr(answer))

    def run(self):
        app = web.Application(middlewares=[exception_middleware])
        app.add_routes([
            web.post('/question', self.answer_question),
        ])
        log.info(f'Running transformers_micro: pid: {os.getpid()}')
        self.transformer_qa = TransformersQA(
                                    model_name=self.model_name,
                                    use_gpu=self.use_gpu,
                                    device=self.device
                                )
        web.run_app(app, host=self.host, port=self.port)
