"""
GIT and ES crud frontends
"""

from .abstract_database import Database
from .abstract_database import QueryDatabase

from .git_database import GitDatabase

from .git_database import GitError
from .git_database import GitAddError
from .git_database import GitResetError
from .git_database import GitRmError
from .git_database import GitCommitError

from .es_database import ElasticsearchDatabase
from .es_database import ElasticsearchDatabaseError

from .git_es_database import GitEsDatabase

