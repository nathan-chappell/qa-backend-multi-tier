# services/database/DatabaseError.py
"""
Errors raised by databases for CRUD operations
"""

from traceback import format_tb
import logging
import sys

log = logging.getLogger('database')

class DatabaseError(RuntimeError):
    message: str
    operation: str

    def __init__(self, message: str):
        self.message = message
        log.error(self)

    @classmethod
    def __init_subclass__(cls: type, operation: str) -> None:
        #def init(self, message: str):
            #super().__init__(operation, message)
        setattr(cls,'operation',operation)

    def __str__(self) -> str:
        cls = self.__class__.__name__
        op = self.operation
        msg = self.message
        return f'{cls}: [{op}]: {msg}'

    def __repr__(self) -> str:
        return f'<{str(self)}>'

class DatabaseCreateError(DatabaseError, operation='Create'): ...
class DatabaseAlreadyExistsError(DatabaseCreateError, operation='Create'): ...
class DatabaseReadError(DatabaseError, operation='Read'): ...
class DatabaseReadNotFoundError(DatabaseReadError, operation='Update'): ...
class DatabaseUpdateError(DatabaseError, operation='Update'): ...
class DatabaseUpdateNotFoundError(DatabaseUpdateError, operation='Update'): ...
class DatabaseDeleteError(DatabaseError, operation='Delete'): ...
class DatabaseQueryError(DatabaseError, operation='Query'): ...
class DatabaseDumpError(DatabaseError, operation='Dump'): ...
