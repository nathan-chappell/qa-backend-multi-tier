# util/from_request.py
"""
Classes which are designed to be constructed from Requests
"""

from json.decoder import JSONDecodeError
from typing import Any
from typing import Generic
from typing import Optional
from typing import TypeVar
from typing import cast
import logging

from aiohttp.web import Request
from attr.validators import in_
from attr.validators import instance_of
from attr.validators import matches_re
from attr.validators import optional
import attr

from .api_error import APIError

log = logging.getLogger('server')
T = TypeVar('T')

class FromRequest(Generic[T]):
    _api_error_message: str
    
    def __init__(self,**kwargs):
        raise RuntimeError('Do not instantiate this class')

    @classmethod
    async def from_request(cls, request: Request) -> T:
        try:
            body = await request.json()
        except JSONDecodeError as e:
            msg = f"{cls._api_error_message}\nError: {e}"
            raise APIError(request, msg)
        try:
            return cast(T,cls(**body))
        except (TypeError, ValueError) as e:
            msg = f"{cls._api_error_message}\nError: {e}"
            raise APIError(request, msg)

def validate_question(self: Any, attr: attr.Attribute, q: str):
    if not type(q) == str:
        raise ValueError('question must be a string')
    if q == '':
        raise ValueError('question must not be empty')

def validate_context(self: Any, attr: attr.Attribute, c: Optional[str]):
    if not type(c) == str:
        raise ValueError('context must be a string')
    if c == '':
        raise ValueError('context must not be empty')

@attr.s
class JsonQuestion(FromRequest['JsonQuestion']):
    question: str = attr.ib(converter=str, validator=validate_question)
    context: str = attr.ib(converter=str, validator=validate_context)

JsonQuestion._api_error_message = \
        'Question Format: {"question":str, "context": str}'

@attr.s
class JsonQuestionOptionalContext(FromRequest['JsonQuestionOptionalContext']):
    question: str = attr.ib(converter=str, validator=validate_question)
    context: Optional[str] = attr.ib(converter=str, default=None,
                                     validator=optional(validate_context))

JsonQuestionOptionalContext._api_error_message = \
        'Question Format: {"question":str, "context": Optional[str]}'

@attr.s
class JsonCrudOperation(FromRequest['JsonCrudOperation']):
    operation: str = attr.ib(validator=in_(['create','update']))
    docId: str = attr.ib(validator=matches_re(r'.*\.txt'))
    text: str = attr.ib(validator=instance_of(str))

JsonCrudOperation._api_error_message = \
    'Json CRUD Operation: {"operation":{create|update}, "docId":str, "text":str}'
