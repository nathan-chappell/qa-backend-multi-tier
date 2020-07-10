# transformer_micro.py
"""
Microservice exposing transformers_qa.
Making pytorch work async in python is probably more trouble than it's worth,
so this is a good compromise
"""

from json.decoder import JSONDecodeError
from traceback import print_tb
from typing import Any
from typing import Dict
from typing import List
from typing import MutableMapping
from typing import Optional
from typing import Tuple
from typing import cast
import logging
import os
import sys

from aiohttp.web import HTTPClientError
from aiohttp.web import Request # type: ignore
from aiohttp.web import Response # type: ignore
from aiohttp.web_middlewares import _Handler # type: ignore
from attr.validators import instance_of
import aiohttp.web as web # type: ignore
import attr

from qa_backend.services.qa import LazyPipeline
from qa_backend.services.qa import TransformersQA
from qa_backend.services.qa import TransformersQAConfig
from qa_backend.util import APIError
from qa_backend.util import Configurable
from qa_backend.util import ConfigurationError
from qa_backend.util import ConfigurationError
from qa_backend.util import JsonQuestion
from qa_backend.util import exception_middleware

log = logging.getLogger('server')

@attr.s(kw_only=True)
class TransformersMicroConfig(Configurable):
    host: str = attr.ib(default='0.0.0.0')
    port: int = attr.ib(default=8081, converter=int)
    path: str = attr.ib(default='question')
    transformers_qa_config: Optional[TransformersQAConfig] = attr.ib(
                                default=None
                            )

    @property
    def url(self) -> str:
        return f'http://{self.host}:{self.port}/{self.path}'

def _extract_keys(
        dict_: MutableMapping[str,str],
        keys: List[str]
    ) -> MutableMapping[str,str]:
    d = {k:dict_.pop(k) for k in keys if k in dict_.keys()}
    return d

def split_micro_config(
        config: MutableMapping[str,str]
        ) -> Tuple[MutableMapping[str,str],MutableMapping[str,str]]:
    """Split config into keys for the micro service and the TransformersQA"""
    micro_keys = ['host','port']
    micro_config = _extract_keys(config, micro_keys)
    transformer_keys = ['model_name','use_gpu','device']
    transformer_config = _extract_keys(config, transformer_keys)
    return micro_config, transformer_config

class TransformersMicro:
    config: TransformersMicroConfig
    transformers_qa: TransformersQA

    def __init__(
            self,
            config: TransformersMicroConfig,
            transformers_qa: Optional[TransformersQA] = None,
            transformers_qa_config: Optional[TransformersQAConfig] = None
        ):
        self.config = config
        if isinstance(transformers_qa, TransformersQA):
            self.transformers_qa = transformers_qa
        elif isinstance(transformers_qa_config, TransformersQAConfig):
            log.info(f'TransformersMicro: creating from config:{transformers_qa_config}')
            self.transformers_qa = TransformersQA(config=transformers_qa_config)
        else:
            msg = f'Either a TransformersQA or config must be specified'
            raise ValueError(msg)
        log.info(f'initialized TransformersMicro: {str(self)}')

    def __str__(self) -> str:
        return f'{self.config.url} | {self.transformers_qa}'

    # TODO: support model_name
    @staticmethod
    def from_config(config: MutableMapping[str,str]) -> 'TransformersMicro':
        log.info('creating TransformersMicro from config')
        log.debug(f"config:\n{config}")
        micro_config, transformer_config = split_micro_config(config)
        micro_config_ = TransformersMicroConfig(**micro_config)
        #transformers_qa = TransformersQA(transformer_config)
        transformers_qa = TransformersQA.from_config(transformer_config)
        log.debug(micro_config_)
        log.debug(transformer_config)
        return TransformersMicro(micro_config_, transformers_qa)

    async def answer_question(self, request: Request) -> Response:
        log.debug('answering question')
        json_question: JsonQuestion = await JsonQuestion.from_request(request)
        log.info(f'json_question: {json_question.question}')
        question = json_question.question
        context = json_question.context
        # QAQueryError will pass to middleware
        answers = await self.transformers_qa.query(question, context=context)
        log.debug(f'micro got answer: {answers}')
        answers_ = [attr.asdict(answer) for answer in answers]
        return web.json_response(answers_)

    def run(self, create_pipeline_now = False) -> None:
        if create_pipeline_now and isinstance(self.transformers_qa.pipeline,
                                              LazyPipeline):
            self.transformers_qa.pipeline.create_now()
        app = web.Application(middlewares=[exception_middleware])
        app.add_routes([
            web.post(f'/{self.config.path}', self.answer_question),
        ])
        log.info(f'Running transformers_micro: pid: {os.getpid()}')
        #self.transformers_qa = TransformersQA(
                                    #model_name=self.model_name,
                                    #use_gpu=self.use_gpu,
                                    #device=self.device
                                #)
        web.run_app(app, host=self.config.host, port=self.config.port)
