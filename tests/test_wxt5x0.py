# Copyright 2026 weewx-packages
# Distributed under the terms of the GNU Public License (GPLv3)
import importlib.util
from pathlib import Path
import socket
import threading
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location('wxt5x0', Path(__file__).parents[1] / 'bin/user/wxt5x0.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_null_bytes_removed():
    station = m.Station(0, 'fixture', 0)
    station.device = Mock()
    station.device.readline.return_value = b'0R0,Ta=1\x002.0C\r\n'
    assert m.Station.parse(station.get_composite())['temperature'] == 12


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
                        connection.sendall(b'2R0,Ta=12.0C,Rc=2.0M\r\n')
        except Exception as error:
            errors.append(error)
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    driver = m.WXT5x0Driver(protocol='tcp', tcp_address='127.0.0.1',
                           tcp_port=listener.getsockname()[1], address=2, retry_wait=0)
    try:
        packet = next(driver.genLoopPackets())
        assert packet['outTemp'] == 12
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
