#!/usr/bin/env python3
"""\
上外自动健康打卡脚本
Copyright (C) 2021 shniubobo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from datetime import datetime, time
from functools import wraps
import json
import logging
from time import sleep

from apscheduler.schedulers.blocking import BlockingScheduler
import requests

import config

__version__ = '0.1.0'
HOMEPAGE = 'https://github.com/shniubobo/sisudaka'
ISSUE_TRACKER = 'https://github.com/shniubobo/sisudaka/issues'
BANNER = f"""\
上外自动健康打卡脚本 v{__version__}
Copyright (C) 2021 shniubobo

免责声明：
    本脚本仅用于学习与交流目的。请自行通过企业微信手动打卡，并填写真实数据。若
    继续使用本脚本，则代表你已了解并愿意自行承担所有相应的责任。否则，请立即按
    CTRL+C 退出！

项目主页：{HOMEPAGE}

如遇 bug，请将所有日志信息提交至 {ISSUE_TRACKER}，
并提供详细的复现方式。

"""

HEADERS = {
    'Origin': 'https://daka.shisu.edu.cn',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KH''TML, like'
        ' Gecko) Chrome/53.0.2785.116 Safari/537.36 QBCore/4.0.1316.400 QQBrow'
        'ser/9.0.2524.400 Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537'
        '.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36 wxwork/3.1'
        '.1 (MicroMessenger/6.2) WindowsWechat'
    ),
    'Accept-Language': 'zh-CN',
    'Accept-Encoding': 'gzip, deflate',
}
TIMEOUT = (10, 20)  # (connnect, read)

URL_ID = 'https://daka.shisu.edu.cn/questionnaireSurvey/queryQuestionnairePageList'    # noqa
URL_DETAIL = 'https://daka.shisu.edu.cn/questionnaireSurvey/queryQuestionnaireDetail'  # noqa
URL_SUBMIT = 'https://daka.shisu.edu.cn/questionnaireSurvey/addQuestionnaireRecord'    # noqa

logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

session = requests.Session()
session.headers.update(HEADERS)

scheduler = BlockingScheduler()


class Questionnaire:
    def __init__(self, rows, questionnaire_id, student_id):
        self._raise_if_not_in_progress(rows)
        self._questions = \
            [Question(row) for row in rows if self._is_question(row)]
        self._id = questionnaire_id
        self._student = student_id

    @classmethod
    def from_resp(cls, resp, *args, **kwargs):
        assert resp.status_code == 200
        response_json = resp.json()
        return cls(response_json['rows'], *args, **kwargs)

    def iter_unanswered(self):
        for question in self._questions:
            if question.is_required and not question.is_answered:
                yield question

    def iter_all(self):
        return (question for question in self._questions)

    @property
    def questionnaire_id(self):
        return self._id

    @property
    def student_id(self):
        return self._student

    @staticmethod
    def _raise_if_not_in_progress(rows):
        for row in rows:
            try:
                state = row['STATE']
            except KeyError:
                pass
            else:
                break
        else:
            raise RuntimeError('无法获取问卷状态')

        if state != '进行中':
            raise RuntimeError(f'目前无法提交问卷（问卷状态：{state}）')

    @staticmethod
    def _is_question(row):
        if 'INDEX' in row:
            return True
        return False


class Question:
    CHOICE = 'choice'
    BLANK = 'blank'
    TYPES = {CHOICE, BLANK}

    def __init__(self, row):
        self._id = row['ITEMID']
        self._text = row['TITLE']
        self._required = row['REQUIRE']
        self._raw_type = row['TYPE']
        self._type = self._get_type()
        assert self._type in self.TYPES
        self._answer = None

        if self._type == self.CHOICE:
            self._choices = [Choice(choice) for choice in row['OPTIONS']]
            self._choices.sort(key=lambda choice: choice.index)
        else:
            self._choices = None

        self._load_default_answer(row)

    def __str__(self):
        return self._text

    def __repr__(self):
        return f'<{self._id}: {self._text}>'

    def answer(self, *, choice=None, text=None):
        if self._type == self.CHOICE:
            assert choice is not None
            self._answer = self._choices[choice]
        else:
            assert text
            assert isinstance(text, str) or callable(text)
            self._answer = text

    def get_answer(self):
        if not self.is_answered and self._required:
            raise ValueError(f'问题还未回答：{self}')
        return self._answer

    def iter_choices(self):
        if self._type != self.CHOICE:
            raise TypeError(f'非选择题：{self}')
        return (choice for choice in self._choices)

    @property
    def is_answered(self):
        if self._answer is None:
            return False
        return True

    @property
    def is_required(self):
        return self._required

    @property
    def is_choices(self):
        if self._type == self.CHOICE:
            return True
        return False

    @property
    def is_blank_filling(self):
        if self._type == self.BLANK:
            return True
        return False

    @property
    def type_(self):
        return self._raw_type

    @property
    def id_(self):
        return self._id

    def _get_type(self):
        if self._raw_type == 'radio':
            return self.CHOICE
        if self._raw_type in {'areaFill', 'textFill'}:
            return self.BLANK
        raise ValueError(f'未知问题类型：{self._raw_type}')

    def _load_default_answer(self, row):
        if self._type == self.CHOICE:
            for choice in self._choices:
                if choice.is_default:
                    self._answer = choice
                    break
        else:
            answer_text = row['ANSWERTEXT']
            if answer_text:
                self._answer = answer_text


class Choice:
    def __init__(self, data):
        self._text = data['OPTION']
        self._id = data['SUBID']
        self._is_default = data['CHECKED']
        self._index = int(data['INDEX'])

    def __hash__(self):
        return hash(self._id)

    def __eq__(self, other):
        if not isinstance(other, Choice):
            return False
        if hash(self) == hash(other):
            return True
        return False

    def __str__(self):
        return self._text

    def __repr__(self):
        return f'<{self._id}: {self._text}>'

    @property
    def is_default(self):
        return self._is_default

    @property
    def index(self):
        return self._index

    @property
    def id_(self):
        return self._id


class Respondent:
    def __init__(self, rules):
        self._rules = rules

    def answer(self, questionnaire):
        for question in questionnaire.iter_unanswered():
            if question.is_choices:
                self._answer_choices(question)
            elif question.is_blank_filling:
                self._answer_blank_filling(question)
            else:
                raise TypeError(f'未知问题类型：{question}')

    def _answer_choices(self, question):
        should_choose = self._match_question_with_answer(question)
        for idx, choice in enumerate(question.iter_choices()):
            if should_choose in str(choice):
                question.answer(choice=idx)
                return
        raise ValueError(f'问题“{question}”无对应答案')

    def _answer_blank_filling(self, question):
        should_fill_in = self._match_question_with_answer(question)
        question.answer(text=should_fill_in)

    def _match_question_with_answer(self, question):
        for text, answer in self._rules.items():
            if text in str(question):
                return answer
        raise ValueError(f'问题“{question}”无对应答案')


class AnswerData:
    def __init__(self, questionnaire):
        self._questionnaire = questionnaire

    def build(self):
        ret = []
        for question in self._questionnaire.iter_all():
            question_data = {
                'itemId': question.id_,
                'itemType': question.type_,
                'answerArr': [self._get_answer(question)],
            }
            ret.append(question_data)
        ret = {'answerData': ret}
        return json.dumps(ret)

    @staticmethod
    def _get_answer(question):
        answer = question.get_answer()
        if answer is None:
            return ''
        elif isinstance(answer, Choice):
            return answer.id_
        elif callable(answer):
            return answer()
        else:
            return answer


class QuestionnaireAnsweredError(Exception):
    pass


def _should_trigger_on_startup():
    time_now = datetime.now().time()
    if (time(5) < time_now < time(10)) or (time(18) < time_now < time(23)):
        return True
    return False


def _get_questionnaire_id(student_id):
    resp = session.post(
        URL_ID,
        data={
            'pageNum': '1',
            'nodataFlag': 'false',
            'pageSize': '10',
            'userId': student_id,
        },
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200
    resp_json = resp.json()
    row = resp_json['rows'][0]
    title = row['TITLE']
    if row['HASANSWER']:
        raise QuestionnaireAnsweredError(f'问卷已完成：{title}')
    logger.info(f'标题：{title}')
    return row['ID']


def _get_questionnaire(questionnaire_id, student_id):
    resp = session.post(
        URL_DETAIL,
        data={
            'questionnaireId': questionnaire_id,
            'userId': student_id,
        },
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200
    return Questionnaire.from_resp(resp, questionnaire_id, student_id)


def _answer_questionnaire(questionnaire, rules):
    respondent = Respondent(rules)
    respondent.answer(questionnaire)


def _submit_questionnaire(questionnaire):
    answer_data = AnswerData(questionnaire)
    resp = session.post(
        URL_SUBMIT,
        data={
            'questionnaireId': questionnaire.questionnaire_id,
            'userId': questionnaire.student_id,
            'answerData': answer_data.build(),
        },
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200


def _is_questionnaire_success(student_id):
    try:
        _get_questionnaire_id(student_id)
    except QuestionnaireAnsweredError:
        return True
    return False


def retry_on(exception, *, times=1, interval=0):
    def decorator(wrapped):
        @wraps(wrapped)
        def wrapper(*args, **kwargs):
            counter = 1
            while True:
                try:
                    return wrapped(*args, **kwargs)
                except exception as e:
                    if counter < times + 1:
                        logger.warning(
                            f'{wrapped} 出错第 {counter} 次，'
                            f'将在 {interval} 秒后重试：{e}'
                        )
                    else:
                        logger.error(
                            f'{wrapped} 出错第 {counter} 次，放弃重试'
                        )
                        raise
                    counter += 1
                    sleep(interval)
        return wrapper
    return decorator


@retry_on(
    Exception,
    times=config.RETRY_TIMES,
    interval=config.RETRY_INTERVAL,
)
def on_trigger(student_id, rules):
    logger.info('开始打卡')
    try:
        questionnaire_id = _get_questionnaire_id(student_id)
    except QuestionnaireAnsweredError as e:
        logger.error(str(e))
        return
    questionnaire = _get_questionnaire(questionnaire_id, student_id)
    _answer_questionnaire(questionnaire, rules)
    _submit_questionnaire(questionnaire)
    if not _is_questionnaire_success(student_id):
        raise RuntimeError('未成功打卡')
    logger.info('打卡成功')


def main():
    print(BANNER)
    scheduler.add_job(
        on_trigger,
        trigger=config.TRIGGER,
        args=(config.ID, config.RULES),
        misfire_grace_time=None,
    )
    if _should_trigger_on_startup():
        scheduler.add_job(
            on_trigger,
            args=(config.ID, config.RULES),
            misfire_grace_time=None,
        )
    else:
        logger.info('等待中……')
    scheduler.start()


if __name__ == '__main__':
    try:
        main()
    finally:
        scheduler.shutdown()
        session.close()
