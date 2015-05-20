import hashlib
import mock
import unittest
import json
import uuid
import time

import over_udp_protocol as oup


class TestUDPPlusConst(unittest.TestCase):

    def test_pack_unpack_frame(self):
        udp = oup.UDPPlusConst()
        uid = uuid.uuid4().get_bytes()
        frame = udp._pack_frame(uid, 100, 1, 1,'test')
        user_id, flag, current_part, max_part, hash_data, data = udp._unpack_frame(frame)
        self.assertEqual(user_id, uid)
        self.assertEqual(flag, 100)
        self.assertEqual(current_part, 1)
        self.assertEqual(max_part, 1)
        self.assertEqual(hash_data, hashlib.md5(data).digest())
        self.assertEqual(data, 'test')

    def test__get_number_of_packs(self):
        udp = oup.UDPPlusConst()
        self.assertEqual(udp._get_number_of_packs('test'), 1)
        self.assertEqual(udp._get_number_of_packs('aa'*udp.MAX_MSG_SIZE), 2)


class TestStorage(unittest.TestCase):

    def test_init_1(self):
        db = oup.Storage(-2)
        self.assertEqual(db.max_client, db._default_connection)

    def test_init_2(self):
        db = oup.Storage(4)
        self.assertEqual(db.max_client, 4)

    def test_del_unused_connection(self):
        db = oup.Storage()
        db._meta_db = {4444: {'time': time.time(), 'address': ('', 8000)},
                       3333: {'time': time.time()+300, 'address': ('', 8000)}}
        db._file_db = {4444: {1: 'time', 2: 'time2'},
                       3333: {1: 'time', 2: 'time2'}}
        db._del_unused_connection()
        self.assertEqual(len(db._meta_db), 1)

    def test__add_client(self):
        db = oup.Storage()
        db._add_client('2222', 'net-address')
        self.assertTrue(len(db._meta_db))

    def test_add_client_1(self):
        db = oup.Storage()
        db._meta_db = {4444: {'time': time.time()-20, 'address': ('', 8000)},
                       3333: {'time': time.time()+300, 'address': ('', 8000)}}
        db._file_db = {4444: {1: 'time', 2: 'time2'},
                       3333: {1: 'time', 2: 'time2'}}
        db.add_client(5555, 'test-address')
        self.assertIn(5555, db._meta_db)

    def test_add_client_2(self):
        db = oup.Storage()
        db._meta_db = {4444: {'time': time.time()-5, 'address': ('', 8000)}}
        db._file_db = {4444: {1: 'time', 2: 'time2'}}
        db.add_client(5555, 'test-address')
        self.assertIn(5555, db._meta_db)

    def test_add_client_3(self):
        db = oup.Storage()
        db._meta_db = {4444: {'time': time.time()+300, 'address': ('', 8000)},
                       5555: {'time': time.time()+300, 'address': ('', 8000)}}
        db._file_db = {4444: {1: 'time', 2: 'time2'},
                       5555: {1: 'time', 2: 'time2'}}
        self.assertRaises(oup.ServerBusy, db.add_client, 6666, 'test-address')

    def test_address(self):
        db = oup.Storage()
        db._meta_db = {4444: {'time': time.time(), 'address': ('', 8000)},
                       5555: {'time': time.time(), 'address': 'test'}}
        self.assertEqual(db.address(5555), 'test')
        self.assertIs(db.address(6666), None)

    def test_verify_client(self):
        db = oup.Storage()
        db._meta_db = {4444: {'time': time.time(), 'address': ('', 8000)},
                       5555: {'time': time.time(), 'address': 'test'}}
        self.assertTrue(db.verify_client(5555))
        self.assertFalse(db.verify_client(6666))

    def test_max_connection(self):
        db = oup.Storage(4)
        self.assertEqual(db.max_connection, 4)

    def test_add_frame_from_client_1(self):
        db = oup.Storage()
        db._file_db = {4444: {1: 'time', 2: 'time2'}}
        db.add_frame_from_client(4444, 3, 'time3')
        self.assertEqual(len(db._file_db), 1)
        self.assertEqual(len(db._file_db[4444]), 3)

    def test_add_frame_from_client_2(self):
        db = oup.Storage()
        db._file_db = {4444: {1: 'time', 2: 'time2'}}
        db.add_frame_from_client(5555, 3, '1111')
        self.assertEqual(len(db._file_db), 2)

    def test_get_msg(self):
        db = oup.Storage()
        db._file_db = {4444: {1: 'ti', 2: 'me'}}
        self.assertEqual(db.get_msg(4444), 'time')


