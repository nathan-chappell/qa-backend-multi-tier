# testing/test_git_db.py

import asyncio
import subprocess
from pathlib import Path
from uuid import uuid4
import unittest

from common import set_up_git_db, tear_down_git_db
from qa_backend.services import Paragraph
from qa_backend.services.database import *

loop = asyncio.get_event_loop()

class GitDatabase_TestInit(unittest.TestCase):
    def setUp(self):
        set_up_git_db(self)

    def tearDown(self):
        tear_down_git_db(self)

    def test_init(self):
        try:
            git_database = GitDatabase(self.git_dir)
        except GitError as e:
            self.fail(msg=str(e))

class GitDatabase_TestCreate(unittest.TestCase):
    def setUp(self):
        set_up_git_db(self)
        self.git_database = GitDatabase(self.git_dir)
        self.paragraphs = [
            Paragraph('foo.txt','foo: this is a test'),
            Paragraph('bar.txt','bar: this is also a test')
        ]

    def tearDown(self):
        tear_down_git_db(self)

    def test_create(self):
        try:
            for paragraph in self.paragraphs:
                with self.subTest(doc_id=paragraph.doc_id):
                    loop.run_until_complete(
                        self.git_database.create(paragraph)
                    )
        except DatabaseCreateError as e:
            self.fail(msg=str(e))

    def test_create_duplicate(self):
        paragraph = self.paragraphs[0]
        with self.assertRaises(DatabaseCreateError):
            loop.run_until_complete(
                self.git_database.create(paragraph)
            )
            loop.run_until_complete(
                self.git_database.create(paragraph)
            )

class GitDatabase_TestRead(unittest.TestCase):
    def setUp(self):
        set_up_git_db(self)
        self.git_database = GitDatabase(self.git_dir)
        self.paragraphs = [
            Paragraph('foo.txt','foo: this is a test'),
            Paragraph('bar.txt','bar: this is also a test')
        ]
        for paragraph in self.paragraphs:
            loop.run_until_complete(
                self.git_database.create(paragraph)
            )

    def tearDown(self):
        tear_down_git_db(self)

    def test_read(self):
        coro = self.git_database.read(self.paragraphs[0].doc_id)
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(1,len(paragraphs))
        self.assertEqual(paragraphs[0].doc_id, self.paragraphs[0].doc_id)
        # strip whitespace (\n added from print())
        self.assertEqual(
            paragraphs[0].text.strip(),
            self.paragraphs[0].text.strip()
        )

    def test_read_no_exist(self):
        coro = self.git_database.read('doesnt_exist')
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(paragraphs, [])

    def test_read_wildcards(self):
        coro = self.git_database.read('*.txt')
        paragraphs = loop.run_until_complete(coro)
        self.assertEqual(2,len(paragraphs))

class GitDatabase_TestUpdate(unittest.TestCase):
    def setUp(self):
        set_up_git_db(self)
        self.git_database = GitDatabase(self.git_dir)
        self.paragraph_0 = Paragraph('foo.txt','foo_0')
        self.paragraph_1 = Paragraph('foo.txt','foo_1')
        self.paragraph_no_exist = Paragraph('bar.txt','...')
        loop.run_until_complete(
            self.git_database.create(self.paragraph_0)
        )

    def tearDown(self):
        tear_down_git_db(self)

    def test_update(self):
        loop.run_until_complete(
            self.git_database.update(self.paragraph_1)
        )
        path = Path(self.git_dir) / self.paragraph_1.doc_id
        with open(path) as file:
            text = file.read()
        self.assertEqual(text.strip(), self.paragraph_1.text.strip())

    def test_update_no_exist(self):
        with self.assertRaises(DatabaseUpdateError):
            coro = self.git_database.update(self.paragraph_no_exist)
            loop.run_until_complete(coro)

class GitDatabase_TestDelete(unittest.TestCase):
    def setUp(self):
        set_up_git_db(self)
        self.git_database = GitDatabase(self.git_dir)
        self.paragraph_0 = Paragraph('foo.txt','foo_0')
        self.paragraph_no_exist = Paragraph('bar.txt','...')
        loop.run_until_complete(
            self.git_database.create(self.paragraph_0)
        )

    def tearDown(self):
        tear_down_git_db(self)

    def test_delete(self):
        loop.run_until_complete(
            self.git_database.delete(self.paragraph_0.doc_id)
        )
        path = Path(self.git_dir) / self.paragraph_0.doc_id
        self.assertFalse(path.exists())

    def test_delete_no_exist(self):
        with self.assertRaises(DatabaseDeleteError):
            coro = self.git_database.delete(self.paragraph_no_exist.doc_id)
            loop.run_until_complete(coro)

if __name__ == '__main__':
    unittest.main()
