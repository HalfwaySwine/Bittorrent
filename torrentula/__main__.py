from .utils.helpers import configure_logging, parse_arguments, validate_arguments
from .core.client import Client

def main():
    configure_logging()
    #argument recv and validate
    args = parse_arguments()
    validate_arguments()
    #client object which parses the information form the torrent file and sets the nessary variables 
    client = Client(args.torr)
    client.download_torrent(args.torr, args.dest)
    


if __name__ == "__main__":
    main()
