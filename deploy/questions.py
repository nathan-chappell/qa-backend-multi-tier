# questions.py

from pathlib import Path
from pprint import pprint
from typing import List

import requests

def get_questions() -> List[List[str]]:
    questions = [[]]
    questions_path = Path('questions.txt')
    with open(questions_path) as file:
        for line in file:
            if line.strip() == '':
                questions.append([])
            else:
                questions[-1].append(line)
    return questions

questions = get_questions()
endpoint = 'http://localhost:8280/question'

