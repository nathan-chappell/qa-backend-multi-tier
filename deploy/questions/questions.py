# questions.py

from json.decoder import JSONDecodeError
from pathlib import Path
from pprint import pprint
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
import atexit
import logging
import sys
import textwrap

import attr
import elasticsearch # type: ignore
import requests

sys.path.append('..')

#from pretty_explain import print_explain
from qa_backend.services.database.es_database import Explanation

es = elasticsearch.Elasticsearch()
log = logging.getLogger('test')
endpoint = 'http://localhost:8280/question'
index = 'deployment-dev-index'
output_file = open('question_results.txt','w')
atexit.register(lambda : output_file.close())

def get_questions() -> List[List[str]]:
    questions: List[List[str]] = [[]]
    questions_path = Path('questions.txt')
    with open(questions_path) as file:
        for line in file:
            if line.strip() == '':
                questions.append([])
            else:
                questions[-1].append(line)
    return questions

def get_questions_flat():
    questions = []
    questions_ = get_questions()
    for l in questions_:
        questions.extend(l)
    return questions

def format_explanation(explanation: Explanation) -> str:
    result: List[str] = []
    docId = explanation.docId
    total = explanation.total_score
    result.append(f'{total:6.3f} {docId}')
    scores = explanation.scores
    scores = sorted(scores, key = lambda tpl: tpl[1], reverse=True)
    for i, tpl in enumerate(scores):
        result.append(' --- ' + f'{tpl[0]:12} {tpl[1]:6.3f} {tpl[2]:2.0f}')
    return "\n".join(result)

class Answer:
    question: str
    answer: str
    docId: str
    qid: str
    text: str
    explanation: Explanation

    def __init__(self, chosen_answer: Dict[str,Any], qid: str):
        self.question = chosen_answer['question']
        self.answer = chosen_answer['answer']
        self.docId = chosen_answer['docId']
        self.qid = qid
        self.text = chosen_answer['paragraph']['text']
        query_body = {'query':{'match':{'text':self.question}}}
        self.explanation = Explanation(query_body, self.docId,
                                       index, self.qid)

    def format(self) -> str:
        result = []
        result.append(f'question - {self.question}')
        result.append(f'answer - {self.answer}')
        result.append(format_explanation(self.explanation))
        result.append('-'*80)
        result.append(textwrap.indent(textwrap.fill(self.text), ' --- '))
        result.append('_'*80)
        return "\n".join(result)

def get_answers(questions: List[str]) -> Tuple[List[Answer],List[str]]:
    answers: List[Answer] = []
    no_answers: List[str] = []
    for question in questions:
        try:
            body = {'question':question}
            response = requests.post(endpoint, json=body)
            chosen_answer = response.json()['chosen_answer']
            if chosen_answer is None:
                no_answers.append(question)
            else:
                qid = response.cookies['qa_server.qid']
                answers.append(Answer(chosen_answer, qid))
        except JSONDecodeError as e:
            log.exception(f'[Error answering question: {question}, {e}')
    return answers, no_answers

if __name__ == '__main__':
    questions = get_questions_flat()
    #answers, no_answers = get_answers(questions[:5])
    answers, no_answers = get_answers(questions)

    for answer in answers:
        print(answer.format(),file=output_file,flush=True)
    print('_-'*40,file=output_file,flush=True)
    for no_answer in no_answers:
        print(no_answer,file=output_file,flush=True)

