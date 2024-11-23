class Peer:
    def __init__(self, ip_address, port):
        self.ip_address
        self.port
        self.socket  # or self.connection
        self.bitfield
        self.am_interested
        self.am_choking
        self.peer_interested
        self.peer_choking

    def handshake(self):
        pass

    def connect(self):
        pass

    def disconnect(self):
        pass

    def upload(self, block):
        pass

    def request(self, piece):
        pass

    def download(self, block):
        pass

    def read_message(self):
        pass

    def poll(self):
        pass

    def send_interested(self):
        pass

    def send_event(self, type):
        pass

    def send_msg(self):
        pass

    def choke(self):
        pass

    def unchoke(self):
        pass
