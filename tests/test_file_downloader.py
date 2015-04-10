import mock
import unittest
from StringIO import StringIO

import file_downloader
import console_downloader_errors as cde


class TestDownloadFile(unittest.TestCase):
    def test_init_valid(self):
        self.assertTrue(file_downloader.DownloadFile("MOCK_URL", "MOCK_PATH"))

    def test_init_invalid_url(self):
        df = file_downloader.DownloadFile("", "MOCK_PATH")
        self.assertEqual(df._download_status, "error")
        self.assertNotEqual(df._download_error_msg, "")

    def test_init_invalid_path(self):
        df = file_downloader.DownloadFile("MOCK_URL", "")
        self.assertEqual(df._download_status, "error")
        self.assertNotEqual(df._download_error_msg, "")

    @mock.patch('file_downloader.random.choice')
    def test_get_file_name_good(self, mock_random_choice):
        mock_random_choice.return_value = "0"
        df = file_downloader.DownloadFile("http://path/to/test.txt", "/tmp/")
        self.assertEqual(df.generate_file_name(), "0000000000")

    def test_get_file_name_call_2(self):
        df = file_downloader.DownloadFile("http://path/to/test.txt", "/tmp/")
        df._file_name = "name"
        self.assertEqual(df.generate_file_name(), "name")

    @mock.patch('file_downloader.os.path.join')
    @mock.patch('file_downloader.urllib2.urlopen')
    def test_run_success(self, mock_urllib2_urlopen, mock_os_path_join):
        mock_os_path_join.return_value = "MOCK_PATH"

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
        self.assertEqual(df._download_status, "error")
        self.assertNotEqual(df._download_error_msg, "")

    @mock.patch('file_downloader.os.path.join')
    @mock.patch('file_downloader.urllib2.urlopen')
    def test_run_file_exception(self, mock_urllib2_urlopen,
                                mock_os_path_join):
        mock_os_path_join.return_value = ""
        mock_urllib2_urlopen.return_value.geturl.return_value = "MOCK_URL"
        mock_urllib2_urlopen.return_value.read.side_effect = 'line1line2line3'
        function = mock.MagicMock()
        function.get_file_name.return_value = ""

        df = file_downloader.DownloadFile('MOCK_URL', 'MOCK_PATH')
        df.run()
        self.assertEqual(df._download_status, "error")
        self.assertNotEqual(df._download_error_msg, '')

    def test_close(self):
        df = file_downloader.DownloadFile("MOCK_URL", "MOCK_PATH")
        self.assertFalse(df.close())

    def test_property_is_running(self):
        df = file_downloader.DownloadFile("MOCK_URL", "MOCK_PATH")
        self.assertTrue(df.is_running)

    def test_property_error_message(self):
        df = file_downloader.DownloadFile("MOCK_URL", "MOCK_PATH")
        df._download_error_msg = 'IOError'
        self.assertEqual(df.error_message, 'IOError')

    def test_property_download_status(self):
        df = file_downloader.DownloadFile("MOCK_URL", "MOCK_PATH")
        df._download_status = 'done'
        self.assertEqual(df.download_status, 'done')

    def test_property_is_finished(self):
        df = file_downloader.DownloadFile("MOCK_URL", "MOCK_PATH")
        df._download_status = 'error'
        self.assertTrue(df.is_finished)

    def test_property_file_name(self):
        df = file_downloader.DownloadFile("MOCK_URL", "MOCK_PATH")
        df._file_name = 'name'
        self.assertEqual(df.file_name, 'name')


class TestDataFeed(unittest.TestCase):
    def test_init(self):
        self.assertTrue(file_downloader.DataFeed('test_dir'))

    def test_init_empty_line(self):
        self.assertRaises(cde.FilePathError, file_downloader.DataFeed, "")

    def test_get_urls_for_downloading_file_exception(self):
        urls = mock.MagicMock()
        urls.return_value.read.return_value.splitlines\
            .return_value = ['1', '1', '2//   ']
        df = file_downloader.DataFeed('MOCK_PATH')
        self.assertRaises(cde.FilePathError,
                          df.parse_file_with_urls_for_downloading)

    def test_get_urls_for_downloading(self):
        df = file_downloader.DataFeed('MOCK_PATH')
        mock_read = mock.MagicMock()
        mock_read.read.return_value.splitlines.return_value = ['1', '1///',
                                                               '2//   ', '2']
        with mock.patch('file_downloader.open', create=True) as mock_open:
            mock_file_handle = mock_open.return_value.__enter__.return_value \
                = mock_read
            rez = df.parse_file_with_urls_for_downloading()
            mock_open.assert_called_with('MOCK_PATH', 'rb')
            mock_open.return_value.__exit__.assert_called_with(None, None, None)
        self.assertListEqual(rez, ['1', '2'])


