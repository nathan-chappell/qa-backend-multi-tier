"""
GIT and ES crud frontends
"""

from .abstract_database import Database
from .abstract_database import DocId
from .abstract_database import QueryDatabase

from .database_error import *

from .es_database import ElasticsearchDatabase
from .es_database import ElasticsearchDatabaseConfig
from .es_database import ElasticsearchDatabaseError
