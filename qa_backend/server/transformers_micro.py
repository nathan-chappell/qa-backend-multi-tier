# transformer_micro.py
"""
Microservice exposing transformer_qa.
Making pytorch work async in python is probably more trouble than it's worth,
so this is a good compromise
"""
import logging
from typing import Dict, Any, Optional, MutableMapping
from traceback import print_tb
import sys
import os

import aiohttp.web as web # type: ignore
from aiohttp.web_middlewares import _Handler # type: ignore
from aiohttp.web import Request, Response # type: ignore
from json.decoder import JSONDecodeError

from qa_backend import Configurable, ConfigurationError, check_config_keys
from qa_backend.services.qa import TransformersQA
from qa_backend.services import init_logs
from . import exception_to_dict

log = logging.getLogger('server')

def api_error(log_error) -> Response:
    msg = "format: {question: str, context: str}"
    log.error(f'[API ERROR]: {log_error}')
    return web.json_response({'api-error':msg},status=400)

@web.middleware
async def handle_errors(request: Request, handler: _Handler) -> web.StreamResponse:
    try:
        return await handler(request)
    except (JSONDecodeError, KeyError, TypeError) as e:
        if os.environ.get('PRINT_TB'):
            print_tb(sys.exc_info()[2]) 
        return api_error(f'{request.remote} - {e}')
    except web.HTTPClientError as e:
        if os.environ.get('PRINT_TB'):
            print_tb(sys.exc_info()[2]) 
        return web.json_response(exception_to_dict(e), status=400)
    except Exception as e:
        if os.environ.get('PRINT_TB'):
            print_tb(sys.exc_info()[2]) 
        return web.json_response(exception_to_dict(e), status=500)

class TransformersMicro(Configurable):
    host: str
    port: int
    transformer_qa: TransformersQA

    def __init__(
            self, host: str = '0.0.0.0', port: int = 8081,
            transformer_qa: Optional[TransformersQA] = None,
            model_name: Optional[str] = None, 
            use_gpu: bool = False,
            device: int = -1,
        ):
        self.host = host
        self.port = port
        if isinstance(transformer_qa, TransformersQA):
            #self.transformer_qa = transformer_qa
            ...
        else:
            self.model_name = model_name
            self.use_gpu = use_gpu
            self.device = device
            #self.transformer_qa = TransformersQA(
                                        #model_name=model_name,
                                        #use_gpu=use_gpu,
                                        #device=device
                                    #)

    # TODO: support model_name
    @staticmethod
    def from_config(config: MutableMapping[str,str]) -> 'TransformersMicro':
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
        log.info(f'micro got question: {request}')
        body = await request.json()
        if set(body.keys()) != set(['question','context']):
            raise TypeError()
        question = body['question']
        context = body['context']
        answer = await self.transformer_qa.query(question, context=context)
        log.info(f'micro got answer: {answer}')
        return web.json_response(text=repr(answer))

    def run(self):
        app = web.Application(middlewares=[handle_errors])
        app.add_routes([
            web.post('/question', self.answer_question),
        ])
        self.transformer_qa = TransformersQA(
                                    model_name=self.model_name,
                                    use_gpu=self.use_gpu,
                                    device=self.device
                                )
        web.run_app(app, host=self.host, port=self.port)
