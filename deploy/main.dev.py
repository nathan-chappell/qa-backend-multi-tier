# main.py

import sys

sys.path.append('..')

from qa_backend import MainServer

main_server = MainServer('main_server.dev.cfg')

print('about to run the main server')

main_server.run()
