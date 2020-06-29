# test_git_es_db.py

import asyncio
import subprocess
from pathlib import Path
from uuid import uuid4
from typing import List

from elasticsearch import Elasticsearch

import fix_path
from services import Paragraph
from services.database import ElasticsearchDatabase
from services.database import GitDatabase
from services.database import GitEsDatabase

es = Elasticsearch()

def get_paragraphs() -> List[Paragraph]:
    paths = Path('es_test_data').glob('*.txt')
    paragraphs: List[Paragraph] = []
    for path in paths:
        with open(path) as file:
            paragraphs.append(Paragraph(path.name, file.read()))
    return paragraphs

def dump_dir(directory):
    print(f'Dumping: {directory}')
    subprocess.run(f'cat {directory}/*',shell=True,check=True)
    print('Dumping git log')
    subprocess.run(f'git -C {directory} log --oneline',shell=True,check=True)
    print('done')

async def test():
    esdb = ElasticsearchDatabase('./es_test_data/config.yml',erase_if_exists=True)
    git_dir = str(uuid4())
    if Path(git_dir).exists():
        raise RuntimeError(f'about to step on {git_dir}')
    git_database = GitDatabase(git_dir)
    print(es.cat.indices())
    git_es_db = GitEsDatabase(git_database, esdb)
    test_data_path = Path('es_test_data')
    try:
        paragraphs = get_paragraphs()
        await git_es_db.create(paragraphs[0])
        await git_es_db.create(paragraphs[1])
        dump_dir(git_dir)
        print(await git_es_db.read(paragraphs[0].doc_id))
        await git_es_db.update(Paragraph(paragraphs[0].doc_id,'update test'))
        print(await git_es_db.read(paragraphs[0].doc_id))
        await git_es_db.delete(paragraphs[0].doc_id)
        print(await git_es_db.read(paragraphs[0].doc_id))
    finally:
        es.indices.delete(git_es_db.es_database.index)
        subprocess.run(['rm','-rf',git_dir],check=True)
        print(es.cat.indices())

loop = asyncio.get_event_loop()
loop.run_until_complete(test())
