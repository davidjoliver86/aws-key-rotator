import os
import types
from unittest.mock import patch, mock_open

import pytest
import boto3
import datetime

from aws_key_rotator import __version__, rotator


SAMPLE_CREDS_FILE_OLD = """[default]
aws_access_key_id = asdf
aws_secret_access_key = asdf
"""

SAMPLE_CREDS_FILE_NEW = """[default]
aws_access_key_id = asdf2
aws_secret_access_key = asdf2
"""

ACCESS_KEY_RESPONSE = {
    "AccessKeyMetadata": [
        {
            "AccessKeyId": "asdf",
            "Status": "Active",
        }
    ]
}


@pytest.fixture(scope="function")
def mock_iam():
    with patch("aws_key_rotator.rotator.boto3") as mock_boto:
        mock_session = mock_boto.Session()
        mock_iam = mock_session.client()
        mock_iam.list_access_keys.return_value = ACCESS_KEY_RESPONSE
        mock_iam.create_access_key.return_value = {
            "AccessKey": {
                "AccessKeyId": "asdf2",
                "SecretAccessKey": "asdf2",
            }
        }
        yield mock_iam


def test_default(mock_iam):
    config = types.SimpleNamespace(credentials="~/.aws/credentials")
    fake_creds_fp = mock_open(read_data=SAMPLE_CREDS_FILE_OLD)
    with patch("builtins.open", fake_creds_fp):
        rotator.IAMKeyRotator(config).main()
    writes = "".join([call[0][0] for call in fake_creds_fp().write.call_args_list])
    assert SAMPLE_CREDS_FILE_NEW in writes


def test_version():
    assert __version__ == "0.1.0"
