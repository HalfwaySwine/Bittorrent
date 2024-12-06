from .peer import Peer
from random import choice
from ..config import MIN_CONNECTED_PEERS, MAX_CONNECTED_PEERS, NUM_RAREST_PIECES


class Strategy:
    def choose_peers(self, peers: list[Peer]) -> list[Peer]:
        """
        Given a list of peers, return a list of peers to unchoke.
        """
        top_four = Strategy.get_top_four(peers)
        not_top_four = [peer for peer in peers if peer not in top_four]
        optimistic_unchoke = [Strategy.get_optimistic_unchoke(not_top_four)] if not_top_four else []
        return top_four + optimistic_unchoke

    def assign_pieces(self, remaining_pieces, peers: list[Peer]):
        """
        Given a list of peers (which contains their bitfields and whether they've unchoked us) and remaining pieces to download, returns a list of the rarest pieces to request from each.
        """
        rarest_pieces = Strategy.calculate_rarest_pieces(peers)
        if not rarest_pieces:
            return
        unchoked_waiting_peers = [
            peer for peer in peers if not peer.peer_choking and peer.am_interested and peer.target_piece is None
        ]
        for peer in unchoked_waiting_peers:
            peer.target_piece = Strategy.choose_rarest_piece_with_randomness(rarest_pieces, peer)
            assert (
                peer.target_piece is not None
            ), "Client should not be interested in a peer that has no desired pieces."

    def send_bitfields(self, actual_bitfield, peers):
        for peer in peers:
            peer.send_bitfield(actual_bitfield)

    def send_haves(self, completed_pieces, actual_bitfield, peers):
        for peer in peers:
            for piece in completed_pieces:
                peer.send_have(piece)

    # Helper methods
    @classmethod
    def choose_rarest_piece_with_randomness(cls, rarest_pieces, peer):
        """
        Returns the rarest piece that a peer possesses.
        """
        has_pieces = []
        for piece in rarest_pieces:
            if peer.bitfield[piece] == True:
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

    @classmethod
    def determine_additional_peers(cls, file, peers: list[Peer]):
        connected_peers = [peer for peer in peers if peer.is_connected]
        if len(connected_peers) < MIN_CONNECTED_PEERS:
            return MAX_CONNECTED_PEERS - len(connected_peers)
        else:
            return 0
