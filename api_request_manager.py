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
            self.logger.debug("Checking cache for %s", url)
            try:
                with open(f"cache/{url.replace('/', '_')}.json", "r", encoding='utf-8') as f:
                    self.logger.debug("Reading from cache")
                    return json.load(f)
            except FileNotFoundError:
                self.logger.debug("Cache miss")

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
        self.logger.debug("%i requests have been made in the last %i seconds",
                         len(self.queue), self.time_window)

        if cache:
            self.logger.info("Caching response from %s", url)
            # make sure the cache directory exists
            os.makedirs("cache", exist_ok=True)
            # write to the cache
            with open(f"cache/{url.replace('/', '_')}.json", "w", encoding='utf-8') as f:
                json.dump(response.json(), f, indent=2)

        return response.json()

    def find_title_from_inspire_record(
        self, record_num: str, cache:bool = True
    ) -> str:
        """
        Get the title of an INSPIRE record from its record ID.

        Args:
            record (str): The record ID of the INSPIRE record.

        Returns:
            str: The title of the INSPIRE record.
        """
        if cache:
            self.logger.debug("Checking title cache for %s", record_num)
            try:
                with open("cache/title_cache.txt", "r", encoding='utf-8') as f:
                    for line in f:
                        if line.startswith(record_num):
                            self.logger.debug("Reading title from cache")
                            return line.split(',')[1].strip()
            except FileNotFoundError:
                self.logger.debug("Cache miss")

        url = f"https://inspirehep.net/api/literature?q=recid:{record_num}&fields=titles"
        response = self.make_api_request(url, cache=False)
        if response is None:
            self.logger.warning("Failed to get response during title search for record %s", record_num)
            return 'No title'

        try:
            title = response['hits']['hits'][0]['metadata']['titles'][0]['title']
        except KeyError:
            self.logger.warning('No title found for record %s', record_num)
            title = 'No title'

        if cache:
            self.logger.debug("Caching title for %s", record_num)
            # make sure the cache directory exists
            os.makedirs("cache", exist_ok=True)
            # write a new line to the title cache
            with open("cache/title_cache.txt", "a", encoding='utf-8') as f:
                f.write(f"{record_num},{title}\n")

        return title
