import logging
import argparse
import os
import sys
from ..config import LOG_FILENAME, LOG_DIRECTORY

logger = logging.getLogger(LOG_FILENAME)


def configure_logging():
    """
    Configures global logger variable for convenient logging to file.
    """
    logger.setLevel(logging.DEBUG)
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler = logging.FileHandler(os.path.join(LOG_DIRECTORY, LOG_FILENAME))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    # logger.propagate = False # Uncomment to have logs additionally print to stderr
    logger.info("Logger initialized.")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="A BitTorrent client to download a .torrent file from its distributed swarm."
    )
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
