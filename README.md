# AWS Key Rotator

Rotates your AWS IAM keys automatically.

## Installation
* Requires Python 3.6+.
* `pip install --user aws-key-rotator`

## Usage
Parses your AWS credentials file, looking for `aws_access_key_id` and `aws_secret_access_key`
keys, then automatically rotates them.

## Cron
It's highly recommended to run this as a cron. Ideally, run this daily, and set the time
to one where your computer is most likely on.

### Behavior
Due to the AWS limit of two access/secret keys per user, the behavior of this script will
vary depending on your situation.

* *If you have only one active access key:*
  * The current access key credentials are used to create the new key.
  * The now-old keys' credentials are then used to inactivate themselves.
  * The new keys are written to the credentials file.

* *If you have one active and one inactive key:*
  * The inactive key will be deleted.
  * The current access key credentials are used to create the new key.
  * The now-old keys' credentials are then used to inactivate themselves.
  * The new keys are written to the credentials file.

* *If you have two active keys:*
  * The key *NOT* matching that in the credentials file is deleted.
  * The other access key credentials are used to create the new key.
  * The now-old keys' credentials are then used to inactivate themselves.
  * The new keys are written to the credentials file.

## Arguments
* `-c`, `--credentials`: Path to your AWS credentials file (default: `~/.aws/credentials`).
* `-v`, `--verbose`: More verbose output (default: `False`).
* `--include`: Comma-separated list of profile names; only rotate these profiles' keys.
  Cannot be used with `--exclude`.
* `--exclude`: Comma-separated list of profile names; rotate all profiles EXCEPT these.
  Cannot be used with `--include`.
