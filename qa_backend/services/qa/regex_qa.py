# regex_qa.py
"""
regex_qa simply tries to match a query against a regular expression,
applys any indicated substitutions, and replies.
"""

from pathlib import Path
from typing import List
from typing import Match
from typing import MutableMapping
from typing import Pattern
from typing import Union
from typing import cast
import logging
import random
import re
import yaml

import attr

from .abstract_qa import QAQueryError
from .abstract_qa import QA
from qa_backend.util import ConfigurationError
from qa_backend.util import QAAnswer

log = logging.getLogger('qa')

@attr.s(slots=True, auto_attribs=True)
class RegexQAConfig:
    file: str

class RegexQA(QA):
    regex: Pattern
    responses: List[str]
    
    def __init__(self, regex: str, responses: List[str]):
        self._requires_context = False
        log.info(f'RegexQA regex: {regex}')
        responses_str = "\n".join(responses)
        log.debug(f"RegexQA responses:\n{responses_str}")
        regex_ = re.sub(r'\s',r'\s+',regex)
        self.regex = re.compile(r'(?i)' + regex_)
        self.responses = responses

    @staticmethod
    def from_config(config: MutableMapping[str,str]) -> List['RegexQA']:
        log.info('creating RegexQA from config')
        log.debug(f"config:\n{config}")
        re_config = RegexQAConfig(**config)
        return RegexQA.from_file(re_config.file)

    async def query(self, question: str, **kwargs) -> List[QAAnswer]:
        log.debug(f'[RegexQA] question: {question}')
        if 'context' in kwargs.keys():
            msg = 'currently not handling context'
            raise QAQueryError(msg)
        match = self.regex.match(question.strip())
        if isinstance(match, Match):
            log.debug(f'got a match')
            r_response = random.choice(self.responses)
            response: str = match.expand(r_response)
            log.debug(f'response: {response}')
            # TODO: calibrate this score
            answers = [QAAnswer(question, response, 1.)]
        else:
            answers = []
        return answers

    @staticmethod
    def from_file(path_: Union[str,Path]) -> List['RegexQA']:
        """Converts multi-doc yaml file into list of RegexQA instances"""
        log.info(f'creating RegexQA from file: {str(path_)}')
        if isinstance(path_,str):
            path = Path(path_)
        else:
            path = cast(Path, path_)
        result: List['RegexQA'] = []
        with open(path) as file:
            for doc in yaml.full_load_all(file):
                regex = doc['regex']
                responses = doc['responses']
                result.append(RegexQA(regex,responses))
        return result
