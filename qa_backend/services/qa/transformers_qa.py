# transformers_qa.py

from typing import List, Optional, cast

from transformers import AutoModelForQuestionAnswering, AutoTokenizer # type: ignore
from transformers import QuestionAnsweringPipeline # type: ignore

from .abstract_qa import QA, QAAnswer, QAQueryError
from . import complete_sentence

def create_pipeline(
        model_name: str,
        use_gpu: bool = False,
        device: Optional[int] = None,
    ) -> QuestionAnsweringPipeline:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForQuestionAnswering.from_pretrained(model_name)
    _device = -1
    if use_gpu:
        model.cuda()
        if device is None:
            _device = 0
    model.eval()
    return QuestionAnsweringPipeline(
                model=model, 
                tokenizer=tokenizer,
                device=_device,
            )

class TransformersQA(QA):
    model_name: str = 'twmkn9/distilbert-base-uncased-squad2'
    pipeline: QuestionAnsweringPipeline

    def __init__(
            self,
            pipeline: Optional[QuestionAnsweringPipeline] = None,
            model_name: Optional[str] = None,
            use_gpu = False,
            device = -1,
        ):
        self._requires_context = True
        if pipeline is not None and model_name is not None:
            msg = 'Only one of pipeline and model_name should be specified'
            raise ValueError(msg)
        if isinstance(pipeline, QuestionAnsweringPipeline):
            self.pipeline = pipeline
            return
        elif isinstance(model_name, str):
            self.model_name = model_name
        else:
            msg = 'either model_name must be a str, '
            msg += 'or pipeline must be a QuestionAnsweringPipeline'
            raise ValueError(msg)
        self.pipeline = create_pipeline(
                            self.model_name,
                            use_gpu,
                            device
                        )
        
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
