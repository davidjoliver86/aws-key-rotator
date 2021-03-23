import logging
from time import sleep
from configparser import ConfigParser
from contextlib import contextmanager
from collections import namedtuple

import boto3
import coloredlogs
from botocore.exceptions import ClientError

from . import constants

AccessKey = namedtuple("AccessKey", "id,status")


class MaximumRetriesExceeded(Exception):
    pass


def retry(attempts, sleep_time):
    """
    Retry decorator.

    Args:
        attempts (int): Number of attempts before throwing MaximumRetriesExceeded
        sleep_time (int): Time to sleep between attempts.
    Raises:
        MaximumRetriesExceeded
    """

    def inner(fn):
        def _inner(*args, **kwargs):
            for _ in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except ClientError as error:
                    if error.response["Error"]["Code"] == "InvalidClientTokenId":
                        sleep(sleep_time)
                    else:
                        raise error
            raise MaximumRetriesExceeded

        return _inner

    return inner


class IAMKeyRotator:
    def __init__(self, config):
        """
        Initialization.

        Args:
            config (argparse.Namespace): Config values taken directly from the
            ArgumentParser in cli.py.
        """
        self.config = config
        self.log = logging.getLogger(__name__)
        log_level = "DEBUG" if config.verbose else "INFO"
        coloredlogs.install(level=log_level, logger=self.log)

    @contextmanager
    def _credentials(self):
        """
        Wrapper around parsing the credentials file, then writing it back if any
        changes are made.

        Use this as a context manager - e.g.:

        with self._credentials() as parser:
            do_stuff(parser)

        Yields:
            ConfigParser: ConfigParser object around the AWS credentials file.
        """
        parser = ConfigParser()
        with open(self.config.credentials, "r") as fp:
            self.log.debug("Reading credentials file %s", self.config.credentials)
            parser.read_string(fp.read())
        yield parser
        with open(self.config.credentials, "w") as fp:
            self.log.debug("Writing to credentials file %s", self.config.credentials)
            parser.write(fp)

    @staticmethod
    def _contains_keypair(section):
        """
        Determine if this section of the credentials file contains an aws_access_key_id
        and aws_secret_access_key.

        Args:
            section (configparser.SectionProxy): The section of the credentials file.

        Returns:
            bool: Whether this section contains aws_access_key_id and aws_secret_access_key.
        """
        try:
            section[constants.AWS_ACCESS_KEY_ID]
            section[constants.AWS_SECRET_ACCESS_KEY]
            return True
        except KeyError:
            return False

    def _get_rotatable_profiles(self):
        """
        Parses the credentials file and returns a list of all profiles that contain
        both an aws_access_key_id and aws_secret_access_key.

        Returns:
            List[str]: List of available profiles that contain access key IDs.
        """
        with self._credentials() as parser:
            profiles = [
                section
                for section in parser.sections()
                if self._contains_keypair(parser[section])
            ]
        self.log.debug("Found profiles: %s", profiles)
        return profiles

    def _get_boto_session(self, profile_name):
        """
        Instantiates a boto session.

        Args:
            profile_name (str): Name of the connection profile to use for boto3.

        Returns:
            boto3.Session
        """
        self.log.debug("Instantiating boto session with profile %s", profile_name)
        return boto3.Session(profile_name=profile_name).client("iam")

    def _get_access_keys(self, iam):
        """
        Retrieves the users' access keys.

        Args:
            iam (boto3.Session): Boto3 session.

        Returns:
            List[AccessKey]: List of access keys and their status.
        """
        access_keys = [
            AccessKey(
                id=key[constants.BOTO_ACCESS_KEY_ID],
                status=key["Status"] == constants.ACTIVE,
            )
            for key in iam.list_access_keys()[constants.BOTO_ACCESS_KEY_METADATA]
        ]
        self.log.debug("Found access keys: %s", access_keys)
        return access_keys

    def _create_key(self, profile_name):
        """
        Creates a new access key, then immediately updates the credentials file with
        the new keys.

        Args:
            profile_name (str): Name of the connection profile to use for boto3.
            This also contains the credentials to be rotated.
        """
        # Instantiate session with current credentials.
        iam = self._get_boto_session(profile_name)
        new_key = iam.create_access_key()[constants.BOTO_ACCESS_KEY]
        self.log.info(
            "Created new access key %s", new_key[constants.BOTO_ACCESS_KEY_ID]
        )
        with self._credentials() as parser:
            parser[profile_name][constants.AWS_ACCESS_KEY_ID] = new_key[
                constants.BOTO_ACCESS_KEY_ID
            ]
            parser[profile_name][constants.AWS_SECRET_ACCESS_KEY] = new_key[
                constants.BOTO_SECRET_ACCESS_KEY
            ]
        self.log.debug("Wrote new credentials for profile %s", profile_name)

    @retry(attempts=20, sleep_time=3)
    def _inactivate_key(self, profile_name, access_key_id):
        """
        Inactivates the given access key.

        This is usually called immediately after _create_key() is called, which does
        update the credentials file locally. The retry decorator ensures that this is
        being called with the correct, new credentials.

        Args:
            profile_name (str): Name of the connection profile to use for boto3.
            access_key_id (str): Access key ID to inactivate.
        """
        self.log.debug("Attempting to inactivate access key %s", access_key_id)
        iam = self._get_boto_session(profile_name)
        iam.update_access_key(AccessKeyId=access_key_id, Status=constants.INACTIVE)
        self.log.warning("Inactivated access key %s", access_key_id)

    def _delete_key(self, profile_name, access_key_id):
        """
        Deletes the given access key.

        Args:
            profile_name (str): Name of the connection profile to use for boto3.
            access_key_id (str): Access key ID to delete.
        """
        self.log.debug("Attempting to delete access key %s", access_key_id)
        iam = self._get_boto_session(profile_name)
        iam.delete_access_key(AccessKeyId=access_key_id)
        self.log.warning("Deleted access key %s", access_key_id)

    def rotate_credentials(self, profile_name):
        """
        Performs IAM keypair rotation.

        Args:
            profile_name (str): Name of the connection profile to use for boto3.
        """
        self.log.info("Performing credential rotation for profile %s", profile_name)
        iam = self._get_boto_session(profile_name)
        access_keys = self._get_access_keys(iam)
        statuses = [access_key.status for access_key in access_keys]

        # Handling deletions and inactivations prior to issuing a new key. If we need
        # to delete a key due to the two key limit, we must do that first.

        if statuses == [True]:
            old_key = access_keys[0]
            self._create_key(profile_name)
            self._inactivate_key(profile_name, old_key.id)
        elif statuses in ([True, False], [False, True]):
            # Delete inactive key, use "current" active key to issue new key,
            # then deactivate the "current" key.
            if access_keys[0].status:
                current_active = access_keys[0]
                current_inactive = access_keys[1]
            else:
                current_active = access_keys[1]
                current_inactive = access_keys[0]
            self._delete_key(profile_name, current_inactive.id)
            self._create_key(profile_name)
            self._inactivate_key(profile_name, current_active.id)
        elif statuses == [True, True]:
            # Delete the key that does *not* match the one in the credentials file.
            # Then generate a new key and inactivate the old.
            with self._credentials() as parser:
                key_id_in_file = parser[profile_name][constants.AWS_ACCESS_KEY_ID]
            if key_id_in_file == access_keys[0].id:
                key_to_delete = access_keys[1]
                key_to_inactivate = access_keys[0]
            else:
                key_to_delete = access_keys[0]
                key_to_inactivate = access_keys[1]
            self._delete_key(profile_name, key_to_delete.id)
            self._create_key(profile_name)
            self._inactivate_key(profile_name, key_to_inactivate.id)
        self.log.info("Credential rotation successful for profile %s!", profile_name)

    def main(self):
        profiles = set(self._get_rotatable_profiles())
        if self.config.include:
            profiles &= set(self.config.include.split(","))
            self.log.debug("Profiles after inclusions: %s", profiles)
        if self.config.exclude:
            profiles -= set(self.config.exclude.split(","))
            self.log.debug("Profiles after exclusions: %s", profiles)
        for profile in profiles:
            self.rotate_credentials(profile)
