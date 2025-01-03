from .piece import Piece
from math import ceil
from pathlib import Path
import os
from ..config import BITFIELD_FILE_SUFFIX, IN_PROGRESS_FILENAME_SUFFIX, ENDGAME_THRESHOLD
from ..utils.helpers import logger


class File:
    def __init__(self, name, destination, length, piece_length, hashes, clean=False, endgame_threshold=ENDGAME_THRESHOLD):
        self.piece_length = piece_length
        self.name = name
        self.destination = destination
        self.hashes = hashes
        self.bitfield_path = Path(destination) / f"{name}{BITFIELD_FILE_SUFFIX}"
        self.torrent_path = Path(destination) / f"{name}{IN_PROGRESS_FILENAME_SUFFIX}"
        self.final_path = Path(self.destination) / self.name
        if clean:
            self.remove_artifacts()
        self.length = length
        self.initialize_file()
        self.total_uploaded = 0  # In bytes
        self.initialize_pieces()
        self.bitfield: list[int] = self.load_bitfield_from_disk()
        self.initialize_missing_pieces()
        self.endgame_mode = False
        self.endgame_threshold = endgame_threshold

    def initialize_pieces(self):
        logger.debug("Initializing pieces...")
        self.pieces: list[Piece] = [Piece(index, self.piece_length, hash, self.length, self.torrent_path, self.file) for index, hash in enumerate(self.hashes)]
        self.pieces[-1].length = self.length - (len(self.pieces) - 1) * self.piece_length
        logger.debug(f"File - last piece length {self.length - (len(self.pieces) - 1) * self.piece_length}")

    def seed_file(self):
        """
        Open complete file for seeding and initialize bitfield to all ones.
        """
        self.file = open(self.torrent_path, "rb")
        self.bitfield = [1] * len(self.hashes)
        self.write_bitfield_to_disk()
        self.initialize_pieces()

    def remove_artifacts(self):
        for path in [self.bitfield_path, self.torrent_path, self.final_path]:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Running with '--clean' argument: removed file '{path}'")

    def initialize_file(self):
        if os.path.exists(self.final_path):  # Assume file already completely downloaded
            self.torrent_path = self.final_path
            self.seed_file()  # TODO May be repetitive but still work.
        elif os.path.exists(self.torrent_path):  # Open existing file without overwriting
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
        """
        Loads bitfield from disk (if it exists) to restart where previous download left off.
        Marks already completed pieces as complete.
        """
        logger.debug("Attempting to load bitfield from disk")
        try:
            # Check if bitfield and partially downloaded file already exists.
            if os.path.isfile(self.bitfield_path) and os.path.isfile(self.torrent_path):
                with open(self.bitfield_path, "r+") as file1:
                    bitfield = [int(char) for char in file1.read().strip()]
                    # Use the stored bitfield data to mark the appropriate pieces as already completed.
                    for index, bit in enumerate(bitfield):
                        if bit == 1:
                            self.pieces[index].set_complete_from_prev_download()
                    logger.info(f"Successfully reloaded progress from bitfield on disk: {bitfield}")
                    return bitfield
            else:  # Bitfield does not exist
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
                self.missing_pieces_set.remove(index)
                newly_completed.append(index)
                self.bitfield[index] = 1

        if newly_completed:  # Bitfield was updated
            self.write_bitfield_to_disk()
            logger.debug("Bitfield updated!")
            logger.debug(
                f"{self.total_downloaded_percentage():.2f}% downloaded (verified), {self.total_downloaded_unverified_percentage():.2f}% downloaded (unverified)"
            )
        # Set all pieces to endgame mode when threshold is surpassed.
        if self.endgame_threshold < 100 and self.total_downloaded_percentage() > self.endgame_threshold and not self.endgame_mode:
            self.endgame_mode = True
            for piece in self.pieces:
                piece.endgame_mode = True

        return newly_completed

    def get_progress(self):
        return f"{self.total_downloaded_percentage():.2f}% ({self.bytes_downloaded() / 1_000_000:.2f} MB of {self.length / 1_000_000:.2f} MB)"

    def __str__(self):
        print("===Overall===")
        print(f"Progress: {self.bytes_downloaded()} / {self.length} ({self.total_downloaded_percentage():.2f}%)")

        print("===Pieces===")
        for index, piece in enumerate(self.pieces):
            print(index, ": ", piece)

    def piece_download_percentages(self) -> str:
        """Returns a list of download percentages by piece."""
        return [piece.get_download_percent() for piece in self.pieces]

    def total_downloaded_percentage(self):
        """Get total download percent for verified data"""
        return (self.bytes_downloaded() / self.length) * 100

    def total_downloaded_unverified_percentage(self):
        """Get total download percent for unverified data"""
        return (self.bytes_downloaded_unverified() / self.length) * 100

    def missing_pieces(self):
        """Returns a list of pieces that have not yet been fully downloaded and/or verified."""
        return self.missing_pieces_set

    def initialize_missing_pieces(self):
        self.missing_pieces_set = set()
        for index, bit in enumerate(self.bitfield):
            if bit == 0:
                self.missing_pieces_set.add(index)

    def has_pieces(self):
        """Returns a list of pieces that have been downloaded and verified."""
        has = []
        for index, bit in enumerate(self.bitfield):
            if bit == 1:
                has.append(index)
        return has

    def complete(self) -> bool:
        """Returns True if file is complete, False otherwise."""
        return not self.missing_pieces()

    def bytes_left(self) -> int:
        """
        Returns the number of bytes this client still has left to download (based on verified data).
        """
        logger.debug("Calculating bytes left...")
        total = 0
        for piece_index in self.missing_pieces():
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

    def bytes_uploaded(self):
        logger.debug(f"{self.total_uploaded} bytes uploaded")
        return self.total_uploaded

    def bytes_downloaded_unverified(self):
        """
        Returns the number of bytes this client still has downloaded (based on unverified data).
        """
        total = 0
        for piece in self.pieces:
            total += piece.downloaded
        logger.debug(f"{total} bytes downloaded (based on unverified data)")
        return total

    def get_data_from_piece(self, offset, length, index):
        for i, piece in enumerate(self.pieces):
            if i == index:
                data = piece.get_data_from_file(offset, length)
                return data
        return 0

    def rename(self, new):
        """Renames the file. Used when the download is complete to remove the temporary suffix."""
        old = self.torrent_path
        os.rename(old, new)
        self.torrent_path = new
        logger.info(f"Renamed file from '{old}' to '{new}'.")

    def remove_bitfield_from_disk(self):
        os.remove(self.bitfield_path)
        logger.info("Removed bitfield from disk.")

    def close_file(self):
        if self.file:
            self.file.close()
