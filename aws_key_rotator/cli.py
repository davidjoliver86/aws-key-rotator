import os
import argparse

DEFAULT_CREDENTIALS_FILE = os.path.expanduser("~/.aws/credentials")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--credentials",
        default=DEFAULT_CREDENTIALS_FILE,
        help="Path to AWS credentials file",
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
    parser.parse_args()


def main():
    parse_args()
