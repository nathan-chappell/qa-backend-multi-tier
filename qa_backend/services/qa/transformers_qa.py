# transformers_qa.py

from typing import List
from typing import MutableMapping
from typing import Optional
from typing import cast
import logging

from transformers import AutoModelForQuestionAnswering # type: ignore
from transformers import AutoTokenizer # type: ignore
from transformers import QuestionAnsweringPipeline # type: ignore

from .abstract_qa import QA
from .abstract_qa import QAQueryError
from qa_backend.util import ConfigurationError
from qa_backend.util import QAAnswer
from qa_backend.util import check_config_keys
from qa_backend.util import complete_sentence

log = logging.getLogger('qa')

def create_pipeline(
        model_name: str,
        use_gpu: bool = False,
        device: Optional[int] = None,
    ) -> QuestionAnsweringPipeline:
    msg = f'<model_name:{model_name}, use_gpu:{use_gpu}, device:{device}>'
    log.info(f'creating pipeline: {msg}')
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
            msg = f'pipline must be a QuestionAnsweringPipeline or model_name must be a str'
            raise ConfigurationError(msg)
        self.pipeline = create_pipeline(
                            self.model_name,
                            use_gpu,
                            device
                        )

    @staticmethod
    def from_config(config: MutableMapping[str,str]) -> 'TransformersQA':
        log.info('creating TransformersQA from config')
        log.debug('config: {config}')
        check_config_keys(config, ['model name','use gpu', 'device'])
        try:
            model_name = config.get('model name')
            use_gpu = config.get('use gpu', False)
            device = int(config.get('device','-1'))
            return TransformersQA(
                        model_name=model_name,
                        use_gpu=use_gpu,
                        device=device
                    )
        except ValueError as e:
            raise ConfigurationError(str(e))
    
    async def query(self, question: str, **kwargs) -> List[QAAnswer]:
        log.debug(f'[TransformersQA] question: {question}')
        context: str = kwargs.get('context','')
        if context == '':
            raise QAQueryError("context required")
        log.debug(f'context: {context}')
        question_ = {'question': question, 'context': context}
        question_args = {'handle_impossible_answer':True, 'topk':1}
        answer = self.pipeline(**question_, **question_args)
        log.debug(f'answer: {answer}')
        # check for "no answer"
        if answer['start'] == answer['end']:
            answer_ = ''
        else:
            start,end = answer['start'], answer['end']
            answer_ = complete_sentence(cast(str,context),start, end)
        log.debug(f'answer_: {answer_}')
        return [QAAnswer(question, answer_, answer['score'])]
