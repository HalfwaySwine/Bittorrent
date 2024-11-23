class Piece:
    def __init__(self, index, length):
        self.index = index
        # self.offset?
        self.length = length
        # self.available = False # Flag to indicate whether data is loaded, complete, and valid.
        self.blocks = {}  # TODO Choose data structure (Could be a dictionary that maps block offset to block)

    def write_to_disk(self):
        pass

    def get_hash(self):
        pass

    def free_memory(self):
        self.blocks = None