class TestManager(unittest.TestCase):

    def test_init(self):
        self.assertTrue(file_downloader.Manager(['1', '2'], "MOCK_PATH"))

    def test_init_path_exception(self):
        self.assertRaises(cde.EmptyInputData, file_downloader.Manager,
                          ['1'], '')

    def test_init_type_exception(self):
        self.assertRaises(cde.EmptyInputData, file_downloader.Manager,
                          '', "MOCK_PATH")

    def test_init_type_exception2(self):
        self.assertRaises(cde.EmptyInputData, file_downloader.Manager,
                          [], "MOCK_PATH")

    @mock.patch("file_downloader.DownloadFile")
    def test__init_all_downloads(self, mock_download_file):
        mock_thread = mock.MagicMock()
        mock_thread.return_value.generate_file_name.side_effect \
            = ["NAME1", "NAME2"]
        mock_download_file.side_effect = [mock_thread, mock_thread]
        manage = file_downloader.Manager(['url1', 'url2'], "/tmp")
        manage._init_all_downloads()
        self.assertDictContainsSubset(mock_thread, manage._thread_list)

    def test_start_all_downloads(self):
        manage = file_downloader.Manager(['url1', 'url2'], "/tmp")
        mock_thread = mock.MagicMock()
        mock_thread.return_value.start = "run"
        manage._thread_list = {}
        manage._init_all_downloads = lambda: manage._thread_list.update({
            "NAME": mock_thread})
        manage.start_all_downloads()
        self.assertIn("NAME", manage._thread_list)

    def test_close_all_downloads(self):
        manage = file_downloader.Manager(['MOCK_URL'], 'MOCK_PATH')
        thread_element = mock.MagicMock()
        thread_element.return_value.close = ''

        manage._thread_list = {"NAME": thread_element, }
        manage.close_all_downloads()
        thread_element.assert_called_once()

    # @mock.patch(file_downloader.InfoDownload)
    def test_property_get_info_about_downloading(self):
        manager = file_downloader.Manager([1, 2, 3], "/tmp/")
        thread_element = mock.MagicMock()
        thread_element.file_name = 'file_name'
        thread_element.download_status = 'done'
        thread_element.error_message = 'download_error_msg'
        manager._thread_list = {'NAME': thread_element}
        self.assertIsInstance(manager.info_about_all_downloading[-1],
            file_downloader.InfoDownload,
            )


class TestInfoDownload(unittest.TestCase):
    def test_init(self):
        info = file_downloader.InfoDownload('name', 'done', '', False)
        self.assertEqual(str(info), info._STR_FORMAT.format(name='name',
                                                       status='done',
                                                       error_msg=''))
    def test_init_2(self):
        info = file_downloader.InfoDownload('name', 'done', '', False)
        self.assertEqual(info.name, 'name')
        self.assertEqual(info.status, 'done')
        self.assertEqual(info.error_msg, '')

class TestUI(unittest.TestCase):

    def test_init_good(self):
        mock_instance = file_downloader.Manager([1, 2], "way")
        self.assertTrue(file_downloader.UI(mock_instance))

    def test_init_exception(self):
        self.assertRaises(cde.EmptyInputData, file_downloader.UI, None)

    def test_close_all_downloads(self):
        mock_instance = file_downloader.Manager([1, 2], "way")
        thread_element = mock.MagicMock()
        thread_element.close.return_value = None
        mock_instance._thread_list = {'NAME': thread_element, }

        ui = file_downloader.UI(mock_instance)
        self.assertIsNone(ui.close_all_downloads())
