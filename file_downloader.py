import os
import urlparse
import urllib2
import ConsoleDownloaderErrors as CDE


class DownloadFile():
    """
    :arg url, path to save dir
    """
    def __init__(self, url, path_to_downloads_dir):
        if not url:
            raise CDE.EmptyInputData("Argument URL can not be empty")
        if not path_to_downloads_dir:
            raise CDE.EmptyInputData("Path to dir can not be empty")
        self._url = url
        self._path_to_downloads_dir = path_to_downloads_dir

    def get_file_name(self):
        try:
            url_handler = urllib2.urlopen(self._url)
            file_name = url_handler.info().getheaders(
                'Content-Disposition')[0]
        except (urllib2.URLError, ValueError) as err:
            raise CDE.DownloadError(err.message)
        except IndexError:
            file_path = urlparse.urlparse(self._url).path.strip("/")
            file_name = file_path.split('/')[-1]
        return file_name

    def start(self):
        try:
            url_handler = urllib2.urlopen(self._url)
        except (urllib2.URLError, ValueError) as err:
            raise CDE.DownloadError(err.message)
        try:
            with open(os.path.join(self._path_to_downloads_dir,
                                   self.get_file_name()), "wb+") as out_file:
                data = url_handler.read()
                out_file.write(data)
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
        except IOError as err:
            raise CDE.FilePathError(err.message)
        for url in out_set:
            out.append(url.strip("/ "))
        out = filter(lambda line: line, set(out))
        return out
