import logging
import argparse
import os
import sys
from ..config import LOG_FILENAME, LOG_DIRECTORY, BITTORRENT_PORT

logger = logging.getLogger(LOG_FILENAME)

from enum import Enum


class Status(Enum):
    SUCCESS = "Success"
    FAILURE = "Failure"
    IN_PROGRESS = "In Progress"


def configure_logging(args):
    """
    Configures global logger variable for convenient logging to file.
    """
    logger.propagate = False  # Do not print logs to stderr unless explicitly set.
    if args.debug:
        logging_level = logging.DEBUG
        logger.info("Logging set to debug level.")
    elif args.info:
        logging_level = logging.INFO
        logger.info("Logging set to info level.")
    else:  # Default
        logging_level = logging.ERROR
        logger.info("Logging set to default level.")
    logger.setLevel(logging_level)  # Set level for top-level logger.

    if args.verbose:
        console_log = True
    else:
        console_log = False

    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s (%(module)s.%(funcName)s:%(lineno)d)")
        # Configure output to log file.
        file_handler = logging.FileHandler(os.path.join(LOG_DIRECTORY, LOG_FILENAME))
        file_handler.setLevel(logging_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        # Configure output to console (stderr).
        if console_log:
            logger.info("Logging to console.")
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(logging_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        else:
            logger.info("Not logging to console.")

    logger.info(f"Logger initialized to level={logger.level} and console_log={console_log}.")


def parse_loopback_ports(value):
    try:
        return [int(port) for port in value.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError("Ports must be a comma-separated list of integers.")


def parse_arguments():
    parser = argparse.ArgumentParser(description="A BitTorrent client to download a .torrent file from its distributed swarm.")
    parser.add_argument(
        "--torr",
        "-t",
        type=str,
        required=True,
        help="The relative path to a .torrent file (from the current directory).",
    )
    parser.add_argument(
        "--dest",
        "-d",
        type=str,
        default=".",
        help="The relative path of the destination directory where the downloaded file will be saved (default: current directory).",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=BITTORRENT_PORT,
        help="The port that the client will listen for incoming connections on.",
    )
    parser.add_argument(
        "--endgame",
        type=int,
        default=101,
        help="The progress percentage that will activate endgame mode.",
    )
    parser.add_argument(
        "--loopback",
        type=parse_loopback_ports,
        default=[],
        help="Comma-separated list of ports to connect to via loopback.",
    )
    parser.add_argument(
        "--nat",
        "-n",
        action="store_true",
        help="Request a public IP and port for NAT traversal.",
    )
    parser.add_argument(
        "--clean",
        "-c",
        action="store_true",
        help="Remove partially downloaded artifacts for the given torrent file in the destination directory before starting download.",
    )
    parser.add_argument(
        "--seed",
        "-s",
        action="store_true",
        help="Seed the torrent file after acquiring the complete file.",
    )
    display_group = parser.add_mutually_exclusive_group()  # User can select one display: verbose (logs) or tui (textual user interface).
    display_group.add_argument(
        "--tui",
        action="store_true",
        help="View download progress in a textual user interface.",
    )
    display_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Include logs with console output (stderr).",
    )
    log_group = parser.add_mutually_exclusive_group()  # User can select one level: debug, info, or none (default).
    log_group.add_argument(
        "--debug",
        action="store_true",
        help="Set logger to debug level (most verbose).",
    )
    log_group.add_argument(
        "--info",
        action="store_true",
        help="Set logger to info level.",
    )
    strategy_group = parser.add_mutually_exclusive_group()  # User can select one strategy: rarest, propshare, or basic (default).
    strategy_group.add_argument(
        "--rarest",
        action="store_true",
        help="Set strategy to rarest first.",
    )
    strategy_group.add_argument(
        "--random",
        action="store_true",
        help="Set strategy to random piece assignment.",
    )
    strategy_group.add_argument(
        "--propshare",
        action="store_true",
        help="Set strategy to proportional share.",
    )
    args = parser.parse_args()
    logging.info(f"Parsed arguments: torr={args.torr}, dest={args.dest}")
    return args


def validate_arguments(torr, dest):
    if not os.path.isfile(torr):
        print(f"Error: The torrent file '{torr}' does not exist")
        sys.exit(1)
    if not os.path.isdir(dest):
        print(f"Error: the destination '{dest}' is not a valid directory.")
        sys.exit(1)
    logger.info("Arguments validated successfully.")
