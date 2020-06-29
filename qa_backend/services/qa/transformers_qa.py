# transformers_qa.py

from typing import List, Optional, cast

from transformers import AutoModelForQuestionAnswering, AutoTokenizer # type: ignore
from transformers import QuestionAnsweringPipeline # type: ignore

from .abstract_qa import QA, QAAnswer, QAQueryError
from . import complete_sentence

def create_default_pipeline() -> QuestionAnsweringPipeline:
    model_name = 'twmkn9/distilbert-base-uncased-squad2'
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    gpu_model = AutoModelForQuestionAnswering.from_pretrained(model_name)
    #gpu_model.cuda()
    gpu_model.eval()
    return QuestionAnsweringPipeline(
                model=gpu_model, 
                tokenizer=tokenizer,
                #device=0
                device=-1
            )

class TransformersQA(QA):
    pipeline: QuestionAnsweringPipeline
    #default_pipeline: QuestionAnsweringPipeline = create_default_pipeline()

    def __init__(self, pipeline: Optional[QuestionAnsweringPipeline] = None):
        self._requires_context = True
        if isinstance(pipeline, QuestionAnsweringPipeline):
            self.pipeline = pipeline
        else:
            self.pipeline = create_default_pipeline()
        
    async def query(self, question: str, **kwargs) -> List[QAAnswer]:
        context: str = kwargs.get('context','')
        if context == '':
            raise QAQueryError("context required")
        question_ = {'question': question, 'context': context}
        question_args = {'handle_impossible_answer':True, 'topk':1}
        answer = self.pipeline(**question_, **question_args)
        # check for "no answer"
        if answer['start'] == answer['end']:
            answer_ = ''
        else:
            start,end = answer['start'], answer['end']
            answer_ = complete_sentence(cast(str,context),start, end)
        return [QAAnswer(question, answer_, answer['score'])]
