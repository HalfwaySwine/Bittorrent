class Tracker:
    """
    Server managing swarm associated with a torrent. A client can join the swarm by sending a request to this server using its associated url or IP address.
    """

    def __init__(self, url):
        self.url = url
        self.timestamp = None

    def join_swarm(self) -> (list, int):
        """
        Returns: Returns a list of peer objects and sets request interval if successful. Terminates program if there is an error.
        """
        self.interval  # Seconds that the client should wait between sending regular requests to the tracker
        pass

    def send_tracker_request(self):
        pass

    def parse_tracker_resonse(self):
        """
        Decodes and unpacks tracker responses, which are bencoded dictionaries in order to obtain a list of peers and rerequest interval.
        Server responses may commonly contain be an alternative, compact represetation of the peer list, specified by BEP 23.

        Validation: If tracker response contains the key b'failure reason', then that maps to a human readable string which explains why the query failed.
        """
        pass
