import logging
import os
import string
import urllib2
import random
import threading
import urwid

import console_downloader_errors as cde

log = logging.getLogger('file_downloader')
log.setLevel(logging.DEBUG)
fh = logging.FileHandler('a.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)


# TODO: add start stop to DownloadFile -> Manager -> UI
class DownloadFile(threading.Thread):
    """
    Class override method run from threading.Thread for downloading file
    from url and save it to directory.
    """
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

    def run(self):
        """
        Override method from class Thread for downloading file in thread.
        """
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
    """
    Parse input file with one URL per line. Validates the URLs, discards
    empty.
    """

    def __init__(self, path_to_file_with_urls):
        """
        :raise: console_downloader_errors.FilePathError
        :param path_to_file_with_urls: path to file with urls one per line
        """
        if not path_to_file_with_urls:
            raise cde.FilePathError("Path to file can not be empty")
        self.file_urls = path_to_file_with_urls

    def parse_file_with_urls_for_downloading(self):
        """
        Parse file, delete duplicate and fix mistake in ending of urls

        :raise: console_downloader_errors.FilePathError
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


class InfoDownload(object):
    """
    Object for save information about thread (name, status, error_msg if
    exist, is_finished)
    """
    _STR_FORMAT = " file_name: {name}  -  status: {status}  {error_msg}"
    name = None
    status = None
    error_msg = ''
    is_finished = False

    def __init__(self, name, status, error_msg, is_finished):
        """

        :param name: file name
        :type name: string
        :param status: download status (done. error, downloading, closed)
        :type status: string
        :param error_msg: error message if was some expecting error
        :type error_msg: string
        :param is_finished: True if status is not downloading
        :type is_finished: bool
        """
        self.name = name
        self.status = status
        self.error_msg = error_msg
        self.is_finished = is_finished

    def __str__(self):
        """
        :return: Formatted line.
         Example: file_name: FREDDI  -  status: error  HTTP Error 503
        """
        return self._STR_FORMAT.format(name=self.name, status=self.status,
                                        error_msg=self.error_msg)


class Manager(object):
    """
    Manager create run and close downloading threads.

    :type _thread_list: dict
    :_thread_list: dict of DownloadFile instance as value, file name as key
    """
    # FIXME : rename _thread_list not list more
    _thread_list = {}

    def __init__(self, url_list, path_to_save_dir):
        """
        :param url_list: string with url
        :param path_to_save_dir: path to directory for save there files
        :raises: console_downloader_errors.EmptyInputData
        """
        if not url_list or type(url_list) not in [list, set]:
            raise cde.EmptyInputData("Wrong input type. Only list or set.")
        if not path_to_save_dir:
            raise cde.EmptyInputData("Path to dir can not be empty")
        self.urls = url_list
        self.path_to_save_dir = path_to_save_dir

    def _clean_finished_thread_from_list(self):
        """
        Delete thread from list which not working (status: done, error, closed)
        """
        for name, thread in self._thread_list.items():
            if thread.is_finished:
                self._thread_list.pop(name)

    def _init_all_downloads(self):
        """
        Append to list _thread_list DownloadFile instance with url and
        path_to_save_dir for init
        """
        for url in self.urls:
            new_downloading_thread = DownloadFile(url, self.path_to_save_dir)
            self._thread_list.update({
                new_downloading_thread.generate_file_name():
                    new_downloading_thread})

    def start_all_downloads(self):
        """
        Start all threads from  _thread_list. If _thread_list is empty call
        method _init_all_downloads for fill it.
        """
        if not self._thread_list:
            self._init_all_downloads()
        for name, thread in self._thread_list.items():
            thread.start()

    def close_all_downloads(self):
        """
        Safely close all threads for it use DownloadFile method close
        """
        for name, thread in self._thread_list.items():
            thread.close()

    def close_download_by_index(self, name):
        """
        :param name: name (key) of thread in dict
        :type name: string
        :raises: console_downloader_errors.WrongIndex
        :return:
        """
        if name in self._thread_list:
            self._thread_list[name].close()
            self._thread_list.pop(name)
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
        for name, thread in self._thread_list.items():
            out.append(InfoDownload(name=thread.file_name,
                                    status=thread.download_status,
                                    error_msg=thread.error_message,
                                    is_finished=thread.is_finished))
        return out


class UI(object):
    """
    Show status of all downloads, and can close all downloads safely
    """
    TIME_UPDATE = 1
    PALETTE = [('reversed', 'yellow,bold', ''),
               ('standout', 'black', 'white')]

    sub_menu = False

    def __init__(self, manager_instance):
        """
        :param manager_instance: object Manager
        """
        if not isinstance(manager_instance, Manager):
            raise cde.EmptyInputData("Wrong input data")
        self.manager = manager_instance
        self.downloads_status = None
        self._init_main()

    def _init_main(self):
        """
        take download status and crate screen for show information
        """

        self.downloads_status = self.manager.info_about_all_downloading
        self.main_screen = urwid.Padding(self.downloads_list_box(),
                                         left=1, right=1)

    def update(self, loop, _):
        """
        callback method for update data from manager

        :param loop: loop with print frame to console
        :type loop: MainLoop
        :param _: None
        :return:
        """
        self.downloads_status = self.manager.info_about_all_downloading
        element, position = self.main_screen.original_widget.original_widget \
            .get_focus()

        if not self.sub_menu:
            self.main_screen.original_widget = self.downloads_list_box()

        self.main_screen.original_widget.original_widget.set_focus(position)
        loop.set_alarm_in(self.TIME_UPDATE, self.update, user_data=(loop, _))

    def downloads_list_box(self):
        """
        Generate list with button. Each button show information(file name,
        status) about one download and connected to submenu for manipulations
        on it download thread.

        :return: Widget with download information and submenu for manipulation
        :rtype: Padding with ListBox inside
        """
        body = [urwid.Text("Downloading list: "), urwid.Divider()]
        for element in self.downloads_status:
            button = urwid.Button(str(element))
            urwid.connect_signal(button, 'click',
                                 self.sub_menu_download, element)
            body.append(urwid.AttrMap(button, None, focus_map='reversed'))
        return urwid.Padding(
            urwid.ListBox(urwid.SimpleFocusListWalker(body)), left=1, right=1)

    def sub_menu_download(self, button, info_download):
        """
        Generate list with button for manipulations on selected download.


        :param button: signal from button with call this method
        :param info_download: object with information about download
        :type: InfoDownload
        """
        self.sub_menu = True
        body = [urwid.Text('Downloading file {}  --  {} \n'.format(
            info_download.name, info_download.status))]

        done = urwid.Button(' Delete')
        back = urwid.Button(' <<<')

        urwid.connect_signal(done, 'click', self.btn_close_download,
                             info_download.name)
        urwid.connect_signal(back, 'click', self.btn_back_to_download_list)

        body.append(urwid.AttrMap(done, None, focus_map='reversed'))
        body.append(urwid.AttrMap(back, None, focus_map='reversed'))
        self.main_screen.original_widget = urwid.Padding(urwid.ListBox(
            urwid.SimpleFocusListWalker(body)), left=1, right=1)

    def btn_close_download(self, button, name):
        """
        Handler pressing the close button

        :param button: signal from button with call this method
        :param name: file name
        :type name: string
        """

        self.manager.close_download_by_index(name)
        self.btn_back_to_download_list(None)

    def btn_back_to_download_list(self, button):
        """
        Handler pressing the back button

        :param button: signal from button with call this method
        """
        self.sub_menu = False
        self.downloads_status = self.manager.info_about_all_downloading
        self.main_screen.original_widget = self.downloads_list_box()

    def run(self):
        """
        Start the main loop handling input events and updating the screen
        and downloading information.
        """
        loop = urwid.MainLoop(self.main_screen, palette=self.PALETTE)
        loop.set_alarm_in(self.TIME_UPDATE, self.update)
        loop.run()

    def close_all_downloads(self):
        """
        Close all downloads. For it use manager api.
        """
        self.manager.close_all_downloads()


if __name__ == '__main__':
    ui = None
    try:
        data = DataFeed("/tmp/1.txt").parse_file_with_urls_for_downloading()
        manage = Manager(data, "/tmp/1/")
        manage.start_all_downloads()
        ui = UI(manage)
        ui.run()
    except KeyboardInterrupt:
        ui.close_all_downloads()
        print "-- Shutdown --"
    except cde.ConsoleDownloadBaseException as error:
        print "Oops... Something wrong --", error
        exit(1)
