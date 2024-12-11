from .peer import Peer
from random import choice
from ..config import MIN_CONNECTED_PEERS, MAX_CONNECTED_PEERS, NUM_RAREST_PIECES
from ..utils.helpers import logger

"""
Strategy Interface:
    def choose_peers(self, peers: list[Peer]) -> list[Peer]:
    def assign_pieces(self, remaining_pieces, peers: list[Peer]):
    def send_haves(self, completed_pieces, actual_bitfield, peers):
    def determine_additional_peers(self, file, connected_peers: list[Peer]) -> int:
"""
class Strategy():
    def choose_peers(self, peers: list[Peer]) -> list[Peer]:
        """
        Given a list of peers, return a list of peers to unchoke.
        """
        # filter out for connected, and interested
        connected = [peer for peer in peers if peer.tcp_established and peer.peer_interested]
        top_four = Strategy.get_top_four(connected)
        not_top_four = [peer for peer in connected if peer not in top_four]
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

    def shuffle_pieces(self, remaining_pieces, peers: list[Peer]):
        """Shuffles piece assignments, may be useful in some cases but not called currently"""
        # set comprehension
        all_peers = {peer for peer in peers if not peer.peer_choking and peer.am_interested}
        for peer in all_peers:
            peer.target_piece = None

    def send_haves(self, completed_pieces, actual_bitfield, peers):
        for peer in peers:
            for piece in completed_pieces:
                peer.send_have(piece)

    def determine_additional_peers(self, file, connected_peers: list[Peer]) -> int:
        if len(connected_peers) < MIN_CONNECTED_PEERS:
            return MAX_CONNECTED_PEERS - len(connected_peers)
        else:
            return 0

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
        # bugfix: we wanted to check if has_pieces was not empty, this accomplishes that
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
    pass

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