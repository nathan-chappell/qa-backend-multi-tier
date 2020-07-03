# test_regex_qa.py

from pathlib import Path
import asyncio
import logging
import sys
import unittest

sys.path.append('..')

from qa_backend.services.qa import RegexQA

log = logging.getLogger('qa')
loop = asyncio.get_event_loop()

class RegexQA_TestQuery(unittest.TestCase):
    def setUp(self):
        regex_path = Path('regex_test_data/regex_qa.yml')
        self.happy, self.not_mad = RegexQA.from_file(regex_path)

    def test_happy_good(self):
        questions = [
            'do you think that jelena is happy?',
            '  is JasENka  sATiSfied   at mono',
        ]
        for question in questions:
            with (self.subTest(question=question)):
                answer = loop.run_until_complete(self.happy.query(question))[0]
                log.info(f'[question]: {question}')
                log.info(f'[ answer ]: {answer.answer}')
                self.assertNotEqual(answer.answer, '')

    def test_happy_bad(self):
        question = 'is it a pipe?'
        answers = loop.run_until_complete(self.happy.query(question))
        self.assertEqual(len(answers), 0)

    def test_notmad_good(self):
        question = 'Is Nathan Mad at the World?'
        answer = loop.run_until_complete(self.not_mad.query(question))[0]
        self.assertNotEqual(answer.answer, '')
        log.info(f'[question]: {question}')
        log.info(f'[ answer ]: {answer.answer}')

if __name__ == '__main__':
    unittest.main()
