import os
import time
import string
import urllib2
import random
import threading

import console_downloader_errors as cde


class DownloadFile(threading.Thread):
    __NAME_LENGTH = 10
    __DOWNLOAD_BLOCK_SIZE = 8192
    __STATUS_ERROR = 'error'
    __STATUS_DOWNLOADING = 'downloading'
    __STATUS_DONE = 'done'
    __STATUS_CLOSED = 'closed'

    _download_error_msg = ''
    _download_status = ''

    def __init__(self, url, path_to_downloads_dir):
        """
        :args: url and path to save dir
        :type url: string
        :type path_to_downloads_dir: string
        """
        self._stop_event = threading.Event()
        if not url:
            self._set_error("Argument URL can not be empty")
        if not path_to_downloads_dir:
            self._set_error("Path to dir can not be empty")
        self._url = url
        self._path_to_downloads_dir = path_to_downloads_dir
        self._file_name = ""
        super(DownloadFile, self).__init__()

    def _set_error(self, msg):
        """
        :param msg: Error message
        :type msg: string
        """
        self.download_error_msg = msg
        self._download_status = self.__STATUS_ERROR
        self._stop_event.set()

    def generate_file_name(self):
        """
        :rtype: string
        :return: random generated(A-Z0-9) file name (max length = __NAME_LENGTH)
        """
        generate_file_name = ""
        if not self._file_name:
            self._file_name = generate_file_name.join(random.choice(
                string.ascii_uppercase + string.digits) for _ in range(
                self.__NAME_LENGTH))
        return self._file_name

    def run(self):
        self._file_name = self.generate_file_name()
        try:
            url_handler = urllib2.urlopen(self._url)
        except (urllib2.URLError, ValueError) as err:
            self._set_error(err)
            return
        self._download_status = self.__STATUS_DOWNLOADING

        try:
            with open(os.path.join(self._path_to_downloads_dir,
                                   self._file_name), "wb") as out_file:
                while not self._stop_event.is_set():
                    file_part = url_handler.read(self.__DOWNLOAD_BLOCK_SIZE)
                    if not file_part:
                        self._download_status = self.__STATUS_DONE
                        break
                    out_file.write(file_part)
        except IOError as err:
            self._set_error(err.args[1])

    def close(self):
        """
        Safely close downloading threads and write appropriate status (
        __STATUS_CLOSED)
        """
        self._download_status = self.__STATUS_CLOSED
        self._stop_event.set()

    @property
    def is_running(self):
        """
        :return: True if download is in progress; False otherwise
        :rtype: bool
        """
        return not self._stop_event.is_set()

    @property
    def error_message(self):
        """
        :return: Error message string or empty string if not error.
        :rtype: str
        """
        return self._download_error_msg

    @property
    def download_status(self):
        """
        :return: one of status (error, done, closed, downloading)
        :rtype: str
        """
        return self._download_status

    @property
    def is_finished(self):
        """
        :return: True if downloading status is __STATUS_DONE, __STATUS_ERROR or
         __STATUS_CLOSED.
        :rtype: bool
        """
        return self._download_status in (self.__STATUS_DONE,
                                         self.__STATUS_ERROR,
                                         self.__STATUS_CLOSED)

    @property
    def file_name(self):
        """
        :return: name of file with downloaded data
        :rtype: str
        """
        return self._file_name


class DataFeed(object):
    def __init__(self, path_to_file_with_urls):
        """
        :param path_to_file_with_urls: path to file with urls one per line
        """
        if not path_to_file_with_urls:
            raise cde.FilePathError("Path to file can not be empty")
        self.file_urls = path_to_file_with_urls

    def get_urls_for_downloading(self):
        """
        :rtype: list
        :return: list of urls from file without duplicate
        """
        out = list()
        try:
            with open(self.file_urls, 'rb') as urls:
                out_set = set(urls.read().splitlines())
        except IOError as err:
            raise cde.FilePathError(err.args[1])
        for url in out_set:
            out.append(url.strip("/ "))
        out = filter(lambda line: line, set(out))
        return out


