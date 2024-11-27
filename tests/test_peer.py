# importing sys
import sys

sys.path.insert(0, '.')
from torrentula.core.peer import Peer
import socket

peer = Peer("72.235.13.154", 6881, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
peer.connect()
peer.handshake(b'\xf3\x1bC\xc3\xa4\x1e\xd3\xf3\xf3\xa4\xd7\x83\x1e~\x9d^\x94ED9', b'12345678901234567890')

# look in wireshark to see if packet is as intended
i = 0
while True:
    i += 1
