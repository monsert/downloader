"""
Simple Data JSON Protocol (SDJP)

+-------------------------------------------------------------+
|HEAD        -- string -- body length. 4 byte                 |
+-------------------------------------------------------------+
|BODY                                                         |
|    type    -- string -- command, json, string, response     |
|    command -- string -- 'info', 'add', 'delete',            |
|                         'pause_start', 'start', 'close_all' |
|    data    -- json/string --                                |
+-------------------------------------------------------------+
HEAD is int length 4 byte.
BODY is JSON. Only data row in BODY can be JSON
If type in body SDJP is COMMAND
    command row most have one command from this list ('INFO', 'ADD', 'DELETE',
         'RUN_ALL', 'PAUSE', 'START'). not case sensitive
    data row will be empty if command not need data.

Example: \x00\x00\x003{'name': 'file4', 'size': 782, 'downloaded': 13110}
"""

import socket
import json
import struct


class SDJPError(Exception):
    pass


class InvalidProtocol(SDJPError):
    pass


class ConnectionError(SDJPError):
    pass


class ConnectionInUse(ConnectionError):
    pass


class ConnectionBreak(ConnectionError):
    pass


class ConnectionClosed(ConnectionError):
    pass


class BaseServerProtocol(object):

    def validation(self, raw_body):
        """
        Handling only with SDJPError and child raise.
        """
        return raw_body

    def action(self, su_self, connection, data):
        """

        :param su_self: refer to server class for use send/receive
        :param connection: connection to client. For sent response if it needed.
        :param data: data after validation function
        """
        pass


class BaseServer(object):
    _IP = 'localhost'
    _PORT = 5000
    _BACKLOG = 1

    def __init__(self):
        """
        :raise: ConnectionInUse
        """
        self.soc = socket.socket()
        try:
            self.soc.bind((self._IP, self._PORT))
            self.soc.listen(self._BACKLOG)
        except socket.error as err:
            raise ConnectionInUse(err.args)

    def _receive(self, connection, size):
        """
        :type size: int
        :param connection: socket connection to client
        :param size: size with read from socket
        :raise: ConnectionClosed
        :return: received data from socket
        """
        buf = ''
        try:
            while size - len(buf) != 0:
                tmp = connection.recv(size - len(buf))
                buf += tmp
        except socket.error as err:
            raise ConnectionClosed(err.args)
        return buf

    def _send(self, connection, msg):
        """
        :param connection: socket connection to client
        :param msg: message for sending
        :raise: ConnectionClosed
        """
        size = len(msg)
        buf = 0
        try:
            while buf < size:
                buf += connection.send(msg)
        except socket.error as err:
            raise ConnectionClosed(err.args)

    def receive_SDJP(self, connection):
        """
        :param connection: socket connection to client
        :raise: InvalidProtocol
        :rtype: dict
        :return: SDJP data, or raise exception if header invalid
        """
        head = self._receive(connection, 4)
        try:
            size = struct.unpack('!i', head)[0]
        except (IndexError, struct.error):
            raise InvalidProtocol('Receive wrong header data')
        data = self._receive(connection, size)
        return data

    def send_SDJP(self, connection, msg):
        """
        :param msg: serializable object
        """
        data = json.dumps(msg)
        frame = '{head}{body}'.format(head=struct.pack('!i', len(data)),
                                                             body=data)
        self._send(connection, frame)


class CustomProtocolServer(BaseServer):
    server_work = True
    download = True

    def __init__(self, protocol):
        """
        :raise: ConnectionInUse
        """
        BaseServer.__init__(self)
        assert isinstance(protocol, BaseServerProtocol)
        self.protocol = protocol

    def shutdown_server(self):
        """
        Safely close server
        """
        self.server_work = False

    def run(self):
        while self.server_work:
            connection, address = self.soc.accept()
            print 'connected address ',address
            self.download = True
            while self.download:
                try:
                    data = self.receive_SDJP(connection)
                    data = self.protocol.validation(data)
                    self.protocol.action(self, connection, data)
                except SDJPError:
                    connection.close()
                    self.download = False
        self.soc.close()


class BaseClient(object):
    _HOST = 'localhost'
    _PORT = 5000

    def __init__(self):
        """
        :raise: ConnectionClosed
        """
        self.soc = socket.socket()
        try:
            self.soc.connect((self._HOST, self._PORT))
        except socket.error as err:
            raise ConnectionClosed(err.args)

    def _receive(self, size):
        """
        :type size: int
        :raise: ConnectionClosed
        :param size: size with read from socket
        :return: received data from socket
        """
        buf = ''
        while size - len(buf) != 0:
            try:
                tmp = self.soc.recv(size - len(buf))
            except socket.error as err:
                raise ConnectionClosed(err.args)
            buf += tmp
        return buf

    def _send(self, msg):
        """
        :raise: ConnectionClosed
        :param msg: message for sending
        """
        size = len(msg)
        buf = 0
        while buf < size:
            try:
                buf += self.soc.send(msg)
            except socket.error as err:
                raise ConnectionClosed(err.args)

    def receive_SDJP(self):
        """
        Receive data from socket in SDJP Format

        :raise: InvalidProtocol
        :rtype: dict
        :return: Body of protocol
        """
        head = self._receive(4)
        try:
            size = struct.unpack('!i', head)[0]
        except (IndexError, struct.error):
            raise InvalidProtocol("Receive wrong data")
        raw_body = self._receive(size)
        return raw_body

    def send_SDJP(self, msg):
        """
        Send data using SDJP.
        :param msg: serializable object
        """
        data = json.dumps(msg)
        frame = '{head}{data}'.format(head=struct.pack('!i',len(data)),
                                                            data=data)
        self._send(frame)
