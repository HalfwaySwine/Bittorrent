from ..utils.helpers import logger
from tracker import Tracker
from file import File
import bencoder
import sys


class Client:
    """
    Enables leeching and seeding a torrent by contacting torrent tracker, managing connections to peers, and exchanging data.
    """

    def __init__(self, torrent_file, port: int = 6881):
        """ """
        self.bytes_uploaded: int  # Total amount uploaded since client sent 'started' event to tracker
        self.bytes_downloaded: int  # Total amount downloaded since client sent 'started' event to tracker
        self.peers  # Connected clients within same swarm
        self.peer_id
        self.metainfo
        self.file
        load_torrent_file(torrent_file)  # Extract
        load_progress_from_disk()

    def load_torrent_file(self, torrent_file):
        try:
            with open(torrent_file, "rb") as f:
                torrent_data = bencoder.bdecode(f.read())
        except Exception as e:
            sys.exit(1)

        # gets the announce url from the tracker file and sets the tracker class
        announce_url = torrent_data[b"announce"].decode()
        # torrent_data[]
        self.length = torrent_data[b"info"][b"length"]
        self.filename = torrent_data[b"info"][b"name"]
        length = torrent_data[b"info"][b"length"]
        self.file = File(self.filename, length)
        self.piece_length = torrent_data[b"info"][b"piece length"]
        self.hashes = split_hashes(torrent_data[b"info"][b"pieces"])
        self.tracker = Tracker(announce_url)

    def split_hashes(bytes):
        # TODO Test this helper function
        if len(bytes) % 20 != 0:
            print("Error: Torrent file hashes are invalid!")
            sys.exit(1)
        hash_length = 20
        hashes = []
        for i in range(0, len(bytes), hash_length):  # Iterates 0 to len - 1 in steps of 20
            hash = bytes[i : i + hash_length]
            hashes.append(hash)
            # print(f"Hash {i} to {i + hash_length}: {hash}")
        return hashes

    def download_torrent(self, torrent, destination="."):
        """
        Downloads the files from a .torrent file to a specified directory.

        This function contacts the torrent tracker, joins the torrent swarm, and attempts to download the associated file to the specified location.

        Parameters:
        torrent (str): The relative path to a .torrent file (from the current directory).
        destination (str): The relative path of the destination directory where the downloaded file will be saved.

        Returns:
        bool: True if the torrent download was successful, False if an error occurred.
        """
        self.tracker.connect()
        self.sock = open_socket()
        raise NotImplementedError("This function has not been implemented yet.")

    def open_socket(self):
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
        Returns the number of bytes this client still has to download.
        """
        pass

    def display_swarm(self):
        pass

    def display_progress(self):
        pass

    def shutdown(self):
        """
        Saves bitmap of pieces to disk and frees client resources.
        """
        pass
