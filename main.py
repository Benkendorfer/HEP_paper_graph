"""
Main script for the HEP graph creator.

Copyright: 2024 by Kees Benkendorfer
"""

import json
import requests

from node import Node

def get_inspire_nodes_from_arxiv(arxiv_id: str):
    """
    Get INSPIRE record from arXiv ID
    """
    url = f"https://inspirehep.net/api/arxiv/{arxiv_id}"
    response = requests.get(url, timeout=5)  # Adding a timeout argument of 5 seconds
    data = response.json()

    # # save data to a pretty json file
    # with open('data.json', 'w', encoding='utf-8') as f:
    #     json.dump(data, f, indent=4)

    nodes = [Node(record=ref['record']['$ref'], title=ref['reference']['misc'])
             for ref in data['metadata']['references'] if 'record' in ref]
    print(f'Found {len(nodes)} references with INSPIRE records')

    return nodes

references = get_inspire_nodes_from_arxiv("2312.03797")
print(references[0])
