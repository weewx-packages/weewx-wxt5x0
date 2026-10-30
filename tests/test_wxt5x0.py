# Copyright 2026 weewx-packages
# Modified 2026-10-30 by weewx-packages: cover internal temperature readings.
# Distributed under the terms of the GNU Public License (GPLv3)
import importlib.util
from pathlib import Path
import runpy
import socket
import sys
import threading
import types
from unittest.mock import Mock

import pytest
import weewx.units

DRIVER = Path(__file__).parents[1] / 'bin/user/wxt5x0.py'
spec = importlib.util.spec_from_file_location('wxt5x0', DRIVER)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_null_bytes_removed():
    station = m.Station(0, 'fixture', 0)
    station.device = Mock()
    station.device.readline.return_value = b'0R0,Ta=1\x002.0C\r\n'
    assert m.Station.parse(station.get_composite())['temperature'] == 12


@pytest.mark.parametrize('message', [b'0R0', b'0R2'])
@pytest.mark.parametrize('reading, expected', [
    (b'25.0C', 25.0),
    (b'0.0C', 0.0),
    (b'-12.5C', -12.5),
    (b'77.0F', 25.0),
    (b'32.0F', 0.0),
    (b'0.0#', None),
])
def test_internal_temperature_parsing(message, reading, expected):
    parsed = m.Station.parse(message + b',Ta=12.0C,Tp=' + reading + b',Th=30.0C\r\n')
    assert parsed['internal_temperature'] == expected
    assert parsed['temperature'] == 12.0
    assert parsed['heating_temperature'] == 30.0


def test_internal_temperature_in_loop_packet():
    driver = m.WXT5x0Driver(protocol='tcp')
    driver._station.get_composite = Mock(
        return_value=b'0R0,Ta=12.0C,Tp=77.0F,Th=30.0C\r\n')
    packet = next(driver.genLoopPackets())
    assert packet['inTemp'] == 25.0
    assert packet['outTemp'] == 12.0
    assert packet['heatingTemp'] == 30.0
    assert packet['usUnits'] == m.weewx.METRICWX
    assert weewx.units.to_std_system(packet, m.weewx.US)['inTemp'] == 77.0


def test_rain_requires_counter():
    driver = object.__new__(m.WXT5x0Driver)
    driver._sensor_map = dict(m.WXT5x0Driver.DEFAULT_MAP)
    driver.last_rain_total = None
    packet = driver._data_to_packet(m.Station.parse(b'0R0,Ri=1.2M,Rp=22.9M'))
    assert packet['rainRate'] == 1.2
    assert 'rain' not in packet
    driver._data_to_packet(m.Station.parse(b'0R0,Rc=10M,Ri=1.2M'))
    packet = driver._data_to_packet(m.Station.parse(b'0R0,Rc=11.5M,Ri=0M'))
    assert packet['rain'] == 1.5
    assert packet['rainRate'] == 0


def test_tcp_disconnect_then_reconnect(monkeypatch):
    monkeypatch.setattr(m.time, 'sleep', lambda _: None)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    listener.settimeout(5)
    errors = []
    def serve():
        try:
            for i in range(2):
                connection, _ = listener.accept()
                with connection:
                    assert connection.recv(128) == b'2R0\r\n'
                    if i:
                        connection.sendall(b'2R0,Ta=12.0C,Tp=25.0C,Rc=2.0M\r\n')
        except Exception as error:
            errors.append(error)
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    driver = m.WXT5x0Driver(protocol='tcp', tcp_address='127.0.0.1',
                           tcp_port=listener.getsockname()[1], address=2, retry_wait=0)
    try:
        packet = next(driver.genLoopPackets())
        assert packet['outTemp'] == 12
        assert packet['inTemp'] == 25
        assert packet['rain_total'] == 2
    finally:
        driver.closePort()
        thread.join(6)
        listener.close()
    assert not errors
    assert not thread.is_alive()


def test_unreachable_tcp_does_not_fail_driver_import():
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
    listener.close()
    driver = m.WXT5x0Driver(protocol='tcp', tcp_address='127.0.0.1', tcp_port=port)
    with pytest.raises(OSError):
        driver._station.get_composite()
    assert driver._station.device is None


