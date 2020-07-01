# main.py
"""
The actual server to run.
"""

import multiprocessing
import logging
import os
from pathlib import Path
from typing import Union, Optional, Dict, Any, List

import yaml
import aiohttp.web as web
from aiohttp.web import Request, Response

from qa_backend.server import QAServer
from qa_backend.server import TransformersMicro

from qa_backend.services.database import GitWebhookDatabase
from qa_backend.services.database import GitWebhookEsDatabase
from qa_backend.services.database import ElasticsearchDatabase

from qa_backend.services.qa import QAAnswer
from qa_backend.services.qa import QA
from qa_backend.services.qa import RegexQA
from qa_backend.services.qa import MicroAdapter

log = logging.getLogger('server')

def load_qas(args: List[Dict[str,Any]]) -> List[QA]:
    ...

def config_substitutions(config_data: Dict[str,Any]) -> Dict[str,Any]:
    """Replace {git_dir} with actual path to git dir"""
    git_dir = config_data['git_webhook_database']['git_dir']
    es_init = config_data['es_database']['init_file']
    config_data['es_database']['init_file'] = es_init.format(git_dir=

#   QAServer
#
#       GitWebhookEsDatabase
#           GitEsDatabase ----------*
#           ElasticsearchDatabase   |
#                                   |
#       QAs:                        |
#           - RegexQA               |
#           - MicroAdapter -*       |
#                           |       |
#   TransformersMicro ------*       |
#                                   |
#   WebhookListener ----------------*

class MainServer:
    qa_server: QAServer
    git_webhook_es_db: GitWebhookEsDatabase
    transformers_micro: Optional[TransformersMicro] = None
    transformers_micro_process: Optional[multiprocessing.Process] = None
    init_path: Path = Path(__file__).with_name('main_server.config.yml')
    init_data: Dict[str, Any] = {}

    def __init__(self, init_path: Union[str,Path]):
        log.info(f'Initializing main server from: {init_path}')
        if isinstance(init_path, Path):
            self.init_path = init_path
        elif isinstance(init_path, str):
            self.init_path = Path(init_path)
        else:
            msg = 'init_path must be a str or Path'
            raise ValueError(msg)
        with open(init_path) as file:
            self.init_data = init_data = yaml.full_load(file)
        log.info(f'Initializing database services')
        git_webhook_db = GitWebhookDatabase(
                                **init_data['git_webhook_database']
                                )
        es_db = ElasticsearchDatabase(
                                **init_data['es_database']
                                )
        self.git_webhook_es_db = GitWebhookEsDatabase(
                                git_webhook_db,
                                es_db
                                )
        if 'transformers_micro' in init_data.keys():
            log.info(f'Initializing transformers micro service')
            self.transformers_micro = TransformersMicro(
                                    **init_data['transformers_micro']
                                    )
        else:
            log.info(f'Running without transformers micro service')
        log.info(f'Loading QA Services')
        qa_conf = init_data.get('qas',[])
        if isinstance(qa_conf, list):
            qas = load_qas(init_data['qas'])
        else:
            name = self.init_path.name
            msg = f'[qas] must be an array (or missing) in: {name}'
            raise ValueError(msg)
        self.qa_server = QAServer(
                                self.git_webhook_es_db, qas,
                                **init_data['qa_server']
                                )
        if init_data['PRINT_TB']:
            log.info(f'PRINT_TB is ON')
            os.environ['PRINT_TB'] = 'True'
        log.info(f'Initialization complete.')

    # TODO: serve the readme maybe?
    # serve some sort of documentation?

    def run_micro(self):
        if self.transformers_micro is None:
            return
        log.info(f'Starting transformers micro service.')
        p = multiprocessing.Process(target=self.transformers_micro.run)
        self.transformers_micro_process = p
        p.start()
        log.info(f'Started on process: {p.pid}')

    def run(self, run_micro: bool = True):
        self.run_micro()
        self.qa_server.run()