class TestSendQuery(unittest.TestCase):

    def test_add_msg_1(self):
        sq = oup.SendQuery()
        sq.add_msg('4444', 'abcdef', ('', 9000))
        self.assertEqual(len(sq._query), 1)
        self.assertEqual(len(sq._query['4444']), 2)

    def test_add_msg_2(self):
        sq = oup.SendQuery()
        sq.MAX_MSG_SIZE = 2
        sq._query = {}
        sq._get_number_of_packs = lambda x: len(x)/2
        sq.add_msg('4444', 'abcdef', ('', 9000))
        self.assertEqual(len(sq._query), 1)
        self.assertEqual(len(sq._query['4444']), 4)

    def test_add_msg_3(self):
        sq = oup.SendQuery()
        sq.MAX_MSG_SIZE = 2
        sq._query = {'4444': []}
        sq._get_number_of_packs = lambda x: len(x)/2
        sq.add_msg('4444', 'abcdef', ('', 9000))
        self.assertEqual(len(sq._query), 1)
        self.assertEqual(len(sq._query['4444']), 4)

    def test_current_pack(self):
        sq = oup.SendQuery()
        sq._query = {'4444': [('test pack', 'address')]}

        self.assertEqual(sq.current_pack('4444'), ('test pack', 'address'))

    def test_next_pack(self):
        sq = oup.SendQuery()
        sq._query = {'4444': [('test', 'address'), ('test2', 'address')]}

        self.assertEqual(sq.next_pack('4444'), ('test2', 'address'))

    def test_is_empty(self):
        sq = oup.SendQuery()
        sq._query = {}
        self.assertTrue(sq.is_empty)
        sq._query = {'4444': [('test', 'address'), ('test2', 'address')]}
        self.assertFalse(sq.is_empty)


class TestUDPPlus(unittest.TestCase):

    @mock.patch('over_udp_protocol.socket')
    def test_init(self, socket):
        base = oup.UDPPlus()
        self.assertTrue(base.soc)

    @mock.patch('SDJP.socket')
    def test_send(self, socket):
        mock_connection = mock.MagicMock()
        mock_connection.sendto.return_value = 6

        base = oup.UDPPlus()
        base.soc.sendto = mock_connection
        base._raw_send_to(('', 9000))
        socket.sendto.assert_with('', 9000)
        base._raw_send_to('', 'address')
        socket.sendto.assert_with('', 'address')

    @mock.patch('SDJP.socket')
    def test_receive_sdjp(self, socket):
        mock_connection = mock.MagicMock()
        mock_connection.recvfrom.side_effect = ['address']

        base = oup.UDPPlus()
        base.soc = mock_connection
        self.assertEqual(base._raw_receive(), 'address')


