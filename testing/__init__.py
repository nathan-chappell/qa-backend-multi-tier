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
from qa_backend.services.database import GitDatabase, ElasticsearchDatabase

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

def get_git_dir():
    git_dir = str(uuid4())
    if Path(git_dir).exists():
        raise RuntimeError(f'about to step on {git_dir}')
    return git_dir

def remove_dir(name: str):
    subprocess.run(['rm', '-rf', name])

def set_up_git_db(test_case):
    test_case.git_dir = get_git_dir()

def tear_down_git_db(test_case):
    remove_dir(test_case.git_dir)

def set_up_git_es_db(test_case):
    set_up_git_db(test_case)
    set_up_es_db(test_case)
    test_case.git_database = GitDatabase(test_case.git_dir)
    test_case.es_database = ElasticsearchDatabase(test_case.init_file)

def tear_down_git_es_db(test_case):
    es.indices.delete(test_case.index)
    remove_dir(test_case.git_dir)
