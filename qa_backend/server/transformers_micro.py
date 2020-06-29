# transformer_micro.py
"""
Microservice exposing transformer_qa.
Making pytorch work async in python is probably more trouble than it's worth,
so this is a good compromise
"""
import logging
from typing import Dict, Any
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

transformer_qa = TransformersQA()
routes = web.RouteTableDef()

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
    except Exception as e:
        if os.environ.get('PRINT_TB'):
            print_tb(sys.exc_info()[2]) 
        return web.json_response(exception_to_dict(e), status=500)

@routes.post('/question')
async def answer_question(request: Request) -> Response:
    body = await request.json()
    if set(body.keys()) != set(['question','context']):
        raise TypeError()
    question = body['question']
    context = body['context']
    answer = transformer_qa.query(question, context)
    return web.json_response(text=repr(answer))

def run():
    app = web.Application(middlewares=[handle_errors])
    app.add_routes(routes)
    web.run_app(app, host='0.0.0.0', port=8081)
