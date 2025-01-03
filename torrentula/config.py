APP_NAME = "Torrentula"
REQUEST_BLOCK_SIZE_BYTES = 2**14
MAX_BLOCK_SIZE = 2**17
MIN_PIECE_SIZE = 2**18
VERSION = "1.0.0"
LOG_FILENAME = f"{APP_NAME.lower()}.log"
LOG_DIRECTORY = "logs"
PEER_INACTIVITY_TIMEOUT_SECS = 120
EPOCH_DURATION_SECS = 10  # From BEP3, the official BitTorrent v1 specification
PEER_ID_LENGTH = 20
HTTP_PORT = 0
BITTORRENT_PORT = 6881
IN_PROGRESS_FILENAME_SUFFIX = ".part"
BITFIELD_FILE_SUFFIX = ".bitfield"
MAX_CONNECTION_ATTEMPTS = 10
LOOPBACK_IP = "127.0.0.1"

# Primary performance tuning parameters
ENDGAME_THRESHOLD = 95
NUM_RAREST_PIECES = 60  # The number of top rarest pieces to randomly choose from.
# basically want to stop egregious request backlog
MAX_PEER_OUTSTANDING_REQUESTS = 100
MAX_CONNECTED_PEERS = 55
MIN_CONNECTED_PEERS = 30
TRACKER_NUMWANT = 80
PIECE_TIMEOUT_SECS = 1