import sys
import os
import unittest

# Add parent directory to sys.path to make 'torrentula' package importable
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)
import torrentula


class ClientTests(unittest.TestCase):
    """
    Usage: python -m unittest discover
    Will run any tests matching the pattern 'test*.py'
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_client_setup(self):
        """
        Example test. Not implemented yet.
        """
        client = torrentula.Client("./tests/fixtures/debian-mac.torrent")
        self.assertIsNotNone(client.peer_id)
        client.download_torrent()


if __name__ == "__main__":
    unittest.main()
