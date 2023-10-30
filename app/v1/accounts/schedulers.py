import time
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


def clear_expired_blacklisted_access_tokens():
    for key in redis_client.scan_iter("access_tokens:*"):
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

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors)

scheduler.add_job(
    clear_expired_refresh_tokens,
    trigger='cron',
    day_of_week=0,
    misfire_grace_time=3600
)

scheduler.add_job(
    clear_expired_blacklisted_access_tokens,
    trigger='cron',
    day_of_week=0,
    misfire_grace_time=3600
)
