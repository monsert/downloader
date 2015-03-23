__author__ = 'andy'
from  file_downloader import DownloadFile
import unittest
import mock
import os


class TestFileDownload(unittest.TestCase):

    @mock.patch('file_downloader.os')
    @mock.patch('file_downloader.os.path')
    def test_validation_input_data_path (self, mock_os, mock_os_path):
        fd = DownloadFile("MOCK_URL", "MOCK_PATH")
        mock_os_path.isdir.return_value = True
        self.assertTrue(fd.is_valid_input_data())

    @mock.patch('file_downloader.os')
    @mock.patch('file_downloader.os.path')
    def test_validation_input_data_url (self, mock_os, mock_os_path):
        fd = DownloadFile("", "MOCK_PATH")
        mock_os_path.isdir.return_value = True
        self.assertFalse(fd.is_valid_input_data())

    def test_get_file_name_good(self):
        fd = DownloadFile("http://site.zone/path/to/test.txt", "/tmp/")
        self.assertEqual(fd.get_file_name(), "test.txt")

    def test_get_file_name(self):
        fd = DownloadFile("http://site.zone/path/to/test.txt/", "/tmp/")
        self.assertEqual(fd.get_file_name(), "test.txt")


    @mock.patch('file_downloader.DownloadFile')
    @mock.patch('file_downloader.DownloadFile.is_valid_data')
    @mock.patch('file_downloader.urllib2.urlopen')
    def test_start (self, mock_DownloadFile,
                    mock_DownloadFile_is_valid_input_data,
                    mock_urllib2_urlopen):
        mock_DownloadFile_is_valid_input_data.return_value = True
        mock_urllib2_urlopen = mock.MagicMock()
        mock_urllib2_urlopen.read.side_effect=['line1', 'line2', 'line3', '']


