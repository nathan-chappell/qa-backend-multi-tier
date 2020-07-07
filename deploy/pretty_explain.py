# pretty_jsonl.py

from pprint import pprint
import json

cur_qid = None

def print_explain(explain):
    #scores = []
    #q = explain['body']['match']['text']
    print('')
    docId = explain['docId']
    total = explain['total_score']
    print(f'{total:6.3f} {docId}')
    scores = explain['scores']
    scores = sorted(scores, key = lambda tpl: tpl[1], reverse=True)
    for i, tpl in enumerate(scores):
        #scores.append(f'{tpl[0]:12} {tpl[1]:6.3f} {tpl[2]:2.0f}')
        print(' --- ' + f'{tpl[0]:12} {tpl[1]:6.3f} {tpl[2]:2.0f}', flush=True)
    #print(json.dumps(json.loads(q),indent=2),flush=True)
    #pprint(explain)

while True:
    q = input()
    explain = json.loads(q)
    qid = explain['qid']
    if cur_qid == None:
        cur_qid = qid
    if cur_qid != qid:
        print('_'*80)
        pprint(explain['body'])
        index = explain['index']
        qid = explain['qid']
        print(f'{qid} {index}')
        cur_qid = qid
    print_explain(explain)
