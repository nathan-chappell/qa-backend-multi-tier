"""
CRUD frontend to git repository
"""
from asyncio import Lock, StreamReader
from asyncio.subprocess import PIPE
import re
from typing import Optional, Coroutine, DefaultDict, Dict, Callable
from typing import cast, Tuple, Iterable, Union, List, Any
from pathlib import Path
from collections import defaultdict
import logging
from uuid import uuid4
import functools

from . import Paragraph, Database, DatabaseError

log = logging.getLogger('database')

class GitError(DatabaseError):
    cmd_args: Iterable[str]
    message: str

    def __init__(
            self, cmd_args: Tuple, message: str = '', *, log_error=True
        ):
        super().__init__()
        self.cmd_args = cmd_args
        self.message = message
        if log_error:
            log.error(str(self))

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        cmd = self.cmd_args
        msg = self.message
        return f'<{cls}:(cmd_args={cmd},message={msg})>'

    @property
    def response(self) -> Response:
        return Response(status=500, reason=repr(self))

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

async def git_reset(git_dir: str):
    await _git_dispatch(git_dir, ('reset','--hard'), GitResetError, reset=False)
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


AsyncMethod = Callable[..., Coroutine[Any,Any,Response]]

def check_initialized(f: AsyncMethod) -> AsyncMethod:
    @functools.wraps(f)
    async def wrapped(self, *args, **kwargs):
        await self.initialize()
        return await f(self, *args, **kwargs)
    return wrapped

def acquire_lock(f: AsyncMethod) -> AsyncMethod:
    @functools.wraps(f)
    async def wrapped(self, *args, **kwargs):
        lock = self.lock
        if lock is not None:
            await lock.acquire()
        result = await f(self, *args, **kwargs)
        if lock is not None:
            lock.release()
        return result
    return wrapped

class GitDb(Database):
    source_dir: str
    lock: Optional[Lock] = None
    initialized: bool

    def __init__(self, source_dir: str, lock: Optional[Lock] = None):
        self.source_dir = source_dir
        self.lock = lock
        self.initialized = False

    @acquire_lock
    async def initialize(self, *args):
        if self.initialized: return
        path = Path(self.source_dir)
        if not path.exists():
            try:
                path.mkdir()
            except Exception as e:
                log.error(f'error creating directory {self.source_dir}: {e}')
                raise
        async with named_locks[self.source_dir]:
            await git_init(self.source_dir, *args)
        self.initialized = True

    @check_initialized
    async def create(
            self, 
            paragraphs: Paragraph
        ) -> None:
        """Add paragraph to git_dir, and reindex"""
        async with self.lock:
            # check for existing document
            path = Path(self.git_dir) / paragraph.doc_id
            if path.exists():
                msg = f'doc_id: {paragraph.doc_id} already exists'
                raise DatabaseCreateError(msg)
            # write file
            with open(path,'w') as file:
                print(doc, file=file)
            # commit to git
            try:
                await git_add(git_dir, path.name)
                await git_commit(git_dir, f'created: {path.name}')
            except Exception as e:
                raise DatabaseCreateError(str(e))
                path.unlink()

    @check_initialized
    async def read(
            self,
            doc_id: DocId
        ) -> Iterable[Paragraph]:
        """Retrieve doc_ids (including wildcards)"""
        paths = list(Path(self.git_dir).glob(doc_id))
        paragraphs: List[Paragraph] = []
        for path in paths:
            with open(path) as file:
                paragraphs.append(Paragraph(path.name,file.read()))
        return paragraphs

    @check_initialized
    async def update(
            self,
            paragraph: Paragraph
        ) -> None:
        """Update paragraph in git_dir"""
        path = Path(self.git_dir) / paragraph.doc_id
        if not path.exists():
            msg = f"doc_id: {paragraph.doc_id} doesn't exist"
            raise DatabaseUpdateError(msg)
        with open(path) as file:
            file.write(paragraph.text)
        try:
            await git_add(self.git_dir, paragraph.doc_id)
            await git_commit(self.git_dir)
        except Exception as e:
            raise DatabaseCreateError(str(e))

    @check_initialized
    async def delete(
            self,
            doc_id: DocId
        ) -> None:
        """Delete paragraph from git_dir"""
        path = Path(self.git_dir) / paragraph.doc_id
        if not path.exists():
            msg = f"doc_id: {paragraph.doc_id} doesn't exist"
            raise DatabaseDeleteError(msg)
        if isinstance(path, Response):
            return path
        try:
            await git_rm(git_dir, docId)
            await git_commit(git_dir, f'removed: {docId}')
        except Exception as e:
            msg = f'delete: error removing {docId}'
            raise DatabaseDeleteError(str(e))

    @check_initialized
    async def pull(self, *args) -> Response:
        return await git_pull(self.source_dir, *args)
