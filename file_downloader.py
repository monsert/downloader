import logging
import os
import string
import urllib2
import random
import threading

import console_downloader_errors as cde
from SDJP import BaseServer

log = logging.getLogger('file_downloader')
log.setLevel(logging.DEBUG)
fh = logging.FileHandler('a.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)


class DownloadFile(threading.Thread):
    """
    Class override method run from threading.Thread for downloading file
    from url and save it to directory.
    """
    __NAME_LENGTH = 10
    __DOWNLOAD_BLOCK_SIZE = 4096
    __STATUS_ERROR = 'error'
    __STATUS_DOWNLOADING = 'downloading'
    __STATUS_DONE = 'done'
    __STATUS_CLOSED = 'closed'
    __STATUS_PAUSE = 'pause'

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
        self.is_thread_paused = False
        self._size_file = 0
        self._size_downloaded = 0
        super(DownloadFile, self).__init__()

    def _set_error(self, msg):
        """
        Save error message to download_error_msg, update status to
        __STATUS_ERROR and stop thread

        :param msg: Error message
        :type msg: string
        """
        self._download_error_msg = msg
        self._download_status = self.__STATUS_ERROR
        self._stop_event.set()

    def generate_file_name(self):
        """
        Generate random file name. Length = 10 (__NAME_LENGTH), consists of [
        A-Z0-9]

        :rtype: string
        :return: random generated file name
        """
        generate_file_name = ""
        if not self._file_name:
            self._file_name = generate_file_name.join(random.choice(
                string.ascii_uppercase + string.digits) for _ in range(
                self.__NAME_LENGTH))
        return self._file_name

    def get_file_size(self):
        try:
            download_file = urllib2.urlopen(self._url)
            file_size = int(download_file.info().getheaders(
                'Content-Length')[0])
        except (urllib2.URLError, ValueError, IndexError):
            return 0
        return file_size

    def run(self):
        """
        Override method from class Thread for downloading file in thread.
        """
        self._file_name = self.generate_file_name()
        self._size_file = self.get_file_size()
        try:
            url_handler = urllib2.urlopen(self._url)
        except (urllib2.URLError, ValueError) as err:
            self._set_error(str(err))
            return

        try:
            with open(os.path.join(self._path_to_downloads_dir,
                                   self._file_name), "wb") as out_file:
                while not self._stop_event.is_set():
                    if not self.is_paused:
                        self._download_status = self.__STATUS_DOWNLOADING
                        file_part = url_handler.read(self.__DOWNLOAD_BLOCK_SIZE)
                        if not file_part:
                            self._download_status = self.__STATUS_DONE
                            break
                        out_file.write(file_part)
                        self._size_downloaded += len(file_part)
        except IOError as err:
            self._set_error(err.args[1])

    def close(self):
        """
        Safely close downloading threads and write appropriate status (
        __STATUS_CLOSED)
        """
        self._download_status = self.__STATUS_CLOSED
        self._stop_event.set()

    def pause_start(self):
        if not self.is_finished and not self.is_thread_paused:
            self.is_thread_paused = True
            self._download_status = self.__STATUS_PAUSE
        else:
            self.is_thread_paused = False

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

    @property
    def is_paused(self):
        """
        :return: True is download is paused.
        :rtype: bool
        """
        return self.is_thread_paused

    @property
    def file_size(self):
        """
        :return: if can not get file size from url return 0.
        :rtype: int
        """
        return self._size_file

    @property
    def downloaded_size(self):
        """
        :return: Current size of downloaded file
        :rtype: int
        """
        return self._size_downloaded


class InfoDownload(object):
    """
    Object for save information about thread (name, status, error_msg if
    exist, is_finished)
    """
    name = None
    status = None
    error_msg = ''
    is_finished = False
    file_size = 0
    file_downloaded_size = 0

    def __init__(self, name, status, error_msg, is_finished, is_paused,
                 file_size, downloaded_size):
        """

        :param name: file name
        :type name: string
        :param status: download status (done. error, downloading, closed)
        :type status: string
        :param error_msg: error message if was some expecting error
        :type error_msg: string
        :param is_finished: True if status is not downloading
        :type is_finished: bool
        :param is_paused: True if downloading is paused
        :type is_paused: bool
        """
        self.name = name
        self.status = status
        self.error_msg = error_msg
        self.is_finished = is_finished
        self.is_paused = is_paused
        self.file_size = file_size
        self.file_downloaded_size = downloaded_size


class Manager(object):
    """
    Manager create run and close downloading threads.

    :type _threads: dict
    :_thread_list: dict of DownloadFile instance as value, file name as key
    """
    _threads = {}

    def __init__(self, path_to_save_dir='/tmp/1/'):
        """
        :param path_to_save_dir: path to directory for save there files
        :raises: console_downloader_errors.EmptyInputData
        """
        if not path_to_save_dir:
            raise cde.EmptyInputData("Path to dir can not be empty")
        self.path_to_save_dir = path_to_save_dir
        self.urls = []

    def add_new_download(self, url):
        """
        Append to list _thread_list DownloadFile instance with url and
        path_to_save_dir and run downloading
        """
        if type(url) is list:
            for element in url:
                self.add_new_download(element)
        else:
            new_downloading_thread = DownloadFile(url, self.path_to_save_dir)
            self._threads.update({new_downloading_thread.generate_file_name():
                                  new_downloading_thread})
            new_downloading_thread.start()

    def start_all_downloads(self):
        """
        Start all threads from  _thread_list. If _thread_list is empty call
        method _init_all_downloads for fill it.
        """
        for name, thread in self._threads.items():
            if thread.is_paused:
                thread.pause_start_download()
            else:
                thread.start()

    def close_all_downloads(self):
        """
        Safely close all threads for it use DownloadFile method close
        """
        for name, thread in self._threads.items():
            thread.close()
        self._threads.clear()

    def close_download_by_index(self, name):
        """
        :param name: name (key) of thread in dict
        :type name: string
        :raises: console_downloader_errors.WrongIndex
        :return:
        """
        if name in self._threads:
            self._threads[name].close()
            self._threads.pop(name)
        else:
            raise cde.WrongIndex("Wrong file name")

    def pause_start_download(self, name):
        """
        Pause or finish downloading file

        :param name: name (key) of thread in dict
        """
        if name in self._threads:
            self._threads[name].pause_start()
        else:
            raise cde.WrongIndex("Wrong file name")

    @property
    def info_about_all_downloading(self):
        """
        Return info about all thread after it delete from list threads
        threads with status closed, done, error

        :return: list with dict. dict has key index, name, status and error_msg
        """
        out = list()
        for name, thread in self._threads.items():
            out.append(InfoDownload(name=thread.file_name,
                                    status=thread.download_status,
                                    error_msg=thread.error_message,
                                    is_finished=thread.is_finished,
                                    is_paused=thread.is_paused,
                                    file_size=thread.file_size,
                                    downloaded_size=thread.downloaded_size))
        return out


class Ninja(BaseServer):
    def __init__(self, manager):
        super(Ninja, self).__init__()
        assert isinstance(manager, Manager)
        self.manager = manager

    def command_delete(self, name):
        self.manager.close_download_by_index(name)

    def command_close_all(self, arg):
        self.manager.close_all_downloads()

    def command_pause_start(self, name):
        self.manager.pause_start_download(name)

    def command_add(self, url):
        self.manager.add_new_download(url)

    def command_info(self, arg):
        out = []
        for info in self.manager.info_about_all_downloading:
            out.append(info.__dict__)
        frame = dict(type='json', command="", data=out)
        self.send_SDJP(frame)


if __name__ == '__main__':
    serv = None
    try:
        manage = Manager()
        serv = Ninja(manage)
        serv.run()
    except KeyboardInterrupt:
        serv.manager.close_all_downloads()
        print "-- Shutdown --"
    except cde.ConsoleDownloadBaseException as error:
        if serv:
            serv.manager.close_all_downloads()
        print "Oops... Something wrong --", error
        exit(1)
    # except Exception as e:
    #     print "Fatal Error", e.message
    #     exit(2)
