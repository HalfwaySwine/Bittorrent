# to run this i ran python tests/test_peer.py in final-project folder
# i wanted to run it separate from all the other test suite
# importing sys
import sys

sys.path.insert(0, '.')
from torrentula.core.peer import Peer
from torrentula.utils.helpers import configure_logging
import socket

configure_logging()
peer = Peer("72.235.13.154", 6881, b'\xf3\x1bC\xc3\xa4\x1e\xd3\xf3\xf3\xa4\xd7\x83\x1e~\x9d^\x94ED9', b'12345678901234567890', socket.socket(socket.AF_INET, socket.SOCK_STREAM))
peer.connect()
peer.handshake()
peer.receive_messages()
print(peer.received_handshake)
peer.receive_messages()
print(peer.received_handshake)


# look in wireshark to see if packet is as intended
i = 0
while True:
    i += 1
