import random

from apscheduler.triggers.cron import CronTrigger

# =========================  这一部分需要修改  =========================
ID = '0123465789'
RULES = {
    '体温': str(random.choice([t/10 for t in range(360, 371)])),
    '是否有发烧': '是或者否',
    '所在位置': '填所在位置即可。引号内的所有内容都会作为答案提交',
}
# ======================================================================

RETRY_TIMES = 5
RETRY_INTERVAL = 10
TRIGGER = CronTrigger(hour='5,18', minute=5)
