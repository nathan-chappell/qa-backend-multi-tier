# test_transformers_qa.py

from pathlib import Path
import unittest
import logging
import asyncio

import common
from qa_backend.services import QAAnswer
from qa_backend.services.qa import TransformersQA, QAQueryError

loop = asyncio.get_event_loop()
log = logging.getLogger('qa')

context = """
Each Hypertext Transfer Protocol (HTTP) message is either a request or a
response. A server listens on a connection for a request, parses each message
received, interprets the message semantics in relation to the identified
request target, and responds to that request with one or more response
messages. A client constructs request messages to communicate specific
intentions, examines received responses to see if the intentions were carried
out, and determines how to interpret the results. This document defines
HTTP/1.1 request and response semantics in terms of the architecture defined
in [RFC7230]. HTTP provides a uniform interface for interacting with a
resource (Section 2), regardless of its type, nature , or implementation, via
the manipulation and transfer of representations ( Section 3).
"""

class TransformersQA_Test(unittest.TestCase):
    trasformers_qa: TransformersQA

    # this is expensive, do it once for the whole class
    @classmethod
    def setUpClass(cls):
        cls.trasformers_qa = TransformersQA()

    def setUp(self):
        self.answerable_questions = [
            'what is http?',
            'what does a server do?',
            'what is the purpose of this document?',
        ]
        self.impossible_questions = [
            'what is a hot dog?',
        ]

    def test_answerable_questions(self):
        for question in self.answerable_questions:
            coro = self.trasformers_qa.query(question, context=context)
            answers = loop.run_until_complete(coro)
            self.assertNotEqual(answers[0].answer, '')
            log.info(answers)

    def test_impossible_questions(self):
        for question in self.impossible_questions:
            coro = self.trasformers_qa.query(question, context=context)
            answers = loop.run_until_complete(coro)
            self.assertEqual(answers[0].answer, '')
            log.info(answers)

if __name__ == '__main__':
    unittest.main()
