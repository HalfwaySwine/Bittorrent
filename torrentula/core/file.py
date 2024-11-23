from .piece import Piece
from math import ceil


class File:
    def __init__(self, name, length, piece_length, hashes):
        self.pieces = [Piece(i, piece_length) for i in range(len(hashes))]
        self.bitfield = self.load_bitfield_from_disk()
        self.piece_length = piece_length
        self.name = name
        self.length = length
        self.hashes = hashes

    def write_bitfield_to_disk(self):
        """
        Writes bitfield to disk to save progress.
        """
        pass

    def load_bitfield_from_disk(self):
        """
        Loads bitfield from disk (if it exists) to restart where previous download left off.
        """

        # Bitfield does not exist
        return [0 for _ in range(ceil(length / piece_length))]

    def update_bitfield(piece, value):
        pass

    def get_progress(self) -> str:
        pass

    def get_missing_pieces(self) -> list:
        pass
