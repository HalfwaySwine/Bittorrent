class Block:
    def __init__(self, length, data):
        self.data = data
        self.length = length

    def get_length(self): 
        return self.length
    
    def get_data(self): 
        return self.data
    
    #returns string for debugging
    def __str__(self):
        return f"Block(length={self.length})"