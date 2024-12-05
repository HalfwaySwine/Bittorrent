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
        if os.path.exists(self.torrent_path):
            self.file = open(self.torrent_path, "wb+")
            logger.debug("In-progress download file already exists.")
        else:
            self.file = open(self.torrent_path, "wb+")
            self.file.write(b"\x00" * self.length)
            logger.debug(f"Created empty in-progress download file with size {self.length}.")

    # returns bitfield
    def get_bitfield(self):
        return self.bitfield

    # writes the updated bitfield to the file
    def write_bitfield_to_disk(self):
        logger.debug("Attempting to write bitfield to disk")
        """
        Writes bitfield to disk to save progress.
        """
        try:
            with open(self.bitfield_path, "w") as file:
                for bit in self.bitfield:
                    file.write(str(bit))
        except OSError as e:
            print(f"Error writing bitfield to disk: {e}")
            logger.debug("Error writing bitfield to disk")

    # loads or creates bitfield in file
    def load_bitfield_from_disk(self):
        logger.debug("attempting to load bitfield from disk")
        """
        Loads bitfield from disk (if it exists) to restart where previous download left off.
        """
        try:
            if os.path.isfile(self.bitfield_path):  # already there
                with open(self.bitfield_path, "r+") as file1:
                    bitfield = [int(char) for char in file1.read().strip()]
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
        return newly_completed

    # toString
    def __str__(self):
        print("===Overall===")
        print(f"Progress: {self.get_total_downloaded()} / {self.length}")

        print("===Pieces===")
        for index, piece in enumerate(self.pieces):
            print(index, ": ", piece)

    # returns list of download precents per piece
    def get_download_percents(self) -> str:
        return [piece.get_download_percent() for piece in self.pieces]

    # gets downloaded amount from piece
    def get_total_downloaded(self) -> str:
        total = 0
        for piece in self.pieces:
            total += piece.downloaded
        return total

    # checks if file has piece undownloaded (helper)
    def get_missing_pieces(self):
        missing = []
        for index, bit in enumerate(self.bitfield):
            if bit == 0:
                missing.append(index)
        return missing

    # checks if file has piece downloaded (helper)
    def get_has_pieces(self):
        has = []
        for index, bit in enumerate(self.bitfield):
            if bit == 1:
                has.append(index)
        return has

    # returns true or false if file is complete
    def complete(self) -> bool:
        """Returns True if file is complete, False otherwise."""
        return self.get_missing_pieces() == []

    # calcs how many bytes are left of verified data
    def bytes_left(self) -> int:
        logger.debug("attempting bytes left")
        """
        Returns the number of bytes this client still has left to download.   
        """
        total = 0
        for piece_index in self.get_missing_pieces():
            print(total)
            total += self.pieces[piece_index].length
        logger.info(f"{total} bytes left")
        return total

    # calcs how many bytes have been downloaded of verfied data
    def bytes_downloaded(self) -> int:
        logger.debug("attempting bytes downloaded")
        """
        Returns the number of bytes this client has downloaded 
        """
        return sum(self.pieces[piece_index].length for piece_index in self.get_has_pieces())

    # helper to get the bytes left/downloaded based on unverifed data (bytesLeft is boolean)
    def bytes_verified_unverified(self, bytesLeft):
        logger.debug("attempting bytes downloaded/left v2")
        total = 0
        if bytesLeft:  # gets bytes left
            for i in self.pieces:
                total += i.length - i.downloaded
        else:  # gets bytes downloaded
            for i in self.pieces:
                total += i.downloaded
        return total

    # removes the .part when the file is complete
    def rename(self, new):
        old = Path(self.destination) / self.name
        os.rename(old, new)
        logger.info("Renamed file from '{old}' to '{new}'.")

    # removes bitfield from file
    def remove_bitfield_from_disk(self):
        os.remove(self.bitfield_path)
        logger.info("Removed bitfield from disk.")
