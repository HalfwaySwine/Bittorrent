import hashlib
from block import Block
import time

BLOCK_SIZE = 16 * 1024 #standard block size we will request 16kb
TIME_OUT = 5 #change to what we need it to be later

#this class is responsible for holding onto the infomartion assosicated with each piece 


''' 
Interface 
    get_next_request()
    @info: gets the next request for a piece to send to a peer 
    @return: tuple (offset to request, length to request)

    add_block()
    @info: adds block after receiving to data structure and when complete will write to disk and verifys with hash
    @returns: -1 if invalid hash (need to restart), 1 if added block successfully but not complete yet, 0 if added block and complete and done 

    get_download_percent()
    @info Returns the percent of how close it is to downloading out of 100
    @return the value out of 100 for how close it is to finishing 

    get_data_from_file(offset,blockLength)
    @info gets the data in bytes that a peer requests from disk
    @returns the data in bytes
    
    __str__()
    @Info toString
    @returns string incluinsoing the current block data it has 

'''

class Piece:
    def __init__(self, index, length, hash):
        self.index = index #index of piece 
        self.length = length #length of entire piece 
        self.blocks = {}  # dictonary only used for reciving data key = offset, value = block class(data,length) however most ask for 16kb 
        self.complete = False # flag to indicate whether all blocks of the piece are present 
        self.hash = hash  #hash of entire piece from torrent file
        self.downloaded = 0 #is increased until it == length of piece
        self.pieceBuffer = None #buffer for after its completed 
        self.pendingRequests = {} #key = offset value = timestamp keeps track of the offsets we have asked for 

    #gets the next offset and length to ask the peer for for a specified client this is on the assumtion that we will always ask for 16kb incriments which is standard
    #return a tuple (offset to request, length to request)
    def get_next_request(self):
        for offset in range(0, self.length, BLOCK_SIZE):
            if offset not in self.blocks: #checks whats the next request I have yet to recive 
                if self._check_if_already_asked(offset): #checks last request time
                    lastLength = self.length - offset
                    lengthToRetun = BLOCK_SIZE
                    if lastLength < BLOCK_SIZE: 
                        lengthToRetun = lastLength
                    #add to pending requests or update time 
                    self.pendingRequests[offset] = time.time()
                    return (offset, lengthToRetun)
        return (None, None) 
    
    #checks if its been to long since it requested this block if so needs to re request it (helper fucntion)
    #returns true if it needs to be requested
    def _check_if_already_asked(self, offset): 
        if offset not in self.pendingRequests: 
            return True
        else: 
            #checks if timestamp is still valid 
            timeSinceRequest = time.time() - self.pendingRequests[offset]
            if timeSinceRequest > TIME_OUT: 
                return True 
            return False
        
    #adds block to block data-structure
    #returns -1 if invalid hash (need to restart), 1 if added block successfully but not complete yet, 0 if added block and complete and done 
    def add_block(self, offset, data):
        blocktoAdd = Block(len(data),data)
        self.blocks[offset] = blocktoAdd
        self.downloaded += len(data)

        #checks if its done downloading 
        if self.downloaded == self.length: 
            self.complete = True
            self.pendingRequests = None #frees pending requests
            self._form_buffer() #forms buffer of everything and frees blocks data structure 
            if not self._is_valid(): #checks if its valid
                #something happended its not valid for whatever reason reset everything 
                self.blocks = {} 
                self.pendingRequests = {} 
                self.pieceBuffer = None 
                self.downloaded = 0
                return -1
            self._write_to_disk()
            return 0
        return 1
    

    #Returns the percent of how close it is to downloading out of 100
    def get_download_percent(self): 
        return (self.downloaded / self.length) * 100
    
 
    #gets the data in bytes that a peer requests from disk      # still needs some work
    def get_data_from_file(self, offset,blockLength): 
        try:
            with open(f"add correct file path here", "r+b") as f:
                f.seek((self.index * self.length) + offset)
                data = f.read(blockLength)
            return data
        except Exception as e:
            print("Error writing to disk: " + str(e))
    


    #forms complete buffer with data in block datastructure (helper fucntion)
    def _form_buffer(self):
        self.pieceBuffer = bytearray(self.length)
        for offset, block in self.blocks.items(): 
            self.pieceBuffer[offset:offset + block.get_length()] = block.get_data()
        self.blocks = None 

    #checks if the completed block matches the hash, pulls from memory (helper fucntion)
    def _is_valid(self):  
        return hashlib.sha1(self.pieceBuffer).digest() == self.hash 
        
    #writes offset of piece to file from recived response from peer                    # seek needs to be fixed to work if last piece size is different
    def _write_to_disk(self):
        try:
            with open(f"add correct file path here", "r+b") as f:
                f.seek(self.index * self.length)
                f.write(self.pieceBuffer)
        except Exception as e:
            print("Error writing to disk: " + str(e))


    #returns string for debugging
    def __str__(self):
        if self.blocks is None:
            return "Already completed"
        info = ""
        for offset, value in self.blocks.items():
            info += "Offset=" + str(offset) + " "
            info += value.__str__()
            info + " "
        return info

    
