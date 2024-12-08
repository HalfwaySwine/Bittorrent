from datetime import datetime, timedelta
from enum import Enum
from ..config import PEER_INACTIVITY_TIMEOUT_SECS
from ..utils.helpers import logger, Status
from .piece import Piece
from .block import Block
import select
import socket
import struct


class MessageType(Enum):
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOT_INTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7
    CANCEL = 8


class Handshake(Enum):
    # didn't receive handshake
    HANDSHAKE_NOT_RECVD = 0
    # means received handshake and can still receive bitmap
    CAN_RECV_BITFIELD = 1
    # means received handshake and can't receive bitmap
    HANDSHAKE_RECVD = 2


class Peer:
    """
    Represents a peer Bittorrent client in the same swarm.
    """

    def __init__(self, ip_address, port, info_hash, peer_id, bitfield_length, sock=None, v4=True):
        """
        Socket argument is provided when the client accepted this connection from a peer rather than initiaiting it.
        bitfield_length is the number of pieces in the torrent
        """
        # IPv4 connections addr is a tuple: (hostname_or_ip_addr, port)
        # IPv6 connections addr is a tuple: (hostname_or_ip, port, flowinfo, scopeid)
        if v4:
            self.addr = (ip_address, port)
        else:
            self.addr = (ip_address, port, 0, 0)

        self.bitfield_length = bitfield_length
        self.bitfield = [0] * self.bitfield_length  # Initialized to all 0 for the length of the torrent

        # Connections start out choked and not interested.
        self.am_interested = False
        self.am_choking = True
        self.peer_interested = False
        self.peer_choking = True

        # Track statistics *per epoch* to inform strategic decision-making.
        self.bytes_received = 0
        self.bytes_sent = 0
        self.connection_attempts = 0

        self.outgoing_requests = []  # List of pieces that we have requested from the peer but have not completed.
        self.incoming_requests = []  # list of incoming requests
        self.target_piece = None  # Piece from peer we are currently requesting, is an int index.
        self.last_received = None  # Time of last message received from peer
        self.last_sent = None  # Time of last message sent to peer

        self.received_handshake = Handshake.HANDSHAKE_NOT_RECVD  # check if we recieved a handshake or not
        self.info_hash: bytes = info_hash  # we keep an info hash here to send and check when received
        self.peer_id: str = peer_id  # we keep a peer_id here in the case of them receiving
        self.sent_handshake = False  # needed to differentiate if we initiate or they initiate connection
        self.can_send_bitfield = False  # client checks and handles sending bitfields
        self.is_connected = False  # self explanatory, if we have a socket and this is false, connection is ongoing
        self.socket = sock  # Value is None when this peer is disconnected.
        # if we pass in a socket we are already connected, send handshake
        if sock is not None:
            self.connection_success()
            self.send_handshake()

    def connection_success(self):
        self.is_connected = True
        self.connection_attempts = 0
        logger.debug(f"Successfully connected to peer at {self.addr}...")

    def connect(self):
        """
        Should throw an error on fail.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)
        try:
            logger.debug(f"Attempting to connect to peer at {self.addr}...")
            self.connection_attempts += 1
            self.last_sent = datetime.now()
            self.last_received = datetime.now()
            self.socket.connect(self.addr)
        except BlockingIOError as e:
            logger.info(f"Connection in progress to peer at {self.addr}")
            return Status.IN_PROGRESS
        except Exception as e:
            logger.info(f"Error connecting to peer at {self.addr}")
            self.socket.close()
            self.socket = None
            return Status.FAILURE
        self.connection_success()
        return Status.SUCCESS

    def disconnect(self):
        """
        Closes socket and resets connection params.
        """
        self.socket.close()

        # reset most parameters, maybe have to add some
        self.outgoing_requests = []  # reset list, we don't expect requests to be fulfilled
        self.incoming_requests = []
        self.socket = None
        self.is_connected = False
        self.sent_handshake = False
        self.received_handshake = Handshake.HANDSHAKE_NOT_RECVD
        self.sent_handshake = False

        self.am_interested = False
        self.am_choking = True
        self.peer_interested = False
        self.peer_choking = True
        self.bitfield = [0] * self.bitfield_length
        self.bytes_received = 0
        self.bytes_sent = 0

    def send_handshake(self):
        """
        Send handshake message.
        """
        pstr = "BitTorrent protocol"
        pstrlen = len(pstr)
        # ! = big endian, B = unsigned char, then string s, then 8 padding 0s, then 2 20 length strings
        # I don't expect to use these 8 padding bytes
        msg = struct.pack(
            f"!B{pstrlen}s8x20s20s", pstrlen, pstr.encode("utf-8"), self.info_hash, self.peer_id.encode("utf-8")
        )
        res = self.send_msg(msg)
        if res == Status.SUCCESS:
            logger.info(f"Handshake succeeded to peer at {self.addr}")
            self.sent_handshake = True
        else:
            logger.info(f"Handshake failed to peer at {self.addr}")
        return res

    # was handled in receive_messages
    # def download(self, block):
    #     pass

    def receive_messages_helper(self, piece):
        """
        Assuming we do the select outside of receive_messages - just handle messages here
        if we haven't received a handshake we expect a handshake before anything else
        If we receive something wrong we disconnect
        Returns Status.FAILURE on disconnect, Status.SUCCESS on success

        This code does not really handle blocking problems on recv, could cause issues in the future
        we also don't really handle unexpected recvs, could cause some erroring that may need to be caught
        """
        logger.debug(f"Receiving message from {self.addr}...")
        if self.received_handshake == Handshake.HANDSHAKE_NOT_RECVD:

            pstrlen_bytes = self.socket.recv(1)
            if len(pstrlen_bytes) == 0:
                logger.debug(f"connection closed, disconnecting")
                self.disconnect()
                return Status.FAILURE

            pstrlen = int.from_bytes(pstrlen_bytes)
            bytes = self.socket.recv(pstrlen + 48)
            if len(bytes) == 0:
                logger.debug(f"connection closed, disconnecting")
                self.disconnect()
                return Status.FAILURE

            pstr, padding, info_hash, peer_id = struct.unpack(f"!{pstrlen}s8s20s20s", bytes)
            logger.debug(f"received {pstr}, {padding}, {info_hash}, {peer_id}")
            # may want to do smth with pstr, padding, and peer_id
            # but rn I only care about checking info_hash
            if info_hash != self.info_hash:
                self.disconnect()
                return Status.FAILURE
            self.received_handshake = Handshake.CAN_RECV_BITFIELD
            # if the connection was an incoming connection we still need to send our side of the handshake
            if not self.sent_handshake:
                self.send_handshake()
            # when we return we expect client object to check this value and send bitfield if needed
            self.can_send_bitfield = True
        else:
            # once we receive any other message other than a handshake we can't receive a bitmap anymore
            self.received_handshake = Handshake.HANDSHAKE_RECVD

            msg_len_bytes = self.socket.recv(4)
            if len(msg_len_bytes) == 0:
                logger.debug(f"connection closed, disconnecting")
                self.disconnect()
                return Status.FAILURE

            msg_len = int.from_bytes(msg_len_bytes, "big")
            logger.debug(f"recieved msg len: {msg_len}")
            # differentiating from keepalive, we don't have to do anything if it's a keepalive
            if msg_len > 0:
                msg = b""
                while len(msg) < msg_len:
                    # wait one second, otherwise timeout. If we ever timeout,
                    # this macgyver solution will not really work because we kinda block too long.
                    rdy, _, _ = select.select([self.socket], [], [], 1)

                    # if list is empty we have timed out
                    if not rdy:
                        logger.debug("WARNING: timed out on receive_messages, our implementation is gonna be slow")
                        self.disconnect()
                        return Status.FAILURE

                    section = self.socket.recv(msg_len - len(msg))
                    # recv returns an empty bytes object when the connection is closed
                    if len(section) == 0:
                        logger.debug(f"connection closed, disconnecting")
                        self.disconnect()
                        return Status.FAILURE

                    msg += section

                msg_type = int.from_bytes(msg[0:1], "big")
                logger.debug(f"recieved msg type: {msg_type}")
                if msg_type == MessageType.CHOKE.value:
                    self.peer_choking = True
                if msg_type == MessageType.UNCHOKE.value:
                    self.peer_choking = False
                if msg_type == MessageType.INTERESTED.value:
                    self.peer_interested = True
                if msg_type == MessageType.NOT_INTERESTED.value:
                    self.peer_interested = False
                if msg_type == MessageType.HAVE.value:
                    piece_index = int.from_bytes(msg[1:], "big")
                    self.bitfield[piece_index] = 1
                if msg_type == MessageType.BITFIELD.value:
                    bitfield_bytes = msg[1:]
                    for i in range(len(self.bitfield)):
                        byte_index = i // 8
                        index_in_byte = i % 8
                        byte = bitfield_bytes[byte_index]
                        self.bitfield[i] = byte >> (7 - index_in_byte) & 1
                if msg_type == MessageType.REQUEST.value:
                    index, offset, length = struct.unpack(f"!III", msg[1:])
                    logger.debug(f"recieved request for index: {index}, offset {offset}, length: {length}")
                    self.incoming_requests.append((index, offset, length))
                if msg_type == MessageType.PIECE.value:
                    # will get the block and add it to the piece
                    # 8 bytes after is info
                    info = msg[1:9]
                    index, offset = struct.unpack(f"!II", info)
                    logger.debug(f"recieved piece with index: {index}, offset {offset}")
                    length = msg_len - 9
                    # we should check index and offset against our request
                    tup = (index, offset, length)
                    if tup in self.outgoing_requests:
                        self.outgoing_requests.remove(tup)
                        piece.add_block(offset, msg[9:])
                        self.bytes_received += length
                if msg_type == MessageType.CANCEL.value:
                    info = msg[1:]
                    index, offset, length = struct.unpack(f"!III", info)
                    tup = (index, offset, length)
                    logger.debug(f"recieved cancel for index: {index}, offset {offset}, length: {length}")
                    if tup in self.incoming_requests:
                        self.incoming_requests.remove(tup)
        self.last_received = datetime.now()
        return Status.SUCCESS

    def receive_messages(self, piece):
        try:
            return self.receive_messages_helper(piece)
        except Exception as e:
            logger.debug(f"receive_messages failed, disconnecting")
            self.disconnect()
            return Status.FAILURE

    def send_keepalive(self):
        msg = struct.pack("!4x")
        return self.send_msg(msg)

    def send_interested(self):
        """also sets our state to interested"""
        self.am_interested = True
        msg = struct.pack(f"!IB", 1, MessageType.INTERESTED.value)
        return self.send_msg(msg)

    def send_not_interested(self):
        """also sets our state to not interested"""
        self.am_interested = False
        msg = struct.pack(f"!IB", 1, MessageType.NOT_INTERESTED.value)
        return self.send_msg(msg)

    def send_have(self, index: int):
        """index is a 4 byte unsigned int"""
        msg = struct.pack(f"!IBI", 5, MessageType.HAVE.value, index)
        return self.send_msg(msg)

    def send_bitfield(self, bitfield):
        """
        Send the bitfield that we have
        """
        bitfield_length = len(bitfield)
        msg_length = len(bitfield) + 1
        msg = struct.pack(f"!IB{bitfield_length}s", msg_length, MessageType.BITFIELD.value, bitfield)
        return self.send_msg(msg)

    def send_request(self, index, offset, length):
        """also takes care of the outgoing requests list"""
        msg = struct.pack(f"!IBIII", 13, MessageType.REQUEST.value, index, offset, length)
        self.outgoing_requests.append((index, offset, length))
        return self.send_msg(msg)

    def send_piece(self, index, offset, data):
        """sends data, passed in as bytes, as well as the index and offset of it
        also takes care of the incoming requests list, if it wasn't in there, fail"""
        tup = (index, offset, data)
        if tup in self.incoming_requests:
            msg_len = len(data) + 9
            msg = struct.pack(f"!IBII{len(data)}s", msg_len, MessageType.PIECE.value, index, offset, data)
            self.incoming_requests.remove(tup)
            return self.send_msg(msg)
        return Status.FAILURE

    def send_cancel(self, index, offset, length):
        """Also takes care of the outgoing requests list, if we didn't request it before, fail"""
        tup = (index, offset, length)
        if tup in self.outgoing_requests:
            self.outgoing_requests.remove(tup)
            msg = struct.pack(f"!IBIII", 13, MessageType.CANCEL.value, index, offset, length)
            return self.send_msg(msg)
        return Status.FAILURE

    def send_msg(self, msg):
        """
        Send msg and update last sent time
        will disconnect if send fails
        returns either success or failure
        """
        # fail if not connected
        if not self.is_connected:
            return Status.FAILURE
        if not self.socket:
            logger.error("Peer's send_msg was called without having a socket.")
        # once we send any other message we can't send a bitfield anymore
        self.can_send_bitfield = False
        logger.debug(f"sending to {self.addr}:")
        logger.debug(msg)
        self.last_sent = datetime.now()
        try:
            self.socket.sendall(msg)
        except Exception as e:
            logger.debug("message failed to send, disconnecting")
            self.disconnect()
            return Status.FAILURE
        return Status.SUCCESS

    def choke(self):
        """
        Sends a choke message to peer and stores that state if peer is currently unchoked. Otherwise, does nothing.
        """
        if self.am_choking == True:
            return Status.FAILURE
        msg = struct.pack(f"!IB", 1, MessageType.CHOKE.value)
        self.am_choking = True
        return self.send_msg(msg)

    def unchoke(self):
        """
        Sends an unchoke message to peer if peer is currently choked, otherwise, does nothing.
        """
        if self.am_choking == False:
            return Status.FAILURE
        msg = struct.pack(f"!IB", 1, MessageType.UNCHOKE.value)
        self.am_choking = False
        return self.send_msg(msg)

    def send_keepalive_if_needed(self):
        if not self.is_connected or datetime.now() - self.last_sent <= timedelta(seconds=PEER_INACTIVITY_TIMEOUT_SECS):
            return  # Keepalive is not necessary
        else:
            self.send_keepalive()

    def establish_new_epoch(self):
        self.bytes_received = 0
        self.bytes_sent = 0

    def disconnect_if_timeout(self):
        if self.socket and datetime.now() - self.last_received > timedelta(seconds=PEER_INACTIVITY_TIMEOUT_SECS):
            self.disconnect()
