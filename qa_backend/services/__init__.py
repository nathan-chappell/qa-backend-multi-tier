"""
TODO: better docstr
Services:
* Database
    * git backend
    * QueryDatabas
        * es backend
* qa_service
    * transformers qa service
"""

import json
import logging
import re
from typing import List

DocId = str

class LoggingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        #print(f'formatting message: {message}')
        lines: List[str] = list(map(str.strip,re.split("\n", message)))
        lines = list(filter(lambda s: s.strip() != '', lines))
        formatted = f'[{record.levelname}] [{record.pathname}:{record.lineno}]'
        if len(lines) == 0:
            return formatted
        elif len(lines) == 1:
            return f'{formatted} - {lines[0]}'
        else:
            eol = "\n" + ' '*4 + '-'*4 + ' '*4
            return formatted + eol + eol.join(lines)
        
def init_logs():
    lognames = ['database','qa','server']
    print(f'initializing logs: {", ".join(lognames)}')
    logs = [logging.getLogger(log) for log in lognames]
    handler = logging.StreamHandler()
    handler.setFormatter(LoggingFormatter())
    for log in logs:
        log.addHandler(handler)
        log.setLevel(logging.INFO)

init_logs()

#
# metaclass for objects to be "automatically serialized"
#
class JsonRepresentation(type):
    """Use json.dumps to __repr__ annotated variables."""
    def __new__(self, cls, bases, namespace):
        def json_repr(self) -> str:
            data = {
                k: getattr(self,k).__repr__()
                for k in namespace['__annotations__']
            }
            return json.dumps(data)
        if '__repr__' not in namespace:
            namespace['__repr__'] = json_repr
        return type(cls, bases, namespace)

class QAAnswer(metaclass=JsonRepresentation):
    __slots__ = ['score','question','answer']
    question: str
    answer: str
    score: float

    def __init__(self, question: str, answer: str, score: float):
        self.question = question
        self.answer = answer
        self.score = score

class Paragraph(metaclass=JsonRepresentation):
    __slots__ = ['doc_id','text']
    doc_id: str
    text: str

    def __init__(self, doc_id: str, text: str):
        self.doc_id = doc_id
        self.text = text

