# AWS Key Rotator

Rotates your AWS IAM keys automatically.

## Installation
* Requires Python 3.6+ and `pip` 19.0+.
* `pip install --user aws-key-rotator`

This will create an `aws-key-rotator` command in your `~/.local/bin` folder. If you see a
message along the lines of:
```
WARNING: The script aws-key-rotator is installed in '/home/vagrant/.local/bin' which is not on PATH.
Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
```
Take the first option and ensure `~/.local/bin` is in your `PATH`.

## Usage
Parses your AWS credentials file, looking for `aws_access_key_id` and `aws_secret_access_key`
keys, then automatically rotates them.

## Cron
It's highly recommended to run this as a cron. Ideally, run this daily, and set the time
to one where your computer is most likely on. First, find the fully-qualified path of the
executable: `which aws-key-rotator`

Then, for example, to run this daily at noon:
```
$ crontab -e
---
12 0 * * * /home/your_user/.local/bin/aws-key-rotator 2>&1 | logger -t aws-key-rotator
```

Recommendation on a Linux machine is to pipe the output to `logger`. You can alternatively just
redirect it to whatever log file you prefer.

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
