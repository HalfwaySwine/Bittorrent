from ..utils.helpers import logger
from .tracker import Tracker
from .file import File
import bencoder
import sys
import signal


class Client:
    """
    Enables leeching and seeding a torrent by contacting torrent tracker, managing connections to peers, and exchanging data.
    """

    def __init__(self, torrent_file, port: int = 6881):
        """ """
        self.bytes_uploaded: int = 0  # Total amount uploaded since client sent 'started' event to tracker
        self.bytes_downloaded: int = 0  # Total amount downloaded since client sent 'started' event to tracker
        self.peers = None  # Connected clients within same swarm
        self.peer_id = Client.generate_id()  # Randomly generate 20 character ASCII string
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
        self.tracker = Tracker(announce_url)
        # Extracts file metadata from torrent file and sets up the File class.
        self.filename = torrent_data[b"info"][b"name"]
        self.length = torrent_data[b"info"][b"length"]
        hashes = Client.split_hashes(torrent_data[b"info"][b"pieces"])
        piece_length = torrent_data[b"info"][b"piece length"]
        assert len(hashes) * piece_length == self.length, "Error: Torrent length, piece length and hashes do not match!"
        self.file = File(self.filename, self.length, piece_length, hashes)

    @classmethod
    def generate_id(cls):
        pass

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
        raise NotImplementedError("This function has not been implemented yet.")
        """
        self.tracker.connect() # TODO Receive and store response somewhere
        self.sock = self.open_socket()
        while(self.file.get_missing_pieces() is not None):
            self.add_peers() # And drop dead connections
            self.strategy = Strategy()
            self.strategy.select_pieces()
            self.send_requests()
            self.receive_messages()
        """
        return False if self.file.get_missing_pieces() else True

    def open_socket(self):
        pass

    def close_socket(self):
        pass

    def add_peers(self):
        pass

    def load_file(self):
        pass

    def upload_piece(self):
        pass

    def request_piece(self):
        pass

    def bytes_left(self) -> int:
        """
        Returns the number of bytes this client still has left to download.
        """
        pass

    def display_swarm(self):
        """
        For debugging purposes.
        """
        pass

    def display_progress(self):
        """
        Displays progress report to user.
        """
        pass

    def shutdown(self):
        """
        Saves bitmap of pieces to disk and frees client resources.
        """
        self.close_socket()
        self.file.write_bitfield_to_disk()
        pass
