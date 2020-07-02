# __init__.py
"""
unittests for the qa-backend
"""

import unittest
import sys
from uuid import uuid4
from pathlib import Path
import subprocess
import yaml

sys.path.append('..')

from elasticsearch import Elasticsearch # type: ignore
from qa_backend.services.database import ElasticsearchDatabase

es = Elasticsearch()

def get_es_init_file() -> str:
    return './es_test_data/config.yml'

def set_up_es_db(test_case):
    test_case.init_file = get_es_init_file()
    with open(test_case.init_file) as file:
        test_case.init_data = yaml.full_load(file)
    test_case.index = test_case.init_data['index']

def tear_down_es_db(test_case):
    es.indices.delete(test_case.index)
