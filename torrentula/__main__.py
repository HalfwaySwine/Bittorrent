from .utils.helpers import configure_logging, parse_arguments, validate_arguments
from .core.client import Client
from .core.strategy import Strategy, RarestFirstStrategy, PropShareStrategy, RandomStrategy


def main():
    args = parse_arguments()
    validate_arguments(args.torr, args.dest)
    configure_logging(args)
    # Initialize client object which unpacks the torrent file.
    if args.rarest:
        strategy = RarestFirstStrategy
    elif args.propshare:
        strategy = PropShareStrategy
    elif args.random:
        strategy = RandomStrategy
    else:
        strategy = Strategy

    kwargs = {
        "torrent_file": args.torr,
        "destination": args.dest,
        "strategy": strategy,
        "clean": args.clean,
        "port": args.port,
        "nat": args.nat,
        "endgame_threshold": args.endgame,
        "loopback_ports": args.loopback,
        "internal": args.internal,
    }
    client = Client(**kwargs)

    if args.tui:
        import curses
        curses.wrapper(client.download_torrent)
    else:
        client.download_torrent()

    if args.seed:
        client.seed_torrent()


if __name__ == "__main__":
    main()
