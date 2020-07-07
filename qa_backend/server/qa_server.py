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
from typing import MutableMapping
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
import attr

from qa_backend.util import APIError
from qa_backend.util import exception_middleware
from qa_backend.services.database import DatabaseAlreadyExistsError
from qa_backend.services.database import DatabaseReadNotFoundError
from qa_backend.services.database import QueryDatabase
from qa_backend.services.qa import QA
from qa_backend.services.qa import QAQueryError
from qa_backend.util import JsonCrudOperation
from qa_backend.util import JsonQuestionOptionalContext
from qa_backend.util import Paragraph
from qa_backend.util import QAAnswer

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

@attr.s(slots=True)
class QAServerConfig:
    host: str = attr.ib(default='0.0.0.0')
    port: int = attr.ib(default=8080, converter=int)
    qa_log_file: Optional[str] = attr.ib(default=None)

    @property
    def origin(self) -> str:
        return f'http://{self.host}:{self.port}'

class QAServer:
    database: QueryDatabase
    qas: List[QA]
    app: web.Application
    config: QAServerConfig
    qa_log: Optional[TextIO] = None
    no_answers: List[str]

    def __init__(
            self,
            database: QueryDatabase,
            qas: List[QA],
            config: QAServerConfig,
        ):
        log.debug(f'initializing qa server: {config}')
        self.database = database
        self.qas = qas
        self.config = config
        if isinstance(config.qa_log_file, str):
            self.qa_log = open(config.qa_log_file, 'a')
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

    def __del__(self):
        log.debug('deleting qa server')
        if isinstance(self.qa_log, TextIO):
            self.qa_log.close()

    def log_qa(self, qa_answers: List[QAAnswer], qid: str):
        log.debug('logging qa')
        if self.qa_log is not None:
            try:
                answers = [attr.asdict(qa_answer) 
                           for qa_answer in qa_answers]
                entry = {'qid': qid, 'answers':answers}
                print(entry, file=self.qa_log, flush=True)
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
        answers_: List[Dict[str,Any]] = []
        for answer in answers:
            answer_ = attr.asdict(answer)
            if hasattr(answer,'paragraph'):
                answer_['paragraph'] = attr.asdict(answer.paragraph)
            else:
                answer_['paragraph'] = None
            answers_.append(answer_)
        if len(answers_) > 0:
            chosen_answer: Optional[Dict[str,Any]] = answers_[0]
        else:
            chosen_answer = None
        return {
            'chosen_answer': chosen_answer,
            'answers': answers_,
        }

    async def answer_question(
            self, request: Request, qa_size=3, ir_size=5
        ) -> Response:
        log.debug('answering question')
        json_question: JsonQuestionOptionalContext\
                = await JsonQuestionOptionalContext.from_request(request)
        log.info(f'json_question {json_question}')
        question = json_question.question
        context = json_question.context
        qid = request['qid']
        if context is None:
            log.info('no context, querying db...')
            paragraphs = list(await self.database.query(question, ir_size, qid))
            log.debug(f'got {len(paragraphs)} paragraphs of context')
            log.debug(f'{paragraphs}')
        else:
            paragraphs = [Paragraph(docId='provided.txt',text=context)]
        retrieved_docids = "\n".join([p.docId for p in paragraphs])
        log.info(f'Retrieved: \n{retrieved_docids}')
        answers: List[QAAnswer] = []
        for qa in self.qas:
            log.info(f'QA: {qa}')
            if qa.requires_context and len(paragraphs) > 0:
                for paragraph in paragraphs:
                    try:
                        new_answers = await qa.query(question, context=paragraph.text)
                        for new_answer in new_answers:
                            if new_answer.answer != '':
                                new_answer.docId = paragraph.docId
                                new_answer.paragraph = paragraph
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
        self.log_qa(answers, qid)
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
        log.info(f'got {len(paragraphs)} paragraphs')
        if len(paragraphs) == 0:
            return HTTPNotFound()
        paragraphs_ = [attr.asdict(paragraph) for paragraph in paragraphs]
        return web.json_response(paragraphs_)

    async def crud_create_update(self, request: Request) -> Response:
        crud_op = await JsonCrudOperation.from_request(request)
        paragraph = Paragraph(crud_op.docId, crud_op.text)
        log.debug(f'create/update paragraph: {str(paragraph)}')
        if crud_op.operation == 'create':
            log.info(f'creating: {crud_op.docId}')
            await self.database.create(paragraph)
            return Response()
        else: # crud_op.operation == 'update':
            log.info(f'updating: {crud_op.docId}')
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
        self.app.add_routes([
            web.get('/index', self.crud_read),
            web.post('/index', self.crud_create_update),
            web.delete('/index', self.crud_delete),
            web.post('/question', self.answer_question),
        ])
        web.run_app(self.app, host=self.config.host, port=self.config.port)
