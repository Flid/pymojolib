import serial
from serial.tools import list_ports
from enum import Enum
import struct
import typing


class RegisterCommandType(Enum):
    read = 0
    write = 1


BAUD_RATE = 500000
TIMEOUT = 1  # seconds


class BaseCommunicatorError(Exception):
    pass


class CommunicatorTimeoutError(BaseCommunicatorError):
    pass


class RegisterCommunicator:
    def __init__(self, baudrate: int=BAUD_RATE, port: bytes=None):
        self._baudrate = baudrate

        devices = [item.device for item in list_ports.comports()]
        if port:
            if port not in devices:
                raise ValueError('Port %s not found. Available options: %s' % (
                    port,
                    devices,
                ))
        else:
            if len(devices) == 0:
                raise ValueError('No devices found')

            if len(devices) > 1:
                raise ValueError(
                    'More than one device found, please pick one of %s' % (
                        devices
                    )
                )

            port = devices[0]

        self._port = port
        self._serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=TIMEOUT,
        )

    def close(self):
        if self._serial:
            self._serial.close()
            self._serial = None

    def _write(self, data: bytes):
        self._serial.write(data)

    def _read(self, size: int = 1):
        data = self._serial.read(size=size)

        if len(data) < size:
            raise CommunicatorTimeoutError()

        return data

    @staticmethod
    def _format_command_byte(
        command_type: RegisterCommandType,
        size: int,
    ):
        c = 0
        c |= command_type.value << 7
        c |= size - 1
        return c

    def register_write(
        self,
        address: int,
        data: typing.List[int],
    ):
        assert len(data) <= 64

        data = struct.pack(
            b'<Bi' + b'i' * len(data),
            self._format_command_byte(
                command_type=RegisterCommandType.write,
                size=len(data),
            ),
            address,
            *data
        )
        self._write(data)

    def register_read(
        self,
        address: int,
        size: int,
    ):
        assert size <= 64

        data = struct.pack(
            b'<Bi',
            self._format_command_byte(
                command_type=RegisterCommandType.read,
                size=size,
            ),
            address,
        )
        self._write(data)

        output = []

        for _ in range(size):
            buf = self._read(size=4)

            output.append(
                struct.unpack(b'<i', buf)[0],
            )

        return output

    def __del__(self):
        self.close()
