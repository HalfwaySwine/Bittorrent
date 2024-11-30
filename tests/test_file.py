import unittest
import os
import hashlib
import sys
from pathlib import Path
# Add parent directory to sys.path to make 'torrentula' package importable
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)
import torrentula

PIECE_LENGTH = 64 * 1024  # 64 KB piece size
FILE_LENGTH = PIECE_LENGTH * 5 + 12345  # Example: 5 full pieces + 12345 bytes
HASHES = [
    hashlib.sha1(b"piece_data_" + bytes([i])).digest() for i in range(6)
]  # 6 hashes (5 full pieces, 1 partial)
BITFIELD_PATH = "test_file.bitfield"
TORRENT_PATH = "test_file.part"

class TestFile(unittest.TestCase):
    def setUp(self):
        """Set up test environment by creating a dummy file and bitfield."""
        # Ensure directory structure
        self.destination = "test_destination"
        os.makedirs(self.destination, exist_ok=True)

        # Initialize File object
        self.file = torrentula.File(
            name="test_file",
            destination=self.destination,
            length=FILE_LENGTH,
            piece_length=PIECE_LENGTH,
            hashes=HASHES,
        )

    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.file.torrent_path):
            os.remove(self.file.torrent_path)
        if os.path.exists(self.file.bitfield_path):
            os.remove(self.file.bitfield_path)
        if os.path.exists(self.destination):
            os.rmdir(self.destination)

    def test_initialization(self):
        """Test that the File object initializes correctly."""
        self.assertEqual(len(self.file.pieces), 6)  # 5 full + 1 partial
        self.assertEqual(self.file.pieces[-1].length, 12345)  # Last piece size
        self.assertEqual(len(self.file.bitfield), 6)  # 1 bit per piece
        self.assertTrue(all(bit == 0 for bit in self.file.bitfield))  # All bits start at 0


    def test_update_bitfield(self):
        """Test updating the bitfield as pieces are completed."""
        # Simulate completing the first piece
        self.file.pieces[0].complete = True
        newly_completed = self.file.update_bitfield()
        self.assertEqual(newly_completed, [0])  # First piece now completed
        self.assertEqual(self.file.bitfield[0], 1)  # Bitfield updated
        self.assertEqual(self.file.bitfield[1], 0)

        # Simulate completing another piece
        self.file.pieces[1].complete = True
        newly_completed = self.file.update_bitfield()
        self.assertEqual(newly_completed, [1])  # Second piece now completed
        self.assertEqual(self.file.bitfield[1], 1)  # Bitfield updated


    def test_bytes_left(self):
        """Test calculation of bytes left to download."""
        # Initially, all bytes are left
        self.assertEqual(self.file.bytes_left(), FILE_LENGTH)

        # Simulate partial downloads
        print(self.file.bytes_left())
        self.file.pieces[0].downloaded = PIECE_LENGTH
        self.file.pieces[0].complete = True
        newly_completed = self.file.update_bitfield()
        self.assertEqual(newly_completed, [0])  # First piece now completed
        self.assertEqual(self.file.bitfield[0], 1) 
        self.assertEqual(self.file.bytes_left(), FILE_LENGTH - PIECE_LENGTH)
        print(self.file.bytes_left())

        self.file.pieces[-1].downloaded = 12345  # Last piece fully downloaded
        self.file.pieces[-1].complete = True
        newly_completed = self.file.update_bitfield()
        self.assertEqual(self.file.bytes_left(), FILE_LENGTH - PIECE_LENGTH - 12345)


    def test_bytes_downloaded(self):
        """Test calculation of bytes downloaded."""
        # Initially, nothing is downloaded
        self.assertEqual(self.file.bytes_downloaded(), 0)

        # Simulate downloads
        self.file.pieces[0].downloaded = PIECE_LENGTH
        self.file.pieces[0].complete = True
        newly_completed = self.file.update_bitfield()
        self.assertEqual(self.file.bytes_downloaded(), PIECE_LENGTH)

        self.file.pieces[-1].downloaded = 12345  # Last piece fully downloaded
        self.file.pieces[-1].complete = True
        newly_completed = self.file.update_bitfield()
        self.assertEqual(self.file.bytes_downloaded(), PIECE_LENGTH + 12345)

    def test_complete(self):
        """Test that file completeness is correctly detected."""
        # Initially, file is not complete
        self.assertFalse(self.file.complete())

        # Simulate all pieces completed
        for piece in self.file.pieces:
            piece.complete = True
        newly_completed = self.file.update_bitfield()
        self.assertTrue(self.file.complete())

    def test_bitfield_disk_operations(self):
        """Test saving and loading the bitfield to/from disk."""
        # Update the bitfield to simulate progress
        self.file.pieces[0].complete = True
        self.file.update_bitfield()

        # Write the bitfield to disk
        self.file.write_bitfield_to_disk()
        self.assertTrue(os.path.exists(self.file.bitfield_path))

        # Load the bitfield from disk and verify its contents
        loaded_bitfield = self.file.load_bitfield_from_disk()
        self.assertEqual(loaded_bitfield, [1, 0, 0, 0, 0, 0])

    def test_remove_bitfield(self):
        """Test removing the bitfield file."""
        # Create the bitfield file
        self.file.write_bitfield_to_disk()
        self.assertTrue(os.path.exists(self.file.bitfield_path))

        # Remove the bitfield file
        self.file.remove_bitfield_from_disk()
        self.assertFalse(os.path.exists(self.file.bitfield_path))

if __name__ == "__main__":
    unittest.main()
