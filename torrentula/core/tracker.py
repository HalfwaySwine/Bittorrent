from ..utils.helpers import logger
import socket
from urllib.parse import urlparse, urlencode, quote_plus, unquote_plus, quote
import bencoder
from .peer import Peer
from ..config import HTTP_PORT, TRACKER_NUMWANT, BITTORRENT_PORT
import sys
from struct import unpack
import select
from datetime import datetime, timedelta
import pynat

class Tracker:
    """
    Server managing swarm associated with a torrent. A client can join the swarm by sending a request to this server using its associated url or IP address.
    """

    def __init__(self, url, peer_id, info_hash, num_pieces):
        self.url = url
        self.timestamp = datetime.now()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", HTTP_PORT))
        self.peer_id = peer_id
        self.info_hash = info_hash
        self.num_pieces = num_pieces
        self.interval = 0
        self.request_in_progress = False
        self.externIP = None
        self.externPort = None

    def join_swarm(self, bytes_left, port) -> list[Peer]:
        """
        Returns: Returns a list of peer objects and sets request interval if successful. Terminates program if there is an error.
        """
        decoded = self.send_tracker_request(port, 0, 0, bytes_left, "started")
        # Extract information
        # Seconds that the client should wait between sending regular requests to the tracker
        peer_list = self.recv_tracker_response(1)  # blocking recv
        return peer_list

    def send_tracker_request(self, port, uploaded, downloaded, left, event):
        if datetime.now() - self.timestamp < timedelta(seconds=self.interval):
            logger.info("Sent Tracker request too soon :(")
            return
        #self.setup_upnp()
        self.setup_nat_pmp()
        params = {
            "peer_id": self.peer_id,
            "port": self.externPort,
            "uploaded": uploaded,
            "downloaded": downloaded,
            "left": left,
            "numwant": TRACKER_NUMWANT,
            "event": event,
            "ip": self.external_ip 
        }
        parsed_url = urlparse(self.url)
        host = parsed_url.hostname
        port = parsed_url.port
        path = parsed_url.path
        tracker_addr = (host, port)
        logger.debug(f"Attempting to connect to tracker at {host}:{port} over TCP...")
        self.sock.connect(tracker_addr)

        # Construct get request
        encoded_params = urlencode(params)
        # Construct the HTTP GET request
        request = f"GET {path}?info_hash={quote(self.info_hash)}&{encoded_params} HTTP/1.1\r\nHost: {host}:{port}\r\nAccept: */*\r\n\r\n"
        self.sock.sendall(request.encode())
        self.timestamp = datetime.now()
        self.request_in_progress = True

    def setup_nat_pmp(self):
        """
        Gets a external ip and port to map to 
        """
        try:
            nat_type, external_ip, external_port = pynat.get_ip_info() #no built in timeout
            if nat_type:
                self.external_ip = external_ip 
                self.externPort = external_port
                logger.info(f"NAT Type: {nat_type}, external IP: {self.external_ip}, port: {external_port}")
                return True
        except Exception as e:
            logger.info(f"Failed to set up NAT-PMP: {e}")
            self.external_ip = None
            return False

    def recv_tracker_response(self, block=0):
        if self.request_in_progress == True:
            response = b""
            rdy, _, _ = select.select([self.sock], [], [], 0)
            if rdy or block == 1:
                while True:
                    data = self.sock.recv(4096)
                    if not data:
                        break
                    response += data
                assert response
                headers, body = response.split(b"\r\n\r\n", 1)
                headers_text = headers.decode(errors="replace")
                status_code = int(headers_text.split("\r\n")[0].split()[1])
                self.request_in_progress = False
                self.disconnect()
                if status_code >= 400:
                    # TODO: Handle bad/invalid http responses
                    logger.critical(f"{headers}")
                    logger.error(f"{headers}")
                    sys.exit()
                else:
                    peer_list = self.parse_tracker_resonse(body)
                    return peer_list
        return []

    def send_scrape(self):
        # unfinished method, will complete later
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", HTTP_PORT))
        parsed_url = urlparse(self.url)
        host = parsed_url.hostname
        port = parsed_url.port
        self.sock.connect((host, port))
        request = f"GET /scrape?info_hash={quote(self.info_hash)} HTTP/1.1\r\nHost: {host}:{port}\r\nAccept: */*\r\n\r\n"
        self.sock.sendall(request.encode())
        response = b""
        while True:
            data = self.sock.recv(4096)
            if not data:
                break
            response += data
        header, body = response.split(b"\r\n\r\n", 1)
        decoded = bencoder.bdecode(body)
        logger.debug(decoded[b"flags"])
        logger.debug(decoded[b"files"])
        self.sock.close()

    def parse_tracker_resonse(self, body):
        """
        Decodes and unpacks tracker responses, which are bencoded dictionaries in order to obtain a list of peers and rerequest interval.
        Server responses may commonly contain be an alternative, compact represetation of the peer list, specified by BEP 23.

        Validation: If tracker response contains the key b'failure reason', then that maps to a human readable string which explains why the query failed.
        """
        try:
            decoded = bencoder.bdecode(body)
        except Exception as e:
            logger.critical(f"error during parsing tracker response: {e}")
            exit(0)
        peer_list = []
        if b"interval" in decoded:
            self.interval = decoded[b"interval"]
        if b"peers" in decoded:
            peers = decoded[b"peers"]
            if isinstance(peers, bytes):  # compact form
                logger.info("Tracker sent peers in compact format.")
                for i in range(0, len(peers), 6):
                    peer_data = peers[i : i + 6]
                    ip = ".".join(map(str, peer_data[:4]))
                    port = unpack(">H", peer_data[4:])[0]
                    peer_list.append(Peer(ip, port, self.info_hash, self.peer_id, self.num_pieces))
            else:  # non compact form
                logger.info("Tracker sent peers in normal (not compact) format.")
                for peer in decoded[b"peers"]:
                    ip = peer[b"ip"].decode("utf-8")
                    port = peer[b"port"]
                    peer_list.append(Peer(ip, port, self.info_hash, self.peer_id, self.num_pieces))
                    logger.debug(f"Peer: {ip}:{port}")
        if b"failure reason" in decoded:
            failure_reason = decoded[b"failure reason"].decode("utf-8")
            logger.critical(f"Query failed. Reason: {failure_reason}")
        return peer_list

    def disconnect(self):
        if self.sock:
            self.sock.close()
