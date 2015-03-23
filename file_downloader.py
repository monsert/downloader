import os
import urllib2
import ConsoleDownloaderErrors as CDE


class DownloadFile():
    """
    :arg url, path to save dir
    """
    DOWNLOAD_BLOCK_SIZE = 8192
    #TODO: add opportunity to cancel downloading
    def __init__(self, url, path_to_dir):
        if not url:
            raise CDE.EmptyInputData("Argument URL can not be empty")
        if not path_to_dir:
            raise CDE.EmptyInputData("Path to dir can not be empty")
        self._url = url
        self._path_to_dir = path_to_dir
        self._downloaded = 0

    def get_file_name(self):
        file_name = self._url.split('/')
        if not file_name[-1]:
            return file_name[-2]
        else:
            return file_name[-1]

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
                    self._downloaded += self.DOWNLOAD_BLOCK_SIZE
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
        out = list()
        try:
            with open(self.file_urls, 'rb') as urls:
                out_set = set(urls.read().splitlines())
            if '' in out_set:
                out = out_set.remove('')
            return list(out)
        except IOError as err:
            raise CDE.FilePathError(err.message)

tmp = DataFeed("/tmp/1.txt")
tmp.get_urls_for_downloading()