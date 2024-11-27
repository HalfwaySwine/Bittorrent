
# importing sys
import sys

sys.path.insert(0, '..')
from torrentula.core.peer import Peer
import socket

peer = Peer("47.54.12.87", "52000", socket.socket(socket.AF_INET, socket.SOCK_STREAM))
peer.connect()
peer.handshake("1234567890123456789012345678901234567890", "1234567890123456789012345678901234567890")

