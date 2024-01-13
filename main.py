"""
Main script for the HEP graph creator.

Copyright: 2024 by Kees Benkendorfer
"""

import logging
import os

from typing import List, Optional

from node import Node, NodeType
from api_request_manager import APIRequestManager

import graph_tool.all as gt
from matplotlib.cm import gist_heat

# Clear the log file
log_file = 'app.log'
if os.path.exists(log_file):
    os.remove(log_file)

# Setup the log file
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_inspire_nodes_from_url(
    url: str, api_manager: APIRequestManager,
    record_filter: Optional[List[str]] = None
) -> List[Node]:
    """
    Get INSPIRE record from URL
    """
    logging.info("Fetching data from %s", url)
    response = api_manager.make_api_request(url, cache=True)
    if response is None:
        logging.error("Failed to fetch data from %s", url)
        return []
    data = response

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

        if (record_filter is not None) and (record not in record_filter):
            logging.debug('Reference is not in the record filter, skipping...')
            continue

        try:
            record_num = record.split('/')[-1]
            title = api_manager.find_title_from_inspire_record(record_num, cache=True)
        except KeyError:
            logging.info(ref)
            logging.warning('KeyError, no title found')
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


def get_inspire_nodes_from_inspire(
    inspire_ref: str, api_manager: APIRequestManager, seed_node: Node
) -> List[Node]:
    """
    Get INSPIRE record from INSPIRE record
    """
    url = f"https://inspirehep.net/api/literature/{inspire_ref}"
    nodes = get_inspire_nodes_from_url(url, api_manager)

    for new_node in nodes:
        new_node.add_parent(seed_node)

    return nodes


def seed_node_from_inspire(
    inspire_ref: str, api_manager: APIRequestManager
) -> Optional[Node]:
    """
    Add seed node from INSPIRE record
    """
    url = f"https://inspirehep.net/api/literature/{inspire_ref}"
    logging.info("Fetching data from %s", url)
    response = api_manager.make_api_request(url, cache=True)
    if response is None:
        logging.error("Failed to fetch data from %s", url)
        return None

    data = response

    try:
        title = data['metadata']['titles'][0]['title']
    except KeyError:
        title = 'No title'

    node = Node(record=url,
                title=title,
                node_type=NodeType.SEED)
    logging.info('Created seed node')

    return node


def seed_node_from_arxiv(
    arxiv_id: str, api_manager: APIRequestManager
) -> Optional[Node]:
    """
    Add seed node from arXiv ID
    """
    url = f"https://inspirehep.net/api/arxiv/{arxiv_id}"
    logging.info("Fetching data from %s", url)
    response = api_manager.make_api_request(url, cache=True)
    if response is None:
        logging.error("Failed to fetch data from %s", url)
        return None

    data = response

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
        seed_node = seed_node_from_inspire(seed, api_manager)
        if seed_node is None:
            logging.error('Failed to create seed node from INSPIRE record %s', seed)
            continue
        references = get_inspire_nodes_from_inspire(seed, api_manager, seed_node)

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
    record_filter = [node.record for node in nodes]

    for i, citing_node in enumerate(nodes):
        logging.info('Finding inter-node citations for node %d/%d', i + 1, len(nodes))
        # We only want to consider non-seed nodes
        if citing_node.node_type == NodeType.SEED:
            continue

        # We only record citations to nodes that are
        # in the original list
        cited_nodes = get_inspire_nodes_from_url(citing_node.record, api_manager, record_filter=record_filter)

        for cited_node in cited_nodes:
            add_inter_node_citation(nodes, citing_node, cited_node)

    return nodes


API_MANAGER = APIRequestManager()

SEEDS = [#"1900929", "1815227",
         "2037744", "2077575"
         ]

ALL_NODES = get_nodes_from_seeds(SEEDS, API_MANAGER)

find_inter_node_citations(ALL_NODES, API_MANAGER)

# create adjacency matrix
adjacency_matrix = {}
for NODE in ALL_NODES:
    if NODE.record not in adjacency_matrix:
        adjacency_matrix[NODE.record] = []
    for parent in NODE.parents:
        if parent.record not in adjacency_matrix:
            adjacency_matrix[parent.record] = []
        adjacency_matrix[parent.record] += [NODE.record]

# create a graph-tools graph from ALL_NODES
g = gt.Graph(adjacency_matrix, directed=True, hashed=True)
pos = gt.sfdp_layout(g)
gt.graph_draw(g, pos=pos, output="output.pdf")
# draw the graph, sizing by degree
deg = g.degree_property_map("in")
gt.graph_draw(g, pos=pos, vertex_fill_color=gt.prop_to_size(deg, 0, 1, power=.1),
              vertex_size=gt.prop_to_size(deg, mi=5, ma=15),
              vorder=deg, vcmap=gist_heat,
              output="output-deg.pdf")
pr = gt.pagerank(g)
gt.graph_draw(g, pos=pos, vertex_fill_color=pr,
              vertex_size=gt.prop_to_size(pr, mi=5, ma=15),
              vorder=pr, vcmap=gist_heat,
              output="output-pr.pdf")

# Sort the nodes by pagerank
sorted_nodes = sorted(g.iter_vertices(), key=lambda v: pr[v], reverse=True)

# Print the top 10 nodes by pagerank
for i, node in enumerate(sorted_nodes[:10]):
    # remove the api from the record
    record_to_print = ALL_NODES[node].record.replace('api/', '')
    print(f"Node {i+1}: {record_to_print} - Pagerank: {pr[node]}")
    print(f"\tTitle: {ALL_NODES[node].title}")
    print(ALL_NODES[node])