class TestUDPPlusServer(unittest.TestCase):

    @mock.patch('over_udp_protocol.socket')
    def test_init(self, socket):
        ser = oup.UDPPlusServer()
        socket.bind.assert_with(ser.address)

    def test_receive_data_stream_1(self):
        ser = oup.UDPPlusServer()
        pack = mock.MagicMock()
        pack.return_value = 1
        send = mock.MagicMock()
        send.return_value = 2

        ser._pack_frame = pack
        ser._raw_send_to = send
        ser._receive_data_stream('4444', 4, 1, 'test', ('', 9000))
        ser._pack_frame.assert_called_with('4444', 201, 1, 1, 'NO')
        ser._raw_send_to.assert_called_with(1, ('', 9000))

    def test_receive_data_stream_2(self):
        ser = oup.UDPPlusServer()
        pack = mock.MagicMock()
        pack.return_value = 1
        send = mock.MagicMock()
        send.return_value = 2

        ser._pack_frame = pack
        ser._raw_send_to = send
        ser._receive_data_stream('4444', 1, 2, 'test', ('', 9000))
        ser._pack_frame.assert_called_with('4444', 200, 1, 1, 'OK')
        ser._raw_send_to.assert_called_with(1, ('', 9000))

    # TODO: reactor

    def test_hand_shake_1(self):
        ser = oup.UDPPlusServer()

        ds = mock.MagicMock()
        ds.add_client.return_value = 1
        send = mock.MagicMock()
        send.return_value = 2

        ser._pack_frame = send
        ser._raw_send_to = send
        ser._hand_shake('4444', 1, 1, 'HS', ('', 9000))
        ser._raw_send_to.assert_called_with(2, ('', 9000))

    def test_hand_shake_2(self):
        ser = oup.UDPPlusServer()

        ds = mock.MagicMock()
        ds.add_client.return_value = 1
        send = mock.MagicMock()
        send.return_value = 2

        ser._pack_frame = send
        ser._raw_send_to = send
        ser._hand_shake('4444', 1, 1, 'HS', ('', 9000))
        ser._raw_send_to.assert_called_with(2, ('', 9000))

    def test_receive_data_1(self):
        ser = oup.UDPPlusServer()
        pack = mock.MagicMock()
        pack.return_value = 1

        send = mock.MagicMock()
        send.return_value = 2

        ser._pack_frame = pack
        ser._raw_send_to = send
        ser.receive_data('4444', 101, 1, 1, 'test', ('', 9000))
        ser._pack_frame.assert_called_with('4444', 200, 1, 1, 'OK')
        ser._raw_send_to.assert_called_with(1, ('', 9000))

    def test_receive_data_2(self):
        ser = oup.UDPPlusServer()
        pack = mock.MagicMock()
        pack.return_value = 1

        send = mock.MagicMock()
        send.return_value = 2

        ser._data_storage.verify_client = lambda x: True
        ser._data_storage.get_msg = lambda x: 'test'

        ser._pack_frame = pack
        ser._raw_send_to = send
        answer = ser.receive_data('4444', 101, 1, 1, 'test', ('', 9000))
        ser._pack_frame.assert_called_with('4444', 200, 1, 1, 'OK')
        ser._raw_send_to.assert_called_with(1, ('', 9000))
        self.assertEqual(answer, 'test')

    def test_send_data_stream_1(self):
        ser = oup.UDPPlusServer()
        ser.send_query._query = {'4444': ['1', '2', '3']}

        send = mock.MagicMock()
        send.return_value = 2

        ser._raw_send_to = send

        ser._send_data_stream('4444', 201, ('', 9000))
        ser._raw_send_to.assert_called_with('1', ('', 9000))
        ser._send_data_stream('4444', 200, ('', 9000))
        ser._raw_send_to.assert_called_with('2', ('', 9000))

    def test_close_server(self):
        ser = oup.UDPPlusServer()
        ser.close_server()
        self.assertFalse(ser.run_server)

    def test_send_msg(self):
        ser = oup.UDPPlusServer()
        ser.send_query.add_msg = lambda x, y, z: y

        send = mock.MagicMock()
        send.return_value = 2
        ser._raw_send_to = send

        ser.send_msg('4444', 'test', ('', 9000))
        ser._raw_send_to.assert_called_with('test')

    def test_filter_frames_1(self):
        ser = oup.UDPPlusServer()
        uid = uuid.uuid4().get_bytes()
               
        frame = ser._pack_frame(uid, 100, 1, 1, 'HS')
        print frame
        client_id, flag, current_part, max_part, data = ser.filter_frames(frame)

        self.assertEqual(client_id, uid)
        self.assertEqual(flag, 100)
        self.assertEqual(current_part, 1)
        self.assertEqual(max_part, 1)
        self.assertEqual(data, 'HS')

    def test_filter_frames_2(self):
        ser = oup.UDPPlusServer()
        self.assertRaises(oup.FrameError, ser.filter_frames, 'a'*46)

