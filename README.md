# Vaisala WXT5x0 for WeeWX

Read Vaisala WXT5x0 wind, pressure, temperature/humidity and precipitation data
through a serial connection or a raw TCP serial server. The implementation has
`serial`, `nmea` and `sdi12` modes with different serial framing; the TCP mode
uses ASCII composite messages. It does not use a cloud API.

This independent continuation preserves
[matthewwall/weewx-wxt5x0](https://github.com/matthewwall/weewx-wxt5x0) history.
Release 0.9.0 adds TCP reconnect handling following OH2LAK's serial-server use
case. Verify message and counter configuration on your actual transmitter.

## Install

An existing WeeWX station is required. Replace `/path/to/weewx.conf`
with its configuration file before running the commands.

The catalog release requires Python >=3.10 and WeeWX >=5.2,<6.

Before running the commands, activate the existing virtual environment that
runs your WeeWX service. Both `python` and `weectl` must come from that
environment. For an OS-packaged WeeWX installation, use compatible distribution
packages instead, or migrate WeeWX and its service to a virtual environment
first. Installing into an unrelated virtual environment will not supply the
running service with dependencies.

Serial modes need `pyserial` in the WeeWX environment:

```sh
python -m pip install 'pyserial==3.5'
```

The distribution is named `pyserial`; it provides the `serial` import.
Do not install the different package named `serial`.

Use the `weectl` from your WeeWX Python environment:

```sh
weectl extension install https://github.com/weewx-packages/weewx-wxt5x0/releases/download/v0.9.0/weewx-wxt5x0-0.9.0.zip --config=/path/to/weewx.conf
weectl station reconfigure --driver=user.wxt5x0 --config=/path/to/weewx.conf
```

Stock WeeWX 5 accepts this fixed URL or a downloaded copy of the same archive.
No catalog integration is required. Restart WeeWX yourself after configuration
changes.

## Connect a serial transmitter

```ini
[Station]
    station_type = WXT5x0
[WXT5x0]
    driver = user.wxt5x0
    protocol = serial
    port = /dev/ttyUSB0
    baud = 19200
    address = 0
    poll_interval = 1
```

Match `address`, protocol and baud rate to the transmitter, and give the WeeWX
service user serial-device access. The protocol defaults are 19200 baud for
ASCII serial, 4800 for NMEA and 1200 for SDI-12. Hardware/interface wiring and
station setup must support the selected mode.

## Connect through a TCP serial server

Replace the transport options in `[WXT5x0]` with:

```ini
    protocol = tcp
    tcp_address = 192.0.2.10
    tcp_port = 5000
    address = 0
```

Use the server's address and port. The server must expose raw ASCII serial data.
The driver opens TCP connections during polling and reconnects after EOF or
socket errors. After `max_tries`, WeeWX receives `RetriesExceeded` and can retry
its engine. TCP configuration must be entered manually; the interactive editor
only offers the serial modes.

## Check observations

Rain accumulation requires `Rc`, the cumulative counter, in composite replies.
`Ri` is a rate and `Rp` is a peak rate; neither replaces `Rc`. The source's
[observation map](bin/user/wxt5x0.py) describes available measurements. Check
WeeWX logs and your transmitter output after restarting the service.

Standalone serial diagnostics require WeeWX to release the device first:

```sh
PYTHONPATH=/path/to/station/bin python -m user.wxt5x0 --help
```

The standalone CLI does not expose the TCP transport. Offline serial parsing
and local TCP reconnect checks do not establish physical telemetry recovery.
Copyright 2017-2024 Matthew Wall. GPL-3.0-only; see [license](license) and
[NOTICE](NOTICE).

<!-- Documentation updated 2026-10-23 by weewx-packages. -->
