import logging
import argparse
import os
import sys
from ..config import LOG_FILENAME, LOG_DIRECTORY

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
    if args.debug:
        logger.propagate = True  # Additionally print logs to stderr.
        logger.info("Logging set to debug level.")
        logger.setLevel(logging.DEBUG)
    elif args.info:
        logger.propagate = True  # Additionally print logs to stderr.
        logger.info("Logging set to info level.")
        logger.setLevel(logging.INFO)
    else:  # Default
        logger.propagate = False  # Do not print logs to stderr.
        logger.info("Logging set to default level.")
        logger.setLevel(logging.WARNING)

    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s (%(module)s.%(funcName)s:%(lineno)d)")

        file_handler = logging.FileHandler(os.path.join(LOG_DIRECTORY, LOG_FILENAME))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    logger.info("Logger initialized.")


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
        "--clean",
        action="store_true",
        help="Remove partially downloaded artifacts for the given torrent file in the destination directory before starting download.",
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
