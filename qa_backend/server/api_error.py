# api_error.py
"""
Error raised when client uses API incorrectly
"""

from json.decoder import JSONDecodeError
from typing import Any
from typing import List
from typing import Mapping
from typing import Type
from typing import Union
import logging

from aiohttp.web import HTTPException
from aiohttp.web import Request
from aiohttp.web import Response
from aiohttp.web import Response
from aiohttp.web import StreamResponse
from aiohttp.web import middleware
from aiohttp.web_middlewares import _Handler # type: ignore

log = logging.getLogger('server')

JsonType = Union[Type[str],
                 Type[int],
                 Type[float],
                 Type[None],
                 ]
TypeCheckArg = Union[JsonType, List[JsonType]]

class APIError(RuntimeError):
    """Exception class to indicate API related errors."""
    message: str
    method: str
    path: str
    def __init__(self, request: Request, message: str):
        super().__init__()
        self.method = request.method
        self.path = request.path
        self.message = message
        # not sure if to make .info or .error...
        log.info(str(self))

    @property
    def _api(self) -> str:
        return f'{self.method} {self.path}'

    def __str__(self) -> str:
        return self._api + ' - ' + self.message

    def __repr__(self) -> str:
        return f'<APIError: {str(self)}>'

@middleware
async def exception_middleware(
        request: Request, 
        handler: _Handler
        ) -> StreamResponse:
    """Catch listed exceptions and convert them to json responses."""
    try:
        result = await handler(request)
        return result
    except APIError as e:
        log.info('[API ERROR]: {str(self)}')
        return Response(status=400, text=str(e))
    except HTTPException as e:
        log.warn(f'HTTPException: {e}')
        return e
    except Exception as e:
        log.exception(e)
        msg = 'an internal error has occurred'
        return Response(text=msg, status=500)

def _get_type_name(types: TypeCheckArg) -> str:
    if isinstance(types, type):
        return types.__name__
    elif isinstance(types,list):
        return '|'.join([type_.__name__ for type_ in types])
    else:
        raise RuntimeError('Unreachable')

def _type_check(type_: type, types: TypeCheckArg) -> bool:
    if isinstance(types, type):
        return type_ == types
    elif isinstance(types, list):
        return type_ in types
    else:
        raise RuntimeError('Unreachable')

# very basic type checking
async def get_json_body(
        request: Request,
        json_fmt: Mapping[str,TypeCheckArg]
    ) -> Mapping[str,Any]:
    """Check for json and do type checking on body"""
    json_fmt_str = str({k:_get_type_name(json_fmt[k]) for k in json_fmt})
    msg = f'required: json with format: {json_fmt_str}'
    try:
        body = await request.json()
    except JSONDecodeError as e:
        raise APIError(request, msg)
    if set(body.keys()) != set(json_fmt.keys()):
        raise APIError(request, msg)
    if not all([_type_check(type(body[k]), json_fmt[k])
                for k in json_fmt]):
        raise APIError(request, msg)
    return body
