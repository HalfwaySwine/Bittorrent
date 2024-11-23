from datetime import datetime, timedelta
from enum import Enum
from ..config import PEER_INACTIVITY_TIMEOUT


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
        self.bitfield
        self.am_interested
        self.am_choking
        self.peer_interested
        self.peer_choking
        self.bytes_received = 0  # To inform strategic decision-making
        self.bytes_sent = 0

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

    def read_message(self):
        pass

    def poll(self):
        pass

    def send_interested(self):
        pass

    def send_event(self, type):
        pass

    def send_msg(self):
        pass

    def choke(self):
        pass

    def unchoke(self):
        pass

    def send_keepalive(self):
        if datetime.now() - self.timestamp <= timedelta(seconds=PEER_INACTIVITY_TIMEOUT):
            return # Keepalive is not necessary
        else:
            raise NotImplementedError("This function has not been implemented yet.")