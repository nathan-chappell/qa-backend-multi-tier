# test_transformers_qa.py

from pathlib import Path

import fix_path
from services import QAAnswer
from services.qa import TransformersQA, QAQueryError

context = """
Each Hypertext Transfer Protocol (HTTP) message is either a request or a
response. A server listens on a connection for a request, parses each message
received, interprets the message semantics in relation to the identified
request target, and responds to that request with one or more response
messages. A client constructs request messages to communicate specific
intentions, examines received responses to see if the intentions were carried
out, and determines how to interpret the results. This document defines
HTTP/1.1 request and response semantics in terms of the architecture defined
in [RFC7230]. HTTP provides a uniform interface for interacting with a
resource (Section 2), regardless of its type, nature , or implementation, via
the manipulation and transfer of representations ( Section 3).
"""

questions = [
    'what is http?',
    'what does a server do?',
    'what is the purpose of this document?',
    'what is a hot dog?',
]

def test():
    trasformers_qa = TransformersQA()
    for question in questions:
        print(trasformers_qa.query(question, context))
    try:
        trasformers_qa.query('this is an error test')
    except QAQueryError as e:
        pass

test()
print('done')
