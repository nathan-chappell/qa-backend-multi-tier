# es_database.py
"""
CRUD frontend to git repository
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import MutableMapping
from typing import Optional
from typing import TextIO
from typing import Tuple
from typing import Union
import asyncio
import logging
import re
import yaml

from elasticsearch import Elasticsearch # type: ignore
from elasticsearch.exceptions import ConflictError # type: ignore
from elasticsearch.exceptions import NotFoundError # type: ignore
from elasticsearch.exceptions import ElasticsearchException
import attr

from .abstract_database import Database
from .abstract_database import DocId
from .abstract_database import Paragraph
from .database_error import *
from qa_backend.util import ConfigurationError
from qa_backend.util import JsonRepresentation
from qa_backend.util import convert_bool

log = logging.getLogger('database')

from . import QueryDatabase

es = Elasticsearch()

class Explanation(JsonRepresentation):
    __slots__ = ['body','scores','docId','index','total_score']
    query: Dict[str,Any]
    total_score: float
    scores: List[Tuple[str,float]]
    docId: str
    index: str
    text_re = re.compile(r'.*\(text:(\w+) .*')

    def __init__(self, body: Dict[str,Any], docId: str, index: str):
        try:
            self.body = body['query']
        except KeyError as e:
            info = '<docId:{docId}, index:{index}>'
            msg = f'explanation body has no query, {info}'
            log.exception(msg)
            raise RuntimeError(msg)
        self.docId = docId
        self.scores = []
        self.index = index
        try:
            explanation = es.explain(index, id=docId, body={'query':self.body})
        except ElasticsearchException as e:
            log.exception('ES Exception: {e}')
            raise RuntimeError(str(e))
        try:
            self.total_score = float(explanation['explanation']['value'])
            for detail in explanation['explanation']['details']:
                text = self.text_re.sub(r'\1',detail['description'])
                score = float(detail['value'])
                self.scores.append((text,score))
        # KeyError, something in re, etc
        except Exception as e:
            log.exception(e)
            raise RuntimeError(str(e))

class ElasticsearchDatabaseError(RuntimeError):
    message: str

    def __init__(self, message: str = ''):
        super().__init__()
        self.message = message
        log.error(str(self))

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        msg = self.message
        return f'<{cls}:(message={msg})>'

@attr.s(slots=True, auto_attribs=True)
class ElasticsearchDatabaseConfig:
    init_file: str
    erase_if_exists: Union[bool,str] = attr.ib(default=False, kw_only=True,
                                       converter=convert_bool)
    explain_filename: Optional[str] = attr.ib(default=None, kw_only=True)
    backup_dir: Optional[str] = attr.ib(default=None, kw_only=True)
    index_on_startup_dir: Optional[str] = attr.ib(default=None, kw_only=True)

class ElasticsearchDatabase(QueryDatabase):
    config: ElasticsearchDatabaseConfig
    init_data: Dict[str,Any] = {}
    explain_log: Optional[TextIO] = None

    def __init__(self, config: ElasticsearchDatabaseConfig):
        log.info(f'creating ElasticsearchDatabase: {config}')
        self.config = config
        self.initialize()
        if isinstance(config.explain_filename, str):
            log.debug(f'opening explain_log: {config.explain_filename}')
            self.explain_log = open(config.explain_filename, 'a')
        if isinstance(config.index_on_startup_dir, str):
            log.debug(f'adding directory: {config.index_on_startup_dir}')
            coro = self.add_directory(config.index_on_startup_dir)
            asyncio.get_event_loop().run_until_complete(coro)

    async def shutdown(self) -> None:
        log.info('shutting down')
        if isinstance(self.config.backup_dir, str):
            timestamp = datetime.now().strftime('%Y%m%d_%h%m%s')
            directory_path = Path(self.config.backup_dir) / timestamp
            directory_path.mkdir(parents=True)
            log.info(f'back up at: {str(directory_path.resolve())}')
            await self.dump_to_directory(directory_path)
            log.info(f'back up complete')

    @staticmethod
    def from_config(
            config: MutableMapping[str,str]
        ) -> 'ElasticsearchDatabase':
        es_config = ElasticsearchDatabaseConfig(**config)
        return ElasticsearchDatabase(es_config)

    def initialize(self, erase_if_exists: bool = False):
        with open(self.config.init_file) as file:
            self.init_data = yaml.full_load(file)
        self.check_init_data()
        log.info(f'init file: {self.config.init_file}, index: {self.index}')
        if not es.indices.exists(self.index):
            es.indices.create(self.index, self.creation)
        elif self.config.erase_if_exists:
            log.warn(f'erasing old index')
            es.indices.delete(self.index)
            es.indices.create(self.index, self.creation)

    def check_init_data(self):
        for k in ['index','creation']:
            if self.init_data.get(k,None) is None:
                msg = f'{k} required to be in init_file: {self.init_file}'
                raise ElasticsearchDatabaseError(msg)

    @property
    def index(self) -> str:
        return self.init_data['index']

    @property
    def creation(self) -> str:
        return self.init_data['creation']

    async def create(
            self, 
            paragraph: Paragraph
        ) -> None:
        body = {'text': paragraph.text}
        log.info(f'creating docId: {paragraph.docId}')
        try:
            es.create(self.index, paragraph.docId, body, refresh=True)
        except ConflictError as e:
            msg = f'docId: {paragraph.docId} already exists'
            raise DatabaseAlreadyExistsError(msg) # type: ignore

    async def get_all(
            self
        ) -> List[Paragraph]:
        return await self.read('*')

    async def read(
            self,
            docId: DocId
        ) -> List[Paragraph]:
        log.info(f'read docId: {docId}')
        try:
            if docId == '*':
                body: Dict[str,Any] = {'query':{'match_all':{}},'size':10000}
                response = es.search(index=self.index, body=body)
                paragraphs = [Paragraph(hit['_id'], hit['_source']['text'])
                              for hit in response['hits']['hits']]
                return paragraphs
            else:
                response = es.get(index=self.index, id=docId)
                return [Paragraph(docId, response['_source']['text'])]
        except NotFoundError as e:
            return []

    async def update(
            self,
            paragraph: Paragraph
        ) -> None:
        log.info(f'updating {paragraph.docId}')
        log.debug(f'text: {paragraph.text}')
        try:
            body = {'doc': {'text': paragraph.text}}
            es.update(self.index, paragraph.docId, body)
            log.info('update complete')
        except NotFoundError as e:
            msg = f"docId: {paragraph.docId} doesn't exist"
            log.info(msg)
            raise DatabaseUpdateNotFoundError(msg) # type: ignore

    async def delete(
            self,
            docId: DocId
        ) -> None:
        log.info(f'delete docId: {docId}')
        try:
            es.delete(self.index, docId)
        except NotFoundError as e:
            msg = f"docId: {docId} doesn't exist"
            raise DatabaseDeleteError(msg) # type: ignore

    async def query(
            self,
            query_string: str,
            size: int = 10
        ) -> Iterable[Paragraph]:
        log.info(f'query[:{size}] {query_string}')
        body = {'query': {'match': {'text': query_string}}, 'size':size}
        response = es.search(index=self.index, body=body)
        paragraphs = []
        for hit in response['hits']['hits']:
            try:
                _id = hit['_id']
                hit_text = hit['_source']['text']
            except KeyError as e:
                log.exception(f'explain failed: {str(e)}')
                return []
            paragraphs.append(Paragraph(_id, hit_text))
            try:
                if self.explain_log is not None:
                        print(Explanation(body,_id,self.index),
                              file=self.explain_log,
                              flush=True)
            except RuntimeError as e:
                log.error(f'explain failed: {e}')
        return paragraphs
