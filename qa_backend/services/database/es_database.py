# es_database.py
"""
CRUD frontend to git repository
"""
import asyncio
from pathlib import Path
import logging
from typing import Dict, List, Any, Iterable, MutableMapping

import yaml
from elasticsearch import Elasticsearch # type: ignore
from elasticsearch.exceptions import ConflictError # type: ignore
from elasticsearch.exceptions import NotFoundError # type: ignore

from qa_backend import check_config_keys, ConfigurationError
from .abstract_database import DocId, Paragraph, Database
from .database_error import DatabaseError
from .database_error import DatabaseCreateError, DatabaseUpdateError
from .database_error import DatabaseDeleteError, DatabaseReadError
from .database_error import DatabaseQueryError

log = logging.getLogger('database')

from . import QueryDatabase

es = Elasticsearch()

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

    def __init__(self, init_file: str, erase_if_exists=False):
        self.init_file = init_file
        self.initialize(erase_if_exists)

    @staticmethod
    def from_config(
            config: MutableMapping[str,str]
        ) -> 'ElasticsearchDatabase':
        check_config_keys(config, ['init file','erase if exists'])
        try:
            init_file = config['init file']
            if 'erase if exists' in config.keys():
                erase_if_exists = True
            else:
                erase_if_exists = False
            return ElasticsearchDatabase(init_file, erase_if_exists)
        except ValueError as e:
            raise ConfigurationError(str(e))

    def initialize(self, erase_if_exists=False):
        with open(self.init_file) as file:
            self.init_data = yaml.full_load(file)
        self.check_init_data()
        if not es.indices.exists(self.index):
            es.indices.create(self.index, self.creation)
        elif erase_if_exists:
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
        try:
            es.create(self.index, paragraph.docId, body, refresh=True)
        except ConflictError as e:
            msg = f'docId: {paragraph.docId} already exists'
            raise DatabaseCreateError(msg) # type: ignore

    async def read(
            self,
            docId: DocId
        ) -> List[Paragraph]:
        try:
            if docId == '*':
                body = {'query': {'match_all': {}}}
                response = es.search(index=self.index, body=body)
                paragraphs = [Paragraph(hit['_id'],h['_source']['text'])
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
        try:
            body = {'doc': {'text': paragraph.text}}
            es.update(self.index, paragraph.docId, body)
        except NotFoundError as e:
            msg = f"docId: {paragraph.docId} doesn't exist"
            raise DatabaseUpdateError(msg) # type: ignore

    async def delete(
            self,
            docId: DocId
        ) -> None:
        try:
            es.delete(self.index, docId)
        except NotFoundError as e:
            msg = f"docId: {docId} doesn't exist"
            raise DatabaseDeleteError(msg) # type: ignore

    async def query(
            self,
            query_string: str,
            size: int = 5
        ) -> Iterable[Paragraph]:
        try:
            body = {'query': {'match': {'text': query_string}}, 'size':size}
            response = es.search(index=self.index, body=body)
            paragraphs = []
            for hit in response['hits']['hits']:
                paragraphs.append(Paragraph(hit['_id'], hit['_source']['text']))
            return paragraphs
        except Exception as e:
            raise DatabaseQueryError(str(e)) # type: ignore
