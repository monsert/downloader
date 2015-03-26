from file_downloader import DownloadFile, DataFeed, Manager
import ConsoleDownloaderErrors as CDE
import unittest
import mock


class TestFileDownload(unittest.TestCase):
    def test_init_valid(self):
        self.assertTrue(DownloadFile("MOCK_URL", "MOCK_PATH"))

    def test_init_invalid_url(self):
        self.assertRaises(CDE.EmptyInputData, DownloadFile, "", "MOCK_PATH")

    def test_init_invalid_path(self):
        self.assertRaises(CDE.EmptyInputData, DownloadFile, "MOCK_URL", "")

    @mock.patch('file_downloader.random.choice')
    def test_get_file_name_good(self, mock_random_choice):
        mock_random_choice.return_value = "0"
        df = DownloadFile("http://site.zone/path/to/test.txt", "/tmp/")
        self.assertEqual(df.get_file_name(), "0000000000")

    @mock.patch('file_downloader.os.path.join')
    @mock.patch('file_downloader.urllib2.urlopen')
    def test_start(self, mock_urllib2_urlopen, mock_os_path_join):
        mock_os_path_join.return_value = "MOCK_PATH"

        mock_urllib2_urlopen.return_value.geturl.return_value = "MOCK_URL"
        mock_urllib2_urlopen.return_value.read.side_effect = ['line1line2line3']

        expected_write_calls = [mock.call('line1line2line3')]

        with mock.patch('file_downloader.open', create=True) as mock_open:
            mock_file_handle = mock_open.return_value.__enter__.return_value

            df = DownloadFile('MOCK_URL', 'MOCK_PATH')
            df.start()

            mock_urllib2_urlopen.assert_called_with("MOCK_URL")
            mock_open.assert_called_with('MOCK_PATH', 'wb+')

            mock_open.return_value.__exit__.assert_called_with(None, None, None)

        self.assertEquals(expected_write_calls,
                          mock_file_handle.write.mock_calls)

    def test_start_web_exception(self):
        df = DownloadFile('MOCK_URL', 'MOCK_PATH')
        self.assertRaises(CDE.DownloadError, df.start)

    @mock.patch('file_downloader.os.path.join')
    @mock.patch('file_downloader.urllib2.urlopen')
    def test_start_file_exception(self, mock_urllib2_urlopen,
                                  mock_os_path_join):
        mock_os_path_join.return_value = ""
        mock_urllib2_urlopen.return_value.geturl.return_value = "MOCK_URL"
        mock_urllib2_urlopen.return_value.read.side_effect = 'line1line2line3'
        df = DownloadFile('MOCK_URL', 'MOCK_PATH')
        self.assertRaises(CDE.FilePathError, df.start)


class TestDataFeed(unittest.TestCase):
    def test_init(self):
        self.assertTrue(DataFeed('test_dir'))

    def test_init_empty_line(self):
        self.assertRaises(CDE.FilePathError, DataFeed, "")

    @mock.patch('file_downloader.urllib2.urlopen')
    def test_get_urls_for_downloading_file_exception(self,
                                                     mock_urllib2_urlopen):
        mock_urllib2_urlopen.return_value.read.return_value.splitlines\
            .return_value = ['1', '1', '2']
        df = DataFeed('MOCK_PATH')
        self.assertRaises(CDE.FilePathError, df.get_urls_for_downloading)

    def test_get_urls_for_downloading(self):
        df = DataFeed('MOCK_PATH')

        with mock.patch('file_downloader.open', create=True) as mock_open:
            mock_file_handle = mock_open.return_value.__enter__.return_value
            df.get_urls_for_downloading()
            mock_open.assert_called_with('MOCK_PATH', 'rb')
            mock_open.return_value.__exit__.assert_called_with(None, None, None)


class TestManager(unittest.TestCase):

    def test_init(self):
        self.assertTrue(Manager(['1', '2'], "MOCK_PATH"))

    def test_init_path_exception(self):
        self.assertRaises(CDE.EmptyInputData, Manager, ['1'], '')

    def test_init_type_exception(self):
        self.assertRaises(CDE.EmptyInputData, Manager, '', "MOCK_PATH")


    def test_init_type_exception2(self):
        self.assertRaises(CDE.EmptyInputData, Manager, [], "MOCK_PATH")

    @mock.patch("file_downloader.DownloadFile")
    @mock.patch('file_downloader.threading.Thread')
    def test_init_all_downloads(self, mock_threading_thread,
                                mock_download_file):
        mock_threading_thread.side_effect = ['thread1', 'thread2']
        mock_download_file.return_value.start.return_value = "download_obj"
        manage = Manager(['url1', 'url2'], "/tmp")
        manage.init_all_downloads()
        self.assertListEqual(manage.THREAD_LIST, ['thread1', 'thread2'])

    def test_start_all_downloads(self):
        manage = Manager(['url1', 'url2'], "/tmp")
        mock_thread = mock.MagicMock()
        mock_thread.return_value.start.return_value = "run"

        manage.THREAD_LIST = [mock_thread]

        init_all_downloads = mock.MagicMock()
        init_all_downloads.return_value = ""

        manage.init_all_downloads = init_all_downloads
        manage.start_all_downloads()
        self.assertIn(mock_thread, manage.THREAD_LIST)
