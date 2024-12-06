import hashlib
from .block import Block
import time
from ..utils.helpers import logger, Status

BLOCK_SIZE = 16 * 1024  # standard block size we will request 16kb
TIME_OUT = 5  # change to what we need it to be later

# this class is responsible for holding onto the infomartion assosicated with each piece


""" 
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
"""


class Piece:
    def __init__(self, index, length, hash, torrentLength, torrentPath, fileDesc):
        self.index = index  # index of piece
        self.length = length  # length of entire piece (will be different for last piece)
        # blocks dictonary only used for reciving data key = offset, value = block class(data,length) however most ask for 16kb
        self.blocks = {}
        self.complete = False  # flag to indicate whether all blocks of the piece are present
        self.hash = hash  # hash of entire piece from torrent file
        self.downloaded = 0  # is increased until it == length of piece
        self.pieceBuffer = None  # buffer for after its completed
        self.pendingRequests = {}  # key = offset value = timestamp keeps track of the offsets we have asked for
        self.torrentLength = torrentLength  # length listed in torrent file
        self.torrentPath = torrentPath
        self.fileDesc = fileDesc #file to write to

    # gets the next offset and length to ask the peer for a specified client this is on the assumtion that we will always ask for 16kb incriments which is standard
    # return a tuple (offset to request, length to request)
    def get_next_request(self):
        logger.debug("attempting to get next request")
        if self.complete: 
            logger.info("status of Get_next_request(): already complete")
            return (None, None)
        if self.length < BLOCK_SIZE:  # if last piece is smaller than the block size
            if 0 not in self.blocks:
                self.pendingRequests[0] = time.time()
                logger.info(f"status of Get_next_request(): 0 {self.length} Last piece is smaller than block")
                return (0, self.length)
            logger.info("status of Get_next_request(): None None Last piece is smaller than block")
            return (None, None)

        for offset in range(0, self.length, BLOCK_SIZE):
            if offset not in self.blocks:  # checks whats the next request I have yet to recive
                if self._check_if_already_asked(offset):  # checks last request time
                    lastLength = self.length - offset
                    lengthToRetun = BLOCK_SIZE
                    if lastLength < BLOCK_SIZE:
                        lengthToRetun = lastLength
                    # add to pending requests or update time
                    self.pendingRequests[offset] = time.time()
                    logger.info(f"status of Get_next_request(): {offset} {lengthToRetun}")
                    return (offset, lengthToRetun)
        logger.info("status of Get_next_request(): None None")
        return (None, None)

    # checks if its been to long since it requested this block if so needs to re request it (helper fucntion)
    # returns true if it needs to be requested
    def _check_if_already_asked(self, offset):
        if offset not in self.pendingRequests:
            logger.debug("Not already pending this request")
            return True
        else:
            # checks if timestamp is still valid
            timeSinceRequest = time.time() - self.pendingRequests[offset]
            if timeSinceRequest > TIME_OUT:
                logger.debug("Timeout on this request")
                return True
            logger.debug("No timeout on this request")
            return False

    # adds block to block data-structure
    # returns -1 if invalid hash (need to restart), 1 if added block successfully but not complete yet, 0 if added block and complete and done
    def add_block(self, offset, data):
        logger.debug("Attempting to add block")
        blocktoAdd = Block(len(data), data)
        self.blocks[offset] = blocktoAdd
        self.downloaded += len(data)

        # checks if its done downloading
        if self.downloaded == self.length:
            self.complete = True
            self.pendingRequests = None  # frees pending requests
            self._form_buffer()  # forms buffer of everything and frees blocks data structure
            if not self._is_valid():  # checks if its valid
                # something happended its not valid for whatever reason reset everything
                self.blocks = {}
                self.pendingRequests = {}
                self.pieceBuffer = None
                self.downloaded = 0
                self.complete = False
                logger.info("Download done invalid hash")
                logger.debug("Download done invalid hash")
                return -1
            self._write_to_disk()
            logger.info("Download Sone and Valid")
            return 0
        logger.info("Download not done")
        return 1

    # Returns the percent of how close it is to downloading out of 100
    def get_download_percent(self):
        return (self.downloaded / self.length) * 100

    # gets the data in bytes that a peer requests from disk
    def get_data_from_file(self, offset, blockLength):
        logger.debug("Attempting get_data_from_file()")
        try:
            
            self.fileDesc.seek((self.index * self.torrentLength) + offset)
            data = self.fileDesc.read(blockLength)
            logger.info("get_data_from_file retunred data")
            return data
        except Exception as e:
            print("Error reading from disk: " + str(e))
            logger.debug("Error reading from disk")

    # forms complete buffer with data in block datastructure (helper fucntion)
    def _form_buffer(self):
        logger.debug("Attempting form_buffer")
        self.pieceBuffer = bytearray(self.length)
        for offset, block in self.blocks.items():
            self.pieceBuffer[offset : offset + block.get_length()] = block.get_data()
        self.blocks = None

    # checks if the completed block matches the hash, pulls from memory (helper fucntion)
    def _is_valid(self):
        return hashlib.sha1(self.pieceBuffer).digest() == self.hash

    # writes offset of piece to file from recived response from peer
    def _write_to_disk(self):
        logger.debug("Attempting write_to_disk")
        try:
            
            self.fileDesc.seek(self.index * self.torrentLength)
            self.fileDesc.write(self.pieceBuffer)
        except Exception as e:
            print("Error writing to disk: " + str(e))
            logger.debug("Error writing to disk")

    # returns string for debugging
    def __str__(self):
        if self.blocks is None:
            return "Already completed"
        info = ""
        for offset, value in self.blocks.items():
            info += "Offset=" + str(offset) + " "
            info += value.__str__()
            info += " "
            into += "Download %: " + str(self.get_download_percent)
        return info
