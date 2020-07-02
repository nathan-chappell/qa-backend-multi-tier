# qa_server.py
"""
* Uses es_git as a queryable backend
* instantiates and connects to transformers_micro for a qa service
* reads regex/response pairs for regex_qa
* TODO: use sentence transformers for qa intent detection
"""

import logging
from typing import Dict, Any, List, TextIO, Optional
from traceback import print_tb
import sys
import os
from uuid import uuid4
import json
import random

import aiohttp.web as web # type: ignore
from aiohttp.web_middlewares import _Handler # type: ignore
from aiohttp.web import Request, Response # type: ignore
from json.decoder import JSONDecodeError
from markdown import markdown # type: ignore

from qa_backend.services.database.database_error import DatabaseAlreadyExistsError

from qa_backend.services import QAAnswer, Paragraph
from qa_backend.services.database import QueryDatabase
from qa_backend.services.qa import QA
from . import exception_to_dict

log = logging.getLogger('server')
#log.setLevel(logging.DEBUG)

#
# Exceptions and exception utilities
#

class APIError(RuntimeError):
    """Exception class to indicate API related errors."""
    message: str
    method: str
    path: str
    def __init__(self, request: web.Request, message: str):
        super().__init__()
        self.method = request.method
        self.path = request.path
        self.message = message

    @property
    def _api(self) -> str:
        return f'{self.method} {self.path}'

    def __str__(self) -> str:
        return self._api + ' - ' + self.message

    def __repr__(self) -> str:
        return f'<APIError: {str(self)}>'

class AnswerError(RuntimeError):
    """Exception class to indicate and error getting an answer"""
    exception: Exception
    question: Dict[str,Any]

    def __init__(self, exception: Exception, question: Dict[str,Any]):
        self.exception = exception
        self.question = question

    def __str__(self) -> str:
        return f'AnswerError: <{self.question}> <{self.exception}>'

    def __repr__(self) -> str:
        return '<' + str(self) + '>'

#
# Middlewares
#
# middleware for server app.  Handles logging, errors, and other logic not
# directly related to the API
#

@web.middleware
async def exception_middleware(
        request: web.Request, 
        handler: _Handler
        ) -> web.StreamResponse:
    """Catch listed exceptions and convert them to json responses."""
    try:
        result = await handler(request)
        log.debug('exception middleware not fired')
        return result
    except JSONDecodeError as e:
        info = exception_to_dict(e, log_error=False)
        return web.json_response(info, status=400)
    except KeyError as e:
        info = exception_to_dict(e, log_error=True)
        return web.json_response(info, status=400)
    except APIError as e:
        info = exception_to_dict(e, log_error=True)
        return web.json_response(info, status=400)
    # catch-all => server error
    except DatabaseAlreadyExistsError as e:
        msg = e.message
        return Response(status=409, reason=msg)
    except Exception as e:
        info = exception_to_dict(e, log_error=True)
        return web.json_response(info ,status=500)

@web.middleware
async def attach_uuid_middleware(
        request: web.Request, 
        handler: _Handler
        ) -> web.StreamResponse:
    """Assign qid to request and set a cookie in the response"""
    qid = str(uuid4())
    request['qid'] = qid
    response = await handler(request)
    response.set_cookie('qa_server.qid',qid)
    return response

#
# API
#

