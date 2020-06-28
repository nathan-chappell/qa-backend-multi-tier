"""
TODO: better docstr
Services:
* Database
    * git backend
    * QueryDatabas
        * es backend
* qa_service
    * transformers qa service
"""

DocId = str

#
# metaclass for objects to be "automatically serialized"
#
class JsonRepresentation:
    """Use json.dumps to __repr__ annotated variables."""
    def __new__(self, cls, bases, namespace) -> type:
        def json_repr(self) -> str:
            data = {
                k: getattr(self,k).__repr__()
                for k in namespace['__annotations__']
            }
            return json.dumps(data)
        if '__repr__' not in namespace:
            namespace['__repr__'] = json_repr
        return type(cls, bases, namespace)

class QaAnswer(metaclass=JsonRepresentation):
    __slots__ = ['score','answer']
    score: float
    answer: str

    def __init__(self, score: float, answer: str):
        self.score = score
        self.answer = answer

    def __repr__(self) -> str:
        return json.dumps({'score': {self.score:5.3f}, 'answer': self.answer})

class Paragraph(metaclass=JsonRepresentation):
    __slots__ = ['doc_id','text']
    doc_id: str
    text: str

    def __init__(self, doc_id: str, text: str):
        self.doc_id = doc_id
        self.text = text

