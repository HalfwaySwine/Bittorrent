from ..utils.helpers import logger
import socket
from urllib.parse import urlparse, urlencode, quote_plus
import bencoder
from peer import Peer
from config import HTTP_PORT


class Tracker:
    """
    Server managing swarm associated with a torrent. A client can join the swarm by sending a request to this server using its associated url or IP address.
    """

    def __init__(self, url):
        self.url = url
        self.timestamp = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", HTTP_PORT))

    def join_swarm(self, peer_id, info_hash, bytes_left) -> list[Peer]:
        """
        Returns: Returns a list of peer objects and sets request interval if successful. Terminates program if there is an error.
        """
        params = {
            "peer_id": peer_id,
            "port": HTTP_PORT,
            "uploaded": 0,
            "downloaded": 0,
            "left": bytes_left,
            "event": "started",
        }

        # Connect to tracker
        parsed_url = urlparse(self.url)
        host = parsed_url.hostname
        port = parsed_url.port
        logger.debug(f"Tracker is at {host}: {port}")
        self.sock.connect((host, port))

        # Construct get request
        encoded_params = urlencode(params)
        # Construct the HTTP GET request
        request = f"GET /announce?info_hash={info_hash}&{encoded_params} HTTP/1.1\r\nHost: {host}:{port}\r\nAccept: */*\r\n\r\n"
        self.sock.sendall(request.encode())
        # Receive response
        response = b""
        while True:
            data = self.sock.recv(4096)
            if not data:
                break
            response += data
        headers, body = response.split(b"\r\n\r\n", 1)
        # TODO: Handle bad/invalid http responses
        # Decode the bencoded body
        decoded = bencoder.bdecode(body)
        print(decoded.keys())
        # Extract information
        # Seconds that the client should wait between sending regular requests to the tracker
        self.interval = decoded[b"interval"]
        peer_list = []
        for peer in decoded[b"peers"]:
            ip = peer[b"ip"].decode("utf-8")
            port = peer[b"port"]
            peer_list.append(Peer(ip, port))
            logger.debug(f"Peer: {ip}:{port}")
        return peer_list

    def send_tracker_request(self):
        pass

    def parse_tracker_resonse(self):
        """
        Decodes and unpacks tracker responses, which are bencoded dictionaries in order to obtain a list of peers and rerequest interval.
        Server responses may commonly contain be an alternative, compact represetation of the peer list, specified by BEP 23.

        Validation: If tracker response contains the key b'failure reason', then that maps to a human readable string which explains why the query failed.
        """
        pass

    def shutdown_tracker(self):
        self.sock.close()
