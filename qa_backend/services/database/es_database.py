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
import asyncio
import logging
import re
import yaml

from elasticsearch import Elasticsearch # type: ignore
from elasticsearch.exceptions import ConflictError # type: ignore
from elasticsearch.exceptions import NotFoundError # type: ignore
from elasticsearch.exceptions import ElasticsearchException

from .abstract_database import Database
from .abstract_database import DocId
from .abstract_database import Paragraph
from .database_error import *
from qa_backend.util import ConfigurationError
from qa_backend.util import JsonRepresentation
from qa_backend.util import check_config_keys

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

class ElasticsearchDatabase(QueryDatabase):
    init_file: str
    init_data: Dict[str,Any] = {}
    explain_log: Optional[TextIO] = None
    backup_dir: Optional[str] = None

    def __init__(
            self, init_file: str, erase_if_exists=False,
            explain_filename: Optional[str] = None,
            init_dir: Optional[str] = None,
            backup_dir: Optional[str] = None,
        ):
        msg = ', '.join([init_file,
                         str(erase_if_exists), 
                         str(explain_filename),
                         str(init_dir),
                         str(backup_dir),
                     ])
        log.info(f'creating ElasticsearchDatabase: {msg}')
        self.init_file = init_file
        self.backup_dir = backup_dir
        self.initialize(erase_if_exists)
        if isinstance(explain_filename, str):
            log.debug(f'opening explain_log: {explain_filename}')
            self.explain_log = open(explain_filename, 'a')
        if isinstance(init_dir, str):
            log.debug(f'adding directory: {init_dir}')
            coro = self.add_directory(init_dir)
            asyncio.get_event_loop().run_until_complete(coro)

    async def shutdown(self):
        log.info('shutting down')
        if isinstance(self.backup_dir, str):
            timestamp = datetime.now().strftime('%Y%m%d_%h%m%s')
            directory_path = Path(self.backup_dir) / timestamp
            directory_path.mkdir(parents=True)
            log.info(f'back up at: {str(directory_path.resolve())}')
            await self.dump_to_directory(directory_path)
            log.info(f'back up complete')

    @staticmethod
    def from_config(
            config: MutableMapping[str,str]
        ) -> 'ElasticsearchDatabase':
        conf_keys = [
                'init file',
                'erase if exists',
                'explain file',
                'init dir',
                'backup dir',
            ]
        log.info('initializing ElasticsearchDatabase from config')
        log.debug(f"config:\n{str(config)}")
        check_config_keys(config, conf_keys)
        try:
            init_file = config['init file']
            if 'erase if exists' in config.keys():
                erase_if_exists = True
            else:
                erase_if_exists = False
            explain_filename = config.get('explain file')
            init_dir = config.get('init dir')
            backup_dir = config.get('backup dir')
            return ElasticsearchDatabase(
                        init_file,
                        erase_if_exists,
                        explain_filename,
                        init_dir,
                        backup_dir,
                    )
        except KeyError as e:
            msg = f'bad ElasticsearchDatabase config: {str(e)}'
            log.exception(msg)
            raise ConfigurationError(msg)
        except ValueError as e:
            msg = f'bad ElasticsearchDatabase config: {str(e)}'
            log.exception(msg)
            raise ConfigurationError(msg)

    def initialize(self, erase_if_exists=False):
        with open(self.init_file) as file:
            self.init_data = yaml.full_load(file)
        self.check_init_data()
        log.info(f'init file: {self.init_file}, index: {self.index}')
        if not es.indices.exists(self.index):
            es.indices.create(self.index, self.creation)
        elif erase_if_exists:
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
