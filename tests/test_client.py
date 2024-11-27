import unittest
from tests import torrentula

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
