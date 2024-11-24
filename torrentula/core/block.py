class Block:
    def __init__(self, length, offset, data):
        self.data = data
        self.length = length
        self.offset  = offset

    def get_length(self): 
        return self.length
    
    def get_data(self): 
        return self.data
    
    #returns string for debugging
    def __str__(self):
        return f"Block(offset={self.offset}, length={self.length})"