import hashlib
from .block import Block

BLOCK_SIZE = 16 * 1024

class Piece:
    def __init__(self, index, length, hash):
        self.index = index #index of piece 
        self.length = length #length of entire piece 
        self.available = False # Flag to indicate whether data is loaded, complete, and valid.
        self.blocks = {}  # dictonary only used for reciving data key = offset, value = block class(data,length, offset) however most ask for 16kb 
        self.complete = False # flag to indicate whether all blocks of the piece are present 
        self.hash = hash  #hash of entire piece from torrent file
        self.downloaded = 0 #is increased until it == length of piece
        

    #checks if the completed block matches the hash, pulls from memory
    def is_valid(self): 
        if self.complete == True: 
            with open(f"unsure on file here", "rb") as f:
                piece_data = f.read()
                return hashlib.sha1(piece_data).digest() == self.hash 
        return False
    
    #writes offset of piece to file from recived response from peer
    def write_to_disk(self, offset, data):
        if offset + len(data) > self.length: 
            raise Exception("Data is larger than given bounds") 
        with open(f"unsure on file here", "r+b") as f:
            f.seek(offset)
            f.write(data)

    #frees data in block based on offset 
    def free_block(self, offset): 
        self.blocks[offset] = None

    #adds block to block data-structure
    def add_block(self, offset, data, write_to_disk=True):
        blocktoAdd = Block(len(data),offset,data)
        self.blocks[offset] = blocktoAdd
        self.downloaded += len(data)
        if write_to_disk: 
            self.write_to_disk(offset, data)
            self.free_block(offset)
        if self.downloaded == self.length: 
            self.complete = True
        
    #frees blocks should only really be called if download is at 100% for piece 
    def freeBlockData(self): 
        self.blocks = None
    
    #returns true or false based on if piece is finished 
    def is_complete(self): 
        return self.complete
    

    #loads entire block from file 
    def load_from_block(self): 
        pass

    #gets the next offset and length to ask the peer for for a specified client this is on the assumtion that we will always ask for 16kb incriments which is standard
    def get_next_request(self):
        for offset in range(0, self.length, BLOCK_SIZE):
            if offset not in self.blocks: 
                lastLength = self.length - offset
                lengthToRetun = BLOCK_SIZE
                if lastLength < BLOCK_SIZE: 
                    lengthToRetun = lastLength
                return (offset, lengthToRetun)
        return (None, None) 


    #returns string for debugging
    def __str__(self):
        info = ""
        for value in self.blocks.values():
            info += value.__str__()
            info + " "
        return info

    