def test_imperial_hail_converted_to_hits_per_cm2():
    parsed = m.Station.parse(b'0R3,Hc=6.4516I,Hi=6.4516I')
    assert parsed['hail'] == pytest.approx(1.0)
    assert parsed['hail_intensity'] == pytest.approx(1.0)


@pytest.mark.parametrize('option, command', [
    ('--get-wind', b'0R1\r\n'),
    ('--get-pth', b'0R2\r\n'),
    ('--get-precip', b'0R3\r\n'),
    ('--get-supervisor', b'0R5\r\n'),
    ('--get-composite', b'0R0\r\n'),
])
def test_single_message_options_take_no_argument(monkeypatch, capsys, option, command):
    device = Mock()
    device.readline.return_value = b'0Rx,Ta=12.0C\r\n'
    serial = types.ModuleType('serial')
    serial.Serial = Mock(return_value=device)
    monkeypatch.setitem(sys.modules, 'serial', serial)
    monkeypatch.setattr(sys, 'argv', ['wxt5x0', option])
    runpy.run_path(str(DRIVER), run_name='__main__')
    device.write.assert_called_once_with(command)
    assert '0Rx,Ta=12.0C' in capsys.readouterr().out


@pytest.mark.parametrize('answers, expected', [
    (['WXT510', 'serial', '/dev/ttyS0', '1'],
     {'model': 'WXT510', 'protocol': 'serial', 'port': '/dev/ttyS0', 'address': '1'}),
    (['WXT510', 'tcp', '192.0.2.10', '4001', '1'],
     {'model': 'WXT510', 'protocol': 'tcp', 'tcp_address': '192.0.2.10',
      'tcp_port': '4001', 'address': '1'}),
])
def test_config_editor_offers_implemented_protocols(answers, expected):
    editor = m.WXT5x0ConfigurationEditor()
    choices = {}
    replies = iter(answers)
    def prompt(label, dflt=None, opts=None):
        choices[label] = opts
        return next(replies)
    editor._prompt = prompt
    assert editor.prompt_for_settings() == expected
    assert choices['protocol'] == ['serial', 'tcp']


@pytest.mark.parametrize('message, crc', [
    ('0r0', 'Kld'),
    ('0r1,Sn=0.1M,Sm=0.1M,Sx=0.1M', 'GOG'),
])
def test_crc_matches_user_guide_examples(message, crc):
    # Examples from the WXT520 user guide M210906EN-C, chapter 7.
    assert m.Station.calc_crc(message) == crc


def test_hail_in_hits_is_not_reported_as_hits_per_area():
    parsed = m.Station.parse(b'0R3,Hc=12H,Hd=20s,Hi=3H')
    assert parsed['hail'] is None
    assert parsed['hail_intensity'] is None
    assert parsed['hail_duration'] == 20


def test_diagnostic_help_names_implemented_protocols(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['wxt5x0', '--help'])
    with pytest.raises(SystemExit):
        runpy.run_path(str(DRIVER), run_name='__main__')
    out = capsys.readouterr().out
    assert 'serial or tcp' in out
    assert 'nmea' not in out


def test_diagnostic_script_polls_over_tcp(monkeypatch, capsys):
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    listener.settimeout(5)
    received = []
    def serve():
        connection, _ = listener.accept()
        with connection:
            received.append(connection.recv(128))
            connection.sendall(b'0R1,Dm=051D,Sm=0.1M\r\n')
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    monkeypatch.setattr(sys, 'argv', [
        'wxt5x0', '--protocol=tcp', '--tcp-address=127.0.0.1',
        '--tcp-port=%d' % listener.getsockname()[1], '--get-wind'])
    try:
        runpy.run_path(str(DRIVER), run_name='__main__')
    finally:
        thread.join(6)
        listener.close()
    assert received == [b'0R1\r\n']
    assert '0R1,Dm=051D,Sm=0.1M' in capsys.readouterr().out
