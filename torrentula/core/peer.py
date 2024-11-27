from datetime import datetime, timedelta
from enum import Enum
from ..config import PEER_INACTIVITY_TIMEOUT_SECS
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


class Peer:
    """
    Represents a peer Bittorrent client in the same swarm.
    """

    def __init__(self, ip_address, port, socket=None, v4=True):
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

    def handshake(self, peer_id, info_hash):
        """
        Send handshake message.
        """
        pstr = "Torrentula"
        pstrlen = len(pstr)
        info_hash = info_hash
        peer_id = peer_id
        # ! = big endian, B = unsigned char, then string s, then 8 padding 0s, then 2 20 length strings
        msg = struct.pack(f"!B{pstrlen}s8x20s20s", pstrlen, pstr, info_hash, peer_id)
        self.socket.sendall(msg)
        
        

    def upload(self, block):
        pass

    def request(self, piece):
        pass

    def download(self, block):
        pass

    def receive_messages(self):
        pass

    def poll(self):
        pass

    def send_interested(self):
        pass

    def send_have(self, index: int):
        pass

    def send_event(self, type):
        pass

    def send_msg(self):
        pass

    def choke(self):
        """
        Sends a choke message to peer and stores that state if peer is currently unchoked. Otherwise, does nothing.
        """
        pass

    def unchoke(self):
        pass

    def send_keepalive(self):
        if self.socket is None or datetime.now() - self.last_sent <= timedelta(seconds=PEER_INACTIVITY_TIMEOUT_SECS):
            return  # Keepalive is not necessary
        else:
            raise NotImplementedError("This function has not been implemented yet.")

    def establish_new_epoch(self):
        self.bytes_downloaded = 0
        self.bytes_uploaded = 0
