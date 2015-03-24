import os
import urlparse
import urllib2
import threading
import ConsoleDownloaderErrors as CDE


class DownloadFile():
    """
    :arg url, path to save dir
    """
    DOWNLOAD_BLOCK_SIZE = 8192

    # TODO: add opportunity to cancel downloading

    def __init__(self, url, path_to_dir):
        if not url:
            raise CDE.EmptyInputData("Argument URL can not be empty")
        if not path_to_dir:
            raise CDE.EmptyInputData("Path to dir can not be empty")
        self._url = url
        self._path_to_dir = path_to_dir
        self._size_downloaded = 0

    def get_file_size(self):
        try:
            download_file = urllib2.urlopen(self._url)
            file_size = int(download_file.info().getheaders(
                'Content-Length')[0])
        except (urllib2.URLError, ValueError, IndexError):
            return 'undefined'
        return file_size

    def get_file_name(self):
        file_path = urlparse.urlparse(self._url).path
        if file_path.endswith('/'):
            return file_path.split('/')[-2]
        else:
            return file_path.split('/')[-1]

    def start(self):
        try:
            url_handler = urllib2.urlopen(self._url)
        except (urllib2.URLError, ValueError) as err:
            raise CDE.DownloadError(err.message)
        try:
            with open(os.path.join(self._path_to_dir, self.get_file_name()),
                      "wb+") as out_file:
                while True:
                    data = url_handler.read(self.DOWNLOAD_BLOCK_SIZE)
                    if not data:
                        break
                    out_file.write(data)
                    self._size_downloaded += self.DOWNLOAD_BLOCK_SIZE
        except IOError as err:
            raise CDE.FilePathError(err.message)


class DataFeed():
    def __init__(self, path_to_file_with_urls):
        """
        :param path_to_file_with_urls: path to file with urls one per line
        :return:
        """
        if not path_to_file_with_urls:
            raise CDE.FilePathError("Path to file can not be empty")
        self.file_urls = path_to_file_with_urls

    def get_urls_for_downloading(self):
        """
        :return: list of urls from file
        """
        try:
            with open(self.file_urls, 'rb') as urls:
                out_set = set(urls.read().splitlines())
        except IOError as err:
            raise CDE.FilePathError(err.message)
        if '' in out_set:
            out = list(out_set.remove(''))
        else:
            out = list(out_set)
        return out