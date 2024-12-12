from .peer import Peer, Handshake
from .file import File
from random import choice
from ..config import MIN_CONNECTED_PEERS, MAX_CONNECTED_PEERS, NUM_RAREST_PIECES, EPOCH_DURATION_SECS
from ..utils.helpers import logger, Status

"""
Strategy Interface:
    def choose_peers(self, peers: list[Peer], upload_speed, download_speed) -> list[Peer]
    def assign_pieces(self, remaining_pieces, peers: list[Peer])
    def send_haves(self, completed_pieces, actual_bitfield, peers)
    def determine_additional_peers(self, file, connected_peers: list[Peer]) -> int
"""


class Strategy:
    def choose_peers(self, peers: list[Peer], upload_speed, download_speed) -> list[Peer]:
        """
        Given a list of peers, return a list of peers to unchoke.
        """
        interested = [peer for peer in peers if peer.peer_interested and peer.tcp_established and peer.received_handshake == Handshake.HANDSHAKE_RECVD]
        top_four = Strategy.get_top_four(interested)
        not_top_four = [peer for peer in interested if peer not in top_four]
        optimistic_unchoke = [Strategy.get_optimistic_unchoke(not_top_four)] if not_top_four else []
        return top_four + optimistic_unchoke

    def assign_pieces(self, remaining_pieces, peers: list[Peer]):
        # set comprehension
        unchoked_peers = {peer for peer in peers if not peer.peer_choking and peer.am_interested and not peer.target_piece}
        remaining_pieces_copy = set(remaining_pieces)
        i = 0
        while unchoked_peers:
            i += 1
            # if we can't assign a piece to a peer at all
            if i == 1000:
                break
            if remaining_pieces_copy:
                piece = choice(list(remaining_pieces_copy))
                for peer in unchoked_peers:
                    if peer.bitfield[piece]:
                        peer.target_piece = piece
                        unchoked_peers.remove(peer)
                        break
                # if no peers take it we have to move on as well
                remaining_pieces_copy.remove(piece)
            else:
                remaining_pieces_copy = set(remaining_pieces)

    def fulfill_requests(self, peers: list[Peer], file: File):
        for peer in peers:
            peer.allotment = file.piece_length  # Default upload limit per turn (equal).
            for block_request in peer.incoming_requests:
                index, offset, length = block_request
                peer.allotment -= length  # Decrement allotment whether or not request is successful.
                if peer.allotment < 0:
                    # Do not remove from requests.
                    break
                data_to_send = file.get_data_from_piece(offset, length, index)
                if data_to_send == 0:  # Issue retrieving data
                    peer.incoming_requests.pop(0)
                    continue
                flag = peer.send_piece(index, offset, data_to_send)
                if flag == Status.SUCCESS:
                    file.total_uploaded += length / 1024  # Update total uploaded
                    logger.debug(f"Data successfully sent to {peer.addr}")
                else:
                    logger.debug(f"Data failed to send to {peer.addr}")

    def send_haves(self, completed_pieces, actual_bitfield, peers):
        for peer in peers:
            for piece in completed_pieces:
                peer.send_have(piece)

    def determine_additional_peers(self, file, connected_peers: list[Peer]) -> int:
        if len(connected_peers) < MIN_CONNECTED_PEERS:
            return MAX_CONNECTED_PEERS - len(connected_peers)
        else:
            return 0

    # Helper methods

    def shuffle_pieces(self, remaining_pieces, peers: list[Peer]):
        """Shuffles piece assignments, may be useful in some cases but not called currently"""
        # Set comprehension
        all_peers = {peer for peer in peers if not peer.peer_choking and peer.am_interested}
        for peer in all_peers:
            peer.target_piece = None

    @classmethod
    def get_top_four(cls, peers: list[Peer]) -> list[Peer]:
        """
        Gets the top four ranking and interested peers in terms of bytes received within the last epoch.
        Also includes any peers that are not interested but higher than the fourth place peer.
        """
        peers_sorted = sorted(peers, key=lambda x: x.bytes_received)
        # Return the top peers but cut the list off after the fourth interested peer.
        num_interested = 0
        cutoff = len(peers_sorted) - 1
        for index, peer in enumerate(peers_sorted):
            if peer.peer_interested:
                num_interested += 1
            if num_interested == 4:
                cutoff = index
                break
        return peers_sorted[: cutoff + 1]

    @classmethod
    def get_optimistic_unchoke(cls, peers: list[Peer]) -> Peer:
        interested = [peer for peer in peers if peer.peer_interested]
        return choice(interested) if interested else []


