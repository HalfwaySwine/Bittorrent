from .utils.helpers import configure_logging, parse_arguments, validate_arguments
from .core.client import Client


def main():
    configure_logging()
    args = parse_arguments()
    validate_arguments(args.torr, args.dest)
    # Initialize client object which unpacks the torrent file.
    client = Client(args.torr)
    client.download_torrent(args.torr, args.dest)


if __name__ == "__main__":
    main()
