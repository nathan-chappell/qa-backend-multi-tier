# util/logging.py
"""
Global logging configuration and utilities
"""

from typing import List
import logging
import re

class LoggingFormatter(logging.Formatter):
    """Formatter used by all logs.  Should look good."""
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
        
_lognames = ['database','qa','server','testing','main','util']

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

