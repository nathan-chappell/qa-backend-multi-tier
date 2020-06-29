# test_regex_qa.py

from pathlib import Path

import fix_path
#from services.qa import RegexQA, QAQueryError, QAAnswer
from services.qa.regex_qa import RegexQA

def test():
    regex_path = Path('regex_test_data/regex_qa.yml')
    regex_qas = RegexQA.from_file(regex_path)
    questions = [
        'do you think that jelena is happy?',
        'is Jasenka satisfied at mono?',
        'is Nathan mad at the world?',
    ]
    for question in questions:
        for regex_qa in regex_qas:
            print(regex_qa.query(question))

test()
print('done')
