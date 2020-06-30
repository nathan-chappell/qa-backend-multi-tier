# qa_server.py
"""
* Uses es_git as a queryable backend
* instantiates and connects to transformers_micro for a qa service
* reads regex/response pairs for regex_qa
* TODO: use sentence transformers for qa intent detection
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

from qa_backend.services.database import GitEsDatabase
from qa_backend.services.qa import RegexQA
from . import exception_to_dict
from .transformers_micro import run

log = logging.getLogger('server')

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
        return await handler(request)
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

async def handle_webhook(request: Request) -> Response:
    body = await request.json()
    log.info('handling webhook')
    #pprint(body)
    if body.get('event_name',None) == 'push':
        await git_client.pull()
        log.info('pull complete')
        await index_all(INDEX_NAME)
        log.info('index all complete')
    return Response(status=200)

class QAServer:
    database: QueryDatabase
    qas: List[QA]

    def __init__(
            self, database: QueryDatabase, qas: List[QA],
            host='0.0.0.0', port=8080
        ):
        self.database = database
        self.qas = qas
        self.qa_log = open('qa_log.multi_json','a')

    def __del__(self):
        self.qa_log.close()

    @property
    def readme(self) -> str:
        readme_path = 'pages/README.md'
        with open(readme_path) as file:
            md = markdown(file.read())
        return f"""
            <!doctype html>
            <head>
                <meta charset="utf8" />
                <link rel="stylesheet" href="/github.css" />
            </head>
            <body>
                {md}
            </body>
            </html>
        """

    @property
    def github_css(self) -> str:
        css_path = 'pages/github.css'
        with open(css_path) as file:
            css = file.read()
        return css

    def log_qa(qa_answers: List[QAAnswer]):
        json.dump(qa_answers, self.qa_log)
        self.qa_log.flush()

    def no_answer_reply(self) -> str:
        return random.choice([
            "I'm sorry, I couldn't find an answer to your question.",
            "I was unable to answer your query.",
            "Unfortunately I don't know how to answer that question."
        ])

    async def serve_readme(request: Request) -> Response:
        return Response(
                    text=self.readme,
                    status=200,
                    content_type='text/html'
                )

    async def serve_github_css(request: Request) -> Response:
        return Response(
                    text=self.github_css,
                    status=200,
                    content_type='text/css'
                )

    async def answer_question(request: Request) -> Response:
        body = await request.json()
        try:
            question = body['question']
        except KeyError as e:
            raise APIError(request, str(e))
        context = body.get('context')
        if context is None:
            contexts = list(await self.database.query(question))
            if len(contexts) > 0:
                context = contexts[0]
        answer = QAAnswer(question, self.no_answer_reply(), 0.)
        for qa in self.qas:
            if qa.requires_context:
                answers = await qa.query(question, context=context)
            else:
                answers = await qa.query(question)
            if len(answers) == 0:
                continue
            self.log_qa(answers)
            answer = answers[0]
            break
        return web.json_response(answers[0].to_dict())

    async def crud_read(request: Request) -> Response:
        query = request.query
        try:
            doc_id = query['docId']
        except KeyError as e:
            raise APIError(request, str(e))
        paragraphs = await self.database.read(doc_id)
        paragraph_ = [paragraph.to_dict() for paragraph in paragraphs]
        return web.json_response(paragraphs_)

    async def crud_create_update(request: Request) -> Response:
        body = await request.json()
        try:
            operation = body['operation']
            doc_id = body['docId']
            text = body['text']
        except KeyError as e:
            raise APIError(request, str(e))
        paragraph = Paragraph(doc_id, text)
        if operation == 'create':
            await self.database.create(paragraph)
            return Response()
        elif operation == 'update':
            await self.database.update(paragraph)
            return Response()

    async def crud_delete(request: Request) -> Response:
        query = request.query
        try:
            doc_id = query['docId']
        except KeyError as e:
            raise APIError(request, str(e))
        await self.database.delete(doc_id)
        return Response()

    def run(self):
        middlewares = [
            exception_middleware,
            attach_uuid_middleware,
        ]
        app = web.Application(middlewares=middlewares)
        app.add_routes([
            web.get('/', self.serve_readme),
            web.get('/github.css', self.serve_github_css),
            web.post('/question', self.answer_question),
            web.get('/index', self.crud_read),
            web.post('/index', self.crud_create_update),
            web.delete('/index', self.crud_delete),
        ])
        web.run_app(app, host=self.host, port=self.port)
