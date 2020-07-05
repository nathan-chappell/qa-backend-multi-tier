# test_es_db.py

from pathlib import Path
from typing import Optional
from typing import cast
import asyncio
import sys
import unittest

from elasticsearch import Elasticsearch # type: ignore
import yaml

sys.path.append('..')

from qa_backend.services.database import ElasticsearchDatabase
from qa_backend.services.database import ElasticsearchDatabaseConfig
from qa_backend.services.database.database_error import *
from qa_backend.util import Paragraph

es = Elasticsearch()
loop = asyncio.get_event_loop()
config = ElasticsearchDatabaseConfig(
    init_file='es_init.yml',
    erase_if_exists=True,
    explain_filename=None,
    backup_dir=None,
    #index_on_startup_dir='es_test_data',
    index_on_startup_dir=None,
)

class ElasticsearchDatabase_TestInit(unittest.TestCase):
    def test_init(self) -> None:
        es_database = ElasticsearchDatabase(config)
        self.assertTrue(es.indices.exists(es_database.index))
        es.indices.delete(es_database.index)

class ElasticsearchDatabase_TestCreate(unittest.TestCase):
    es_database: Optional[ElasticsearchDatabase] = None

    def setUp(self) -> None:
        self.es_database = ElasticsearchDatabase(config)
        self.paragraphs = [
            Paragraph('foo.txt','foo: this is a test'),
            Paragraph('bar.txt','bar: this is also a test')
        ]

    def test_create(self) -> None:
        es_database = cast(ElasticsearchDatabase, self.es_database)
        try:
            for paragraph in self.paragraphs:
                with self.subTest(docId=paragraph.docId):
                    loop.run_until_complete(
                        es_database.create(paragraph)
                    )
        except DatabaseCreateError as e:
            self.fail(msg=str(e))

    def test_create_duplicate(self) -> None:
        es_database = cast(ElasticsearchDatabase, self.es_database)
        paragraph = self.paragraphs[0]
        with self.assertRaises(DatabaseCreateError):
            loop.run_until_complete(
                es_database.create(paragraph)
            )
            loop.run_until_complete(
                es_database.create(paragraph)
            )

class ElasticsearchDatabase_TestRead(unittest.TestCase):
    es_database: Optional[ElasticsearchDatabase] = None

    def setUp(self) -> None:
        self.es_database = ElasticsearchDatabase(config)
        self.paragraphs = [
            Paragraph('foo.txt','foo: this is a test'),
            Paragraph('bar.txt','bar: this is also a test')
        ]
        for paragraph in self.paragraphs:
            loop.run_until_complete(
                self.es_database.create(paragraph)
            )

    def test_read(self) -> None:
        es_database = cast(ElasticsearchDatabase, self.es_database)
        coro = es_database.read(self.paragraphs[0].docId)
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(1,len(paragraphs))
        self.assertEqual(paragraphs[0].docId, self.paragraphs[0].docId)
        # strip whitespace (\n added from print())
        self.assertEqual(
            paragraphs[0].text.strip(),
            self.paragraphs[0].text.strip()
        )

    def test_read_no_exist(self) -> None:
        es_database = cast(ElasticsearchDatabase, self.es_database)
        coro = es_database.read('doesnt_exist')
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(paragraphs, [])

    # wildcards don't work for the doc _id field
    @unittest.expectedFailure
    def test_read_wildcards(self) -> None:
        es_database = cast(ElasticsearchDatabase, self.es_database)
        coro = es_database.read('*.txt')
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(2,len(paragraphs))

class ElasticsearchDatabase_TestUpdate(unittest.TestCase):
    es_database: Optional[ElasticsearchDatabase] = None

    def setUp(self) -> None:
        self.es_database = ElasticsearchDatabase(config)
        self.paragraph_0 = Paragraph('foo.txt','foo_0')
        self.paragraph_1 = Paragraph('foo.txt','foo_1')
        self.paragraph_no_exist = Paragraph('bar.txt','...')
        loop.run_until_complete(
            self.es_database.create(self.paragraph_0)
        )

    def test_update(self) -> None:
        es_database = cast(ElasticsearchDatabase, self.es_database)
        loop.run_until_complete(
            es_database.update(self.paragraph_1)
        )
        text = es.get(es_database.index, 
                      self.paragraph_1.docId)['_source']['text']
        self.assertEqual(text.strip(), self.paragraph_1.text.strip())

    def test_update_no_exist(self) -> None:
        es_database = cast(ElasticsearchDatabase, self.es_database)
        with self.assertRaises(DatabaseUpdateError):
            coro = es_database.update(self.paragraph_no_exist)
            loop.run_until_complete(coro)

class ElasticsearchDatabase_TestDelete(unittest.TestCase):
    es_database: Optional[ElasticsearchDatabase] = None

    def setUp(self) -> None:
        self.es_database = ElasticsearchDatabase(config)
        self.paragraph_0 = Paragraph('foo.txt','foo_0')
        self.paragraph_no_exist = Paragraph('bar.txt','...')
        loop.run_until_complete(
            self.es_database.create(self.paragraph_0)
        )

    def test_delete(self) -> None:
        es_database = cast(ElasticsearchDatabase, self.es_database)
        loop.run_until_complete(
            es_database.delete(self.paragraph_0.docId)
        )
        self.assertFalse(
            es.exists(
                index=es_database.index,
                id=self.paragraph_0.docId
            )
        )

    def test_delete_no_exist(self) -> None:
        es_database = cast(ElasticsearchDatabase, self.es_database)
        with self.assertRaises(DatabaseDeleteError):
            coro = es_database.delete(self.paragraph_no_exist.docId)
            loop.run_until_complete(coro)

# TODO: Test query

if __name__ == '__main__':
    unittest.main()

