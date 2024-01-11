"""
Main script for the HEP graph creator.

Copyright: 2024 by Kees Benkendorfer
"""

import logging
import os

import json
from typing import List

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
    arxiv_id: str, api_manager: APIRequestManager, seed_node: Node
) -> List[Node]:
    """
    Get INSPIRE record from arXiv ID
    """
    url = f"https://inspirehep.net/api/arxiv/{arxiv_id}"
    logging.info("Fetching data from %s", url)
    response = api_manager.make_api_request(url)
    data = response.json()

    nodes = []
    for ref in data['metadata']['references']:
        if 'record' not in ref:
            logging.info('Reference has no INSPIRE record, skipping...')
            continue

        record = ref['record']['$ref']

        try:
            title = ref['reference']['misc']
        except KeyError:
            title = 'No title'

        new_node = Node(record=record, title=title)
        new_node.add_parent(seed_node)
        nodes += [new_node]

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

seeds = ["2312.03797", "2202.12134"]

# iterate over seeds and generate a list of all references
all_nodes = []
for seed in seeds:
    seed_node = seed_node_from_arxiv(seed, API_MANAGER)
    references = get_inspire_nodes_from_arxiv(seed, API_MANAGER, seed_node)

    all_nodes += [seed_node]
    all_nodes += references

# Remove duplicates based on record
unique_nodes = []
record_set = set()

for node in all_nodes:
    if node.record not in record_set:
        unique_nodes.append(node)
        record_set.add(node.record)
    else:
        # Merge parents into the first node
        existing_node = next((n for n in unique_nodes if n.record == node.record), None)
        if existing_node is not None:
            existing_node.parents = existing_node.parents.union(node.parents)

# Replace all_nodes with unique_nodes
all_nodes = unique_nodes

logging.info('Found %d unique nodes', len(all_nodes))

with open('graph.dot', 'w') as f:
    f.write('digraph G {\n')
    f.write('rankdir=LR;\n')  # Set the rank direction to left-to-right
    f.write('node [shape=rectangle];\n')
    f.write('graph [layout=twopi, overlap=false, splines=true];\n')  # Use the "neato" layout algorithm, disable overlap, and enable splines
    for node in all_nodes:
        if node in seeds:
            f.write(f'"{node.record}" [color=orange];\n')  # Color seed nodes orange
        for parent in node.parents:
            f.write(f'"{parent.record}" -> "{node.record}";\n')
    f.write('}')
