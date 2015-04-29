import mock
import unittest
import json
import struct

import UI
import SDJP
import file_downloader
import console_downloader_errors as cde


class TestDownloadFile(unittest.TestCase):
    def test_init_valid(self):
        self.assertTrue(file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH'))

    def test_init_invalid_url(self):
        df = file_downloader.DownloadFile('', 'MOCK_PATH')
        self.assertEqual(df._download_status, 'error')
        self.assertNotEqual(df._download_error_msg, '')

    def test_init_invalid_path(self):
        df = file_downloader.DownloadFile('MOCK_URL', '')
        self.assertEqual(df._download_status, 'error')
        self.assertNotEqual(df._download_error_msg, '')

    @mock.patch('file_downloader.random.choice')
    def test_get_file_name_good(self, mock_random_choice):
        mock_random_choice.return_value = '0'
        df = file_downloader.DownloadFile('http://path/to/test.txt', '/tmp/')
        self.assertEqual(df.generate_file_name(), '0000000000')

    def test_get_file_name_call_2(self):
        df = file_downloader.DownloadFile('http://path/to/test.txt', '/tmp/')
        df._file_name = 'name'
        self.assertEqual(df.generate_file_name(), 'name')

    @mock.patch('file_downloader.os.path.join')
    @mock.patch('file_downloader.urllib2.urlopen')
    def test_run_success(self, mock_urllib2_urlopen, mock_os_path_join):
        mock_os_path_join.return_value = 'MOCK_PATH'

        mock_urllib2_response = mock.MagicMock()
        mock_urllib2_response.read.side_effect = ['line1', 'line2', 'line3', '']
        mock_urllib2_urlopen.return_value = mock_urllib2_response

        expected_write_calls = [mock.call('line1'), mock.call('line2'),
                                mock.call('line3')]

        with mock.patch('file_downloader.open', create=True) as mock_open:
            mock_file_handle = mock_open.return_value.__enter__.return_value

            df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
            df.run()
            mock_urllib2_urlopen.assert_called_with('MOCK_URL')
            mock_open.assert_called_with('MOCK_PATH', 'wb')

            mock_open.return_value.__exit__.assert_called_with(None, None, None)

        self.assertEquals(expected_write_calls,
                          mock_file_handle.write.mock_calls)

    def test_run_web_exception(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df.run()
        self.assertEqual(df._download_status, 'error')
        self.assertNotEqual(df._download_error_msg, '')

    @mock.patch('file_downloader.os.path.join')
    @mock.patch('file_downloader.urllib2.urlopen')
    def test_run_file_exception(self, mock_urllib2_urlopen,
                                mock_os_path_join):
        mock_os_path_join.return_value = ''
        mock_urllib2_urlopen.return_value.geturl.return_value = 'MOCK_URL'
        mock_urllib2_urlopen.return_value.read.side_effect = 'line1line2line3'
        function = mock.MagicMock()
        function.get_file_name.return_value = ''

        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df.run()
        self.assertEqual(df._download_status, 'error')
        self.assertNotEqual(df._download_error_msg, '')

    def test_close(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        self.assertFalse(df.close())

    def test_pause_star(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df._download_status = 'downloading'
        df.pause_start()
        self.assertTrue(df.is_paused)
        self.assertEqual(df.download_status, 'pause')

    def test_pause_star2(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df._download_status = 'done'
        df.pause_start()
        self.assertFalse(df.is_paused)
        self.assertEqual(df.download_status, 'done')

    def test_property_is_running(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        self.assertTrue(df.is_running)

    def test_property_error_message(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df._download_error_msg = 'IOError'
        self.assertEqual(df.error_message, 'IOError')

    def test_property_download_status(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df._download_status = 'done'
        self.assertEqual(df.download_status, 'done')

    def test_property_is_finished(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df._download_status = 'error'
        self.assertTrue(df.is_finished)

    def test_property_file_name(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df._file_name = 'name'
        self.assertEqual(df.file_name, 'name')

    def test_property_file_size(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df._size_file = 123
        self.assertEqual(df.file_size, 123)

    def test_property_downloaded_size(self):
        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df._size_downloaded = 1234
        self.assertEqual(df.downloaded_size, 1234)


class TestManager(unittest.TestCase):

    def test_init(self):
        self.assertTrue(file_downloader.Manager('MOCK_PATH'))

    def test_init_path_exception(self):
        self.assertRaises(cde.EmptyInputData, file_downloader.Manager, '')

    @mock.patch('file_downloader.DownloadFile')
    def test_add_new_download(self, DownloadFile):
        DownloadFile.return_value.generate_file_name.return_value = 'test_name'
        DownloadFile.start.return_value = True

        manage = file_downloader.Manager('/tmp')
        manage._threads = {}

        manage.add_new_download('new download')
        self.assertIn('test_name', manage._threads)

    @mock.patch('file_downloader.DownloadFile')
    def test_add_new_download2(self, DownloadFile):
        DownloadFile.return_value.generate_file_name.return_value = 'test_name'
        DownloadFile.start.return_value = True

        manage = file_downloader.Manager('/tmp')
        manage._threads = {}

        manage.add_new_download(['new download', 'new download'])
        self.assertIn('test_name', manage._threads)

    def test_start_all_downloads(self):
        manage = file_downloader.Manager('/tmp')

        mock_thread = mock.MagicMock()
        mock_thread.is_paused = True
        mock_thread.return_value.pause_start_download.return_value = True

        manage._threads = {'NAME': mock_thread}
        manage.start_all_downloads()
        mock_thread.pause_start_download.assert_called_once()
        self.assertIn('NAME', manage._threads)

    def test_start_all_downloads2(self):
        manage = file_downloader.Manager('/tmp')

        mock_thread = mock.MagicMock()
        mock_thread.is_paused = False
        mock_thread.return_value.start.return_value = True

        manage._threads = {'NAME': mock_thread}
        manage.start_all_downloads()
        mock_thread.start.assert_called_once()
        self.assertIn('NAME', manage._threads)

    def test_close_all_downloads(self):
        manage = file_downloader.Manager('MOCK_PATH')
        thread_element = mock.MagicMock()
        thread_element.return_value.close = ''

        manage._threads = {'NAME': thread_element, }
        manage.close_all_downloads()
        thread_element.assert_called_once()

    def test_close_download_by_index(self):
        manage = file_downloader.Manager('MOCK_PATH')
        thread_element = mock.MagicMock()
        thread_element.return_value.close = ''

        manage._threads = {'NAME': thread_element, }
        manage.close_download_by_index('NAME')
        thread_element.assert_called_once()
        self.assertFalse(manage._threads)

    def test_close_download_by_index_exception(self):
        manage = file_downloader.Manager('MOCK_PATH')
        self.assertRaises(cde.WrongIndex, manage.close_download_by_index, 'id')

    def test_pause_start(self):
        manage = file_downloader.Manager('MOCK_PATH')
        thread_element = mock.MagicMock()
        thread_element.return_value.pause_start_download = ''

        manage._threads = {'NAME': thread_element, }
        manage.close_download_by_index('NAME')
        thread_element.assert_called_once()
        self.assertFalse(manage._threads)

    def test_pause_start_exception(self):
        manage = file_downloader.Manager('MOCK_PATH')
        self.assertRaises(cde.WrongIndex, manage.pause_start_download, 'id')

    def test_property_get_info_about_downloading(self):
        manager = file_downloader.Manager('/tmp/')
        thread_element = mock.MagicMock()
        thread_element.file_name = 'file_name'
        thread_element.download_status = 'done'
        thread_element.error_message = 'download_error_msg'
        manager._threads = {'NAME': thread_element}
        self.assertIsInstance(manager.info_about_all_downloading[-1],
                              file_downloader.InfoDownload)


class TestInfoDownload(unittest.TestCase):
    def test_init(self):
        info = file_downloader.InfoDownload('name', 'done', '', False, False,
                                            0, 100)
        self.assertEqual(info.name, 'name')
        self.assertEqual(info.status, 'done')
        self.assertEqual(info.error_msg, '')
        self.assertFalse(info.is_finished)
        self.assertFalse(info.is_paused)
        self.assertEqual(info.file_size, 0)
        self.assertEqual(info.file_downloaded_size, 100)


class TestCommandServerProtocol(unittest.TestCase):

    @mock.patch('SDJP.socket')
    def test_init(self, socket):
        manage = file_downloader.Manager()
        self.assertTrue(file_downloader.CommandServerProtocol(manage))

    @mock.patch('SDJP.socket')
    def test_init_exception(self, socket):
        self.assertRaises(AssertionError, file_downloader.CommandServerProtocol, '')

    @mock.patch('SDJP.socket')
    def test_command_delete(self, socket):
        man = file_downloader.Manager()
        mock_manage = mock.MagicMock()
        mock_manage.close_download_by_index.return_value = True
        serv = file_downloader.CommandServerProtocol(man)
        serv.manager = mock_manage
        serv.command_delete(None, None, 'name')
        mock_manage.close_download_by_index.assert_called_once_with('name')

    def test_command_close_all(self):
        man = file_downloader.Manager()
        mock_manage = mock.MagicMock()
        mock_manage.close_all_downloads.return_value = True
        serv = file_downloader.CommandServerProtocol(man)
        serv.manager = mock_manage
        su_self = mock.MagicMock
        su_self.download = True
        serv.command_close_all(su_self, None, '')
        mock_manage.close_all_downloads.assert_called_once()
        self.assertFalse(su_self.download)

    def test_command_pause_start(self):
        man = file_downloader.Manager()
        mock_manage = mock.MagicMock()
        mock_manage.pause_start_download.return_value = True
        serv = file_downloader.CommandServerProtocol(man)
        serv.manager = mock_manage
        serv.command_pause_start(None, None, 'name')
        mock_manage.pause_start_download.assert_called_once_with('name')

    def test_command_add(self):
        man = file_downloader.Manager()
        mock_manage = mock.MagicMock()
        mock_manage.add_new_download.return_value = True
        serv = file_downloader.CommandServerProtocol(man)
        serv.manager = mock_manage
        serv.command_add(None, None, 'url')
        mock_manage.add_new_download.assert_called_once_with('url')

    def test_command_get_info(self):
        man = file_downloader.Manager()

        mock_manage = mock.MagicMock()
        mock_info = mock.MagicMock()

        mock_info.return_value.__dict__ = {'name': 'object'}
        mock_manage.info_about_all_downloading = [mock_info]

        serv = file_downloader.CommandServerProtocol(man)
        serv.send_SDJP = lambda x: True
        serv.manager = mock_manage
        su_self = mock.MagicMock()
        su_self.send_SDJP.return_value = True
        serv.command_info(su_self, None, '')
        mock_manage.command_info.assert_called_once()

# ------------------------UI.py------------------------------


class TestDataFeed(unittest.TestCase):
    def test_init(self):
        self.assertTrue(UI.DataFeed('test_dir'))

    def test_init_empty_line(self):
        self.assertRaises(cde.FilePathError, UI.DataFeed, '')

    def test_get_urls_for_downloading_file_exception(self):
        urls = mock.MagicMock()
        urls.return_value.read.return_value.splitlines\
            .return_value = ['1', '1', '2//   ']
        df = UI.DataFeed('MOCK_PATH')
        self.assertRaises(cde.FilePathError,
                          df.parse_file_with_urls_for_downloading)

    def test_parse_file_with_urls_for_downloading(self):
        df = UI.DataFeed('MOCK_PATH')
        mock_read = mock.MagicMock()
        mock_read.read.return_value.splitlines.return_value = ['1', '1///',
                                                               '2//   ', '2']
        with mock.patch('UI.open', create=True) as mock_open:
            mock_file_handle = mock_open.return_value.__enter__.return_value\
                = mock_read
            rez = df.parse_file_with_urls_for_downloading()
            mock_open.assert_called_with('MOCK_PATH', 'rb')
            mock_open.return_value.__exit__.assert_called_with(None, None, None)
        self.assertListEqual(rez, ['1', '2'])


class TestNetworkAdapter(unittest.TestCase):
    valid_msg = {'type': 'command', 'command': 'ADD', 'data': 'name'}
    invalid_msg = {'type': '', 'command': 'ADD', 'data': 'name'}

    def test_validation(self):
        m = file_downloader.Manager()
        base = file_downloader.CommandServerProtocol(m)
        self.assertRaises(SDJP.InvalidProtocol, base.validation, "test")
        self.assertRaises(SDJP.InvalidProtocol, base.validation, json.dumps(
            self.invalid_msg))
        self.assertEqual(base.validation(json.dumps(self.valid_msg)),
                         self.valid_msg)

    @mock.patch('SDJP.socket')
    def test_command_add(self, socket):
        mock_send = mock.MagicMock()
        mock_send.send_SDJP.return_value = True

        net = UI.NetworkAdapter()
        net.send_SDJP = mock_send
        urls = ['1', '2', '3', '4']
        net.command_add(urls)

        self.assertEqual(net.send_SDJP.call_count, 4)
#
    @mock.patch('SDJP.socket')
    @mock.patch('SDJP.BaseClient')
    def test_command_add2(self, base, socket):
        mock_send = mock.MagicMock()
        mock_send.send_SDJP.return_value = True

        net = UI.NetworkAdapter()
        net.send_SDJP = mock_send
        urls = '1'
        net.command_add(urls)

        self.assertEqual(net.send_SDJP.call_count, 1)

    @mock.patch('SDJP.socket')
    def test_command_delete(self, socket):
        mock_send = mock.MagicMock()
        mock_send.send_SDJP.return_value = True

        net = UI.NetworkAdapter()
        net.send_SDJP = mock_send
        net.command_delete('name')
        net.send_SDJP.assert_called_with(dict(type='COMMAND', command='DELETE',
                                              data='name'))

    @mock.patch('SDJP.socket')
    def test_command_close_all(self, socket):
        mock_send = mock.MagicMock()
        mock_send.send_SDJP.return_value = True

        net = UI.NetworkAdapter()
        net.send_SDJP = mock_send
        net.command_close_all()
        net.send_SDJP.assert_called_with(dict(type='COMMAND',
                                              command='CLOSE_ALL',
                                              data=''))

    @mock.patch('SDJP.socket')
    def test_command_pause_start(self, socket):
        mock_send = mock.MagicMock()
        mock_send.send_SDJP.return_value = True

        net = UI.NetworkAdapter()
        net.send_SDJP = mock_send
        net.command_pause_start('name')
        net.send_SDJP.assert_called_with({'type': 'COMMAND',
                                          'command': 'PAUSE_START',
                                          'data': 'name'})

    @mock.patch('SDJP.socket')
    def test_command_info(self, socket):
        mock_send = mock.MagicMock()
        mock_recv = mock.MagicMock()
        mock_send.send_SDJP.return_value = True
        mock_recv.receive_SDJP.return_value = {'type': 'command',
                                               'command': 'add',
                                               'data': 'data'}
        net = UI.NetworkAdapter()
        net.send_SDJP = mock_send
        net.receive_SDJP = mock_recv
        net.command_info()
        net.send_SDJP.assert_called_with(dict(type='COMMAND',
                                              command='INFO',
                                              data=''))

# -----------------------SDJP.py-----------------------------


class TestBaseSDJP (unittest.TestCase):
    valid_msg = {'type': 'command', 'command': 'ADD', 'data': 'name'}
    invalid_msg = {'type': '', 'command': 'ADD', 'data': 'name'}

    def test_validation(self):
        m = file_downloader.Manager()
        base = file_downloader.CommandServerProtocol(m)
        self.assertRaises(SDJP.InvalidProtocol, base.validation, "test")
        self.assertRaises(SDJP.InvalidProtocol, base.validation, json.dumps(
            self.invalid_msg))
        self.assertEqual(base.validation(json.dumps(self.valid_msg)),
                         self.valid_msg)

    def test_action(self):
        valid_msg = [{'command': 'PAUSE_START', 'data': 'name'},
                     {'command': 'DELETE', 'data': 'name'},
                     {'command': 'ADD', 'data': 'name'},
                     {'command': 'CLOSE_ALL', 'data': ''},
                     {'command': 'INFO', 'data': ''}]
        su_self = mock.MagicMock()
        su_self.download = True
        su_self.send_SDJP.return_value = True

        mock_thread = mock.MagicMock()
        mock_thread.close.return_value = True

        m = file_downloader.Manager()
        m._threads = {'name': mock_thread}
        base = file_downloader.CommandServerProtocol(m)
        for di in valid_msg:
            self.assertEqual(base.action(su_self, None, di), None)


class TestBaseClient(unittest.TestCase):
    valid_msg = {'type': 'command', 'command': 'ADD', 'data': 'name'}
    invalid_msg = {'type': '', 'command': 'ADD', 'data': 'name'}

    @mock.patch('SDJP.socket')
    def test_init(self, socket):
        base = SDJP.BaseClient()
        socket.connect.send.assert_with((base._HOST, base._PORT))

    @mock.patch('SDJP.socket')
    def test_receive(self, socket):
        mock_connection = mock.MagicMock()
        mock_connection.recv.side_effect = ['000111**',]

        base = SDJP.BaseClient()
        base.soc = mock_connection
        self.assertEqual(base._receive(8), '000111**')

    @mock.patch('SDJP.socket')
    def test_send(self, socket):
        mock_connection = mock.MagicMock()
        mock_connection.send.return_value = 6

        base = SDJP.BaseClient()
        base.soc = mock_connection
        base._send('000111')
        socket.send.assert_with('000111')

    @mock.patch('SDJP.socket')
    def test_receive_sdjp(self, socket):
        mock_connection = mock.MagicMock()
        tmp = json.dumps(self.valid_msg)
        mock_connection.recv.side_effect = [struct.pack( '!i', len(tmp)), tmp]

        base = SDJP.BaseClient()
        base.soc = mock_connection
        self.assertEqual(base.receive_SDJP(), tmp)

    @mock.patch('SDJP.socket')
    def test_receive_sdjp2(self, socket):
        mock_connection = mock.MagicMock()
        mock_connection.recv.side_effect = ['aaaa',
                                            json.dumps(self.valid_msg)]

        base = SDJP.BaseClient()
        base._receive = mock_connection
        self.assertRaises(SDJP.InvalidProtocol, base.receive_SDJP)

    @mock.patch('SDJP.socket')
    def test_receive_sdjp3(self, socket):
        mock_connection = mock.MagicMock()
        tmp = json.dumps(self.valid_msg)
        mock_connection.recv.side_effect = [struct.pack( '!i', len(tmp)), tmp]

        base = SDJP.BaseClient()
        base.soc = mock_connection
        self.assertEqual(base.receive_SDJP(), tmp)

    @mock.patch('SDJP.socket')
    def test_send_sdjp(self, socket):
        mock_connection = mock.MagicMock()
        mock_connection.send.side_effect = [1111, 2222, 3, 4, 5, 6]

        base = SDJP.BaseClient()
        base.soc = mock_connection
        base.send_SDJP('test msg')
        socket.send.assert_called_once()


class TestBaseServer(unittest.TestCase):
    valid_msg = {'type': 'command', 'command': 'ADD', 'data': 'name'}
    invalid_msg = {'type': '', 'command': 'delete', 'data': 'name'}

    @mock.patch('SDJP.socket')
    def test_init(self, socket):
        base = SDJP.BaseServer()
        socket.bind.assert_with((base._IP, base._PORT))
        socket.listen.assert_with(base._BACKLOG)

    @mock.patch('SDJP.socket')
    def test_receive(self, socket):
        mock_connection = mock.MagicMock()
        mock_connection.recv.side_effect = ['000111**',]

        base = SDJP.BaseServer()
        self.assertEqual(base._receive(mock_connection, 8), '000111**')

    @mock.patch('SDJP.socket')
    def test_send(self, socket):
        mock_connection = mock.MagicMock()
        mock_connection.send.return_value = 6

        base = SDJP.BaseServer()
        base._send(mock_connection, '000111')
        socket.send.assert_with('000111')

    @mock.patch('SDJP.socket')
    def test_receive_sdjp(self, socket):
        mock_connection = mock.MagicMock()
        tmp = json.dumps(self.valid_msg)
        mock_connection.recv.side_effect = [struct.pack( '!i', len(tmp)), tmp]

        base = SDJP.BaseServer()
        self.assertEqual(base.receive_SDJP(mock_connection), tmp)

    @mock.patch('SDJP.socket')
    def test_receive_sdjp2(self, socket):
        mock_connection = mock.MagicMock()
        mock_connection._receive.side_effect = ['0000',
                                            json.dumps(self.valid_msg)]

        base = SDJP.BaseServer()
        base._receive = mock_connection
        self.assertRaises(SDJP.InvalidProtocol, base.receive_SDJP,
                          None)

    @mock.patch('SDJP.socket')
    def test_receive_sdjp3(self, socket):
        mock_connection = mock.MagicMock()
        tmp = json.dumps(self.valid_msg)
        mock_connection.recv.side_effect = [struct.pack( '!i', len(tmp)), tmp]

        base = SDJP.BaseServer()
        self.assertEqual(base.receive_SDJP(mock_connection), tmp)

    @mock.patch('SDJP.socket')
    def test_send_sdjp(self, socket):
        mock_connection = mock.MagicMock()
        mock_connection.send.side_effect = [1111, 2222, 3, 4, 5, 6]

        base = SDJP.BaseServer()
        base.send_SDJP(mock_connection, 'test msg')
        socket.send.assert_called_once()
        socket.send.assert_with("{'test msg'}")


class TestCustomProtocolServer(unittest.TestCase):
    valid_msg = {'type': 'command', 'command': 'ADD', 'data': 'name'}
    invalid_msg = {'type': '', 'command': 'delete', 'data': 'name'}


    @mock.patch('SDJP.socket')
    def test_shutdown_server(self, socket):
        m = SDJP.BaseServerProtocol()
        base = SDJP.CustomProtocolServer(m)
        base.shutdown_server()
        self.assertFalse(base.server_work)

    @mock.patch('SDJP.socket')
    def test_run(self, socket):
        m = SDJP.BaseServerProtocol()
        mock_connection = mock.MagicMock()
        tmp = json.dumps(self.valid_msg)
        mock_connection.recv.side_effect = [struct.pack( '!i', len(tmp)),
                                            tmp,
                                            struct.pack( '!i', len(tmp)),
                                            tmp]
        mock_connection.close.return_value = True

        mock_accept = mock.MagicMock()
        mock_accept.accept.return_value = mock_connection, 'localhost'
        mock_accept.close.return_value = None

        tmp_invalid = json.dumps(self.invalid_msg)
        mock__receive = mock.MagicMock()
        mock__receive.side_effect = [struct.pack( '!i', len(tmp)),
                                     tmp,
                                     struct.pack( '!i', len(tmp_invalid)),
                                     tmp_invalid]

        base = SDJP.CustomProtocolServer(m)
        base._receive = mock__receive

        base.soc = mock_accept
        base.connection = mock_connection
        try:
            base.run()
        except StopIteration:
            base.shutdown_server()
            base.run()
        self.assertEqual(base.soc.accept.call_count, 1)
        self.assertTrue(base.download)
        base.soc.close.assert_called_once()
