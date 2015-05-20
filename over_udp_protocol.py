# coding=utf-8
import hashlib
import struct
import socket
import uuid


# TODO: обгорнути в try except всі struct
# FIXME: якщо не було CLOSE то слієнт далі в БД
import time


class myTCP(Exception):
    pass


class FrameError(myTCP):
    pass


class FrameFlagError(myTCP):
    pass


class HandShakeError(myTCP):
    pass


class myTCPClose(myTCP):
    pass


class ServerBusy(myTCP):
    pass


class UDPPlusConst(object):
    MAX_PACKET_SIZE = 8192
    MAX_MSG_SIZE = 8150

    FLAG_HAND_SHAKE = 100
    FLAG_DATA_STEAM = 101
    FLAG_VALID = 200
    FLAG_INVALID = 201
    FLAG_TIMEOUT = 202
    FLAG_MSG_END = 300
    FLAG_CLOSE = 301

    def _pack_frame(self, uid, flag, part_number, quantity_parts, msg):
        frame = uid
        frame += struct.pack('!h2I', flag, part_number, quantity_parts)
        frame += hashlib.md5(msg).digest()
        frame += msg
        return frame

    def _unpack_frame(self, frame):
        """
        :param frame: raw string from socket
        :rtype: raw, int, int, int, raw, str
        :return: user_id, flag, current_part, max_part, hash_data, data
        """
        user_id = frame[:16]
        try:
            flag, current_part, max_part = struct.unpack('!h2I', frame[16:26])
        except struct.error:
            raise FrameError ('Receive invalid frame')
        hash_data = frame[26:42]
        data = frame[42:]
        return user_id, flag, current_part, max_part, hash_data, data

    def _get_number_of_packs(self, msg):
        length = len(msg)
        if length % self.MAX_MSG_SIZE == 0:
            return length / self.MAX_MSG_SIZE
        else:
            return length / self.MAX_MSG_SIZE + 1


class Storage(object):
    _default_connection = 2
    _kill_connection_time = 600  # sec

    _meta_db = {}
    # {uid: {'time': 2073.000648, 'address': ('', 8000)}}
    _file_db = {}
    # {uid: {1: 'msg part1', 2: 'msg part2'}}



    def __init__(self, number_of_connection=2):
        if number_of_connection <= 0:
            number_of_connection = self._default_connection
        self.max_client = number_of_connection

    def _del_unused_connection(self):
        for uid, data in self._meta_db.items():
            if data['time'] < time.time():
                self._meta_db.pop(uid)
                self._file_db.pop(uid)

    def _add_client(self, uid, net_address):
        self._meta_db.update({uid: {'time': time.time() +
                                            self._kill_connection_time,
                                    'address': net_address}})

    def add_client(self, uid, net_address):
        if len(self._meta_db) < self.max_client:
            self._add_client(uid, net_address)
        else:
            self._del_unused_connection()
            if len(self._meta_db) < self.max_client:
                self._add_client(uid, net_address)
            else:
                raise ServerBusy('Connection limited')

    def address(self, uid):
        if uid in self._meta_db:
            return self._meta_db[uid]['address']
        else:
            return None

    def verify_client(self, uid):
        if uid in self._meta_db:
            return True
        else:
            return False

    @property
    def max_connection(self):
        return self.max_client

    def add_frame_from_client(self, uid, part, data):
        if uid in self._file_db:
            self._file_db[uid].update({part: data})
        else:
            self._file_db.update({uid: {part: data}})

    def get_msg(self, uid):
        msg = ""
        if uid in self._file_db:
            temp = self._file_db.pop(uid)
            for k, v in temp.items():
                msg += v
            return msg
        else:
            return None


