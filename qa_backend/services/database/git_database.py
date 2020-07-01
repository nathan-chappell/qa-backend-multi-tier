"""
CRUD frontend to git repository
"""
import asyncio
from asyncio import Lock, StreamReader
from asyncio.subprocess import PIPE
from typing import Optional, Tuple, Iterable, List, MutableMapping
from pathlib import Path
import logging
import subprocess

from qa_backend import check_config_keys, ConfigurationError
from .abstract_database import DocId, Paragraph, Database, acquire_lock
from .database_error import DatabaseError
from .database_error import DatabaseCreateError, DatabaseUpdateError
from .database_error import DatabaseDeleteError, DatabaseReadError

log = logging.getLogger('database')

class GitError(RuntimeError):
    cmd_args: Iterable[str]
    message: str

    def __init__(self, cmd_args: Tuple, message: str = ''):
        super().__init__()
        self.cmd_args = cmd_args
        self.message = message
        log.error(str(self))

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        cmd = self.cmd_args
        msg = self.message
        return f'<{cls}:(cmd_args={cmd},message={msg})>'

class GitAddError(GitError): pass
class GitResetError(GitError): pass
class GitRmError(GitError): pass
class GitCommitError(GitError): pass

### HERE

async def _get_output(reader: Optional[StreamReader]) -> str:
    if isinstance(reader, StreamReader):
        output = await reader.read()
        return output.decode('utf-8')
    return ''
 
async def _git_dispatch(git_dir: str, args, GitErrorClass, *, log_error=True, reset=False):
    git = await asyncio.create_subprocess_exec(
            'git','-C',git_dir, *args,
            stdin=PIPE, stdout=PIPE, stderr=PIPE
        )
    log.debug(f'Git Dispatch: {args}')
    await git.wait()
    if git.returncode != 0:
        err_str = await _get_output(git.stderr)
        log.error(f'git error: {args}, {git.returncode}, code {err_str}')
        if reset:
            await git_reset(git_dir)
        args = (err_str,log_error)
        raise GitErrorClass(args)
    else:
        out_str = await _get_output(git.stdout)
        log.info(out_str)

async def git_add(git_dir: str, docId: DocId):
    await _git_dispatch(git_dir, ('add',docId), GitAddError, reset=True)
    log.info(f'git SUCCESS: [add] {docId}')

async def git_rm(git_dir: str, docId: DocId):
    await _git_dispatch(git_dir, ('rm',docId), GitRmError, reset=True)
    log.info(f'git SUCCESS: [rm] {docId}')

async def git_reset(git_dir: str, commit: str = ''):
    args: tuple = ('reset','--hard')
    if commit != '':
        args = args + (commit,)
    await _git_dispatch(git_dir, args, GitResetError, reset=False)
    log.info(f'git SUCCESS: [reset]')

async def git_commit(git_dir: str, message: str, reset=True):
    await _git_dispatch(git_dir, ('commit','-m',message), GitCommitError, reset=reset)
    log.info(f'git SUCCESS: [commit] {message}')

async def git_init(git_dir: str):
    await _git_dispatch(git_dir, ('init',), GitError)
    log.info(f'git SUCCESS: [init]')

# TODO if it proves necessary,
# make this better (configure remote/ branch...)
async def git_pull(git_dir: str):
    await _git_dispatch(git_dir, ('pull','origin','master'), GitError)
    log.info(f'git SUCCESS: [init]')

class GitDatabase(Database):
    git_dir: str
    lock: Lock

    def __init__(self, git_dir: str, lock: Optional[Lock] = None):
        self.git_dir = git_dir
        if isinstance(lock,Lock):
            self.lock = lock
        else:
            self.lock = Lock()
        #loop = asyncio.get_event_loop()
        #asyncio.ensure_future(self.initialize())
        self.initialize()

    @staticmethod
    def from_config(
            config: MutableMapping[str,str]
        ) -> 'GitDatabase':
        check_config_keys(config, ['git dir'])
        try:
            git_dir = config['init file']
            return GitDatabase(git_dir)
        except ValueError as e:
            raise ConfigurationError(str(e))

    # this needs to be done synchronously, so we do it "by hand"
    def initialize(self, *args):
        path = Path(self.git_dir)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                log.error(f'error creating directory {self.git_dir}: {e}')
                raise
        args = ('git','-C',str(path),'init')
        proc = subprocess.run(args,stderr=subprocess.PIPE)
        if proc.returncode != 0:
            err = proc.stderr.read()
            raise GitError(args,err)

    @acquire_lock
    async def create(
            self, 
            paragraph: Paragraph
        ) -> None:
        """Add paragraph to git_dir, and reindex"""
        # check for existing document
        log.debug(f'GitDB: Creating {paragraph}')
        path = Path(self.git_dir) / paragraph.doc_id
        if path.exists():
            msg = f'doc_id: {paragraph.doc_id} already exists'
            raise DatabaseCreateError(msg) # type: ignore
        # write file
        with open(path,'w') as file:
            print(paragraph.text, file=file)
        # commit to git
        try:
            await git_add(self.git_dir, path.name)
            await git_commit(self.git_dir, f'created: {path.name}')
        except GitError as e:
            # if add fails, the file gets removed
            # if commit fails, the repo gets reset
            path.unlink()
            raise DatabaseCreateError(str(e)) # type: ignore

    @acquire_lock
    async def read(
            self,
            doc_id: DocId
        ) -> Iterable[Paragraph]:
        """Retrieve doc_ids (including wildcards)"""
        paths = list(Path(self.git_dir).glob(doc_id))
        # only return .txt files
        paths = list(filter(lambda p: p.name.endswith('.txt'), paths))
        paths = list(filter(Path.is_file, paths))
        paragraphs: List[Paragraph] = []
        for path in paths:
            with open(path) as file:
                paragraphs.append(Paragraph(path.name, file.read()))
        return paragraphs

    @acquire_lock
    async def update(
            self,
            paragraph: Paragraph
        ) -> None:
        """Update paragraph in git_dir"""
        path = Path(self.git_dir) / paragraph.doc_id
        if not path.exists():
            msg = f"doc_id: {paragraph.doc_id} doesn't exist"
            raise DatabaseUpdateError(msg) # type: ignore
        with open(path, 'w') as file:
            file.write(paragraph.text)
        try:
            await git_add(self.git_dir, paragraph.doc_id)
            await git_commit(self.git_dir, f'update: {paragraph.doc_id}')
        except GitError as e:
            raise DatabaseUpdateError(str(e)) # type: ignore

    @acquire_lock
    async def delete(
            self,
            doc_id: DocId
        ) -> None:
        """Delete paragraph from git_dir"""
        path = Path(self.git_dir) / doc_id
        if not path.exists():
            msg = f"doc_id: {doc_id} doesn't exist"
            raise DatabaseDeleteError(msg) # type: ignore
        try:
            await git_rm(self.git_dir, doc_id)
            await git_commit(self.git_dir, f'removed: {doc_id}')
        except Exception as e:
            msg = f'delete: error removing {doc_id}'
            raise DatabaseDeleteError(str(e)) # type: ignore

    @acquire_lock
    async def pull(self, *args) -> None:
        await git_pull(self.git_dir, *args)

    @acquire_lock
    async def reset(self, commit: str = '') -> None:
        await git_reset(self.git_dir, commit)
