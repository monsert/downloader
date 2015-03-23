from file_downloader import DownloadFile, DataFeed
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

    def test_get_file_name_good(self):
        df = DownloadFile("http://site.zone/path/to/test.txt", "/tmp/")
        self.assertEqual(df.get_file_name(), "test.txt")

    def test_get_file_name(self):
        df = DownloadFile("http://site.zone/path/to/test.txt/", "/tmp/")
        self.assertEqual(df.get_file_name(), "test.txt")

    @mock.patch('file_downloader.os.path.join')
    @mock.patch('file_downloader.urllib2.urlopen')
    def test_start(self, mock_urllib2_urlopen, mock_os_path_join):
        mock_os_path_join.return_value = "MOCK_PATH"

        mock_urllib2_response = mock.MagicMock()
        mock_urllib2_response.read.side_effect = ['line1', 'line2', 'line3', '']
        mock_urllib2_urlopen.return_value = mock_urllib2_response

        expected_write_calls = [mock.call('line1'), mock.call('line2'),
                                mock.call('line3')]

        with mock.patch('file_downloader.open', create=True) as mock_open:
            mock_file_handle = mock_open.return_value.__enter__.return_value

            df = DownloadFile('MOCK_URL', 'MOCK_PATH')
            df.start()
            mock_urllib2_urlopen.assert_called_with('MOCK_URL')
            mock_open.assert_called_with('MOCK_PATH', 'wb+')

            mock_open.return_value.__exit__.assert_called_with(None, None, None)

        self.assertEquals(expected_write_calls,
                          mock_file_handle.write.mock_calls)

    def test_start_web_exception(self):
        df = DownloadFile('MOCK_URL', 'MOCK_PATH')
        self.assertRaises(CDE.DownloadError, df.start)

    @mock.patch('file_downloader.urllib2.urlopen')
    def test_start_file_exception(self, mock_urllib2_urlopen):
        df = DownloadFile('MOCK_URL', 'MOCK_PATH')
        self.assertRaises(CDE.FilePathError, df.start)


class TestDataFeed(unittest.TestCase):
    def setUp(self):
        pass

    def test_init(self):
        self.assertTrue(DataFeed('test_dir'))

    def test_init_empty_line(self):
        self.assertRaises(CDE.FilePathError, DataFeed, "")

    def test_get_urls_for_downloading_file_exception(self):
        df = DataFeed('MOCK_PATH')
        self.assertRaises(CDE.FilePathError, df.get_urls_for_downloading)

    def test_get_urls_for_downloading(self):
        df = DataFeed('MOCK_PATH')

        with mock.patch('file_downloader.open', create=True) as mock_open:
            mock_file_handle = mock_open.return_value.__enter__.return_value
            df.get_urls_for_downloading()
            mock_open.assert_called_with('MOCK_PATH', 'r')
            mock_open.return_value.__exit__.assert_called_with(None, None, None)
