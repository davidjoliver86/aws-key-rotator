import os
import types
from unittest.mock import patch, mock_open

import pytest
import boto3
import datetime

from aws_key_rotator import __version__, rotator


def credential_section(profile_name, access_key_and_secret_id):
    return """[{profile_name}]
aws_access_key_id = {access_key_and_secret_id}
aws_secret_access_key = {access_key_and_secret_id}
""".format(
        profile_name=profile_name, access_key_and_secret_id=access_key_and_secret_id
    )


ACCESS_KEY_RESPONSE_ONE_KEY = {
    "AccessKeyMetadata": [
        {
            "AccessKeyId": "asdf",
            "Status": "Active",
        }
    ]
}

ACCESS_KEY_RESPONSE_TWO_KEYS_ONE_ACTIVE = {
    "AccessKeyMetadata": [
        {
            "AccessKeyId": "asdf",
            "Status": "Active",
        },
        {
            "AccessKeyId": "sdfg",
            "Status": "Inactive",
        },
    ]
}

ACCESS_KEY_RESPONSE_TWO_KEYS_BOTH_ACTIVE = {
    "AccessKeyMetadata": [
        {
            "AccessKeyId": "asdf",
            "Status": "Active",
        },
        {
            "AccessKeyId": "sdfg",
            "Status": "Active",
        },
    ]
}


@pytest.fixture(scope="function")
def mock_iam_one_key():
    with patch("aws_key_rotator.rotator.boto3") as mock_boto:
        mock_session = mock_boto.Session()
        mock_iam = mock_session.client()
        mock_iam.list_access_keys.return_value = ACCESS_KEY_RESPONSE_ONE_KEY
        mock_iam.create_access_key.return_value = {
            "AccessKey": {
                "AccessKeyId": "asdf2",
                "SecretAccessKey": "asdf2",
            }
        }
        yield mock_iam


@pytest.fixture(scope="function")
def mock_iam_two_keys_one_inactive():
    with patch("aws_key_rotator.rotator.boto3") as mock_boto:
        mock_session = mock_boto.Session()
        mock_iam = mock_session.client()
        mock_iam.list_access_keys.return_value = ACCESS_KEY_RESPONSE_TWO_KEYS_ONE_ACTIVE
        mock_iam.create_access_key.return_value = {
            "AccessKey": {
                "AccessKeyId": "asdf2",
                "SecretAccessKey": "asdf2",
            }
        }
        yield mock_iam


@pytest.fixture(scope="function")
def mock_iam_two_keys_both_active():
    with patch("aws_key_rotator.rotator.boto3") as mock_boto:
        mock_session = mock_boto.Session()
        mock_iam = mock_session.client()
        mock_iam.list_access_keys.return_value = (
            ACCESS_KEY_RESPONSE_TWO_KEYS_BOTH_ACTIVE
        )
        mock_iam.create_access_key.return_value = {
            "AccessKey": {
                "AccessKeyId": "asdf2",
                "SecretAccessKey": "asdf2",
            }
        }
        yield mock_iam


@pytest.fixture(scope="function")
def config():
    yield types.SimpleNamespace(
        credentials="~/.aws/credentials", verbose=False, include=None, exclude=None
    )


def test_simple_rotation(config, mock_iam_one_key):
    """
    Simple use case of rotating one profile.
    """
    fake_creds_fp = mock_open(read_data=credential_section("default", "asdf"))
    with patch("builtins.open", fake_creds_fp):
        rotator.IAMKeyRotator(config).main()
    writes = "".join([call[0][0] for call in fake_creds_fp().write.call_args_list])
    assert credential_section("default", "asdf2") in writes


def test_two_profiles(config, mock_iam_one_key):
    """
    Rotating two different profiles.
    """
    creds_data = "{}\n\n{}".format(
        credential_section("default", "asdf"), credential_section("nondefault", "asdf")
    )
    fake_creds_fp = mock_open(read_data=creds_data)
    with patch("builtins.open", fake_creds_fp):
        rotator.IAMKeyRotator(config).main()
    writes = "".join([call[0][0] for call in fake_creds_fp().write.call_args_list])
    write_one = credential_section("default", "asdf2") in writes
    write_two = credential_section("nondefault", "asdf2") in writes
    assert write_one and write_two


def test_bad_credentials_nothing_happens(config, mock_iam_one_key):
    """
    If the credentials file doesn't contain both keys, nothing should happen.
    """
    creds_data = credential_section("default", "asdf")
    creds_data = creds_data.replace("aws_secret_access_key", "bad")
    fake_creds_fp = mock_open(read_data=creds_data)
    with patch("builtins.open", fake_creds_fp):
        rotator.IAMKeyRotator(config).main()
    total_calls = (
        mock_iam_one_key.create_access_key.call_count
        + mock_iam_one_key.update_access_key.call_count
        + mock_iam_one_key.delete_access_key.call_count
    )
    assert total_calls == 0


def test_simple_rotation_one_inactive(config, mock_iam_two_keys_one_inactive):
    """
    Rotating credentials with one active and one inactive key. When run regularly, this
    is the most common use case.
    """
    fake_creds_fp = mock_open(read_data=credential_section("default", "asdf"))
    with patch("builtins.open", fake_creds_fp):
        rotator.IAMKeyRotator(config).main()
    writes = "".join([call[0][0] for call in fake_creds_fp().write.call_args_list])
    assert credential_section("default", "asdf2") in writes


def test_simple_rotation_both_active(config, mock_iam_two_keys_both_active):
    """
    Simple use case of rotating one profile.
    """
    fake_creds_fp = mock_open(read_data=credential_section("default", "asdf"))
    with patch("builtins.open", fake_creds_fp):
        rotator.IAMKeyRotator(config).main()
    writes = "".join([call[0][0] for call in fake_creds_fp().write.call_args_list])
    assert credential_section("default", "asdf2") in writes


def test_version():
    assert __version__ == "0.1.2"
