# transformers_qa.py

from typing import List
from typing import MutableMapping
from typing import Optional
from typing import Union
from typing import cast
import logging

from attr.validators import instance_of
from transformers import AutoModelForQuestionAnswering # type: ignore
from transformers import AutoTokenizer # type: ignore
from transformers import QuestionAnsweringPipeline # type: ignore
import attr

from .abstract_qa import QA
from .abstract_qa import QAQueryError
from qa_backend.util import ConfigurationError
from qa_backend.util import QAAnswer
from qa_backend.util import complete_sentence
from qa_backend.util import convert_bool

log = logging.getLogger('qa')

@attr.s(kw_only=True)
class TransformersQAConfig:
    model_name: str = attr.ib(default='twmkn9/distilbert-base-uncased-squad2',
                              validator=instance_of(str))
    device: int = attr.ib(default=0, converter=int)
    use_gpu: bool = attr.ib(default=True, converter=convert_bool)

def create_pipeline(config: TransformersQAConfig) -> QuestionAnsweringPipeline:
    log.info(f'creating pipeline: {config}')
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    model = AutoModelForQuestionAnswering.from_pretrained(config.model_name)
    if config.use_gpu:
        model.cuda()
    model.eval()
    return QuestionAnsweringPipeline(
                model=model, 
                tokenizer=tokenizer,
                device=config.device,
            )

class LazyPipeline:
    """Doesn't create pipeline until called"""
    _pipeline: Optional[QuestionAnsweringPipeline] = None
    config: TransformersQAConfig

    def __init__(self, config: TransformersQAConfig):
        self.config = config

    def __call__(self, *args, **kwargs):
        if self._pipeline is None:
            self._pipeline = create_pipeline(self.config)
        return self._pipeline(*args, **kwargs)

class TransformersQA(QA):
    pipeline: Union[QuestionAnsweringPipeline, LazyPipeline]
    config: Optional[TransformersQAConfig] = None
    _requires_context = True

    def __init__(
            self,
            pipeline: Optional[QuestionAnsweringPipeline] = None,
            config: Optional[TransformersQAConfig] = None
        ):
        if isinstance(pipeline, QuestionAnsweringPipeline) and config is None:
            self.pipeline = pipeline
        elif isinstance(config, TransformersQAConfig) and pipeline is None:
            self.pipeline = LazyPipeline(config)
        else:
            msg = 'Either a config or pipeline must be specified'
            raise ValueError(msg)

    def __str__(self) -> str:
        if self.config is not None:
            return f'{self.config}'
        else:
            return f'{self.pipeline}'

    @staticmethod
    def from_config(config: MutableMapping[str,str]) -> 'TransformersQA':
        log.info('creating TransformersQA from config')
        log.debug('config: {config}')
        t_config = TransformersQAConfig(**config)
        return TransformersQA(config=t_config)
    
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
