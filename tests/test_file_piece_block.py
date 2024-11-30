#test for file/piece/blokc 

import hashlib
import os
import sys
import unittest
import filecmp

# Add parent directory to sys.path to make 'torrentula' package importable
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)
import torrentula

PIECE_LENGTH = 64 * 1024  # 64 KB piece size
BLOCK_SIZE = 16 * 1024    # 16 KB block size
HASH = hashlib.sha1(
    (b"test_piece_data" * ((PIECE_LENGTH // len("test_piece_data")) + 1))[:PIECE_LENGTH]
).digest()
TORRENT_PATH = "test_piece.torrent"  # Test file path
ADD_PATH = "thisistest.part"

class testPiece(unittest.TestCase):
    """
    Usage: python -m unittest discover
    Will run any tests matching the pattern 'test*.py'
    """
    def setUp(self):
        """Set up test environment by creating a dummy torrent file."""
        self.data = (b"test_piece_data" * ((PIECE_LENGTH // len("test_piece_data")) + 1))[:PIECE_LENGTH]
        with open(TORRENT_PATH, "wb") as f:
            f.write(self.data)
        
        f = open(ADD_PATH, "x")
       
        self.piece = torrentula.Piece(0, PIECE_LENGTH, HASH, PIECE_LENGTH, ADD_PATH)
        print(f"Expected Piece Length: {PIECE_LENGTH}, Actual Data Length: {len(self.data)}")

    def tearDown(self):
        """Clean up test environment by removing the test file."""
        if os.path.exists(TORRENT_PATH):
            os.remove(TORRENT_PATH)
        if os.path.exists(ADD_PATH):
            os.remove(ADD_PATH)

    def are_files_equal(self, file1, file2):
        """Compare two files."""
        return filecmp.cmp(file1, file2, shallow=False)
                

    #test basic adding to peice class
    def test_add_block(self):
        print("test1")
        """Test adding blocks and checking download progress."""

        for offset in range(0, PIECE_LENGTH, BLOCK_SIZE):
            tup = self.piece.get_next_request()
            print(tup[0])
            self.assertEqual(offset, tup[0])
            self.assertEqual(BLOCK_SIZE, tup[1])
            block_data = self.data[offset:offset + BLOCK_SIZE]
            result = self.piece.add_block(offset, block_data)

        self.assertEqual(self.piece.get_next_request(), (None, None))   
        print(self.piece.get_download_percent())
        self.assertEqual(self.piece.get_download_percent(), 100.0)
        self.assertTrue(self.piece.complete)
        self.assertTrue(self.are_files_equal(TORRENT_PATH, ADD_PATH))
        #pull data from piece 
        for offset in range(0, PIECE_LENGTH, BLOCK_SIZE):
            self.assertEqual(len(self.piece.get_data_from_file(offset,BLOCK_SIZE)), BLOCK_SIZE)
    
    #test file with last block not same size
    def test_last_block_smaller(self):
        print("test2")
        """Test with a piece where the last block is smaller than BLOCK_SIZE."""
        smaller_piece_length = BLOCK_SIZE * 3 + 5000  # Example: 3 full blocks + 5000 bytes
        data = (b"test_piece_data" * ((smaller_piece_length // len("test_piece_data")) + 1))[:smaller_piece_length]
        hash = hashlib.sha1(data).digest()

        # Write the smaller piece to the torrent path
        with open(TORRENT_PATH, "wb") as f:
            f.write(data)

        # Create a new piece object with a smaller piece length
        piece = torrentula.Piece(0, smaller_piece_length, hash, PIECE_LENGTH, ADD_PATH)

        # Test adding blocks
        for offset in range(0, smaller_piece_length, BLOCK_SIZE):
            next_request = piece.get_next_request()
            print(next_request)
            self.assertEqual(offset, next_request[0])
            block_size = min(BLOCK_SIZE, smaller_piece_length - offset)
            self.assertEqual(block_size, next_request[1])

            # Add the block data
            block_data = data[offset:offset + block_size]
            result = piece.add_block(offset, block_data)

        # Ensure no further requests and verify piece completion
        self.assertEqual(piece.get_next_request(), (None, None))
        self.assertEqual(piece.get_download_percent(), 100.0)
        self.assertTrue(piece.complete)

        # Validate file writing
        piece._write_to_disk()
        self.assertTrue(self.are_files_equal(TORRENT_PATH, ADD_PATH))



if __name__ == "__main__":
    unittest.main()



