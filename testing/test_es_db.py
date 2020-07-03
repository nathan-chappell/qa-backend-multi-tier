# test_es_db.py

from pathlib import Path
import asyncio
import sys
import unittest

from elasticsearch import Elasticsearch # type: ignore
import yaml

sys.path.append('..')

from qa_backend.services.database import ElasticsearchDatabase
from qa_backend.services.database.database_error import *
from qa_backend.util import Paragraph

es = Elasticsearch()
loop = asyncio.get_event_loop()

def set_up_es_db(test_case):
    test_case.init_file = get_es_init_file()
    with open(test_case.init_file) as file:
        test_case.init_data = yaml.full_load(file)
    test_case.index = test_case.init_data['index']

def tear_down_es_db(test_case):
    es.indices.delete(test_case.index)

class ElasticsearchDatabase_TestInit(unittest.TestCase):
    def setUp(self):
        set_up_es_db(self)

    def tearDown(self):
        tear_down_es_db(self)

    def test_init(self):
        es_database = ElasticsearchDatabase(self.init_file)
        self.assertTrue(es.indices.exists(self.index))

class ElasticsearchDatabase_TestCreate(unittest.TestCase):
    def setUp(self):
        set_up_es_db(self)
        self.es_database = ElasticsearchDatabase(self.init_file)
        self.paragraphs = [
            Paragraph('foo.txt','foo: this is a test'),
            Paragraph('bar.txt','bar: this is also a test')
        ]

    def tearDown(self):
        tear_down_es_db(self)

    def test_create(self):
        try:
            for paragraph in self.paragraphs:
                with self.subTest(doc_id=paragraph.doc_id):
                    loop.run_until_complete(
                        self.es_database.create(paragraph)
                    )
        except DatabaseCreateError as e:
            self.fail(msg=str(e))

    def test_create_duplicate(self):
        paragraph = self.paragraphs[0]
        with self.assertRaises(DatabaseCreateError):
            loop.run_until_complete(
                self.es_database.create(paragraph)
            )
            loop.run_until_complete(
                self.es_database.create(paragraph)
            )

class ElasticsearchDatabase_TestRead(unittest.TestCase):
    def setUp(self):
        set_up_es_db(self)
        self.es_database = ElasticsearchDatabase(self.init_file)
        self.paragraphs = [
            Paragraph('foo.txt','foo: this is a test'),
            Paragraph('bar.txt','bar: this is also a test')
        ]
        for paragraph in self.paragraphs:
            loop.run_until_complete(
                self.es_database.create(paragraph)
            )

    def tearDown(self):
        tear_down_es_db(self)

    def test_read(self):
        coro = self.es_database.read(self.paragraphs[0].doc_id)
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(1,len(paragraphs))
        self.assertEqual(paragraphs[0].doc_id, self.paragraphs[0].doc_id)
        # strip whitespace (\n added from print())
        self.assertEqual(
            paragraphs[0].text.strip(),
            self.paragraphs[0].text.strip()
        )

    def test_read_no_exist(self):
        coro = self.es_database.read('doesnt_exist')
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(paragraphs, [])

    # wildcards don't work for the doc _id field
    @unittest.expectedFailure
    def test_read_wildcards(self):
        coro = self.es_database.read('*.txt')
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(2,len(paragraphs))

class ElasticsearchDatabase_TestUpdate(unittest.TestCase):
    def setUp(self):
        set_up_es_db(self)
        self.es_database = ElasticsearchDatabase(self.init_file)
        self.paragraph_0 = Paragraph('foo.txt','foo_0')
        self.paragraph_1 = Paragraph('foo.txt','foo_1')
        self.paragraph_no_exist = Paragraph('bar.txt','...')
        loop.run_until_complete(
            self.es_database.create(self.paragraph_0)
        )

    def tearDown(self):
        tear_down_es_db(self)

    def test_update(self):
        loop.run_until_complete(
            self.es_database.update(self.paragraph_1)
        )
        text = es.get(self.index, self.paragraph_1.doc_id)['_source']['text']
        self.assertEqual(text.strip(), self.paragraph_1.text.strip())

    def test_update_no_exist(self):
        with self.assertRaises(DatabaseUpdateError):
            coro = self.es_database.update(self.paragraph_no_exist)
            loop.run_until_complete(coro)

class ElasticsearchDatabase_TestDelete(unittest.TestCase):
    def setUp(self):
        set_up_es_db(self)
        self.es_database = ElasticsearchDatabase(self.init_file)
        self.paragraph_0 = Paragraph('foo.txt','foo_0')
        self.paragraph_no_exist = Paragraph('bar.txt','...')
        loop.run_until_complete(
            self.es_database.create(self.paragraph_0)
        )

    def tearDown(self):
        tear_down_es_db(self)

    def test_delete(self):
        loop.run_until_complete(
            self.es_database.delete(self.paragraph_0.doc_id)
        )
        path = Path(self.init_file) / self.paragraph_0.doc_id
        self.assertFalse(path.exists())

    def test_delete_no_exist(self):
        with self.assertRaises(DatabaseDeleteError):
            coro = self.es_database.delete(self.paragraph_no_exist.doc_id)
            loop.run_until_complete(coro)

# TODO: Test query

if __name__ == '__main__':
    unittest.main()

