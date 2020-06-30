# main.py
"""
The actual server to run.
"""

from qa_backend.server import QAServer
from qa_backend.server import TransformersMicro

from qa_backend.services.database import GitWebhookDatabase
from qa_backend.services.database import GitWebhookEsDatabase
from qa_backend.services.database import ElasticsearchDatabase

from qa_backend.services.qa import QAAnswer
from qa_backend.services.qa import QA
from qa_backend.services.qa import RegexQA
from qa_backend.services.qa import MicroAdapter

# TODO
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
