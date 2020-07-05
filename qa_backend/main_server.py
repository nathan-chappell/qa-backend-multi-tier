# main.py
"""
The actual server to run.
"""

from configparser import ConfigParser
from configparser import ExtendedInterpolation
from multiprocessing import Process
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import MutableMapping
from typing import Optional
from typing import Union
import asyncio
import logging
import multiprocessing
import os
import signal

import aiohttp.web as web

from qa_backend.server import QAServer
from qa_backend.server import QAServerConfig
from qa_backend.server import TransformersMicro
from qa_backend.services.database import ElasticsearchDatabase
from qa_backend.services.database import QueryDatabase
from qa_backend.services.qa import MicroAdapterQA
from qa_backend.services.qa import QA
from qa_backend.services.qa import RegexQA
from qa_backend.util import Configurable
from qa_backend.util import set_all_loglevels

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
            qas.append(MicroAdapterQA.from_config(qa_cfg))
            log.info('<MICRO ADAPTER>')
        else:
            raise ValueError(f'unknown QA type: {type_}')
    return qas

#   QAServer
#
#       ElasticsearchDatabase       |
#                                   |
#       QAs:                        |
#           - RegexQA               |
#           - [Other QA services]   |
#           - MicroAdapterQA -*       |
#                           |       |
#   TransformersMicro ------*       |
#

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
        es_config = config['es database']
        es_database = ElasticsearchDatabase.from_config(es_config)
        self.database = es_database
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
        qa_server_config = QAServerConfig(**config['qa server'])
        self.qa_server = QAServer(self.database, self.qas, qa_server_config)
        self.qa_server.app.on_shutdown.append(self.shutdown)
        # miscellaneous
        if 'PRINT_TB' in config['miscellaneous']:
            log.info(f'PRINT_TB is ON')
            os.environ['PRINT_TB'] = 'True'
        set_all_loglevels(config['miscellaneous'].get('log levels','info'))
        log.info(f'Initialization complete.')

    async def shutdown(self, app: web.Application):
        log.info('<main server> shutting down')
        await asyncio.tasks.gather(*[qa.shutdown() for qa in self.qas])
        await self.database.shutdown()
        if isinstance(self.transformers_micro_process, Process):
            log.info(f'shutting down transformers_micro_process')
            p = self.transformers_micro_process
            if p.is_alive() and isinstance(p.pid, int):
                log.info(f'INT/join process: {p.pid} from {os.getpid()}')
                os.kill(p.pid, signal.SIGINT)
                os.kill(p.pid, signal.SIGTERM)
                p.join()
            else:
                log.warn(f'{p.pid} is not alive!')

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
