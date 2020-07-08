# interactive.py
#
# intended to be run in interactive mode: mostly does some convenience imports 

from pprint import pprint
import json
import re
import textwrap

from ansimarkup import ansiprint
from transformers import AutoModelForQuestionAnswering
from transformers import AutoTokenizer
from transformers import QuestionAnsweringPipeline
import elasticsearch
import requests

es = elasticsearch.Elasticsearch()
idx = 'deployment-dev-index'
ep = 'http://localhost:8280/question'
epqa = 'http://localhost:8281/question'

model_names = {
    'dbert-s2': 'twmkn9/distilbert-base-uncased-squad2',
    'sbert-s2': 'mrm8488/bert-small-finetuned-squadv2',
    'dbert-s1': 'distilbert-base-uncased-distilled-squad',
    '_bert-s2': 'twmkn9/bert-base-uncased-squad2',
}

models = {
    k: {'model':AutoModelForQuestionAnswering.from_pretrained(v),
        'tokenizer':AutoTokenizer.from_pretrained(v)}
    for k,v in model_names.items()
}
for k,m in models.items():
    m['model'].eval()

pipelines = {
    k: QuestionAnsweringPipeline(**v, device=-1)
    for k,v in models.items()
}

def h1(s):
    return f'<bg white><fg red>{s}</fg red></bg white>'

def h2(s):
    return f'<fg red>{s}</fg red>'

def h3(s):
    return f'<bg green><fg black>{s}</fg black></bg green>'

def query_all(question,context):
    r = 50
    ansiprint(h1('question:') + '  ' + h2(question))
    ansiprint(h1('context:'))
    ctx_ = textwrap.fill(context, 60)
    ctx_ = textwrap.indent(ctx_, ' -- ')
    #print(context)
    print(ctx_)
    for name,pipeline in pipelines.items():
        ansiprint(h3(name))
        answer = pipeline({'question':question, 'context':context},handle_impossible_answer=True)
        pprint(answer)
        b,e = answer['start'],answer['end']
        context_ = context[max(b-30,0):e+30]
        b_ = 30 - max(0,30-b)
        e_ = b_ + e-b
        t1,t2,t3 = context_[0:b_],context_[b_:e_],context_[e_:]
        ansiprint(t1 + h2(t2) + t3)

ctxs = []
size = 3
def get_ctx_by_query(question):
    global ctxs
    ctxs = []
    hits = es.search(index=idx, body={'query':{'match':{'text':question}},'size':size})['hits']['hits']
    for hit in hits:
        ctxs.append({'_id':hit['_id'], 'text':hit['_source']['text']})

ectd_ctx = es.search(index=idx,body={'query':{'match':{'text':'ectd'}}})['hits']['hits'][0]['_source']['text']

query_all('what is mono ectd office?', ectd_ctx)

