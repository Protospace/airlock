# Airlock

Door controller for scanning Protospace member cards on the front and back doors.

## Setup

Install dependencies:

```text
$ sudo apt update
$ sudo apt install python3 python3-pip python3-virtualenv supervisor git
```

Clone this repo:

```text
$ git clone https://github.com/Protospace/airlock.git
$ sudo mv airlock/ /opt/
$ cd /opt/airlock
```

### Hardware Access

Ensure Pi user has read permissions to `/dev/ttyACA0` and `/dev/watchdog`.

Configure `/etc/udev/rules.d/local.rules`:

```text
ACTION=="add", KERNEL=="dialout", MODE="0666"
ACTION=="add", KERNEL=="ttyACM0", MODE="0666"
ACTION=="add", KERNEL=="ttyAMA0", MODE="0666"
KERNEL=="watchdog", MODE="0666"
```

Also ensure `/boot/cmdline.txt` doesn't contain `console=serial0,115200`.

Then reboot:

```text
$ sudo reboot
```

### Main Script

Create a venv, activate it, and install:

```text
$ virtualenv -p python3 env
$ source env/bin/activate
(env) $ pip install -r requirements.txt
```

Start an empty card_data.json:

```text
(env) $ echo "{}" > card_data.json
```

Now you can run the script to test:

```text
(env) $ DEBUG=true python main.py
```

Copy and edit the settings file:

```text
(env) $ cp secrets.py.example secrets.py
(env) $ vim secrets.py
```

## Process management

The script is kept alive with [supervisor](https://pypi.org/project/supervisor/).

Configure `/etc/supervisor/conf.d/airlock.conf`:

```text
[program:airlock]
user=pi
directory=/opt/airlock
command=/opt/airlock/env/bin/python -u main.py
stopasgroup=true
stopsignal=INT
autostart=true
autorestart=true
stderr_logfile=/var/log/airlock.log
stderr_logfile_maxbytes=10MB
stdout_logfile=/var/log/airlock.log
stdout_logfile_maxbytes=10MB
```

Script logs to /var/log/airlock.log. Remove `-u` from the above command when you're done testing.

## License

This program is free and open-source software licensed under the MIT License. Please see the `LICENSE` file for details.

That means you have the right to study, change, and distribute the software and source code to anyone and for any purpose. You deserve these rights.
