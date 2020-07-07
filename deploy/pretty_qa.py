# pretty_qa.py

from pprint import pprint
import json

def print_qa(qa):
    pprint(qa)

while True:
    qa = input()
    print_qa(qa)
    print('_'*80)
