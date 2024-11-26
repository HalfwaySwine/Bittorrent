from ..utils.helpers import logger
from ..config import EPOCH_DURATION_SECS, PEER_ID_LENGTH, MAX_PEER_OUTSTANDING_REQUESTS, MAX_PEERS
from .tracker import Tracker
from .strategy import Strategy
from .file import File
import bencoder
import sys
import signal
import socket
import select
from random import choices
from string import printable
from datetime import datetime, timedelta
import hashlib
from urllib.parse import quote_plus


class Client:
    """
    Enables leeching and seeding a torrent by contacting torrent tracker, managing connections to peers, and exchanging data.
    """

    def __init__(self, torrent_file, destination, port: int = 6881):
        self.bytes_uploaded: int = 0  # Total amount uploaded since client sent 'started' event to tracker
        self.bytes_downloaded: int = 0  # Total amount downloaded since client sent 'started' event to tracker
        self.peers = []  # Connected clients within same swarm
        self.port = port
        self.peer_id = Client.generate_id()
        self.destination = destination
        self.load_torrent_file(torrent_file)
        # Register signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def load_torrent_file(self, torrent_file):
        """
        Decodes and extracts information for a given '.torrent' file.
        """
        try:
            with open(torrent_file, "rb") as f:
                torrent_data = bencoder.bdecode(f.read())
                logger.debug(f"Torrent '{torrent_file}' decoded:")
                logger.debug(torrent_data)
        except Exception as e:
            print(f"Error: Could not decode torrent file '{torrent_file}'!")
            print(e)
            sys.exit(1)

        # Extracts announce url from the torrent file and sets up the Tracker class.
        announce_url = torrent_data[b"announce"].decode()
        self.info_hash = quote_plus(hashlib.sha1(bencoder.bencode(torrent_data[b"info"])).digest())
        self.tracker = Tracker(announce_url, self.peer_id, self.info_hash)
        # Extracts file metadata from torrent file and sets up the File class.
        self.filename = torrent_data[b"info"][b"name"]
        self.length = torrent_data[b"info"][b"length"]
        hashes = Client.split_hashes(torrent_data[b"info"][b"pieces"])
        piece_length = torrent_data[b"info"][b"piece length"]
        assert len(hashes) * piece_length == self.length, "Error: Torrent length, piece length and hashes do not match!"
        self.file = File(self.filename, self.destination, self.length, piece_length, hashes)

    @classmethod
    def generate_id(cls):
        """
        Generate a random string of 20 ASCII printable characters.
        """
        return "".join(choices(printable, k=PEER_ID_LENGTH))

    @classmethod
    def split_hashes(cls, bytes):
        hash_length = 20
        assert (
            len(bytes) % 20 == 0
        ), f"Error: Torrent file hashes ({len(bytes)} bytes) are not a multiple of hash_length ({hash_length})!"
        hashes = []
        for i in range(0, len(bytes), hash_length):  # Iterates 0 to len - 1 in steps of 20
            hash = bytes[i : i + hash_length]
            hashes.append(hash)
        return hashes

    def download_torrent(self, torrent, destination=".") -> bool:
        """
        Downloads the files from a .torrent file to a specified directory.

        This function contacts the torrent tracker, joins the torrent swarm, and attempts to download the associated file to the specified location.

        Parameters:
        torrent (str): The relative path to a .torrent file (from the current directory).
        destination (str): The relative path of the destination directory where the downloaded file will be saved.

        Returns:
        bool: True if the torrent download was successful, False if an error occurred.
        """
        self.peers = self.tracker.join_swarm()
        self.sock = self.open_socket()
        self.strategy = Strategy()
        self.epoch_start_time = datetime.now()
        while not self.file.complete():
            self.accept_peers()
            self.receive_messages()
            completed_pieces = self.file.update_bitfield()
            self.send_haves(completed_pieces)
            self.send_requests()
            self.send_keepalives()
            if datetime.now() - self.epoch_start_time >= timedelta(seconds=EPOCH_DURATION_SECS):
                self.establish_new_epoch()
        return True if self.file.complete() else False

    def open_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = "0.0.0.0" # Listen on all interfaces
        self.sock.connect((host, self.port))
        self.sock.listen(MAX_PEERS)
        print(f"Listening for connections on {host}:{self.port}...")


    def establish_new_epoch(self):
        for peer in self.peers:
            peer.establish_new_epoch()
        self.epoch_start_time = datetime.now()

    def accept_peers(self):
        timeout = 0
        rdy, _, _ = select.select([self.sock], [], [], timeout)
        connected_peers = len(peer for peer in self.peers if peer.socket is not None)
        while rdy and connected_peers < MAX_PEERS: # Accept up to the maximum number of peers
            sock, addr = self.sock.accept()
            connected_peers += 1
            print(f"Connection established with {addr}")
            rdy, _, _ = select.select([self.sock], [], [], timeout)

    def close_socket(self):
        self.sock.close()

    def add_peers(self):
        additional_peers = self.strategy.determine_additional_peers(self.file, self.peers)
        if additional_peers > 0:
            # Check if we know of any peers that aren't connected
            not_connected = [peer for peer in self.peers if peer.socket is None]
            for peer in not_connected:
                peer.connect()
            self.tracker.request_peers():

    def send_haves(self, completed_pieces):
        """
        Sends messages to peers inform them that we have acquired new pieces.
        """
        self.strategy.send_haves(completed_pieces, self.file.bitfield, self.peers)

    def send_keepalives(self):
        for peer in self.peers:
            peer.send_keepalive()

    def send_requests(self):
        self.strategy.assign_pieces()
        available_peers = [peer for peer in self.peers if peer.am_unchoked and peer.am_interested]
        for peer in available_peers:
            num_requests = MAX_PEER_OUTSTANDING_REQUESTS - len(peer.active_requests)
            for req in range(num_requests):
                offset, length = self.pieces[peer.target_piece].get_next_request()
                if offset is None or length is None:  # Target piece is complete
                    break
                peer.send_request(peer.target_piece, offset, length)

    def receive_messages(self):
        rdy_peers = select.select([peer.socket for peer in self.peers if peer.sock is not None], [], [],  0)
        for peer in rdy_peers:
            peer.receive_messages()
        check_liveness = [peer for peer in self.peers if peer not in rdy_peers and peer.sock is not None]
        for peer in check_liveness:
            peer.check_timeout()

    def bytes_left(self) -> int:
        """
        Returns the number of bytes this client still has left to download.
        """
        return sum(self.pieces[piece_index].length for piece_index in self.file.get_missing_pieces())

    def display_peers(self):
        """
        For debugging purposes.
        """
        print("=== Peers ===")
        for index, peer in enumerate(self.peers):
            print(index, ": ", peer)

    def __str__(self):
        """
        Displays progress report to user.
        """
        print("=== Client ===")
        # print(f"Torrent: ", {self.filename}")
        # print(f"Destination: ", {self.destination}")
        # print(f"Peer Id: ", {self.peer_id}")

        # Dynamic approach
        instance_variables = {
            key: value for key, value in self.__dict__.items() if not callable(value) and not key.startswith("__")
        }
        longest_name = max(map(len, instance_variables.keys()))
        for name, value in instance_variables.items():
            print(f"{name:<{longest_name}} = {value}")

        self.display_peers()
        print(self.file)

    def shutdown(self):
        """
        Saves bitmap of pieces to disk and frees client resources.
        """
        self.close_socket()
        self.file.write_bitfield_to_disk()
        pass
