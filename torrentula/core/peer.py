class Peer:
    def __init__(self, ip_address, port):
        self.ip_address
        self.port
        self.socket # or self.connection
        self.bitfield
        self.am_interested
        self.am_choking
        self.peer_interested
        self.peer_choking
    def handshake():
        pass
    def connect():
        pass
    def disconnect():
        pass
    def upload(block):
        pass
    def request(piece):
        pass
    def download(block):
        pass
    def read_message():
        pass
    def poll():
        pass
    def send_event(type):
        pass
    def choke():
        pass
    def unchoke():
        pass
