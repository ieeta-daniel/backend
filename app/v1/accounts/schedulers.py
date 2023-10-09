import time
from fastapi import Depends

from app.config import settings
from app.dependencies import cache
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

redis_client = cache()


def clear_expired_refresh_tokens():
    for key in redis_client.scan_iter("refresh_tokens:*"):

        current_timestamp = int(time.time())

        redis_client.zremrangebyscore(key, '-inf', current_timestamp)

        if redis_client.zcard(key) == 0:
            redis_client.delete(key)


jobstores = {
    'default': SQLAlchemyJobStore(url=settings.sync_database_url)
}

executors = {
    'default': ThreadPoolExecutor(10)
}

clear_expired_refresh_token_scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors)

clear_expired_refresh_token_scheduler.add_job(
    clear_expired_refresh_tokens,
    trigger='cron',
    hour=0,
    minute=0,
    misfire_grace_time=3600
)