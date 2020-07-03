# qa_server.py
"""
* Uses es_git as a queryable backend
* instantiates and connects to transformers_micro for a qa service
* reads regex/response pairs for regex_qa
* TODO: use sentence transformers for qa intent detection
"""

from traceback import print_tb
from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import TextIO
from uuid import uuid4
import json
import logging
import os
import random
import sys

from aiohttp.web import Request # type: ignore
from aiohttp.web import Response # type: ignore
from aiohttp.web import HTTPNotFound # type: ignore
from aiohttp.web_middlewares import _Handler # type: ignore
from json.decoder import JSONDecodeError
from markdown import markdown # type: ignore
import aiohttp.web as web # type: ignore

from .api_error import APIError
from .api_error import JsonType
from .api_error import TypeCheckArg
from .api_error import exception_middleware
from .api_error import get_json_body
from qa_backend.services.database import DatabaseAlreadyExistsError
from qa_backend.services.database import DatabaseReadNotFoundError
from qa_backend.services.database import QueryDatabase
from qa_backend.services.qa import QA
from qa_backend.services.qa import QAQueryError
from qa_backend.util import Paragraph
from qa_backend.util import QAAnswer
from qa_backend.util import exception_to_dict

log = logging.getLogger('server')

#
# Middlewares
#
# middleware for server app.  Handles logging, errors, and other logic not
# directly related to the API
#

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
        log.debug('initializing qa server')
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
        log.debug('deleting qa server')
        if isinstance(self.qa_log, TextIO):
            self.qa_log.close()

    def log_qa(self, qa_answers: List[QAAnswer]):
        log.debug('logging qa')
        if self.qa_log is not None:
            try:
                print(repr(qa_answers), file=self.qa_log, flush=True)
            except Exception as e:
                log.error(f'Error while logging: {e}')

    def no_answer_reply(self) -> str:
        log.debug('getting reply instead of answer')
        return random.choice(self.no_answers)

    def get_answers_for_response(
            self, answers: List[QAAnswer]
        ) -> Dict[str,Any]:
        log.debug(f'getting answers from list of length: {len(answers)}')
        answers = list(sorted(answers, key=lambda a: a.score, reverse=True))
        answers_ = [answer.to_dict() for answer in answers]
        if len(answers_) > 0:
            chosen_answer: Optional[Dict[str,Any]] = answers_[0]
        else:
            chosen_answer = None
        return {
            'chosen_answer': chosen_answer,
            'answers': answers_,
        }

    async def answer_question(self, request: Request, qa_size=3, ir_size=5) -> Response:
        log.debug('answering question')
        json_fmt: Mapping[str,TypeCheckArg] = {'question': str, 'context': [str, type(None)]}
        body = await get_json_body(request, json_fmt)
        log.debug(f'body {body}')
        question = body['question']
        context = body.get('context')
        if context is None:
            log.debug('no context, querying db...')
            paragraphs = list(await self.database.query(question, ir_size))
            log.debug(f'got {len(paragraphs)} paragraphs of context')
            log.debug(f'{paragraphs}')
        retrieved_docids = "\n".join([p.docId for p in paragraphs])
        log.info(f'Retrieved: \n{retrieved_docids}')
        answers: List[QAAnswer] = []
        for qa in self.qas:
            log.debug(f'QA: {qa}')
            if qa.requires_context and len(paragraphs) > 0:
                for paragraph in paragraphs:
                    try:
                        new_answers = await qa.query(question, context=paragraph.text)
                        for new_answer in new_answers:
                            if new_answer.answer != '':
                                new_answer.docId = paragraph.docId
                                answers.append(new_answer)
                    except QAQueryError as e:
                        msg = f'[QAQueryError]: {str(e)}'
                        log.exception(msg)
            else:
                try:
                    new_answers = await qa.query(question)
                    answers.extend(new_answers)
                except QAQueryError as e:
                    msg = f'[QAQueryError]: {str(e)}'
                    log.exception(msg)
        self.log_qa(answers)
        log.debug(f'got {len(answers)} answers')
        response_answers = self.get_answers_for_response(answers)
        response_answers.update({'question':question})
        log.debug(f'response_answers: type: {type(response_answers)}, val: {response_answers}')
        return web.json_response(response_answers)

    async def crud_read(self, request: Request) -> Response:
        api_message = 'read requires a querystring parameter: /index?docId=...'
        query = request.query
        try:
            docId = query['docId']
        except KeyError as e:
            raise APIError(request, api_message)
        log.info(f'[READ] docId={docId}')
        try:
            paragraphs = await self.database.read(docId)
        except DatabaseReadNotFoundError as e:
            return HTTPNotFound()
        log.info('got {len(paragraphs)} paragraphs')
        if len(paragraphs) == 0:
            return HTTPNotFound()
        paragraphs_ = [paragraph.to_dict() for paragraph in paragraphs]
        return web.json_response(paragraphs_)

    async def crud_create_update(self, request: Request) -> Response:
        json_fmt = {'operation':str, 'docId':str, 'text':str}
        body = await get_json_body(request, json_fmt)
        operation = body['operation']
        docId = body['docId']
        text = body['text']
        paragraph = Paragraph(docId, text)
        log.debug(f'create/update paragraph: {str(paragraph)}')
        if operation not in ['create','update']:
            raise APIError(request, 'operation must be in [create, update]')
        if operation == 'create':
            log.info(f'creating: {docId}')
            await self.database.create(paragraph)
            return Response()
        else: # operation == 'update':
            log.info(f'updating: {docId}')
            await self.database.update(paragraph)
            return Response()

    async def crud_delete(self, request: Request) -> Response:
        api_message = 'delete requires a querystring parameter: /index?docId=...'
        query = request.query
        try:
            docId = query['docId']
        except KeyError as e:
            raise APIError(request, api_message)
        log.info(f'deleting: {docId}')
        await self.database.delete(docId)
        return Response()

    def run(self):
        log.info('running qa_server')
        web.run_app(self.app, host=self.host, port=self.port)
