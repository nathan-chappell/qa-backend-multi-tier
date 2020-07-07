# main.py

import sys
sys.path.append('..')
import logging

from qa_backend import MainServer

main_server = MainServer('main_server.dev.cfg')

print('about to run the main server')
logging.getLogger().setLevel(logging.DEBUG)

main_server.run()