# Vaisala WXT5x0 for WeeWX

A WeeWX driver that polls a Vaisala WXT510 or WXT520 for wind, pressure,
temperature, humidity and precipitation. It talks the ASCII protocol over a
serial port or a raw TCP serial server. NMEA and SDI-12 are not implemented.

This is an independent continuation of
[matthewwall/weewx-wxt5x0](https://github.com/matthewwall/weewx-wxt5x0), with
TCP support that follows OH2LAK's upstream pull request #12.

## Requirements

- A WXT5x0 transmitter set up for the ASCII protocol, connected over RS-232,
  RS-485 or RS-422, or through a TCP serial server that passes raw ASCII data.
- For a serial connection: access to the serial device for the user that runs
  WeeWX, and `pyserial` in the Python environment that runs WeeWX:

  ```sh
  python -m pip install 'pyserial==3.5'
  ```

  Activate that environment first, so that `python` and `weectl` both come from
  it. For an OS-packaged WeeWX, install the distribution package for pyserial
  instead. The package is named `pyserial` and provides the `serial` import. Do
  not install the different package named `serial`.

## Installation

Install `wxt5x0` from the [WeeWX packages catalog](https://github.com/weewx-packages/catalog/blob/main/packages/wxt5x0.md).
The catalog page lists the current release, its WeeWX and Python
requirements, and the install, update and removal commands.

Then select the driver and restart WeeWX:

```sh
weectl station reconfigure --driver=user.wxt5x0 --config=/path/to/weewx.conf
```

The prompts offer `serial`, `nmea` and `sdi12`. Choose `serial`. For TCP, edit
`weewx.conf` by hand as shown below.

## Configuration

Serial connection:

```ini
[Station]
    station_type = WXT5x0

[WXT5x0]
    driver = user.wxt5x0
    protocol = serial
    port = /dev/ttyUSB0
    address = 0
```

TCP serial server, replacing `protocol` and `port`:

```ini
[WXT5x0]
    driver = user.wxt5x0
    protocol = tcp
    tcp_address = 192.0.2.10
    tcp_port = 5000
    address = 0
```

| Option | Default | Meaning |
|---|---|---|
| `protocol` | `serial` | `serial` or `tcp`. With `nmea` or `sdi12` the driver fails to start. |
| `port` | `/dev/ttyUSB0` | Serial device. |
| `baud` | `19200` | Serial baud rate. |
| `tcp_address` | `localhost` | Host of the TCP serial server. |
| `tcp_port` | `5000` | Port of the TCP serial server. |
| `address` | `0` | Device address of the transmitter. |
| `model` | `WXT520` | Hardware name that WeeWX reports. |
| `poll_interval` | `1` | Seconds between polls. `0` polls without a pause. |
| `max_tries` | `5` | Read attempts before the driver gives up. |
| `retry_wait` | `10` | Seconds between read attempts. |

Match `address` and `baud` to the transmitter.

Over TCP, the driver connects on the first poll. After end of stream or a socket
error it closes the connection and reconnects on the next attempt. After
`max_tries` failed attempts, the driver raises `RetriesExceeded`. WeeWX then
waits and restarts its engine.

### Observations

The driver requests composite messages (`R0`) and converts the values to
`METRICWX` units. It maps these fields of the reply:

| Field | WeeWX field |
|---|---|
| `Dm`, `Sm` | `windDir`, `windSpeed` |
| `Dx`, `Sx` | `windGustDir`, `windGust` |
| `Ta`, `Ua`, `Pa` | `outTemp`, `outHumidity`, `pressure` |
| `Rc` | `rain_total`, from which the driver computes `rain` |
| `Ri` | `rainRate` |
| `Hc`, `Hi` | `hail`, `hailRate` |
| `Th`, `Vh`, `Vs`, `Vr` | `heatingTemp`, `heatingVoltage`, `supplyVoltage`, `referenceVoltage` |

Rain accumulation needs `Rc`, the cumulative counter. `Ri` is a rate and `Rp` a
peak rate; neither replaces `Rc`. Fields without a WeeWX name, such as
`Rp` or `Rd`, keep the driver's own names, for example `rain_intensity_peak` and
`rain_duration`.

### Serial diagnostics

Stop WeeWX first, so that the serial port is free. Without options the script
polls composite messages every 3 seconds and prints them raw and parsed:

```sh
PYTHONPATH=/path/to/station/bin python -m user.wxt5x0 --port=/dev/ttyUSB0
PYTHONPATH=/path/to/station/bin python -m user.wxt5x0 --help
```

The script has no TCP transport.

## Limitations

- Not tested on WXT5x0 hardware by weewx-packages.
- Only the ASCII protocol works. NMEA and SDI-12 are not implemented.
- The single-message options of the diagnostic script (`--get-wind` and the
  other `--get-*` options) require an argument, and `--get-precip` fails.
- Hail values reported in imperial units are converted with the wrong factor.
- The TCP tests run against a local socket. They do not show recovery on a real
  serial server.

## Development

Run the tests in a Python environment with WeeWX and pytest:

```sh
python -m pytest -q tests
```

## License

Copyright 2017-2024 Matthew Wall. Distributed under the GNU General Public
License version 3; see [license](license) and [NOTICE](NOTICE). The source
thanks Antonis Katsonis for providing a WXT520 for development.
