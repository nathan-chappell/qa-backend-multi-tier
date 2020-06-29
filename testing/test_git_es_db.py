# test_git_es_db.py

import asyncio
import unittest
from pathlib import Path
from uuid import uuid4
import subprocess

from elasticsearch import Elasticsearch
import yaml

import fix_path
from qa_backend.services import Paragraph
from qa_backend.services.database import *

es = Elasticsearch()
loop = asyncio.get_event_loop()

def get_init_file() -> str:
    return './es_test_data/config.yml'

def get_git_dir():
    git_dir = str(uuid4())
    if Path(git_dir).exists():
        raise RuntimeError(f'about to step on {git_dir}')
    return git_dir

def remove_dir(name: str):
    subprocess.run(['rm', '-rf', name])

class GitEsDatabase_TestInit(unittest.TestCase):
    def setUp(self):
        self.init_file = get_init_file()
        with open(self.init_file) as file:
            self.init_data = yaml.full_load(file)
        self.index = self.init_data['index']
        self.git_dir = get_git_dir()
        self.es_database = ElasticsearchDatabase(self.init_file)
        self.git_database = GitDatabase(self.git_dir)

    def tearDown(self):
        es.indices.delete(self.index)
        remove_dir(self.git_dir)

    def test_init(self):
        self.git_es_database = GitEsDatabase(
                                    self.git_database,
                                    self.es_database
                               )

class GitEsDatabase_TestCreate(unittest.TestCase):
    def setUp(self):
        self.init_file = get_init_file()
        with open(self.init_file) as file:
            self.init_data = yaml.full_load(file)
        self.index = self.init_data['index']
        self.git_dir = get_git_dir()
        self.git_database = GitDatabase(self.git_dir)
        self.es_database = ElasticsearchDatabase(self.init_file)
        self.git_es_database = GitEsDatabase(
                                    self.git_database,
                                    self.es_database
                               )
        self.paragraphs = [
            Paragraph('foo.txt','foo: this is a test'),
            Paragraph('bar.txt','bar: this is also a test')
        ]

    def tearDown(self):
        es.indices.delete(self.index)
        remove_dir(self.git_dir)

    def test_create(self):
        try:
            for paragraph in self.paragraphs:
                with self.subTest(doc_id=paragraph.doc_id):
                    loop.run_until_complete(
                        self.git_es_database.create(paragraph)
                    )
        except DatabaseCreateError as e:
            self.fail(msg=str(e))

    def test_create_duplicate(self):
        paragraph = self.paragraphs[0]
        with self.assertRaises(DatabaseCreateError):
            loop.run_until_complete(
                self.git_es_database.create(paragraph)
            )
            loop.run_until_complete(
                self.git_es_database.create(paragraph)
            )

class GitEsDatabase_TestRead(unittest.TestCase):
    def setUp(self):
        self.init_file = get_init_file()
        with open(self.init_file) as file:
            self.init_data = yaml.full_load(file)
        self.index = self.init_data['index']
        self.git_dir = get_git_dir()
        self.git_database = GitDatabase(self.git_dir)
        self.es_database = ElasticsearchDatabase(self.init_file)
        self.git_es_database = GitEsDatabase(
                                    self.git_database,
                                    self.es_database
                               )
        self.paragraphs = [
            Paragraph('foo.txt','foo: this is a test'),
            Paragraph('bar.txt','bar: this is also a test')
        ]
        for paragraph in self.paragraphs:
            loop.run_until_complete(
                self.git_es_database.create(paragraph)
            )

    def tearDown(self):
        es.indices.delete(self.index)
        remove_dir(self.git_dir)

    def test_read(self):
        coro = self.git_es_database.read(self.paragraphs[0].doc_id)
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(1,len(paragraphs))
        self.assertEqual(paragraphs[0].doc_id, self.paragraphs[0].doc_id)
        # strip whitespace (\n added from print())
        self.assertEqual(
            paragraphs[0].text.strip(),
            self.paragraphs[0].text.strip()
        )

    def test_read_no_exist(self):
        coro = self.git_es_database.read('doesnt_exist')
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(paragraphs, [])

    def test_read_wildcards(self):
        coro = self.git_es_database.read('*.txt')
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(2,len(paragraphs))

class GitEsDatabase_TestUpdate(unittest.TestCase):
    def setUp(self):
        self.init_file = get_init_file()
        with open(self.init_file) as file:
            self.init_data = yaml.full_load(file)
        self.index = self.init_data['index']
        self.git_dir = get_git_dir()
        self.git_database = GitDatabase(self.git_dir)
        self.es_database = ElasticsearchDatabase(self.init_file)
        self.git_es_database = GitEsDatabase(
                                    self.git_database,
                                    self.es_database
                               )
        self.paragraph_0 = Paragraph('foo.txt','foo_0')
        self.paragraph_1 = Paragraph('foo.txt','foo_1')
        self.paragraph_no_exist = Paragraph('bar.txt','...')
        loop.run_until_complete(
            self.git_es_database.create(self.paragraph_0)
        )

    def tearDown(self):
        es.indices.delete(self.index)
        remove_dir(self.git_dir)

    def test_update(self):
        loop.run_until_complete(
            self.git_es_database.update(self.paragraph_1)
        )
        text = es.get(self.index, self.paragraph_1.doc_id)['_source']['text']
        self.assertEqual(text.strip(), self.paragraph_1.text.strip())

    def test_update_no_exist(self):
        with self.assertRaises(DatabaseUpdateError):
            coro = self.git_es_database.update(self.paragraph_no_exist)
            loop.run_until_complete(coro)

class GitEsDatabase_TestDelete(unittest.TestCase):
    def setUp(self):
        self.init_file = get_init_file()
        with open(self.init_file) as file:
            self.init_data = yaml.full_load(file)
        self.index = self.init_data['index']
        self.git_dir = get_git_dir()
        self.git_database = GitDatabase(self.git_dir)
        self.es_database = ElasticsearchDatabase(self.init_file)
        self.git_es_database = GitEsDatabase(
                                    self.git_database,
                                    self.es_database
                               )
        self.paragraph_0 = Paragraph('foo.txt','foo_0')
        self.paragraph_0 = Paragraph('foo.txt','foo_0')
        self.paragraph_no_exist = Paragraph('bar.txt','...')
        loop.run_until_complete(
            self.git_es_database.create(self.paragraph_0)
        )

    def tearDown(self):
        es.indices.delete(self.index)
        remove_dir(self.git_dir)

    def test_delete(self):
        loop.run_until_complete(
            self.git_es_database.delete(self.paragraph_0.doc_id)
        )
        path = Path(self.init_file) / self.paragraph_0.doc_id
        self.assertFalse(path.exists())

    def test_delete_no_exist(self):
        with self.assertRaises(DatabaseDeleteError):
            coro = self.git_es_database.delete(self.paragraph_no_exist.doc_id)
            loop.run_until_complete(coro)

if __name__ == '__main__':
    unittest.main()
