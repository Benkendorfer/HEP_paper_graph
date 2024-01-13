from collections import deque
import json
import os
import time
from typing import Dict, Optional

import requests
import logging


class APIRequestManager:
    """
    A class representing a request queue. The queue is implemented to conform
    to the INSPIRE API rate limiter.

    Attributes:
        queue (deque): A deque object to store the requests.
        max_requests (int): The maximum number of requests allowed in the queue.
        time_window (int): The time window (in seconds) within which requests are considered valid.

    Methods:
        enqueue(request_time): Adds a request to the queue.
        dequeue(): Removes and returns the oldest request from the queue.
        can_make_request(): Checks if a request can be made based on the current state
            of the request queue.
        wait_until_request_possible(): Waits until a request can be made based on the
            current state of the request queue.
        make_api_request(url): Makes an API request, given a URL, taking the timing into account.
            If we cannot make a request, then wait until we can.
    """

    def __init__(self):
        self.queue = deque()
        self.max_requests = 15
        self.time_window = 5
        self.logger = logging.getLogger(__name__)

    def enqueue(self, request_time):
        """
        Adds a request to the queue.

        Args:
            request_time (float): The time at which the request was made.
        """
        self.queue.append(request_time)
        self._remove_expired_requests()

    def dequeue(self):
        """
        Removes and returns the oldest request from the queue.

        Returns:
            float or None: The oldest request time, or None if the queue is empty.
        """
        if len(self.queue) < self.max_requests:
            return self.queue.popleft()

        return None

    def _remove_expired_requests(self):
        """
        Removes expired requests from the queue.

        An expired request is one that has been in the queue for longer than the time window.
        """
        current_time = time.time()
        while self.queue and current_time - self.queue[0] > self.time_window:
            self.queue.popleft()

    def can_make_request(self):
        """
        Checks if a request can be made based on the current state of the request queue.

        Returns:
            bool: True if a request can be made, False otherwise.
        """
        if len(self.queue) < self.max_requests:
            return True
        if time.time() - self.queue[0] < self.time_window:
            return False
        return True

    def wait_until_request_possible(self):
        """
        Waits until a request can be made based on the current state of the request queue.
        """
        while not self.can_make_request():
            sleep_time = self.time_window - (time.time() - self.queue[0])
            if sleep_time > 0:
                self.logger.info("Waiting %f seconds until a request can be made", sleep_time)
                time.sleep(sleep_time + 0.05)

    def make_api_request(self, url: str, cache: bool = False) -> Optional[Dict]:
        """
        Makes an API request, given a URL, taking the timing into account.
        If we cannot make a request, then wait the minimum time until we can.

        Args:
            url (str): The URL to make the API request to.

        Returns:
            bool: True if the request was successful, False otherwise.
        """
        # read from the cache if we can
        if cache:
            self.logger.info("Checking cache for %s", url)
            try:
                with open(f"cache/{url.replace('/', '_')}.json", "r", encoding='utf-8') as f:
                    self.logger.info("Reading from cache")
                    return json.load(f)
            except FileNotFoundError:
                self.logger.info("Cache miss")

        if not self.can_make_request():
            self.wait_until_request_possible()

        request_time = time.time()
        self.enqueue(request_time)

        try:
            response = requests.get(url, timeout=5)
        except requests.exceptions.Timeout:
            self.logger.warning("API request to %s timed out", url)
            return None
        except requests.exceptions.ConnectionError:
            self.logger.warning("API request to %s failed due to a connection error", url)
            return None

        self.logger.info("API request to %s successful", url)
        self.logger.info("%i requests have been made in the last %i seconds",
                         len(self.queue), self.time_window)

        if cache:
            self.logger.info("Caching response from %s", url)
            # make sure the cache directory exists
            os.makedirs("cache", exist_ok=True)
            # write to the cache
            with open(f"cache/{url.replace('/', '_')}.json", "w", encoding='utf-8') as f:
                json.dump(response.json(), f, indent=2)

        return response.json()
