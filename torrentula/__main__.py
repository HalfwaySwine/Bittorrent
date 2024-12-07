from .utils.helpers import configure_logging, parse_arguments, validate_arguments
from .core.client import Client


def main():
    args = parse_arguments()
    validate_arguments(args.torr, args.dest)
    configure_logging(args)
    # Initialize client object which unpacks the torrent file.
    client = Client(args.torr, args.dest)
    client.download_torrent()


if __name__ == "__main__":
    main()
