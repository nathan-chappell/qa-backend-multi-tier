# api_error.py
"""
Error raised when client uses API incorrectly
"""

from json.decoder import JSONDecodeError
from typing import Any
from typing import List
from typing import MutableMapping
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
        log.info(f'[API ERROR]: {str(e)}')
        return Response(status=400, text=str(e))
    except HTTPException as e:
        log.warn(f'{e.__class__.__name__}: {e}')
        return e
    except Exception as e:
        log.exception(e,exc_info=True,stack_info=True)
        msg = 'an internal error has occurred'
        return Response(text=msg, status=500)
