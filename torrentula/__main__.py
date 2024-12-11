from .utils.helpers import configure_logging, parse_arguments, validate_arguments
from .core.client import Client
from .core.strategy import Strategy, RarestFirstStrategy, PropShareStrategy


def main():
    args = parse_arguments()
    validate_arguments(args.torr, args.dest)
    configure_logging(args)
    # Initialize client object which unpacks the torrent file.
    if args.rarest:
        strategy = RarestFirstStrategy
    elif args.propshare:
        strategy = PropShareStrategy
    else:
        strategy = Strategy
    
    client = Client(args.torr, args.dest, strategy, args.clean)
    if args.tui:
        import curses
        curses.wrapper(client.download_torrent)
    else:
        client.download_torrent()


if __name__ == "__main__":
    main()
