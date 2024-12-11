from ..utils.helpers import logger, Status
from ..config import (
    EPOCH_DURATION_SECS,
    PEER_ID_LENGTH,
    MAX_PEER_OUTSTANDING_REQUESTS,
    MAX_CONNECTED_PEERS,
    IN_PROGRESS_FILENAME_SUFFIX,
    BITTORRENT_PORT,
    MAX_CONNECTION_ATTEMPTS,
)
from .tracker import Tracker
from .strategy import Strategy, RarestFirstStrategy, PropShareStrategy
from .file import File
from .piece import Piece
import bencoder
import traceback
import os
import sys
import signal
import time
import socket
import select
from random import choices
from string import printable
from datetime import datetime, timedelta
import hashlib
from urllib.parse import quote_plus
from pathlib import Path
from .peer import Peer, Handshake
import errno


class Client:
    """
    Enables leeching and seeding a torrent by contacting torrent tracker, managing connections to peers, and exchanging data.
    """

    def __init__(self, torrent_file: str, destination: str = ".", strategy = Strategy, port: int = BITTORRENT_PORT, pref:str ="http"):
        self.start_time = time.monotonic()
        self.bytes_uploaded: int = 0  # Total amount uploaded since client sent 'started' event to tracker
        self.bytes_downloaded: int = 0  # Total amount downloaded since client sent 'started' event to tracker
        self.download_speed = 0  # Measured per epoch in KB/s
        self.upload_speed = 0  # Measured per epoch in KB/s
        self.peers = []  # Connected clients within same swarm
        self.port = port
        self.peer_id = Client.generate_id()
        self.destination = destination
        self.tracker_pref = pref #replace with command line arg later
        self.load_torrent_file(torrent_file)
        self.strategy = strategy()
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
        except Exception as e:
            print(f"Error: Could not decode torrent file '{torrent_file}'!")
            print(e)
            sys.exit(1)
        # Extracts announce url from the torrent file and sets up the Tracker class.
        announce_url = torrent_data[b"announce"].decode()
        #check announce-list for preference, if it doesn't exist, just use default
        if self.tracker_pref not in  announce_url:
            if b"announce-list" in torrent_data:
                tracker_list = torrent_data[b"announce-list"]
                for i in range(0, len(tracker_list)):
                    if self.tracker_pref in tracker_list[i][0].decode():
                        announce_url = tracker_list[i][0].decode()
        self.info_hash = hashlib.sha1(bencoder.bencode(torrent_data[b"info"])).digest()
        hashes = Client.split_hashes(torrent_data[b"info"][b"pieces"])
        self.tracker = Tracker(announce_url, self.peer_id, self.info_hash, len(hashes))
        # Extracts file metadata from torrent file and sets up the File class.
        self.filename: str = torrent_data[b"info"][b"name"].decode("utf-8")
        self.length = int(torrent_data[b"info"][b"length"])
        piece_length = int(torrent_data[b"info"][b"piece length"])
        # Verify integrity of torrent file size, hashes, and pieces.
        last_piece_size = self.length - (piece_length * (len(hashes) - 1))  # Last piece can be smaller.
        assert last_piece_size <= piece_length, "Error: Last piece is larger than piece size."
        calc_size_total = ((len(hashes) - 1) * piece_length) + last_piece_size
        assert calc_size_total == self.length, "Error: Torrent length, piece length and hashes do not match!"
        self.file = File(self.filename, self.destination, self.length, piece_length, hashes)
        # Initialize variables for upload/download tracking statistics.
        # self.last_bytes_downloaded = self.file.bytes_downloaded()
        # self.last_bytes_uploaded = self.file.bytes_uploaded()
        # self.last_interval = time.monotonic()

    @classmethod
    def generate_id(cls):
        """
        Generate a random string of 20 ASCII printable characters.
        """
        return "".join(choices(printable, k=PEER_ID_LENGTH))

    @classmethod
    def split_hashes(cls, bytes):
        hash_length = 20
        assert len(bytes) % 20 == 0, f"Error: Torrent file hashes ({len(bytes)} bytes) are not a multiple of hash_length ({hash_length})!"
        hashes = []
        for i in range(0, len(bytes), hash_length):  # Iterates [0, len - 1] in steps of 20.
            hash = bytes[i : i + hash_length]
            hashes.append(hash)
        return hashes

    def download_torrent(self) -> bool:
        """
        Downloads the files from a .torrent file to a specified directory.

        This function contacts the torrent tracker, joins the torrent swarm, and attempts to download the associated file to the specified location.

        Parameters:
        torrent (str): The relative path to a .torrent file (from the current directory).
        destination (str): The relative path of the destination directory where the downloaded file will be saved.

        Returns:
        bool: True if the torrent download was successful, False if an error occurred.
        """
        self.open_socket()
        self.peers = self.tracker.join_swarm(self.file.bytes_left(), self.port)
        self.epoch_start_time = datetime.now()
        self.repaint_progress()
        track_while_loop_delta = datetime.now()
        # Main event loop
        while not self.file.complete():

            # # only uncomment if you need it, will flood log
            # while_loop_delta_2 = datetime.now()
            # logger.error(f"Time of while loop: {while_loop_delta_2 - track_while_loop_delta}")
            # track_while_loop_delta = while_loop_delta_2

            self.add_peers()
            self.accept_peers()
            self.receive_messages()
            self.cleanup_peers()
            completed_pieces = self.file.update_bitfield()
            if completed_pieces:
                self.repaint_progress()
                self.send_uninterested()
            self.send_haves(completed_pieces)
            self.send_requests()
            #self.send_requests_reponses_back()
            self.send_keepalives()
            self.send_interested()
            if datetime.now() - self.epoch_start_time >= timedelta(seconds=EPOCH_DURATION_SECS):
                self.establish_new_epoch()
        # Clean up resources
        self.cleanup()

        if self.file.complete():  # If file is complete, rename file to real name and delete bitfield.
            path = Path(self.destination)
            self.file.rename(path / self.filename)
            self.file.remove_bitfield_from_disk()
            print("\nTorrent download complete!")
            return True
        return False

    def open_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        host = "0.0.0.0"  # Listen on all interfaces
        self.sock.bind((host, self.port))
        self.sock.listen(MAX_CONNECTED_PEERS)
        logger.info(f"Listening for connections on {host}:{self.port}...")

    def establish_new_epoch(self):
        total_downloaded = 0
        total_uploaded = 0
        for peer in self.peers:
            downloaded, uploaded = peer.establish_new_epoch()
            total_downloaded += downloaded
            total_uploaded += uploaded
        self.download_speed = total_downloaded / 10_485_760  # Convert bytes to MB and average over 10 seconds.
        self.uploaded_speed = total_uploaded / 10_485_760
        self.execute_choke_transition()
        self.epoch_start_time = datetime.now()
        logger.debug("Established new epoch.")

    def execute_choke_transition(self):
        currently_unchoked = [peer for peer in self.peers if not peer.am_choking]
        to_unchoke = self.strategy.choose_peers(self.peers)
        for peer in to_unchoke:
            peer.unchoke()
        choke = [peer for peer in currently_unchoked if peer not in to_unchoke]
        for peer in choke:
            peer.choke()

    def accept_peers(self):
        timeout = 0
        assert self.sock.fileno() > 0
        rdy, _, _ = select.select([self.sock], [], [], timeout)
        connected_peers: int = len([peer for peer in self.peers if peer.tcp_established])
        while rdy and connected_peers < MAX_CONNECTED_PEERS:  # Accept up to the maximum number of peers
            sock, addr = self.sock.accept()
            new_peer = Peer(addr[0], addr[1], self.info_hash, self.peer_id, len(self.file.bitfield), sock)
            self.peers.append(new_peer)
            connected_peers += 1
            logger.info(f"Connection established with peer: {addr}")
            rdy, _, _ = select.select([self.sock], [], [], timeout)  # Poll again to check for more peers

    def close_socket(self):
        if self.sock:
            self.sock.close()

    def add_peers(self):
        # Start establishment of connections to peers
        additional_peers = self.strategy.determine_additional_peers(self.file, self.connected_peers())
        if additional_peers > 0:
            # Check if we know of any peers that aren't connected
            not_connected = [peer for peer in self.peers if peer.socket is None]
            if not_connected:
                logger.debug(f"Attempting to connect to {len(not_connected)} additional peers (has space for {additional_peers} additional peers)...")
                for peer in not_connected:
                    if peer.connect() == Status.SUCCESS:
                        assert False, "Unexpected instantaneous connection success. Review expected behavior of non-blocking sockets and alter code."

            # self.tracker.request_peers(): TODO

        # Check for peers that have accepted the connection
        connections_in_progress: list[Peer] = [peer for peer in self.peers if peer.socket is not None and not peer.tcp_established]
        pending_peers = {peer.socket: peer for peer in connections_in_progress}
        _, writable, _ = select.select([], pending_peers.keys(), [], 0)
        for sock in writable:
            peer = pending_peers[sock]
            error = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if error != 0:
                logger.info(f"Connection to peer at {peer.addr} failed with error code {error}: {errno.errorcode.get(error, 'Unknown error')}")
                peer.disconnect()
                continue
            peer.record_tcp_established()
            if peer.send_handshake() == Status.SUCCESS:
                logger.info(f"In-progress TCP connection completed to peer at {peer.addr}")
        logger.debug(self.display_peers())

    def send_haves(self, completed_pieces):
        """
        Sends messages to peers inform them that we have acquired new pieces.
        """
        # note: shouldn't we send new pieces only once to each peer?
        # maybe we should keep track of pieces we already have notified peers of.
        self.strategy.send_haves(completed_pieces, self.file.bitfield, self.connected_peers())

    def connected_peers(self):
        return [peer for peer in self.peers if peer.tcp_established and peer.received_handshake == Handshake.HANDSHAKE_RECVD]

    def send_requests_reponses_back(self):
        """
        Sends data to pieces who are unchoked and have requested data
        """
        for peer in self.peers:
            if peer.am_choking == False: #checks if choking
                if len(peer.incoming_requests) > 0:
                    data = peer.incoming_requests[0]
                    dataToSend = self.file.get_data_from_piece(data[1], data[2], data[0])
                    if dataToSend == 0: #issue getting data
                        continue
                    flag = peer.send_piece(data[0], data[1], dataToSend)
                    if flag == Status.SUCCESS:
                        self.file.totalUploaded += data[2] #update total uploaded
                        logger.debug(f"Data send back to {peer.addr} successfully")
                    else: #failed
                        logger.debug(f"Data failed to send back to {peer.addr}")

    def send_keepalives(self):
        for peer in self.peers:
            peer.send_keepalive_if_needed()

    def send_requests(self):
        connected = self.connected_peers()
        self.strategy.assign_pieces(self.file.missing_pieces(), connected)
        available_peers = [peer for peer in connected if not peer.peer_choking and peer.am_interested and peer.target_piece is not None]
        for peer in available_peers:
            # Reset target_piece if completed already.
            target_piece_object: Piece = self.file.pieces[peer.target_piece]
            if target_piece_object.complete:
                peer.target_piece = None
            else:
                num_requests = MAX_PEER_OUTSTANDING_REQUESTS - len(peer.incoming_requests)
                for req in range(num_requests):
                    offset, length = target_piece_object.get_next_request()
                    if offset is None or length is None:  # Target piece has allocated all block requests.
                        break
                    peer.send_request(peer.target_piece, offset, length)

    def send_interested(self):
        uninterested = [peer for peer in self.connected_peers() if not peer.am_interested]
        for peer in uninterested:
            for index in self.file.missing_pieces():
                if peer.bitfield[index] == 1:
                    peer.send_interested()
                    break

    def send_uninterested(self):
        interested = [peer for peer in self.connected_peers() if peer.am_interested]
        for peer in interested:
            have_missing_piece = False
            for index in self.file.missing_pieces():
                if peer.bitfield[index] == 1:
                    have_missing_piece = True
                    break
            # Peer has no missing pieces.
            if not have_missing_piece:
                peer.send_uninterested()

    def receive_messages(self):
        sockets_to_peers = {peer.socket: peer for peer in self.peers if peer.tcp_established}
        ready_peers, _, _ = select.select(sockets_to_peers.keys(), [], [], 0)
        logger.debug(f"There are {len(ready_peers)} peers with messages to receive")
        for socket in ready_peers:
            target_piece_index = sockets_to_peers[socket].target_piece
            if target_piece_index != None:
                target_piece = self.file.pieces[target_piece_index]
                sockets_to_peers[socket].receive_messages(target_piece)
            else:
                sockets_to_peers[socket].receive_messages(None)

    def cleanup_peers(self):
        check_liveness = [peer for peer in self.peers if peer.tcp_established]
        for peer in check_liveness:
            # Disconnects but does not remove peer from peers list.
            peer.disconnect_if_timeout()
        unreliable = [peer for peer in self.peers if peer.connection_attempts > MAX_CONNECTION_ATTEMPTS]
        for peer in unreliable:
            peer.disconnect()
            logger.error(f"Removing unreliable peer at {peer.addr} after {peer.connection_attempts} connection attempts.")
            self.peers.remove(peer)

    def display_peers(self):
        """
        For debugging purposes.
        """
        output = "=== Peers ===\n"
        for index, peer in enumerate(self.peers):
            output += f"{index}: {peer}\n"
        return output

    def repaint_progress(self):
        # Calculate upload and download speeds
        # secs_since_last_repaint = time.monotonic() - self.last_interval
        # bytes_downloaded_since_last_repaint = self.file.bytes_downloaded() - self.last_bytes_downloaded
        # bytes_uploaded_since_last_repaint = self.file.bytes_uploaded() - self.last_bytes_uploaded
        # Convert bytes to MB and average over seconds since last repaint.
        # self.download_speed = bytes_downloaded_since_last_repaint / 10_485_76 / secs_since_last_repaint
        # self.uploaded_speed = bytes_uploaded_since_last_repaint / 10_485_76 / secs_since_last_repaint

        # Calculate time elapsed
        time_elapsed = time.monotonic() - self.start_time
        minutes = int(time_elapsed // 60)
        seconds = int(time_elapsed % 60)

        connected_peers: int = len([peer for peer in self.peers if peer.tcp_established])
        # Construct output string
        output = f"File: {self.filename} | "
        output += f"Time: {minutes}:{seconds:02d} | "
        output += f"Peers: {len(self.peers)} ({connected_peers} connected) | "
        output += f"Completed: {self.file.get_progress()} | "
        output += f"Download Speed: {self.download_speed:.2f} MB/s | "
        output += f"Upload Speed: {self.upload_speed:.2f} MB/s"
        sys.stdout.write("\033[2K\r")  # Clear the line
        sys.stdout.write(f"\r{output}")  # Clear the previous output with a carriage return
        sys.stdout.flush()  # Ensure the output is written immediately

        # Update variables for next call
        # self.last_interval = time.monotonic()
        # self.last_bytes_downloaded = self.file.bytes_downloaded()
        # self.last_bytes_uploaded = self.file.bytes_uploaded()

    def __str__(self):
        """
        Displays progress report to user.
        """
        print("=== Client ===")
        # print(f"Torrent: ", {self.filename}")
        # print(f"Destination: ", {self.destination}")
        # print(f"Peer Id: ", {self.peer_id}")

        # Dynamic approach
        instance_variables = {key: value for key, value in self.__dict__.items() if not callable(value) and not key.startswith("__")}
        longest_name = max(map(len, instance_variables.keys()))
        for name, value in instance_variables.items():
            print(f"{name:<{longest_name}} = {value}")

        self.display_peers()
        print(self.file)

    def shutdown(self, signum=None, frame=None):
        """
        Saves bitmap of pieces to disk and frees client resources.
        Runs upon early termination as a handler for SIGINT and SIGTERM.
        """
        traceback.print_stack()
        print("Received SIGINT or SIGTERM. Cleaning up resource and shutting down...")
        self.cleanup()
        self.file.write_bitfield_to_disk()
        sys.exit(1)

    def cleanup(self):
        """
        Saves bitmap of pieces to disk and frees client resources.
        Invoked for both normal and early (interrupted) termination.
        """
        self.file.close_file()
        self.tracker.disconnect()
        self.close_socket()
