from ..utils.helpers import logger
import bencodepy


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
        self.tracker
        self.file
        self.sock
        open_torrent_file()  # Extract
        load_progress_from_disk()

    def download_torrent(torrent, destination="."):
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

    def open_socket():
        pass

    def add_peers():
        pass

    def load_file():
        pass

    def upload_piece():
        pass

    def request_piece():
        pass

    def bytes_left() -> int:
        """
        Returns the number of bytes this client still has to download.
        """
        pass

    def display_swarm():
        pass

    def display_progress():
        pass

    def shutdown():
        """
        Saves bitmap of pieces to disk and frees client resources.
        """
        pass
