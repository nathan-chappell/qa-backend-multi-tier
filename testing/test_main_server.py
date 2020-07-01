# test_main_server.py

import sys
sys.path.append('..')

from qa_backend.server.main_server import MainServer

main_server = MainServer('main_server.cfg')

main_server.run()
