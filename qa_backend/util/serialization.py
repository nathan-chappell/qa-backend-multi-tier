# util/serialization.py
"""
Utilities for generic serialization.
"""

from typing import Any
from typing import Dict
from typing import Optional
import json
import re

from attr.validators import matches_re
import attr

#
# metaclass for objects to be "automatically serialized"
#
class JsonRepresentation:
    """Use json.dumps to __repr__ annotated variables."""
    def to_json(self) -> str:
        return json.dumps(attr.asdict(self))

@attr.s(auto_attribs=True, slots=True)
class Paragraph(JsonRepresentation):
    docId: str = attr.ib(validator=matches_re(r'[a-zA-Z_\-0-9]+.txt'))
    text: str

@attr.s(auto_attribs=True, slots=True)
class QAAnswer(JsonRepresentation):
    question: str
    answer: str
    score: float
    docId: str = ''
    paragraph: Optional[Paragraph] = None
    original_span: Optional[str] = ''
