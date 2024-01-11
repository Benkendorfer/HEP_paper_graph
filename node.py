class Node:
    """
    Represents a node in a graph.

    Attributes:
        record (str): The record of the node.
        title (str): The title of the node.
    """

    def __init__(self, record: str, title: str):
        self.record = record
        self.title = title

    def __str__(self):
        return f"Record: {self.record}\nTitle: {self.title}"
