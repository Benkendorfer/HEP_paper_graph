"""
Main script for the HEP graph creator.

Copyright: 2024 by Kees Benkendorfer
"""

import logging
import os

import json
from typing import List
import requests

from node import Node
from api_request_manager import APIRequestManager

# Clear the log file
log_file = 'app.log'
if os.path.exists(log_file):
    os.remove(log_file)

# Setup the log file
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_inspire_nodes_from_arxiv(
    arxiv_id: str, api_manager: APIRequestManager
) -> List[Node]:
    """
    Get INSPIRE record from arXiv ID
    """
    url = f"https://inspirehep.net/api/arxiv/{arxiv_id}"
    logging.info("Fetching data from %s", url)
    response = api_manager.make_api_request(url)
    data = response.json()

    # # save data to a pretty json file
    # with open('data.json', 'w', encoding='utf-8') as f:
    #     json.dump(data, f, indent=4)

    nodes = [Node(record=ref['record']['$ref'], title=ref['reference']['misc'])
             for ref in data['metadata']['references'] if 'record' in ref]
    logging.info('Found %d references with INSPIRE records', len(nodes))

    return nodes


def seed_node_from_arxiv(
    arxiv_id: str, api_manager: APIRequestManager
) -> Node:
    """
    Add seed node from arXiv ID
    """
    url = f"https://inspirehep.net/api/arxiv/{arxiv_id}"
    logging.info("Fetching data from %s", url)
    response = api_manager.make_api_request(url)
    data = response.json()

    metadata = data['metadata']

    node = Node(record=url,
                title=metadata['titles'][0]['title'])
    logging.info('Created seed node')

    return node


API_MANAGER = APIRequestManager()

seeds = ["2312.03797"]

seed_node = seed_node_from_arxiv(seeds[0], API_MANAGER)
references = get_inspire_nodes_from_arxiv(seeds[0], API_MANAGER)
print(references[0])
