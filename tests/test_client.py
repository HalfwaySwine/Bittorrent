import sys
import os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)
import torrentula

client = torrentula.Client("tests/fixtures/alice.torrent")
client.download_torrent()