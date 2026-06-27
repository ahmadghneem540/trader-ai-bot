from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.core.logging.logger import get_logger
from typing import Callable, Optional

logger = get_logger(__name__)


class Scheduler:
    _instance: Optional['Scheduler'] = None
    _scheduler: Optional[AsyncIOScheduler] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._scheduler = AsyncIOScheduler()
        self._initialized = True

    def start(self):
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Scheduler shutdown")

    def add_job(
        self,
        func: Callable,
        trigger: str = "interval",
        seconds: Optional[int] = None,
        cron: Optional[dict] = None,
        id: Optional[str] = None,
        **kwargs
    ):
        if not self._scheduler:
            raise Exception("Scheduler not initialized")
        if trigger == "cron" and cron:
            job = self._scheduler.add_job(
                func=func,
                trigger=CronTrigger(**cron),
                id=id,
                replace_existing=True,
                **kwargs
            )
            logger.info(f"Added cron job {job.id} with {cron}")
        else:
            job = self._scheduler.add_job(
                func=func,
                trigger=IntervalTrigger(seconds=seconds or 60),
                id=id,
                replace_existing=True,
                **kwargs
            )
            logger.info(f"Added job {job.id} with interval {seconds}s")
        return job

    def remove_job(self, job_id: str):
        if self._scheduler:
            self._scheduler.remove_job(job_id)
            logger.info(f"Removed job {job_id}")

    def get_jobs(self):
        if self._scheduler:
            return self._scheduler.get_jobs()
        return []


def get_scheduler() -> Scheduler:
    return Scheduler()
