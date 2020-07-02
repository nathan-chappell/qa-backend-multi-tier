"""
GIT and ES crud frontends
"""

from .abstract_database import Database
from .abstract_database import QueryDatabase

from .database_error import DatabaseError
from .database_error import DatabaseCreateError
from .database_error import DatabaseReadError
from .database_error import DatabaseUpdateError
from .database_error import DatabaseDeleteError
from .database_error import DatabaseQueryError

from .es_database import ElasticsearchDatabase
from .es_database import ElasticsearchDatabaseError
