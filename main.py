"""
Main script for the HEP graph creator.

Copyright: 2024 by Kees Benkendorfer
"""

import logging
import os

from typing import List, Optional

from node import Node, NodeType
from api_request_manager import APIRequestManager

# Clear the log file
log_file = 'app.log'
if os.path.exists(log_file):
    os.remove(log_file)

# Setup the log file
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_inspire_nodes_from_url(
    url: str, api_manager: APIRequestManager
) -> List[Node]:
    """
    Get INSPIRE record from URL
    """
    logging.info("Fetching data from %s", url)
    response = api_manager.make_api_request(url)
    if response is None:
        logging.error("Failed to fetch data from %s", url)
        return []
    data = response.json()

    try:
        references = data['metadata']['references']
    except KeyError:
        logging.info('No references found')
        return []

    nodes = []
    for ref in references:
        if 'record' not in ref:
            logging.debug('Reference has no INSPIRE record, skipping...')
            continue

        record = ref['record']['$ref']

        try:
            title = ref['reference']['misc'][0]
        except KeyError:
            title = 'No title'

        new_node = Node(record=record, title=title)
        nodes += [new_node]

    logging.info('Found %d references with INSPIRE records', len(nodes))

    return nodes


def get_inspire_nodes_from_arxiv(
    arxiv_id: str, api_manager: APIRequestManager, seed_node: Node
) -> List[Node]:
    """
    Get INSPIRE record from arXiv ID
    """
    url = f"https://inspirehep.net/api/arxiv/{arxiv_id}"
    nodes = get_inspire_nodes_from_url(url, api_manager)

    for new_node in nodes:
        new_node.add_parent(seed_node)

    return nodes


def seed_node_from_arxiv(
    arxiv_id: str, api_manager: APIRequestManager
) -> Optional[Node]:
    """
    Add seed node from arXiv ID
    """
    url = f"https://inspirehep.net/api/arxiv/{arxiv_id}"
    logging.info("Fetching data from %s", url)
    response = api_manager.make_api_request(url)
    if response is None:
        logging.error("Failed to fetch data from %s", url)
        return None

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
    logging.info('Found %d unique nodes', len(all_nodes))
    return all_nodes


def add_inter_node_citation(
    nodes: List[Node], citing_node: Node, cited_node: Node
):
    # Parent relationship is defined such that
    # the citing node is the parent of the cited node
    for node in nodes:
        if node == cited_node:
            node.add_parent(citing_node)


def find_inter_node_citations(
    nodes: List[Node], api_manager: APIRequestManager
):
    """
    Find citations between nodes in the given list.

    Args:
        nodes (list): A list of nodes.

    Returns:
        list: A list of nodes with citations.
    """
    for i, citing_node in enumerate(nodes):
        logging.info('Finding inter-node citations for node %d/%d', i + 1, len(nodes))
        # We only want to consider non-seed nodes
        if citing_node.node_type == NodeType.SEED:
            continue

        cited_nodes = get_inspire_nodes_from_url(citing_node.record, api_manager)

        # We only record citations to nodes that are
        # in the original list
        for cited_node in cited_nodes:
            add_inter_node_citation(nodes, citing_node, cited_node)

    return nodes


API_MANAGER = APIRequestManager()

SEEDS = ["2312.03797", "2202.12134", "2205.02817", "2312.04450"]

ALL_NODES = get_nodes_from_seeds(SEEDS, API_MANAGER)

find_inter_node_citations(ALL_NODES, API_MANAGER)

node_map = {}
for i, NODE in enumerate(ALL_NODES):
    # node_map[NODE.record] = f"N{i}"
    node_map[NODE.record] = NODE.record

# sort all_nodes by number of parents
ALL_NODES.sort(key=lambda x: len(x.parents), reverse=True)

# keep only the top few nodes
ALL_NODES = ALL_NODES[:25] + [node for node in ALL_NODES if node.node_type == NodeType.SEED]

with open('graph.dot', 'w', encoding='utf-8') as f:
    f.write('digraph G {\n')
    f.write('rankdir=LR;\n')  # Set the rank direction to left-to-right
    f.write('node [shape=rectangle];\n')
    f.write('graph [engine=twopi, overlap=false, splines=true, ranksep=20];\n')

    min_parents = min(len(NODE.parents) for NODE in ALL_NODES)

    for NODE in ALL_NODES:
        num_parents = len(NODE.parents)
        size = (num_parents - min_parents) * 0.1 + 0.5
        # size = num_parents * 0.01  # Adjust the scaling factor as needed

        if NODE.node_type == NodeType.SEED:
            f.write(f'"{node_map[NODE.record]}" [color=orange, style=filled, width={size*2 + 10}, height={size}, fontsize={size}];\n')  # Color seed nodes orange
        else:
            f.write(f'"{node_map[NODE.record]}" [width={size}, height={size}, fontsize={size*2 + 10}];\n')

        for parent in NODE.parents:
            if parent in ALL_NODES:
                f.write(f'"{node_map[parent.record]}" -> "{node_map[NODE.record]}";\n')

    f.write('}\n')
