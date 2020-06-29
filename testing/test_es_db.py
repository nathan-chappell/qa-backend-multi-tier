# test_es_db.py

import asyncio
import subprocess
from pathlib import Path
from uuid import uuid4
from typing import List

from elasticsearch import Elasticsearch

import fix_path
from services import Paragraph
from services.database import ElasticsearchDatabase

es = Elasticsearch()

def get_paragraphs() -> List[Paragraph]:
    paths = Path('es_test_data').glob('*.txt')
    paragraphs: List[Paragraph] = []
    for path in paths:
        with open(path) as file:
            paragraphs.append(Paragraph(path.name, file.read()))
    return paragraphs

async def test():
    esdb = ElasticsearchDatabase('./es_test_data/config.yml',erase_if_exists=True)
    print(es.cat.indices())
    test_data_path = Path('es_test_data')
    try:
        paragraphs = get_paragraphs()
        await esdb.create(paragraphs[0])
        await esdb.create(paragraphs[1])
        print(await esdb.read(paragraphs[0].doc_id))
        await esdb.update(Paragraph(paragraphs[0].doc_id,'update test'))
        print(await esdb.read(paragraphs[0].doc_id))
        await esdb.delete(paragraphs[0].doc_id)
        print(await esdb.read(paragraphs[0].doc_id))
    finally:
        es.indices.delete(esdb.index)
        print(es.cat.indices())

loop = asyncio.get_event_loop()
loop.run_until_complete(test())
