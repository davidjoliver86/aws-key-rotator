# AWS Key Rotator

Rotates your AWS IAM keys automatically.

## Installation
* Requires Python 3.6+.
* `pip install aws-key-rotator`

## Usage
Parses your AWS credentials file, looking for `aws_access_key_id` and `aws_secret_access_key`
keys, then automatically rotates them.

### Behavior
Due to the AWS limit of two access/secret keys per user, the behavior of this script will
vary depending on your situation.

* *If you have only one active access key* - The existing access key will be deactivated and
  a new one will be spun up. You'll have a new, active keypair, and your old inactive keypair.

* *If you have only one inactive access key* - A new key is created. The existing key remains
  inactive. The next run will have to delete that key to make room for a new rotation.

* *If you have one active and one inactive key* - The current inactive key will be deleted.
  The current active key will then be inactivated to make way for the new active key. If
  this script is run as a cron, this should be the standard state of affairs.

* *If you have two active keys* - The key that matches the one in the credentials file will
  have to be deleted to make room for the new key. The other active key will remain
  untouched.

* *If you have two inactive keys* - Same as above; the matching key pair will have to be
  deleted to make room for the new key. Keep in mind that if this is run again, the "one
  active, one inactive" scenario applies; the other former inactive key gets deleted, the
  previously-rotated one gets inactivated, and a new one is created.

## Arguments
* `-c`, `--credentials`: Path to your AWS credentials file (default: `~/.aws/credentials`)
