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
        formatted = ''.join([f'{"["+record.levelname+"]":10}',
                              f'{"["+record.name+"]":10}',
                              f'[{record.pathname}:{record.lineno}]'])
        if len(lines) == 0:
            return formatted
        elif len(lines) == 1:
            return f'{formatted} - {lines[0]}'
        else:
            eol = "\n" + ' '*4 + '-'*4 + ' '*4
            return formatted + eol + eol.join(lines)
        
_lognames = ['database','qa','server','testing','main']
def init_logs():
    print(f'initializing logs: {", ".join(_lognames)}')
    logs = [logging.getLogger(log) for log in _lognames]
    handler = logging.StreamHandler()
    handler.setFormatter(LoggingFormatter())
    for log in logs:
        log.addHandler(handler)

def set_all_loglevels(levelname: str):
    level_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARN,
        'error': logging.ERROR,
    }
    for logname in _lognames:
        logging.getLogger(logname).setLevel(level_map[levelname])

init_logs()
set_all_loglevels('info')

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
    __slots__ = ['docId','text']
    docId: str
    text: str

    def __init__(self, docId: str, text: str):
        if not docId.endswith('.txt'):
            raise ValueError("Paragraph.docId must have .txt as suffix")
        self.docId = docId
        self.text = text


