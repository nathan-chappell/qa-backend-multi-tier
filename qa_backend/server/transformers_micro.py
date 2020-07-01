# transformer_micro.py
"""
Microservice exposing transformer_qa.
Making pytorch work async in python is probably more trouble than it's worth,
so this is a good compromise
"""
import logging
from typing import Dict, Any, Optional
from traceback import print_tb
import sys
import os

import aiohttp.web as web # type: ignore
from aiohttp.web_middlewares import _Handler # type: ignore
from aiohttp.web import Request, Response # type: ignore
from json.decoder import JSONDecodeError

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

class TransformersMicro:
    host: str
    port: int
    transformer_qa: TransformersQA

    def __init__(
            self, host: str = '0.0.0.0', port: int = 8081,
            transformer_qa: Optional[TransformersQA] = None,
        ):
        self.host = host
        self.port = port
        if isinstance(transformer_qa, TransformersQA):
            self.transformer_qa = transformer_qa
        else:
            self.transformer_qa = TransformersQA()

    async def answer_question(self, request: Request) -> Response:
        body = await request.json()
        if set(body.keys()) != set(['question','context']):
            raise TypeError()
        question = body['question']
        context = body['context']
        answer = await self.transformer_qa.query(question, context=context)
        return web.json_response(text=repr(answer))

    def run(self):
        app = web.Application(middlewares=[handle_errors])
        app.add_routes([
            web.post('/question', self.answer_question),
        ])
        web.run_app(app, host=self.host, port=self.port)
