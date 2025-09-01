import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from tzlocal import get_localzone

from daily_tasks import run_daily_tasks
from monthly_tasks import run_monthly_tasks


LOG_FILE = 'app.log'

# Set up logging configuration (reuse same format and file as app.py)
logger = logging.getLogger('scheduler')
logger.setLevel(logging.DEBUG)

# Avoid adding duplicate handlers if re-imported
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def _is_last_day_of_month(dt: datetime) -> bool:
    """Return True if the given date is the last day of its month."""
    next_day = dt + timedelta(days=1)
    return next_day.month != dt.month


def run_monthly_if_last_day():
    """Run monthly tasks only if today is the last day of the month."""
    now = datetime.now(get_localzone())
    if _is_last_day_of_month(now):
        logger.info("Today is the last day of the month. Running monthly tasks...")
        try:
            run_monthly_tasks()
        except Exception:
            logger.exception("Error while running monthly tasks")
    else:
        logger.info("Not the last day of the month. Skipping monthly tasks.")


def main():
    logger.info("Starting standalone scheduler (daily at 14:00, monthly on last day at 14:05)")

    tz = get_localzone()
    scheduler = BlockingScheduler(timezone=tz)

    # Daily: follow 50 users at 14:00 local time
    scheduler.add_job(run_daily_tasks, 'cron', hour=14, minute=0, id='daily_follow_2pm')

    # Monthly (last day): check at 14:05 local time
    scheduler.add_job(run_monthly_if_last_day, 'cron', hour=14, minute=5, id='monthly_unfollow_last_day')

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == '__main__':
    main()
