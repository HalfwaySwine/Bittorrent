import hashlib
from .block import Block
import time
from io import BufferedRandom
from ..utils.helpers import logger, Status
from ..config import PIECE_TIMEOUT_SECS

BLOCK_SIZE = 16 * 1024  # standard block size we will request 16kb
TIME_OUT = PIECE_TIMEOUT_SECS

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
    def __init__(self, index, length, hash, torrentLength, torrentPath, fileDesc: BufferedRandom):
        self.index = index  # index of piece
        self.length = length  # length of entire piece (will be different for last piece)
        self.default_piece_length = length  # default piece length for index calculation, we only change self.length after the constructor
        # blocks dictonary only used for reciving data key = offset, value = block class(data,length) however most ask for 16kb
        self.blocks = {}
        self.complete = False  # flag to indicate whether all blocks of the piece are present
        self.hash = hash  # hash of entire piece from torrent file
        self.downloaded = 0  # is increased until it == length of piece
        self.pieceBuffer = None  # buffer for after its completed
        self.pendingRequests = {}  # key = offset value = timestamp keeps track of the offsets we have asked for
        self.torrentLength = torrentLength  # length listed in torrent file
        self.torrentPath = torrentPath
        self.fileDesc = fileDesc  # file to write to

        # endgame mode stuff
        self.endgame_mode = False
        self.endgame_mode_offsets = set(range(0, self.length, BLOCK_SIZE))

    # gets the next offset and length to ask the peer for a specified client this is on the assumtion that we will always ask for 16kb incriments which is standard
    # return a tuple (offset to request, length to request)
    def get_next_request(self):
        if self.complete:
            logger.debug("Request for a piece already complete.")
            return (None, None)
        if self.length < BLOCK_SIZE:  # if last piece is smaller than the block size
            if 0 not in self.blocks:
                self.pendingRequests[0] = time.time()
                logger.debug(f"Last piece is smaller than block, returning: 0 {self.length}")
                return (0, self.length)
            logger.debug("Last piece is smaller than block, returning: None None")
            return (None, None)

        for offset in range(0, self.length, BLOCK_SIZE):
            if offset not in self.blocks:  # checks whats the next request I have yet to recive
                if self._check_if_already_asked(offset):  # checks last request time
                    lastLength = self.length - offset
                    lengthToReturn = BLOCK_SIZE
                    if lastLength < BLOCK_SIZE:
                        lengthToReturn = lastLength
                    # add to pending requests or update time
                    self.pendingRequests[offset] = time.time()
                    logger.debug(f"Return value: {offset} {lengthToReturn}")
                    return (offset, lengthToReturn)
        
        # in endgame mode we ignore already asked limitations
        if self.endgame_mode:
            # reset set if empty with unfulfilled blocks
            if not self.endgame_mode_offsets:
                self.endgame_mode_offsets = set(range(0, self.length, BLOCK_SIZE)) - set(self.blocks.keys())

            offset = self.endgame_mode_offsets.pop()
            lastLength = self.length - offset
            lengthToReturn = BLOCK_SIZE
            if lastLength < BLOCK_SIZE:
                lengthToReturn = lastLength
            # add to pending requests or update time
            self.pendingRequests[offset] = time.time()
            logger.debug(f"Return value: {offset} {lengthToReturn}")
            return (offset, lengthToReturn)

        logger.debug("All requests for this piece are currently allocated to peers.")
        return (None, None)

    # checks if its been to long since it requested this block if so needs to re request it (helper function)
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
            return False

    # adds block to block data-structure
    # returns -1 if invalid hash (need to restart), 1 if added block successfully but not complete yet, 0 if added block and complete and done
    def add_block(self, offset, data):
        # if we already have the block return -2
        if offset in self.blocks:
            return -2
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
                logger.debug("Download done but invalid hash")
                return -1
            self._write_to_disk()
            logger.debug("Download done and valid")
            return 0
        logger.debug("Download not done")
        return 1

    # Returns the percent of how close it is to downloading out of 100
    def get_download_percent(self):
        return (self.downloaded / self.length) * 100

    # gets the data in bytes that a peer requests from disk
    def get_data_from_file(self, offset, blockLength):
        logger.debug("Attempting get_data_from_file()")
        try:

            self.fileDesc.seek((self.index * self.default_piece_length) + offset)
            data = self.fileDesc.read(blockLength)
            logger.debug("get_data_from_file retunred data")
            return data
        except Exception as e:
            print("Error reading from disk: " + str(e))
            logger.debug("Error reading from disk")
            return 0

    def set_complete_from_prev_download(self):
        """
        sets a piece to complete. This may be used to set a piece to complete based on a previous download
        """
        self.downloaded = self.length
        self.complete = True

    # forms complete buffer with data in block datastructure (helper fucntion)
    def _form_buffer(self):
        logger.debug("Attempting form_buffer")
        self.pieceBuffer = bytearray(self.length)
        for offset, block in self.blocks.items():
            self.pieceBuffer[offset : offset + block.get_length()] = block.get_data()
        self.blocks = {}

    # checks if the completed block matches the hash, pulls from memory (helper fucntion)
    def _is_valid(self):
        return hashlib.sha1(self.pieceBuffer).digest() == self.hash

    # writes offset of piece to file from recived response from peer
    def _write_to_disk(self):
        logger.debug("Attempting write_to_disk")
        try:

            self.fileDesc.seek(self.index * self.default_piece_length)
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
