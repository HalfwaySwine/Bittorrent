from datetime import datetime, timedelta
from enum import Enum
from ..config import PEER_INACTIVITY_TIMEOUT_SECS


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

    def __init__(self, ip_address, port, socket=None):
        """
        Socket argument is provided when the client accepted this connection from a peer rather than initiaiting it.
        """
        # For IPv4 connections addr is a tuple: (hostname_or_ip_addr, port)
        # This may cause issues withwhere IPv6 connections addr is a tuple: (hostname_or_ip, port, flowinfo, scopeid)
        self.addr = (ip_address, port)
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

    def handshake(self):
        pass

    def connect(self):
        pass

    def disconnect(self):
        """
        Closes socket and sets socket to None.
        """
        pass

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
        if datetime.now() - self.last_sent <= timedelta(seconds=PEER_INACTIVITY_TIMEOUT_SECS):
            return  # Keepalive is not necessary
        else:
            raise NotImplementedError("This function has not been implemented yet.")

    def establish_new_epoch(self):
        self.bytes_downloaded = 0
        self.bytes_uploaded = 0
        # self.choke()
