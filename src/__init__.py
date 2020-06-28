"""
QA Server

Uses
* Git as a database backend,
* Elasticsearch as a search tool
* transformers for QA

"""

import logging
import re
from typing import List

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
    logs = [logging.getLogger(log) for log in lognames]
    handler = StreamHandler()
    handler.setFormatter(LoggingFormatter())
    for log in logs:
        log.setHandler(handler)
        log.setLevel(logging.INFO)

init_logs()
