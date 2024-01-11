"""
Main script for the HEP graph creator.

Copyright: 2024 by Kees Benkendorfer
"""

import logging
import os

import json
from typing import List

from node import Node, NodeType
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
                title=metadata['titles'][0]['title'],
                node_type=NodeType.SEED)
    logging.info('Created seed node')

    return node


def remove_duplicates(all_nodes):
    """
    Remove duplicates from a list of nodes based on their record attribute.
    If a duplicate is found, merge the parents of the duplicate node into the first occurrence.

    Args:
        all_nodes (list): A list of nodes.

    Returns:
        list: A list of unique nodes with merged parents.
    """
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

    return unique_nodes


def get_nodes_from_seeds(seeds, api_manager):
    """
    Retrieves a list of references from the given seeds.

    Args:
        seeds (list): A list of seed values.
        api_manager (object): An instance of the API manager.

    Returns:
        list: A list of unique nodes.
    """
    all_nodes = []
    for seed in seeds:
        seed_node = seed_node_from_arxiv(seed, api_manager)
        references = get_inspire_nodes_from_arxiv(seed, api_manager, seed_node)

        all_nodes += [seed_node]
        all_nodes += references

    all_nodes = remove_duplicates(all_nodes)
    logging.info('Found %d unique nodes', len(ALL_NODES))
    return all_nodes


API_MANAGER = APIRequestManager()

SEEDS = ["2312.03797", "2202.12134", "2205.02817", "2312.04450"]

ALL_NODES = get_nodes_from_seeds(SEEDS, API_MANAGER)

node_map = {}
for i, node in enumerate(ALL_NODES):
    node_map[node.record] = f"N{i}"

# sort all_nodes by number of parents
ALL_NODES.sort(key=lambda x: len(x.parents), reverse=True)

with open('graph.dot', 'w') as f:
    f.write('digraph G {\n')
    f.write('rankdir=LR;\n')  # Set the rank direction to left-to-right
    f.write('node [shape=rectangle];\n')
    f.write('graph [layout=twopi, overlap=true, splines=true, ranksep=25];\n')
    for node in ALL_NODES:
        num_parents = len(node.parents)
        f.write(f'"{node_map[node.record]}" [width={num_parents}, height={num_parents}];\n')

        if node.node_type == NodeType.SEED:
            f.write(f'"{node_map[node.record]}" [color=orange, style=filled];\n')  # Color seed nodes orange
        else:
            f.write(f'"{node_map[node.record]}" [color=grey, style=filled];\n')

        for parent in node.parents:
            f.write(f'"{node_map[parent.record]}" -> "{node_map[node.record]}";\n')

    f.write('}\n')
