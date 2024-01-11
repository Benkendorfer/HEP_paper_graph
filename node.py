class Node:
    def __init__(self, record: str, title: str):
        self.record = record
        self.title = title

    def __str__(self):
        return f"Record: {self.record}\nTitle: {self.title}"
