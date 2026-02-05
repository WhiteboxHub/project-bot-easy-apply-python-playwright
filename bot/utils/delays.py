import random
import time
import logging

log = logging.getLogger(__name__)

def sleep_random(min_time=1.5, max_time=2.9):
    rando_time = random.uniform(min_time, max_time)
    log.debug(f"Sleeping for {round(rando_time, 1)}")
    time.sleep(rando_time)

def sleep(seconds):
    time.sleep(seconds)
