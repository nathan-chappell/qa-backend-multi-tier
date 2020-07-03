# util/serialization.py
"""
Utilities for generic serialization.
"""

from typing import Any
from typing import Dict
from typing import Optional
import json
import re

#
# metaclass for objects to be "automatically serialized"
#
class JsonRepresentation:
    """Use json.dumps to __repr__ annotated variables."""
    def to_dict(self) -> Dict[str,Any]:
        return {k: getattr(self,k) for k in self.__slots__}

    def __repr__(self) -> str:
        return json.dumps(self.to_dict())

class QAAnswer(JsonRepresentation):
    __slots__ = ['score','question','answer','docId']
    question: str
    answer: str
    score: float
    docId: Optional[str]

    def __init__(self, question: str, answer: str, score: float, docId: Optional[str] = None):
        self.question = question
        self.answer = answer
        self.score = score
        self.docId = docId

class Paragraph(JsonRepresentation):
    __slots__ = ['docId','text']
    docId: str
    text: str

    def __init__(self, docId: str, text: str):
        if not docId.endswith('.txt'):
            raise ValueError("Paragraph.docId must have .txt as suffix")
        self.docId = docId
        self.text = text


