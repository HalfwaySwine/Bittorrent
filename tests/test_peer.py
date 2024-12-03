# to run this i ran python tests/test_peer.py in final-project folder
# i wanted to run it separate from all the other test suite
# importing sys
import sys

sys.path.insert(0, '.')
from torrentula.core.peer import Peer
from torrentula.core.piece import Piece
from torrentula.utils.helpers import configure_logging
import hashlib
import socket
import select


PIECE_LENGTH = 262144
BLOCK_SIZE = 16 * 1024    # 16 KB block size
HASH = hashlib.sha1(
    (b"test_piece_data" * ((PIECE_LENGTH // len("test_piece_data")) + 1))[:PIECE_LENGTH]
).digest()
TORRENT_PATH = "test_piece.torrent"  # Test file path
ADD_PATH = "thisistest.part"
piece = Piece(0, PIECE_LENGTH, HASH, PIECE_LENGTH, ADD_PATH)


configure_logging()
# apparently this guy is a seeder that's always running or smth
peer = Peer("72.235.13.154", 6881, b'\xf3\x1bC\xc3\xa4\x1e\xd3\xf3\xf3\xa4\xd7\x83\x1e~\x9d^\x94ED9', b'12345678901234567890', 2516, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
peer.connect()
peer.handshake()
peer.receive_messages()
print(peer.received_handshake)
# send a bitfield of all 0s
peer.send_bitfield(bytes(315))
peer.receive_messages()
print(peer.received_handshake)
peer.send_interested()

# look in wireshark to see if packet is as intended
i = 0
while True:
    rdy, _, _ = select.select([peer.socket], [], [], 0)
    
    if rdy:
        print(rdy)
        peer.receive_messages()
    if peer.peer_choking == False and i < 1:
        offset, length = piece.get_next_request()
        peer.send_request(piece, offset, length)
        i += 1


