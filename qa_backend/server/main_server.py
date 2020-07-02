# main.py
"""
The actual server to run.
"""

import multiprocessing
import logging
import os
import signal
import atexit
from pathlib import Path
from typing import Union, Optional, Dict, Any, List, MutableMapping
from configparser import ConfigParser, ExtendedInterpolation
import asyncio

import aiohttp.web as web
from aiohttp.web import Request, Response

from qa_backend import check_config_keys


from qa_backend.server import QAServer
from qa_backend.server import TransformersMicro

from qa_backend.services import set_all_loglevels

from qa_backend.services.database import QueryDatabase
from qa_backend.services.database import GitWebhookDatabase
from qa_backend.services.database import GitWebhookEsDatabase
from qa_backend.services.database import ElasticsearchDatabase

from qa_backend.services.qa import QAAnswer
from qa_backend.services.qa import QA
from qa_backend.services.qa import RegexQA
from qa_backend.services.qa import MicroAdapter

log = logging.getLogger('main')

def load_qas_from_config(config: ConfigParser) -> List[QA]:
    qas : List[QA] = []    
    for qa_name in config['question answer services']:
        qa_cfg = dict(config[qa_name])
        type_ = qa_cfg.pop('type')
        if type_ == 'regex_qa':
            qas.extend(RegexQA.from_config(qa_cfg))
            log.info('<REGEX QA>')
        elif type_ == 'micro_adapter':
            qas.append(MicroAdapter.from_config(qa_cfg))
            log.info('<MICRO ADAPTER>')
        else:
            raise ValueError(f'unknown QA type: {type_}')
    return qas

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
    database: QueryDatabase
    transformers_micro: Optional[TransformersMicro] = None
    transformers_micro_process: Optional[multiprocessing.Process] = None
    config_path: Path = Path(__file__).with_name('main_server.cfg')

    def __init__(self, config_path: Optional[Union[str,Path]] = None):
        log.info(f'Initializing main server from: {config_path}')
        if config_path is None:
            pass
        elif isinstance(config_path, Path):
            self.config_path = config_path
        elif isinstance(config_path, str):
            self.config_path = Path(config_path)
        else:
            msg = 'config_path must be a str or Path or None'
            raise ValueError(msg)
        config = ConfigParser(interpolation=ExtendedInterpolation())
        config.read(self.config_path)
        # database
        log.info(f'Initializing database services')
        #
        # this git-webhook stuff was all a big dumb idea.
        #
        #gw_cfg = config['git webhook database']
        #git_webhook_db = GitWebhookDatabase.from_config(gw_cfg)
        es_cfg = config['es database']
        es_db = ElasticsearchDatabase.from_config(es_cfg)
        self.database = es_db
        # micro
        if 'enabled' in config['transformers micro service']:
            log.info(f'Initializing transformers micro service')
            tm_cfg = dict(config['transformers micro service'])
            tm_cfg.pop('enabled')
            self.transformers_micro = TransformersMicro.from_config(tm_cfg)
        else:
            log.info(f'Running without transformers micro service')
        # qa
        log.info(f'Loading QA Services')
        self.qas = load_qas_from_config(config)
        # qa_server
        qa_kwargs = self.get_qa_config(config['qa server'])
        self.qa_server = QAServer(self.database, self.qas, **qa_kwargs)
        self.qa_server.app.on_shutdown.append(self.shutdown)
        # miscellaneous
        if 'PRINT_TB' in config['miscellaneous']:
            log.info(f'PRINT_TB is ON')
            os.environ['PRINT_TB'] = 'True'
        set_all_loglevels(config['miscellaneous'].get('log levels','info'))
        log.info(f'Initialization complete.')

    def get_qa_config(self, config: MutableMapping[str,str]) -> Dict[str,Any]:
        check_config_keys(config, ['host', 'port', 'qa log file'])
        result: Dict[str,Any] = {}
        result['host'] = config.get('host','localhost')
        result['port'] = int(config.get('port',8080))
        result['qa_log_file'] = config.get('qa log file','qa_log.jsonl')
        return result

    async def shutdown(self, app: web.Application):
        log.info('<main server> shutting down')
        await asyncio.tasks.gather(*[qa.shutdown() for qa in self.qas])
        p = self.transformers_micro_process
        if p.is_alive():
            log.info(f'INT/join process: {p.pid} from {os.getpid()}')
            os.kill(p.pid, signal.SIGINT)
            os.kill(p.pid, signal.SIGTERM)
            p.join()

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
        log.info(f'running qa_server')
        self.run_micro()
        self.qa_server.run()

