# testing/test_git_db.py

import asyncio
import subprocess
from pathlib import Path
from uuid import uuid4

import fix_path
from services import Paragraph
from services.database import GitDatabase
from services.database import GitDatabase

def dump_dir(directory):
    print(f'Dumping: {directory}')
    subprocess.run(f'cat {directory}/*',shell=True,check=True)
    print('Dumping git log')
    subprocess.run(f'git -C {directory} log --oneline',shell=True,check=True)
    print('done')

async def test():
    git_dir = str(uuid4())
    if Path(git_dir).exists():
        raise RuntimeError(f'about to step on {git_dir}')
    git_database = GitDatabase(git_dir)
    try:
        doc_id = 'test.txt'
        paragraph = Paragraph(doc_id,"this is a test")
        await git_database.create(paragraph)
        paragraph.text = "this is not a test"
        await git_database.update(paragraph)
        await git_database.create(Paragraph(
            'foo.txt',
            'foo bar basdf'
        ))
        paragraphs = await git_database.read('*')
        for paragraph_ in paragraphs:
            print(paragraph_)
        await git_database.delete(doc_id)
        dump_dir(git_dir)
    finally:
        subprocess.run(['rm','-rf',git_dir],check=True)

loop = asyncio.get_event_loop()
loop.run_until_complete(test())
