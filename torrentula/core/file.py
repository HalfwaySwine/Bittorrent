from .piece import Piece
from math import ceil
from pathlib import Path
import os
from ..config import BITFIELD_FILE_SUFFIX, IN_PROGRESS_FILENAME_SUFFIX
from ..utils.helpers import logger


class File:
    def __init__(self, name, destination, length, piece_length, hashes):
        self.piece_length = piece_length
        self.name = name
        self.destination = destination
        self.bitfield_path = Path(destination) / f"{name}{BITFIELD_FILE_SUFFIX}"
        self.torrent_path = Path(destination) / f"{name}{IN_PROGRESS_FILENAME_SUFFIX}"
        self.length = length
        self.initialize_file()
        logger.debug("Attepting to init pieces")
        self.pieces = [
            Piece(index, piece_length, hash, length, self.torrent_path, self.file) for index, hash in enumerate(hashes)
        ]
        self.pieces[-1].length = length - (len(self.pieces) - 1) * piece_length  # TODO check this
        logger.debug(f"File - last piece length {length - (len(self.pieces) - 1) * piece_length}")
        self.bitfield: list[int] = self.load_bitfield_from_disk()

    def initialize_file(self):
        if os.path.exists(self.torrent_path):  # Open existing file without overwriting
            self.file = open(self.torrent_path, "rb+")
            logger.debug("In-progress download file already exists.")
        else:  # Create a new empty file
            self.file = open(self.torrent_path, "wb+")
            self.file.write(b"\x00" * self.length)
            logger.debug(f"Created empty in-progress download file with size {self.length}.")

    def get_bitfield(self):
        return self.bitfield

    def write_bitfield_to_disk(self):
        """
        Writes bitfield to disk to save progress.
        """
        logger.debug("Attempting to write bitfield to disk")
        try:
            with open(self.bitfield_path, "w") as file:
                for bit in self.bitfield:
                    file.write(str(bit))
        except OSError as e:
            print(f"Error writing bitfield to disk: {e}")
            logger.debug("Error writing bitfield to disk")

    def load_bitfield_from_disk(self):
        logger.debug("attempting to load bitfield from disk")
        """
        Loads bitfield from disk (if it exists) to restart where previous download left off. If already done it will set downloaded pieces to complete
        """
        try:
            if os.path.isfile(self.bitfield_path):  # already there
                with open(self.bitfield_path, "r+") as file1:
                    bitfield = [int(char) for char in file1.read().strip()]
                    # set pieces that are comlpete to complete and downloaded
                    for index, bit in enumerate(bitfield): 
                        if bit == 1: 
                            self.pieces[index].set_complete_from_prev_download()
                    return bitfield
            else:  # doesn't exist yet
                bitfield = [0] * len(self.pieces)
                with open(self.bitfield_path, "w") as file1:
                    file1.write("".join(map(str, bitfield)))
                return bitfield
        except OSError as e:
            print(f"Error accessing bitfield file: {e}")
            logger.debug("Error accessing bitfield file")
        except ValueError as e:
            print(f"Error parsing bitfield data: {e}")
            logger.debug("Error parsing bitfield data")

    def update_bitfield(self):
        """
        Scans through progress on pieces to update bitfield in memory and writes it to disk to save any progress. Returns a list of indices representing newly completed pieces.
        """
        newly_completed = []
        for index, bit in enumerate(self.bitfield):
            if bit == 0 and self.pieces[index].complete:
                newly_completed.append(index)
                self.bitfield[index] = 1

        if newly_completed:  # Bitfield was updated
            logger.debug("Attempting to update bitfield...")
            self.write_bitfield_to_disk()
            logger.debug("Bitfield updated!")
            logger.info(
                f"{self.total_downloaded_percentage()}% downloaded (verified), {self.total_downloaded_unverified_percentage()}% downloaded (unverified)"
            )
        return newly_completed

    def __str__(self):
        print("===Overall===")
        print(f"Progress: {self.bytes_downloaded()} / {self.length}")

        print("===Pieces===")
        for index, piece in enumerate(self.pieces):
            print(index, ": ", piece)

    def piece_download_percentages(self) -> str:
        """Returns a list of download percentages by piece."""
        return [piece.get_download_percent() for piece in self.pieces]

    def total_downloaded_percentage(self):
        """Get total download percent for verified data"""
        return (self.bytes_downloaded_unverified() / self.length) * 100

    def total_downloaded_unverified_percentage(self):
        """Get total download percent for unverified data"""
        return (self.bytes_downloaded_unverified() / self.length) * 100

    def missing_pieces(self):
        """Returns a list of pieces that have not yet been fully downloaded and/or verified."""
        missing = []
        for index, bit in enumerate(self.bitfield):
            if bit == 0:
                missing.append(index)
        return missing

    def has_pieces(self):
        """Returns a list of pieces that have been downloaded and verified."""
        has = []
        for index, bit in enumerate(self.bitfield):
            if bit == 1:
                has.append(index)
        return has

    def complete(self) -> bool:
        """Returns True if file is complete, False otherwise."""
        return self.missing_pieces() == []

    def bytes_left(self) -> int:
        """
        Returns the number of bytes this client still has left to download (based on verified data).
        """
        logger.debug("Calculating bytes left...")
        total = 0
        for piece_index in self.missing_pieces():
            print(total)
            total += self.pieces[piece_index].length
        logger.debug(f"{total} bytes left")
        return total

    def bytes_downloaded(self) -> int:
        """
        Returns the number of bytes this client has downloaded that have also been verified.
        """
        total = sum(self.pieces[piece_index].length for piece_index in self.has_pieces())
        logger.debug(f"{total} bytes downloaded")
        return total

    def bytes_left_unverified(self):
        """
        Returns the number of bytes this client still has left to download (based on unverified data).
        """
        total = self.length - self.bytes_downloaded_unverified()
        logger.debug("{total} bytes left (based on unverified data)")
        return total

    def bytes_downloaded_unverified(self):
        """
        Returns the number of bytes this client still has downloaded (based on unverified data).
        """
        total = 0
        for piece in self.pieces:
            total += piece.downloaded
        logger.debug("{total} bytes downloaded (based on unverified data)")
        return total

    def rename(self, new):
        """Renames the file. Used when the download is complete to remove the temporary suffix."""
        old = Path(self.destination) / self.name
        os.rename(old, new)
        logger.info("Renamed file from '{old}' to '{new}'.")

    def remove_bitfield_from_disk(self):
        os.remove(self.bitfield_path)
        logger.info("Removed bitfield from disk.")

    def close_file(self):
        self.file.close()