class SendQuery(UDPPlusConst):
    _query = {}

    def add_msg(self, uid, msg, address):
        net_query = list()
        if len(msg) > self.MAX_MSG_SIZE:
            number = 0
            last_pack = self._get_number_of_packs(msg)
            for i in range(0, len(msg), self.MAX_MSG_SIZE):
                number += 1
                net_query.append((self._pack_frame(uid, self.FLAG_DATA_STEAM,
                                                   number, last_pack,
                                                   msg[i:i+self.MAX_MSG_SIZE]),
                                  address))
            net_query.append((self._pack_frame(uid, self.FLAG_MSG_END,
                                               1, 1, 'end'), address))
        else:
            net_query.append((self._pack_frame(uid, self.FLAG_DATA_STEAM, 1, 1,
                                               msg), address))
            net_query.append((self._pack_frame(uid, self.FLAG_MSG_END,
                                               1, 1, 'end'), address))
        if uid in self._query:
            self._query.update({uid: self._query[uid] + net_query})
        else:
            self._query.update({uid: net_query})
        return net_query[0]

    def current_pack(self, uid):
        return self._query[uid][0]

    def next_pack(self, uid):
        self._query[uid].pop(0)
        return self.current_pack(uid)

    @property
    def is_empty(self):
        if len(self._query):
            return False
        return True


class UDPPlus(UDPPlusConst):

    def __init__(self):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = ('', 9000)

    def _raw_send_to(self, msg, address=None):
        """
        :type msg: srt
        :param msg: data for sending
        :type address: tuple
        :param address: IP and port
        """
        if type(msg) is tuple:
            self.soc.sendto(msg[0], msg[1])
        else:
            if not address:
                address = self.address
            self.soc.sendto(msg, address)

    def _raw_receive(self, time_receiving=2.0):
        """
        :type time_receiving: float
        :param time_receiving: tome for receive msg
        :return: data from socket (max. size = MAX_PACKET_SIZE)
        """
        self.soc.settimeout(time_receiving)
        data = self.soc.recvfrom(self.MAX_PACKET_SIZE)
        return data


class UDPPlusServer(UDPPlus):

    run_server = True

    def __init__(self):
        super(UDPPlusServer, self).__init__()
        self.soc.bind(self.address)
        self._data_storage = Storage()
        self.send_query = SendQuery()

    def reactor(self):
        while self.run_server:
            frame, address = self.soc.recvfrom(self.MAX_PACKET_SIZE)
            try:
                user_id, flag, current_part, max_part, data =\
                    self.filter_frames(frame)
            except FrameFlagError:
                pass
            else:
                if flag == self.FLAG_DATA_STEAM:
                    self._receive_data_stream(user_id, current_part, max_part,
                                              data, address)
                elif flag == self.FLAG_HAND_SHAKE:
                    self._hand_shake(user_id, current_part, max_part, data,
                                     address)
                elif flag == self.FLAG_MSG_END or flag == self.FLAG_CLOSE:
                    self.receive_data(user_id, flag, current_part, max_part,
                                      data, address)
                elif flag == self.FLAG_VALID or flag == self.FLAG_INVALID:
                    self._send_data_stream(user_id, flag, address)

    def _receive_data_stream(self, client_id, current_part,
                             max_part, data, address):
        if current_part > max_part:
            self._raw_send_to(self._pack_frame(client_id,
                                               self.FLAG_INVALID, 1, 1, 'NO'),
                              address)
        else:
            self._data_storage.add_frame_from_client(client_id, current_part,
                                                     data)
            self._raw_send_to(self._pack_frame(client_id,
                                               self.FLAG_VALID, 1, 1, 'OK'),
                              address)

    def _hand_shake(self, client_id, current_part, max_part, data, address):
        if current_part == max_part:
            try:
                self._data_storage.add_client(client_id, address)
            except ServerBusy:
                self._raw_send_to(self._pack_frame(client_id, self.FLAG_TIMEOUT,
                                                   1, 1, 'TO'), address)
            self._raw_send_to(self._pack_frame(client_id, self.FLAG_HAND_SHAKE,
                                               1, 1, 'HS'), address)

    def receive_data(self, user_id, flag, current_part, max_part, data, address):
        self._raw_send_to(self._pack_frame(user_id, self.FLAG_VALID, 1, 1,
                                           'OK'), address)
        if self._data_storage.verify_client(user_id):
            msg = self._data_storage.get_msg(user_id)
            if msg is not None:
                return msg
    # FIXME: ???

    def _send_data_stream(self, client_id, flag, address):
        if not self.send_query.is_empty:
            if flag == self.FLAG_INVALID:
                self._raw_send_to(self.send_query.current_pack(client_id),
                                  address)
            elif flag == self.FLAG_VALID:
                self._raw_send_to(self.send_query.next_pack(client_id), address)

    def close_server(self):
        self.run_server = False

    def send_msg(self, uid, msg, address):
        first_frame = self.send_query.add_msg(uid, msg, address)
        self._raw_send_to(first_frame)

    def filter_frames(self, frame):
        """
        :param frame: raw UDP+ frame from socket
        :return: client_id, flag, part_number, quantity_parts, data
        """
        client_id, flag, current_part, max_part, hash_data, data = \
            self._unpack_frame(frame)
        if hashlib.md5(data).digest() == hash_data:
            return client_id, flag, current_part, max_part, data
        raise FrameError('Invalid data. Wrong hash')


