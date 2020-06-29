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

readme_path = 'README.md'
css_path = './github.css'

qa_log = open('qa_log.multi_json','a')
atexit.register(lambda : qa_log.close())

with open(readme_path) as file:
    md = markdown(file.read())
with open(css_path) as file:
    css = file.read()

readme = f"""
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

@routes.get('/github.css')
async def get_stylesheet(request: Request) -> Response:
    return Response(text=css, content_type='text/css')

@routes.get('/')
async def serve_readme(request: Request) -> Response:
    return Response(text=readme, content_type='text/html')

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

def get_qa_data(text: str) -> Dict[str,Any]:
    try:
        reply = json.loads(text)
    except JSONDecodeError:
        return {}
    try:
        keys = ['question', 'answer', 'chosen_answer']
        qa_data = {k:reply[k] for k in keys}
    except KeyError:
        return {}
    else:
        return qa_data

@web.middleware
async def log_qa_middleware(
        request: web.Request, 
        handler: _Handler
        ) -> web.StreamResponse:
    response = await handler(request)
    response = cast(web.Response, response)
    text = response.text
    if isinstance(text, str):
        qa_data = get_qa_data(text)
        # TODO: in real life, we probably shouldn't flush this
        print(json.dumps(qa_data), file=qa_log, flush=True)
    return response

#
# API
#

def get_chosen_answer(answers: List[Dict[str,Any]]) -> str:
    """Implement heuristic to choose an answer.

    Right now, it's unclear which answer to choose.  Given that the empty span
    is the best answer for a paragraph, then we can can ignore that paragraph.
    Comparing the ratings returned from the model for different paragraphs is
    problematic...
    Here are the two current ideas:

    1. Choose the first non-empty answer
    2. Choose best rated non-empty answer

    1. Means that we assume that the most relevant paragraph found by
       ElasticSearch is most likely to contain the right answer, so we pick it.
    2. Means that we take the best rated answer.

    Option 1 has experimentally demonstrated better results (see the reports
    on the blog qa), while 2 is the most commonly implemented heuristic.  As
    of right now, ElasticSearch needs to be better configured to make option 1
    work properly.  Option 2 may be a good option if the model can be trained
    to better identify when a paragraph is irrelevant.

    Better configuring ElasticSearch means incorporating boosts, stopwords,
    and making the base text better.
    More training of the model is a bit more interesting, but perhaps less
    promising...
    """
    def filter_no_answers(candidates: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
        return list(filter(lambda answer: answer['answer'] != '', candidates))
    def sort_by_rating(answers_: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
        return list(sorted(answers_, key=lambda a: a['rating'], reverse=True))
    candidates = answers
    candidates = filter_no_answers(candidates)
    candidates = sort_by_rating(candidates)
    if len(candidates) > 0:
        return candidates[0]['answer']
    else:
        return no_answer()

def make_answer(
        answer: str, rating: float = 0., paragraph: str = "",
        paragraph_rank: int = 0, docId: str = ''
        ) -> Dict[str,Union[str,float,int]]:
    return {
        'answer': answer,
        'rating': rating,
        'paragraph': paragraph,
        'paragraph_rank': paragraph_rank,
        'docId': docId,
    }

async def get_answers(query: str) -> List[Dict[str,Any]]:
    """Consult ES and the model to return potential answers."""
    result: List[Dict[str,Any]] = []
    answers = []
    # 
    # At Jelena's request...
    #
    # so this is sort of a toy implementation/ joke, but it's a glimpse of
    # what's to come if we're going to do much brute force chatbotting...
    #
    happy_employee = get_happy_employee(query)
    if happy_employee is not None:
        return [make_answer(happy_employee)]
    #
    paragraphs = await get_paragraphs_for_query(query, INDEX_NAME, topk=5)
    for rank,paragraph in enumerate(paragraphs):
        context = paragraph['text']
        answer = gpu_pipeline({'question': query, 'context': context},
                           handle_impossible_answer=True,
                           topk=1)
        answers.append(make_answer(
            answer=answer_to_complete_sentence(answer['answer'],context),
            rating=answer['score'],
            paragraph=context,
            paragraph_rank=rank,
            docId=paragraph['_id'],
        ))
    return answers

async def get_question(request: Request) -> Dict[str,str]:
    if request.content_type != 'application/json':
        raise APIError(request,'missing header: content-type:application/json')
    body = await request.json()
    try:
        question = body['question']
        context = body.get('context')
    except KeyError:
        raise APIError(request, 'question required')
    return {'question': question, 'context': context}

@routes.post('/question')
async def answer_question(request: Request) -> Response:
    """Implement QA API."""
    #import pdb
    #pdb.set_trace()
    qid = request['qid']
    question_info = await get_question(request)
    # if context is none: check no_context_qa
    # if they fail: 
    #   retrieve docs 
    #   get answer

    ###
    response: Dict[str,Any] = {'question': {'text': question, 'qid': qid}}
    try:
        response['answers'] = await get_answers(question)
    except Exception as e:
        raise AnswerError(e, question)
    response['chosen_answer'] = get_chosen_answer(response['answers'])
    return json_response(response)

#
# CRUD and webhook
#

@routes.post('/webhook')
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

@routes.post('/index')
async def create_update(request: Request) -> Response:
    """Dispatch create and update requests"""
    body = await request.json()
    command = body.get('command',None)
    if command == 'create':
        docId = body['docId']
        text = body['text']
        git_response = await git_client.create(text,docId)
        index_one(INDEX_NAME, text, docId)
        return git_response
    elif command == 'update':
        docId = body['docId']
        docs = body['docs']
        git_response = await git_client.update(docId, docs)
        await index_all(INDEX_NAME)
        return git_response
    else:
        msg = "require a 'command' with value 'create' or 'update'"
        raise APIError(request, msg)

@routes.delete('/index')
async def delete(request: Request) -> Response:
    """Dispatch create and update requests"""
    query = request.query
    docId = query.get('docId')
    git_response = await git_client.delete(docId)
    es.delete(index=INDEX_NAME,id=docId)
    return git_response



class QAServer:
    database: QueryDatabase
    qas: List[QA]
    micro_endpoint: MicroEndpoint

    def __init__(self, database: QueryDatabase, qas: List[QA]):
        self.database = database
        self.qas = qas

    async def answer_question(question: str, **kwargs) -> QAAnswer:
        ...
        

#
# Server Boilerplate
#

middlewares = [
    exception_to_json_middleware,
    answer_exception_middleware,
    attach_uuid_middleware,
    log_qa_middleware,
]
app = web.Application(middlewares=middlewares)
app.add_routes(routes)

web.run_app(app,host='0.0.0.0',port=8080)
