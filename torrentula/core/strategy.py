from core.peer import Peer
from random import choice
from collections import Counter
from config import MIN_PEERS, MAX_PEERS 
NUM_RAREST_PIECES = 3 # The number of top rarest pieces to randomly choose from. 
class Strategy:
    def __init__(self):
        pass

    def choose_peers(self, peers: list[Peer]) -> list[Peer]:
        """
        Given a list of peers, return a list of peers to unchoke.
        """
        top_four = get_top_four(peers)
        not_top_four = [peer for peer in peers if peer not in top_four]
        optimistic_unchoke = get_optimistic_unchoke(not_top_four)
        return top_four + [optimistic_unchoke]

    def assign_pieces(self, remaining_pieces, peers: list[Peer]):
        """
        Given a list of peers (which contains their bitfields and whether they've unchoked us) and remaining pieces to download, returns a list of the rarest pieces to request from each.

        TODO Is there any guidance on how many different pieces to be pursuing at a given time?
        Or how many pieces to be pursuing from a given peer at once?
        Or how many requests to send out to peers that have unchoked us?
        """
        rarest_pieces = calculate_rarest_pieces(peers)
        unchoked_waiting_peers = [peer for peer in peers if peer.am_unchoked and peer.am_interested and peer.target_piece is None]
        for peer in unchoked_waiting_peers:
            peer.target_piece = choose_rarest_piece_with_randomness(rarest_pieces, peer)
            assert peer.target_piece is not None, "Client should not be interested in a peer that has no desired pieces."

    def send_bitfields(self, actual_bitfield, peers):
        for peer in peers:
            peer.send_bitfield(actual_bitfield)

    def send_haves(self, completed_pieces, actual_bitfield, peers):
        # TODO Implement strategic piece revelation
        for peer in self.peers:
            for piece in self.completed_pieces:
                peer.send_have(piece)

    def choose_requests(self, outstanding_requests, remaining_pieices, peers):
        pass


# Helper methods
def choose_rarest_piece_with_randomness(rarest_pieces, peer):
    """
    Returns the rarest piece that a peer possesses.
    """
    has_pieces = []
    for piece in rarest_pieces:
        if peer.bitfield[piece] == True:
            has_pieces.append(piece)
        if len(has_pieces) == NUM_RAREST_PIECES:
            break
    return choice(has_pieces) if not has_pieces.is_empty() else None

def calculate_rarest_pieces(peers: list[Peer]) -> list[int]:
    """
    Given a list of peers containing the peers' bitfield, returns a ranking of the rarest pieces, identified by their indices.
    """
    bitfields = [peer.bitfield for peer in peers]  # [[1, 0], [1, 1], [0, 0]]
    frequencies = [sum(respective_bits) for respective_bits in zip(*bitfields)]  # [[1, 1, 0], [0, 1, 0]]
    sorted_frequencies = sorted(enumerate(frequencies), key=lambda x: x[1], reverse=True)
    return [index for index, frequency in sorted_frequencies]  # Return the indices of the pieces


def get_top_four(peers: list[Peer]) -> list[Peer]:
    """
    Gets the top four ranking and interested peers in terms of bytes received within the last epoch.
    Also includes any peers that are not interesteed but higher than the fourth place peer. 
    """
    peers_sorted = sorted(peers, key=lambda x: x.bytes_received)
    # Return the top peers but cut the list off after the fourth interested peer.
    num_interested = 0
    cutoff = len(peers_sorted) - 1
    for index, peer in enumerate(peers_sorted):
        if peer.is_interested:
            num_interested += 1
        if num_interested == 4:
            cutoff = index
            break
    return peers_sorted[:cutoff + 1]


def get_optimistic_unchoke(peers: list[Peer]) -> Peer:
    return choice(peers)


def determine_additional_peers(file, peers):
    if len(peers) < MIN_PEERS:
        return MAX_PEERS - len(peers)