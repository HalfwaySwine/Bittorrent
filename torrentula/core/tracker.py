from ..utils.helpers import logger
import socket
from urllib.parse import urlparse, urlencode, quote_plus, unquote_plus
import bencoder
from .peer import Peer
from ..config import HTTP_PORT
import sys

class Tracker:
    """
    Server managing swarm associated with a torrent. A client can join the swarm by sending a request to this server using its associated url or IP address.
    """

    def __init__(self, url, peer_id, info_hash, num_pieces):
        self.url = url
        self.timestamp = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", HTTP_PORT))
        self.peer_id = peer_id
        self.info_hash = info_hash
        self.num_pieces = num_pieces

    def join_swarm(self, bytes_left, port) -> list[Peer]:
        """
        Returns: Returns a list of peer objects and sets request interval if successful. Terminates program if there is an error.
        """
        decoded = self.send_tracker_request(port, 0, 0, bytes_left, "started")
        # Extract information
        # Seconds that the client should wait between sending regular requests to the tracker
        self.interval = decoded[b"interval"]
        peer_list = []
        for peer in decoded[b"peers"]:
            ip = peer[b"ip"].decode("utf-8")
            port = peer[b"port"]
            peer_list.append(Peer(ip, port, self.info_hash, self.peer_id, self.num_pieces))
            logger.debug(f"Peer: {ip}:{port}")
        return peer_list

    def send_tracker_request(self, port, uploaded, downloaded, left, event):
        params = {
            "peer_id": self.peer_id,
            "port": port,
            "uploaded": uploaded,
            "downloaded": downloaded,
            "left": left,
            "numwant": 30,
            "event": event,
        }
        parsed_url = urlparse(self.url)
        host = parsed_url.hostname
        port = parsed_url.port
        self.sock.connect((host, port))

         # Construct get request
        encoded_params = urlencode(params)
        # Construct the HTTP GET request
        request = f"GET /announce?info_hash={quote_plus(self.info_hash)}&{encoded_params} HTTP/1.1\r\nHost: {host}:{port}\r\nAccept: */*\r\n\r\n"
        self.sock.sendall(request.encode())
        # Receive response
        response = b""
        while True:
            data = self.sock.recv(4096)
            if not data:
                break
            response += data

        status_code = int(response.decode().split('\r\n')[0].split()[1])
        headers, body = response.split(b"\r\n\r\n", 1)
        if status_code >= 400:
            # TODO: Handle bad/invalid http responses
            logger.critical(f"{headers}")
            sys.exit()
        # Decode the bencoded body
        decoded = bencoder.bdecode(body)
        return decoded

    def send_scrape(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", HTTP_PORT))
        parsed_url = urlparse(self.url)
        host = parsed_url.hostname
        port = parsed_url.port
        self.sock.connect((host, port))
        request = f"GET /scrape?info_hash={quote_plus(self.info_hash)} HTTP/1.1\r\nHost: {host}:{port}\r\nAccept: */*\r\n\r\n"
        self.sock.sendall(request.encode())
        print(request)
        # Receive response
        response = b""
        while True:
            data = self.sock.recv(4096)
            if not data:
                break
            response += data
        print(response)
        #status_code = int(response.decode().split('\r\n')[0].split()[1])
        header, body = response.split(b"\r\n\r\n", 1)
        # if status_code >= 400:
        #     # TODO: Handle bad/invalid http responses
        #     logger.critical(f"{headers}")
        #     sys.exit()
        # Decode the bencoded body
        decoded = bencoder.bdecode(body)
        logger.debug(decoded[b"flags"])
        logger.debug(decoded[b"files"])
        self.sock.close()


    def parse_tracker_resonse(self):
        """
        Decodes and unpacks tracker responses, which are bencoded dictionaries in order to obtain a list of peers and rerequest interval.
        Server responses may commonly contain be an alternative, compact represetation of the peer list, specified by BEP 23.

        Validation: If tracker response contains the key b'failure reason', then that maps to a human readable string which explains why the query failed.
        """
        pass

    def disconnect(self):
        if self.sock:
            self.sock.close()
