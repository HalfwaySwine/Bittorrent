from .piece import Piece
from math import ceil
from pathlib import Path


class File:
    def __init__(self, name, destination, length, piece_length, hashes):
        self.pieces = [Piece(index, piece_length, hash, length, destination) for index, hash in enumerate(hashes)]
        self.piece_length = piece_length
        self.name = name
        self.destination = destination
        self.length = length
        self.bitfield: list[int] = self.load_bitfield_from_disk()

    def get_bitfield(self):
        return self.bitfield
    
    def write_bitfield_to_disk(self):
        """
        Writes bitfield to disk to save progress.
        """
        path = Path(self.destination) / f"{self.name}.bitfield"
        with open(path, "w") as file:
            for bit in self.bitfield:
                file.write(str(bit))

    def load_bitfield_from_disk(self):
        """
        Loads bitfield from disk (if it exists) to restart where previous download left off.
        """
        if False:
            # Bitfield exists on disk
            raise NotImplementedError("This function has not been implemented yet.")
        else:
            # Bitfield does not exist
            return [0 for _ in range(ceil(self.length / self.piece_length))]

    def update_bitfield(self) -> list[int]:
        """
        Scans through progress on pieces to update bitfield in memory and write it to disk to save any progress. Returns a list of indices representing newly completed pieces.
        """
        newly_completed = []
        for index, bit in enumerate(self.bitfield):
            if bit == 0 and self.pieces[index].complete:
                newly_completed.append(index)
                self.bitfield[index] = 1

        if not newly_completed.empty():
            self.write_bitfield_to_disk()
        return newly_completed

    def __str__(self):
        print("===Overall===")
        print(f"Progress: {get_total_downloaded()}")
        
        print("===Pieces===")
        for index, piece in enumerate(self.pieces):
            print(index, ": ", piece)

    def get_download_percents(self) -> str:
        return [piece.get_download_percent() for piece in self.pieces]
    
    def get_total_downloaded(self) -> str:
        total = 0
        for piece in pieces:
            total += piece.downloaded
        return total

    def get_missing_pieces(self) -> list[int]:
        missing = []
        for index, bit in enumerate(self.bitfield):
            if bit == 0:
                missing.append(index)
        return missing
        

    def complete(self) -> bool:
        """Returns True if file is complete, False otherwise."""
        return self.get_missing_pieces() == []
