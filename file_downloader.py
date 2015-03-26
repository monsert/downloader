import os
import string
import urllib2
import random
import threading

import ConsoleDownloaderErrors as CDE


class DownloadFile(threading.Thread):
    """
    :arg url, path to save dir
    """
    __NAME_LENGTH = 10

    def __init__(self, url, path_to_downloads_dir):
        """
        :type url: str
        """
        if not url:
            raise CDE.EmptyInputData("Argument URL can not be empty")
        if not path_to_downloads_dir:
            raise CDE.EmptyInputData("Path to dir can not be empty")
        self._url = url
        self._path_to_downloads_dir = path_to_downloads_dir
        self._file_name = ""
        self.live = True
        super(DownloadFile, self).__init__()

    def get_file_name(self):
        generate_file_name = ""
        if not self._file_name:
            self._file_name = generate_file_name.join(random.choice(
                string.ascii_uppercase + string.digits) for _ in range(
                self.__NAME_LENGTH))
        return self._file_name

    def run(self):
        try:
            url_handler = urllib2.urlopen(self._url)
        except (urllib2.URLError, ValueError) as err:
            raise CDE.DownloadError(err.message)
        try:
            with open(os.path.join(self._path_to_downloads_dir,
                                   self.get_file_name()), "wb+") as out_file:
                while self.live:
                    file_part = url_handler.read(8192)
                    if not file_part:
                        break
                    out_file.write(file_part)
        except IOError as err:
            raise CDE.FilePathError(err.message)

    def close(self):
        self.live = False


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


class Manager():
    thread_list = []

    def __init__(self, url_list, path_to_save_dir):
        if not url_list or type(url_list) not in [list, set]:
            raise CDE.EmptyInputData("Wrong input type. Only list or set.")
        if not path_to_save_dir:
            raise CDE.EmptyInputData("Path to dir can not be empty")
        self.urls = url_list
        self.path_to_save_dir = path_to_save_dir

    def init_all_downloads(self):
        for url in self.urls:
            new_downloading_thread = DownloadFile(url, self.path_to_save_dir)
            self.thread_list.append(new_downloading_thread)

    def start_all_downloads(self):
        self.init_all_downloads()
        for thread in self.thread_list:
            thread.start()
