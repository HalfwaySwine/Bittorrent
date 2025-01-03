# to run this i ran python tests/test_peer.py in final-project folder
# i wanted to run it separate from all the other test suite
# importing sys
import sys

sys.path.insert(0, ".")
from torrentula.core.peer import Peer
from torrentula.core.piece import Piece
from torrentula.utils.helpers import configure_logging
import hashlib
import socket
import select
import time
import argparse

PIECE_LENGTH = 262144
BLOCK_SIZE = 16 * 1024  # 16 KB block size
HASH = hashlib.sha1((b"test_piece_data" * ((PIECE_LENGTH // len("test_piece_data")) + 1))[:PIECE_LENGTH]).digest()
TORRENT_PATH = "test_piece.torrent"  # Test file path
ADD_PATH = "thisistest.part"
piece = Piece(0, PIECE_LENGTH, HASH, PIECE_LENGTH, ADD_PATH, 0)


configure_logging(argparse.Namespace(torr='tests/fixtures/debian-mac.torrent', dest='.', clean=False, verbose=True, debug=True, info=False))
# apparently this guy is a seeder that's always running or smth
peer = Peer("72.235.13.154", 6881, b'\xf3\x1bC\xc3\xa4\x1e\xd3\xf3\xf3\xa4\xd7\x83\x1e~\x9d^\x94ED9', '12345678901234567890', 2516)
# peer = Peer("188.242.229.57", 11096, b'\xf3\x1bC\xc3\xa4\x1e\xd3\xf3\xf3\xa4\xd7\x83\x1e~\x9d^\x94ED9', '12345678901234567890', 2516)
peer.target_piece = piece
peer.connect()
print(peer.socket)
while True:
    _, rdy, _ = select.select([], [peer.socket], [], 0)
    if rdy:
        error = rdy[0].getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        print(error)
        peer.record_tcp_established()
        break
peer.send_handshake()
print("can send bitfield: ", peer.can_send_bitfield)
_, _, _ = select.select([peer.socket], [], [], 5)
peer.receive_messages(piece)
print(peer.received_handshake)
print("can send bitfield: ", peer.can_send_bitfield)
# send a bitfield of all 0s
peer.send_bitfield(bytes(315))
_, _, _ = select.select([peer.socket], [], [], 1)
peer.receive_messages(piece)
print(peer.received_handshake)
print("can send bitfield: ", peer.can_send_bitfield)
peer.send_interested()
peer.send_keepalive()
# peer.send_not_interested()
# peer.unchoke()
# peer.choke()
# peer.send_piece(1, 1, b'21349023849328203859')
# peer.send_cancel(piece, 1, 1)
# look in wireshark to see if packet is as intended
i = 0
while True:
    rdy, _, _ = select.select([peer.socket], [], [], 0)

    if rdy:
        peer.receive_messages(piece)
    if peer.peer_choking == False and i < 4:
        offset, length = piece.get_next_request()
        peer.send_request(piece.index, offset, length)
        i += 1
    rdy = []
