from datetime import datetime, timedelta
from enum import Enum
from ..config import PEER_INACTIVITY_TIMEOUT_SECS
from ..utils.helpers import logger
import socket
import struct

class MessageType(Enum):
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOT_INTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7
    CANCEL = 8

class Handshake(Enum):
    # didn't receive handshake
    HANDSHAKE_NOT_RECVD = 0
    # means received handshake and can still receive bitmap
    CAN_RECV_BITFIELD = 1
    # means received handshake and can't receive bitmap
    HANDSHAKE_RECVD = 2



class Peer:
    """
    Represents a peer Bittorrent client in the same swarm.
    """

    def __init__(self, ip_address, port, info_hash, peer_id, socket=None, v4=True):
        """
        Socket argument is provided when the client accepted this connection from a peer rather than initiaiting it.
        """
        # IPv4 connections addr is a tuple: (hostname_or_ip_addr, port)
        # IPv6 connections addr is a tuple: (hostname_or_ip, port, flowinfo, scopeid)
        if v4:
            self.addr = (ip_address, port)
        else :
            self.addr = (ip_address, port, 0, 0)

        self.socket = socket  # Value is None when this peer is disconnected.
        self.bitfield = None # Populated when first bitfield is received and kept up-to-date as peer sends updates.

        # Connections start out choked and not interested.
        self.am_interested = False
        self.am_choking = True
        self.peer_interested = False
        self.peer_choking = True

        # Track statistics *per epoch* to inform strategic decision-making.
        self.bytes_received = 0
        self.bytes_sent = 0

        self.active_requests = [] # List of pieces that we have requested from the peer but have not completed.
        self.target_piece = None # Piece from peer we are currently requesting.
        self.last_received = None # Time of last message received from peer
        self.last_sent = None # Time of last message sent to peer

        self.received_handshake = Handshake.HANDSHAKE_NOT_RECVD # check if we recieved a handshake or not
        self.info_hash = info_hash # we keep an info hash here to send and check when received
        self.peer_id = peer_id # we keep a peer_id here in the case of them receiving 
        self.sent_handshake = False # needed to differentiate if we initiate or they initiate connection
        self.can_send_bitfield = False # client checks and handles sending bitfields

    def connect(self):
        """ 
        Should throw an error on fail.
        """
        self.socket.connect(self.addr)


    def disconnect(self):
        """
        Closes socket and sets socket to None.
        """
        self.socket.close()
        self.socket = None

    def handshake(self):
        """
        Send handshake message.
        """
        pstr = "BitTorrent protocol"
        pstrlen = len(pstr)
        # ! = big endian, B = unsigned char, then string s, then 8 padding 0s, then 2 20 length strings
        # I don't expect to use these 8 padding bytes
        msg = struct.pack(f"!B{pstrlen}s8x20s20s", pstrlen, pstr.encode('utf-8'), self.info_hash, self.peer_id)
        self.send_msg(msg)
        self.sent_handshake = True

    def upload(self, block):
        pass

    def request(self, piece):
        pass

    def download(self, block):
        pass

    def receive_messages(self):
        """
        Assuming we do the select outside of receive_messages - just handle messages here
        if we haven't received a handshake we expect a handshake before anything else
        If we receive something wrong we disconnect
        Returns -1 on error, 1 on correct handling

        This code does not really handle blocking problems on recv, could cause issues in the future
        we also don't really handle unexpected recvs, could cause some erroring that may need to be caught
        """
        if self.received_handshake == Handshake.HANDSHAKE_NOT_RECVD:
            pstrlen = int.from_bytes(self.socket.recv(1))
            bytes = self.socket.recv(pstrlen + 48)
            pstr, padding, info_hash, peer_id = struct.unpack(f"!{pstrlen}s8s20s20s", bytes)
            logger.debug(f"received {pstr}, {padding}, {info_hash}, {peer_id}")
            # may want to do smth with pstr, padding, and peer_id 
            # but rn I only care about checking info_hash
            if info_hash != self.info_hash:
                self.disconnect()
                return -1
            self.received_handshake = Handshake.CAN_RECV_BITFIELD
            # if the connection was an incoming connection we still need to send our side of the handshake
            if not self.sent_handshake:
                self.handshake()
            # when we return we expect client object to check this value and send bitfield if needed
            self.can_send_bitfield = True
        else:
            # once we receive any other message other than a handshake we can't receive a bitmap anymore
            self.received_handshake = Handshake.HANDSHAKE_RECVD
            msg_len = int.from_bytes(self.socket.recv(4), "big")
            logger.debug(f"msg len: {msg_len}")
            # differentiating from keepalive, we don't have to do anything if it's a keepalive
            if (msg_len > 0):
                msg_type = int.from_bytes(self.socket.recv(1), "big")
                logger.debug(f"msg type: {msg_type}")
        self.last_received = datetime.now()
        return 1

    def send_interested(self):
        pass

    def send_have(self, index: int):
        pass

    def send_event(self, type):
        pass

    def send_bitfield(self, bitfield):
        """
        Send the bitfield that we have
        """
        bitfield_length = len(bitfield)
        msg_length = len(bitfield) + 1 
        msg = struct.pack(f"!iB{bitfield_length}s", msg_length, MessageType.BITFIELD.value, bitfield)
        self.send_msg(msg)

    def send_msg(self, msg):
        """
        Send msg and update last sent time
        """
        # once we send any other message we can't send a bitfield anymore
        self.can_send_bitfield = False
        logger.debug("sending:")
        logger.debug(msg)
        self.last_sent = datetime.now()
        self.socket.sendall(msg)

    def choke(self):
        """
        Sends a choke message to peer and stores that state if peer is currently unchoked. Otherwise, does nothing.
        """
        if self.am_choking == True:
            return

    def unchoke(self):
        if self.am_choking == False:
            return

    def send_keepalive(self):
        if self.socket is None or datetime.now() - self.last_sent <= timedelta(seconds=PEER_INACTIVITY_TIMEOUT_SECS):
            return  # Keepalive is not necessary
        else:
            raise NotImplementedError("This function has not been implemented yet.")

    def establish_new_epoch(self):
        self.bytes_downloaded = 0
        self.bytes_uploaded = 0