class RarestFirstStrategy(Strategy):
    def assign_pieces(self, remaining_pieces, peers: list[Peer]):
        """
        Given a list of peers (which contains their bitfields and whether they've unchoked us) and remaining pieces to download, returns a list of the rarest pieces to request from each.
        """
        unchoked_waiting_peers = [peer for peer in peers if not peer.peer_choking and peer.am_interested and peer.target_piece is None]
        if not unchoked_waiting_peers:
            return  # No peer needs a piece assigned.
        remaining_pieces = set(remaining_pieces)
        rarest_pieces: list[int] = RarestFirstStrategy.calculate_rarest_pieces(peers)
        # Remove pieces we've already downloaded.
        rarest_pieces_left: list[int] = set(piece_index for piece_index in rarest_pieces if piece_index in remaining_pieces)
        if not rarest_pieces_left:  # None of the peers have pieces we need.
            return
        for peer in unchoked_waiting_peers:
            peer.target_piece = RarestFirstStrategy.choose_rarest_piece_with_randomness(rarest_pieces_left, peer)
            assert peer.target_piece is not None, "Client should not be interested in a peer that has no desired pieces."

    # Helper methods
    @classmethod
    def choose_rarest_piece_with_randomness(cls, rarest_pieces, peer):
        """
        Returns the rarest piece that a peer possesses.
        """
        has_pieces = []
        for piece in rarest_pieces:
            if peer.bitfield[piece] == 1:
                has_pieces.append(piece)
            if len(has_pieces) == NUM_RAREST_PIECES:
                break
        return choice(has_pieces) if has_pieces else None

    @classmethod
    def calculate_rarest_pieces(cls, peers: list[Peer]) -> list[int]:
        """
        Given a list of peers containing the peers' bitfield, returns a ranking of the rarest pieces, identified by their indices.
        """
        bitfields = [peer.bitfield for peer in peers if peer.bitfield is not None]  # [[1, 0], [1, 1], [0, 0]]
        if not bitfields:
            return []
        frequencies = [sum(respective_bits) for respective_bits in zip(*bitfields)]  # [[1, 1, 0], [0, 1, 0]]
        sorted_frequencies = sorted(enumerate(frequencies), key=lambda x: x[1], reverse=True)
        return [index for index, frequency in sorted_frequencies]  # Return the indices of the pieces


class PropShareStrategy(Strategy):
    def __init__(self):
        self.upload_bandwidth = 0  # Bytes uploaded last epoch

    def choose_peers(self, peers: list[Peer], upload_speed, download_speed) -> list[Peer]:
        # Determine available upload_bandwidth.
        self.upload_bandwidth = upload_speed * EPOCH_DURATION_SECS
        # Unchoke any peer who uploaded to us in the last epoch.
        interested = [peer for peer in peers if peer.peer_interested]
        unchoke = []
        for peer in interested:
            if peer.bytes_received > 0:
                unchoke.append(peer)
                # Assign a proportional upload allotment.
                peer.allotment = int(peer.last_bytes_received / self.upload_bandwidth)
        return unchoke

    def fulfill_requests(self, peers: list[Peer], file: File):
        for peer in peers:
            # Allotment variable will be used per epoch instead of per method invocation.
            # Will represent the proportion of upload bandwidth to dedicate to client [0,1].
            requests_per_iteration = 16
            for block_request in peer.incoming_requests[:requests_per_iteration]:
                index, offset, length = block_request
                peer.allotment -= length  # Decrement allotment whether or not request is successful.
                if peer.allotment < 0:
                    # Do not remove from requests.
                    break
                data_to_send = file.get_data_from_piece(offset, length, index)
                if data_to_send == 0:  # Issue retrieving data
                    peer.incoming_requests.pop(0)
                    continue
                flag = peer.send_piece(index, offset, data_to_send)
                if flag == Status.SUCCESS:
                    file.total_uploaded += length / 1024  # Update total uploaded
                    logger.debug(f"Data successfully sent to {peer.addr}")
                else:
                    logger.debug(f"Data failed to send to {peer.addr}")


class RandomStrategy(Strategy):
    def assign_pieces(self, remaining_pieces, peers: list[Peer]):
        unchoked_peers = {peer for peer in peers if not peer.peer_choking and peer.am_interested and not peer.target_piece}
        remaining_pieces = list(remaining_pieces)
        if unchoked_peers:
            for peer in unchoked_peers:
                while True:
                    piece = choice(remaining_pieces)
                    if peer.bitfield[piece]:
                        peer.target_piece = piece
                        break