class Manager(object):
    """
    :type _thread_list: list
    :_thread_list: list of DownloadFile instance
    """
    _thread_list = []

    def __init__(self, url_list, path_to_save_dir):
        """
        :param url_list: string with url
        :param path_to_save_dir: path to directory for save there downloaded
        files
        :raises: console_downloader_errors.EmptyInputData
        :return:
        """
        if not url_list or type(url_list) not in [list, set]:
            raise cde.EmptyInputData("Wrong input type. Only list or set.")
        if not path_to_save_dir:
            raise cde.EmptyInputData("Path to dir can not be empty")
        self.urls = url_list
        self.path_to_save_dir = path_to_save_dir

    def _clean_finished_thread_from_list(self):
        """
        Filter _thread_list by is_finished property and save it to _thread_list
        """
        self._thread_list = filter(lambda thread: not thread.is_finished,
                                   self._thread_list)

    def _init_all_downloads(self):
        """
        Append to list _thread_list DownloadFile instance with url and
        path_to_save_dir for init
        :return:
        """
        for url in self.urls:
            new_downloading_thread = DownloadFile(url, self.path_to_save_dir)
            self._thread_list.append(new_downloading_thread)

    def start_all_downloads(self):
        self._init_all_downloads()
        for thread in self._thread_list:
            thread.start()

    def close_download_by_index(self, index):
        """
        :param index: number of thread in list
        :type index: int
        :raises: console_downloader_errors.WrongIndex, AssertionError
        :return:
        """
        assert isinstance(index, int)
        try:
            self._thread_list[index].close()
            self._thread_list.pop(index)
        except IndexError as err:
            raise cde.WrongIndex(err.message)

    def close_all_downloads(self):
        """
        Safely close all threads for it use DownloadFile method close
        :return:
        """
        for thread in self._thread_list:
            thread.close()

    @property
    def get_info_about_downloading(self):
        """
        :return: list with dict. dict has key index, name, status and error_msg
        """
        out = list()
        for index, thread in enumerate(self._thread_list):
            out.append(dict(index=index,
                            name=thread.file_name,
                            status=thread.download_status,
                            error_msg=thread.error_message))

        self._clean_finished_thread_from_list()
        return out


class UI(object):
    _OUTPUT_FORMAT = "#{id} file_name: {name} - {status} {error_msg}  "
    TIME_UPDATE = 0.5

    def __init__(self, manager_instance):
        if not isinstance(manager_instance, Manager):
            raise cde.EmptyInputData("Wrong input data")
        self.manager = manager_instance

    def convert_downloading_info_to_string(self, download_info):
        return self._OUTPUT_FORMAT.format(
            id=download_info['index'],
            name=download_info['name'],
            status=download_info['status'].center(11),
            error_msg=download_info['error_msg'])

    def show_progress(self):
        while True:
            ui_body = ''
            downloads_info = self.manager.get_info_about_downloading
            if not downloads_info:
                print "No more files. Downloads done"
                break
            for element_info in downloads_info:
                ui_body += self.convert_downloading_info_to_string(element_info)
            ui_body += '\r'
            print ui_body,
            time.sleep(self.TIME_UPDATE)

    def close_all_downloads(self):
        self.manager.close_all_downloads()


if __name__ == '__main__':
    ui = None
    try:
        data = DataFeed("/tmp/1.txt").get_urls_for_downloading()
        manage = Manager(data, "/tmp/1/")
        manage.start_all_downloads()
        ui = UI(manage)
        ui.show_progress()
    except KeyboardInterrupt:
        ui.close_all_downloads()
        print "-- Shutdown --"
    except cde.ConsoleDownloadBaseException as error:
        print "Oops... Something wrong --", error
        exit(1)