class QAServer:
    database: QueryDatabase
    qas: List[QA]
    app: web.Application
    qa_log: Optional[TextIO] = None
    no_answers: List[str]

    def __init__(
            self, database: QueryDatabase, qas: List[QA],
            host='0.0.0.0', port=8080,
            qa_log_file: Optional[str] = None,
        ):
        self.database = database
        self.qas = qas
        self.host = host
        self.port = port
        if isinstance(qa_log_file, str):
            self.qa_log = open(qa_log_file, 'a')
            log.info(f'qa_log_file: {qa_log_file}')
        self.no_answers = [
            "I'm sorry, I couldn't find an answer to your question.",
            "I was unable to answer your query.",
            "Unfortunately I don't know how to answer that question.",
        ]

        middlewares = [
            exception_middleware,
            attach_uuid_middleware,
        ]
        self.app = web.Application(middlewares=middlewares)
        self.app.add_routes([
            web.post('/question', self.answer_question),
            web.get('/index', self.crud_read),
            web.post('/index', self.crud_create_update),
            web.delete('/index', self.crud_delete),
        ])

    def __del__(self):
        if isinstance(self.qa_log, TextIO):
            self.qa_log.close()

    def log_qa(self, qa_answers: List[QAAnswer]):
        if self.qa_log is not None:
            try:
                print(repr(qa_answers), file=self.qa_log, flush=True)
            except Exception as e:
                log.error(f'Error while logging: {e}')

    def no_answer_reply(self) -> str:
        return random.choice(self.no_answers)

    def get_answers_for_response(
            self, answers: List[QAAnswer]
        ) -> Dict[str,Any]:
        answers = list(sorted(answers, key=lambda a: a.score, reverse=True))
        answers_ = [answer.to_dict() for answer in answers]
        if len(answers_) > 0:
            chosen_answer = answers_[0]
        else:
            chosen_answer = None
        return {
            'chosen_answer': chosen_answer,
            'answers': answers_,
        }

    async def answer_question(self, request: Request, qa_size=3, ir_size=5) -> Response:
        log.info(f'got question... {request}')
        body = await request.json()
        log.debug(f'body: {body}')
        try:
            question = body['question']
        except KeyError as e:
            raise APIError(request, str(e))
        context = body.get('context')
        log.debug(f'body has context: {context}')
        if context is None:
            log.debug('no context, query db...')
            paragraphs = list(await self.database.query(question, ir_size))
            log.debug(f'got paragraphs: {paragraphs}')
        retrieved_docids = [p.docId for p in paragraphs]
        log.info(f'Retrieved: {", ".join(retrieved_docids)}')
        answers: List[QAAnswer] = []
        for qa in self.qas:
            if qa.requires_context and len(paragraphs) > 0:
                log.debug(f'QA: {qa}')
                for paragraph in paragraphs:
                    new_answers = await qa.query(question, context=paragraph.text)
                    for new_answer in new_answers:
                        if new_answer.answer != '':
                            new_answer.docId = paragraph.docId
                            answers.append(new_answer)
            else:
                new_answers = await qa.query(question)
                answers.extend(new_answers)
        self.log_qa(answers)
        response_answers = self.get_answers_for_response(answers)
        response_answers.update({'question':question})
        log.debug(f'response_answers: type: {type(response_answers)}, val: {response_answers}')
        return web.json_response(response_answers)

    async def crud_read(self, request: Request) -> Response:
        query = request.query
        try:
            docId = query['docId']
        except KeyError as e:
            raise APIError(request, str(e))
        paragraphs = await self.database.read(docId)
        paragraphs_ = [paragraph.to_dict() for paragraph in paragraphs]
        return web.json_response(paragraphs_)

    async def crud_create_update(self, request: Request) -> Response:
        body = await request.json()
        try:
            operation = body['operation']
            docId = body['docId']
            text = body['text']
        except KeyError as e:
            raise APIError(request, str(e))
        paragraph = Paragraph(docId, text)
        if operation not in ['create','update']:
            raise APIError(request, 'operation must be in [create, update]')
        if operation == 'create':
            await self.database.create(paragraph)
            return Response()
        else: # operation == 'update':
            await self.database.update(paragraph)
            return Response()

    async def crud_delete(self, request: Request) -> Response:
        query = request.query
        try:
            docId = query['docId']
        except KeyError as e:
            raise APIError(request, str(e))
        await self.database.delete(docId)
        return Response()

    def run(self):
        web.run_app(self.app, host=self.host, port=self.port)
