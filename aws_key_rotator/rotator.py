from configparser import ConfigParser
from contextlib import contextmanager
from collections import namedtuple

AccessKey = namedtuple("AccessKey", "id,status")

import boto3

ACTIVE = "Active"
INACTIVE = "Inactive"


class IAMKeyRotator:
    def __init__(self, config):
        """Initialization.

        Args:
            config (argparse.Namespace): Config values taken directly from the
            ArgumentParser in cli.py.
        """
        self.config = config

    @contextmanager
    def _credentials(self):
        """Wrapper around parsing the credentials file, then writing it back if any
        changes are made.

        Use this as a context manager - e.g.:

        with self._credentials() as parser:
            do_stuff(parser)

        Yields:
            ConfigParser: ConfigParser object around the AWS credentials file.
        """
        parser = ConfigParser()
        with open(self.config.credentials, "r") as fp:
            parser.read_file(fp)
        yield parser
        with open(self.config.credentials, "w") as fp:
            parser.write(fp)

    @staticmethod
    def _contains_keypair(section):
        """Determine if this section of the credentials file contains an aws_access_key_id
        and aws_secret_access_key.

        Args:
            section (configparser.SectionProxy): The section of the credentials file.

        Returns:
            bool: Whether this section contains aws_access_key_id and aws_secret_access_key.
        """
        try:
            section["aws_access_key_id"]
            section["aws_secret_access_key"]
            return True
        except KeyError:
            return False

    def _get_rotatable_profiles(self):
        """
        Parses the credentials file and returns a list of all profiles that contain
        both an aws_access_key_id and aws_secret_access_key.
        """
        with self._credentials() as parser:
            profiles = [
                section
                for section in parser.sections()
                if self._contains_keypair(parser[section])
            ]
        return profiles

    @staticmethod
    def _get_access_keys(iam):
        return [
            AccessKey(id=key["AccessKeyId"], status=key["Status"] == ACTIVE)
            for key in iam.list_access_keys()["AccessKeyMetadata"]
        ]

    def rotate_credentials(self, profile_name):
        """Performs IAM keypair rotation.

        Args:
            profile_name (str): The named section in the credentials file. Will be used
            to instantiate the boto3 connection.
        """
        iam = boto3.Session(profile_name=profile_name).client("iam")
        access_keys = self._get_access_keys(iam)
        statuses = [access_key.status for access_key in access_keys]

        # Handling deletions and inactivations prior to issuing a new key. If we need
        # to delete a key due to the two key limit, we must do that first.

        if statuses == [True]:
            # Deactivate current active key
            iam.update_access_key(AccessKeyId=access_keys[0].id, Status=INACTIVE)
        elif statuses in ([True, False], [False, True]):
            if access_keys[0].status:
                current_active = access_keys[0]
                current_inactive = access_keys[1]
            else:
                current_active = access_keys[1]
                current_inactive = access_keys[0]
            iam.delete_access_key(AccessKeyId=current_inactive.id)
            iam.update_access_key(AccessKeyId=current_active.id, Status=INACTIVE)
        elif statuses in ([True, True], [False, False]):
            # Delete key that matches one in credentials file
            pass

    def main(self):
        for profile in self._get_rotatable_profiles():
            self.rotate_credentials(profile)