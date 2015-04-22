"""
Simple Data JSON Protocol (SDJP)

+-------------------------------------------------------------+
|HEAD        -- string -- body length. format 000123**        |
+-------------------------------------------------------------+
|BODY                                                         |
|    type    -- string -- command, json, string, response     |
|    command -- string -- 'info', 'add', 'delete',            |
|                         'pause_start', 'start', 'close_all' |
|    data    -- json/string --                                |
+-------------------------------------------------------------+
HEAD is string length 8 char. First 6 its length of body, Last 2  is '**'.
BODY is JSON. Only data row in BODY can be JSON
If type in body SDJP is COMMAND
    command row most have one command from this list ('INFO', 'ADD', 'DELETE',
         'RUN_ALL', 'PAUSE', 'START'). not case sensitive
    data row will be empty if command not need data.

Example: 000051**{'name': 'file4', 'size': 782, 'downloaded': 13110}
"""

import socket
import json


class SDJPError(Exception):
    pass


class InvalidProtocol(SDJPError):
    pass


class ConnectionError(SDJPError):
    pass


SDJP_COMMAND = ('info', 'add', 'delete', 'pause_start', 'start', 'close_all')
SDJP_TYPE = ('json', 'string', 'command')


class BaseSDJP(object):
    def validation(self, raw_body):
        """
        :param raw_body: JSON
        :rtype: dict
        :raise: InvalidProtocol
        :return: Body of protocol
        """
        try:
            data = json.loads(raw_body)
        except ValueError:
            raise InvalidProtocol('Wrong protocol body')
        if 'type' and 'command' and 'data' in data:
            if data['type'].lower() in SDJP_TYPE:
                return data
        raise InvalidProtocol('Wrong protocol rows')

    def run_command(self, data):
        cmd_map = {'close_all': self.command_close_all,
                   'delete': self.command_delete,
                   'pause_start': self.command_pause_start,
                   'info': self.command_info,
                   'add': self.command_add,}

        cmd_map[data['command'].lower()](data['data'])

    def command_add(self, arg):
        """
        You may override this method in a subclass. If you want to use this
        command from SDJP.
        :param arg: one argument with is data in SDJP
        """
        pass

    def command_delete(self, arg):
        """
        You may override this method in a subclass. If you want to use this
        command from SDJP.
        :param arg: one argument with is data in SDJP
        """
        pass

    def command_close_all(self, arg):
        """
        You may override this method in a subclass. If you want to use this
        command from SDJP.
        :param arg: one argument with is data in SDJP
        """
        pass

    def command_pause_start(self, arg):
        """
        You may override this method in a subclass. If you want to use this
        command from SDJP.
        :param arg: one argument with is data in SDJP
        """
        pass

    def command_info(self, arg):
        """
        You may override this method in a subclass. If you want to use this
        command from SDJP.
        :param arg: one argument with is data in SDJP
        """
        pass


class BaseServer(BaseSDJP):
    """
    Server with consume data only in SDJP.
    """
    _IP = 'localhost'
    _PORT = 5000
    _BLOCK_SIZE = 1024
    _BACKLOG = 2

    server_work = True
    download = True

    def __init__(self):
        self.soc = socket.socket()
        self.soc.bind((self._IP, self._PORT))
        self.soc.listen(self._BACKLOG)

    def _receive(self, size):
        """
        :type size: int
        :param size: size with read from socket
        :return: received data from socket
        """
        buf = ''
        while size - len(buf) != 0:
            tmp = self.connection.recv(size - len(buf))
            buf += tmp
        return buf

    def _send(self, msg):
        """
        :param msg: message for sending
        """
        size = len(msg)
        buf = 0
        while buf < size:
            buf += self.connection.send(msg)

    def receive_SDJP(self):
        data = self._receive(32)
        try:
            size = int(data, base=2)
        except ValueError:
            raise InvalidProtocol(111)
        data = self._receive(size)
        data = self.validation(data)
        return data

    def send_SDJP(self, msg):
        data = json.dumps(msg)
        frame = '{head:032b}{body}'.format(head=len(data), body=data)
        self._send(frame)

    def shutdown_server(self):
        self.server_work = False

    def run(self):
        while self.server_work:
            self.connection, address = self.soc.accept()
            self.download = True
            while self.download:
                try:
                    data = self.receive_SDJP()
                    self.run_command(data)
                except InvalidProtocol:
                    self.connection.close()
                    self.download = False
        self.soc.close()


class BaseClient(BaseSDJP):
    _HOST = 'localhost'
    _PORT = 5000
    _BLOCK_SIZE = 1024

    work = True

    def __init__(self):
        self.soc = socket.socket()
        self.soc.connect((self._HOST, self._PORT))

    def _receive(self, size):
        """
        :type size: int
        :param size: size with read from socket
        :return: received data from socket
        """
        buf = ''
        while size - len(buf) != 0:
            tmp = self.soc.recv(size - len(buf))
            buf += tmp
        return buf

    def _send(self, msg):
        """
        :param msg: message for sending
        """
        size = len(msg)
        buf = 0
        while buf < size:
            buf += self.soc.send(msg)

    def receive_SDJP(self):
        """
        Receive data from socket in SDJP Format

        :raise: InvalidProtocol
        :rtype: dict
        :return: Body of protocol
        """
        head = self._receive(32)
        try:
            size = int(head, base=2)
        except ValueError:
            raise InvalidProtocol(92)
        raw_body = self._receive(size)
        if raw_body:
            raw_body = self.validation(raw_body)
        return raw_body

    def send_SDJP(self, msg):
        """
        Send data using SDJP.

        :param msg: dict with keys command, type, data
        """
        data = json.dumps(msg)
        frame = '{head:032b}{data}'.format(head=len(data), data=data)
        self._send(frame)