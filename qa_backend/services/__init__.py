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
from typing import List, Dict, Any, Optional

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
class JsonRepresentation:
    """Use json.dumps to __repr__ annotated variables."""
    def to_dict(self) -> Dict[str,Any]:
        return {k: getattr(self,k) for k in self.__slots__}

    def __repr__(self) -> str:
        return json.dumps(self.to_dict())

class QAAnswer(JsonRepresentation):
    __slots__ = ['score','question','answer','docId']
    question: str
    answer: str
    score: float
    docId: Optional[str]

    def __init__(self, question: str, answer: str, score: float, docId: Optional[str] = None):
        self.question = question
        self.answer = answer
        self.score = score
        self.docId = docId

class Paragraph(JsonRepresentation):
    __slots__ = ['doc_id','text']
    doc_id: str
    text: str

    def __init__(self, doc_id: str, text: str):
        if not doc_id.endswith('.txt'):
            raise ValueError("Paragraph.doc_id must have .txt as suffix")
        self.doc_id = doc_id
        self.text = text


