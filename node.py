from typing import Set
from enum import Enum

class NodeType(Enum):
    REFERENCE = 0
    SEED = 1

class Node:
    """
    Represents a node in a graph.

    Attributes:
        record (str): The record of the node.
        title (str): The title of the node.
        parents (set): Set of parent nodes.
        node_type (NodeType): The type of the node.
    """

    def __init__(self, record: str, title: str,
                 node_type: NodeType = NodeType.REFERENCE):
        self.record = record
        self.title = title
        self.parents: Set[Node] = set()
        self.node_type = node_type

    def __str__(self):
        return f"Record: {self.record}\nTitle: {self.title}"

    def __hash__(self):
        """
        Returns the hash value of the node based on its record and title.

        Returns:
            int: The hash value of the node.
        """
        return hash((self.record, self.title))

    def __eq__(self, other):
        """
        Checks if two nodes are equal based on their record.

        Parameters:
            other (Node): The other node to compare.

        Returns:
            bool: True if the nodes are equal, False otherwise.
        """
        if isinstance(other, Node):
            return self.record == other.record
        return False

    def add_parent(self, parent_node: 'Node'):
        """
        Adds a parent node to the current node.

        Parameters:
            parent_node (Node): The parent node to be added.

        Returns:
            None
        """
        self.parents.add(parent_node)