class UDPPlusClient(UDPPlus):

    _hs_trigger = False

    def __init__(self):
        super(UDPPlusClient, self).__init__()
        self.client_id = uuid.uuid4().get_bytes()

    def _hand_shake(self):
        self._raw_send_to(self._pack_frame(self.client_id, self.FLAG_HAND_SHAKE,
                                           1, 1, 'HS'), self.address)
        try:
            data, address = self._raw_receive(5)
            flag, current_part, max_part, hs_data = self.filter_frames(data)
        except (FrameError, socket.timeout):
            pass
        else:
            self._hs_trigger = True

    def _split_msg(self, msg):
        net_query = list()
        if len(msg) > self.MAX_MSG_SIZE:
            number = 0
            last_pack = self._get_number_of_packs(msg)
            for i in range(len(msg), self.MAX_MSG_SIZE):
                number += 1
                net_query.append(self._pack_frame(self.client_id, 101, number,
                                                  last_pack,
                                                  msg[i:i+self.MAX_MSG_SIZE]))
            net_query.append(self._pack_frame(self.client_id, self.FLAG_MSG_END,
                                              1, 1, 'end'))
        else:
            net_query.append(self._pack_frame(self.client_id,
                                              self.FLAG_DATA_STEAM, 1, 1, msg))
            net_query.append(self._pack_frame(self.client_id, self.FLAG_MSG_END,
                                              1, 1, 'end'))
        return net_query

    def send_udpplus(self, msg):
        if not self._hs_trigger:
            self._hand_shake()
        query = self._split_msg(msg)
        self.soc.settimeout(None)
        for frame in query:
            valid = False
            while not valid:
                self._raw_send_to(frame)
                try:
                    data, address = self._raw_receive(5)
                    flag, current_part, max_part, hs_data = \
                        self.filter_frames(data)
                except (socket.timeout, FrameError):
                    pass
                else:
                    if flag == self.FLAG_VALID:
                        valid = True

    def receive_udpplus(self):
        """
        :raise: myTCPClose
        :rtype: str
        :return: full message, not part of it
        """
        receiving = True
        msg_buffer = ''
        while receiving:
            try:
                data, address = self._raw_receive(5)
                flag, current_part, max_part, data = self.filter_frames(data)
            except socket.timeout:
                pass
            except FrameError:
                    self._raw_send_to(self._pack_frame(self.client_id, 1, 1,
                                                       self.FLAG_INVALID, 'NO'))
            else:
                if flag == self.FLAG_DATA_STEAM:
                    msg_buffer += data
                if flag == self.FLAG_CLOSE or flag == self.FLAG_MSG_END:
                    if current_part != max_part:
                        self._raw_send_to(self._pack_frame(self.client_id, 1,
                                                           1, self.FLAG_VALID,
                                                           'OK'))
                        raise myTCPClose('Connection closed')

                self._raw_send_to(self._pack_frame(self.client_id, 1, 1,
                                                   self.FLAG_VALID, 'OK'))
                return msg_buffer

    def filter_frames(self, frame):
        """
        :param frame: raw UDP+ frame from socket
        :return: client_id, flag, part_number, quantity_parts, data
        """
        client_id, flag, current_part, max_part, hash_data, data = \
            self._unpack_frame(frame)
        if hashlib.md5(data).digest() == hash_data:
            return flag, current_part, max_part, data
        raise FrameError('Invalid data. Wrong hash')
