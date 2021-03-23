import os
import argparse
from . import rotator

DEFAULT_CREDENTIALS_FILE = os.path.expanduser("~/.aws/credentials")

# Removes some of the extra verbosity in the log messages.
os.environ["COLOREDLOGS_LOG_FORMAT"] = "%(message)s"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--credentials",
        default=DEFAULT_CREDENTIALS_FILE,
        help="Path to AWS credentials file",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help="Verbose output"
    )

    include_or_exclude_list = parser.add_mutually_exclusive_group()
    include_or_exclude_list.add_argument(
        "--include",
        help="Comma separated list of profile names, will only rotate specified profiles' keys",
    )
    include_or_exclude_list.add_argument(
        "--exclude",
        help="Comma separated list of profile names, will rotate all profiles excluding specified",
    )
    return parser.parse_args()


def main():
    rotator.IAMKeyRotator(parse_args()).main()
