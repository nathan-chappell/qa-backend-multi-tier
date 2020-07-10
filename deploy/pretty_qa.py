# pretty_qa.py

from pprint import pprint, pformat
import json

from ansimarkup import ansiprint

def highlight(highlight_this,in_this):
    highlighter = f'<bg white><red>{highlight_this}</red></bg white>'
    split_ = in_this.split(highlight_this)
    print(f'[NUMBER OF SPLITS] {len(split_)}')
    return highlighter.join(split_)

def print_qa(qa):
    qa_body = json.loads(qa)
    qa_str = pformat(qa_body, indent=2)
    try:
        for answer in qa_body['answers']:
            original_span = answer['original_span']
            if original_span != '':
                qa_str = highlight(original_span, qa_str)
    except KeyError as e:
        print(f'[ERROR]: {e}')
    ansiprint(qa_str)

while True:
    qa = input()
    print_qa(qa)
    print('_'*80)
