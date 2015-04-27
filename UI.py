import logging
import urwid

import console_downloader_errors as cde
from SDJP import BaseClient, InvalidProtocol, SDJPError, ConnectionError

log = logging.getLogger('file_downloader')
log.setLevel(logging.DEBUG)
fh = logging.FileHandler('b.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
log.addHandler(fh)


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


class NetworkAdapter(BaseClient):
    """
    Class with send command to server in specifically format (SDJP)
    """
    def command_add(self, url):
        if type(url) in (set, list):
            for element in url:
                body = dict(type="COMMAND", command="ADD", data=element)
                self.send_SDJP(body)
        else:
            body = dict(type="COMMAND", command="ADD", data=url)
            self.send_SDJP(body)

    def command_delete(self, name):
        body = dict(type="COMMAND", command="DELETE", data=name)
        self.send_SDJP(body)

    def command_close_all(self, arg=None):
        body = dict(type="COMMAND", command="CLOSE_ALL", data='')
        self.send_SDJP(body)

    def command_pause_start(self, name):
        body = dict(type="COMMAND", command="PAUSE_START", data=name)
        self.send_SDJP(body)

    def command_info(self, arg=None):
        body = dict(type="COMMAND", command="INFO", data='')
        self.send_SDJP(body)
        try:
            info = self.receive_SDJP()
        except InvalidProtocol:
            return []
        return info['data']


class UI(object):
    """
    Show status of all downloads, and can manipulate on them. ^C -- close all
    downloads safely
    """
    TIME_UPDATE = 1
    STATUS_FORMAT = " file_name: {name}  - status: {status}  {size}   {" \
                    "error_msg}"
    PALETTE = [('reversed', 'yellow,bold', 'black'),
               ('standout', 'black', 'white')]

    sub_menu = False

    def __init__(self, network_adapter_instance, file_path):
        """
        :param network_adapter_instance: object Manager
        """
        assert isinstance(network_adapter_instance, NetworkAdapter)

        self.network = network_adapter_instance
        self.info_about_downloads = None
        if file_path:
            self._init_main(file_path)
        else:
            raise cde.EmptyInputData("Wrong path to file")

    def _init_main(self, file_path):
        """
        take download status and crate screen for show information
        """
        self.network.command_add(
            DataFeed(file_path).parse_file_with_urls_for_downloading())
        self.info_about_downloads = self.network.command_info()
        self.main_screen = urwid.Padding(
            self.generate_downloads_status_list_box(self.info_about_downloads),
            left=1, right=1)

    def update(self, loop, _):
        """
        callback method for update data from manager

        :param loop: loop with print frame to console
        :type loop: MainLoop
        :param _: None
        :return:
        """
        self.info_about_downloads = self.network.command_info()
        element, position = self.main_screen.original_widget.original_widget \
            .get_focus()

        if not self.sub_menu:
            self.main_screen.original_widget = \
                self.generate_downloads_status_list_box(
                    self.info_about_downloads)

        self.main_screen.original_widget.original_widget.set_focus(position)
        loop.set_alarm_in(self.TIME_UPDATE, self.update, user_data=(loop, _))

    def generate_downloads_status_list_box(self, info_about_downloads):
        """
        Generate list with button. Each button show information(file name,
        status) about one download and connected to submenu for manipulations
        on it download thread.

        :param info_about_downloads: list of InfoDownload objects
        :type info_about_downloads: list
        :return: Widget with download information and submenu for manipulation
        :rtype: Padding with ListBox inside
        """
        body = [urwid.Text("Downloading list: "), urwid.Divider()]
        for element in info_about_downloads:
            button = urwid.Button(self.str_format(element))
            urwid.connect_signal(button, 'click',
                                 self.sub_menu_download, element)
            body.append(urwid.AttrMap(button, None, focus_map='reversed'))

        return urwid.Padding(urwid.ListBox(urwid.SimpleFocusListWalker(body)),
                             left=1, right=1)

    def sub_menu_download(self, button, info_download):
        """
        Generate list with button for manipulations on selected download.

        :param button: signal from button with call this method
        :param info_download: object with information about download
        :type: InfoDownload
        """
        self.sub_menu = True
        body = [urwid.Text('\n Downloading file  {}  --  {} \n'.format(
            info_download['name'], info_download['status']), align="center")]

        done = urwid.Button(' Delete')
        pause = urwid.Button(' Pause')
        back = urwid.Button(' <<<')

        urwid.connect_signal(done, 'click', self.btn_close_download,
                             info_download['name'])
        urwid.connect_signal(pause, 'click', self.btn_pause_download,
                             info_download['name'])
        urwid.connect_signal(back, 'click', self.btn_back_to_download_list)

        if info_download['is_finished']:
            done.set_label(" OK")
            body.append(urwid.AttrMap(done, None, focus_map='reversed'))
            body.append(urwid.AttrMap(back, None, focus_map='reversed'))
        else:
            if info_download['is_paused']:
                pause.set_label(' Start')
            body.append(urwid.AttrMap(pause, None, focus_map='reversed'))
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
        self.network.command_delete(name)
        self.btn_back_to_download_list(button)

    def btn_pause_download(self, button, name):
        """
        Handler pressing the pause button

        :param button: signal from button with call this method
        :param name: file name
        :type name: string
        """
        self.network.command_pause_start(name)
        self.btn_back_to_download_list(button)

    def btn_back_to_download_list(self, button):
        """
        Handler pressing the back button

        :param button: signal from button with call this method
        """
        self.sub_menu = False
        self.info_about_downloads = self.network.command_info()
        if not self.info_about_downloads:
            raise KeyboardInterrupt("No more downloads")
        self.main_screen.original_widget = \
            self.generate_downloads_status_list_box(self.info_about_downloads)

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
        self.network.command_close_all()

    def str_format(self, info_download):
        if not info_download['file_size']:
            download_size = "{0:.2f} kb".format(
                info_download['file_downloaded_size'] / 1000.0)
        else:
            download_size = "{0:.2f} %".format(
                (info_download['file_downloaded_size'] /
                 float(info_download['file_size'])) * 100.0)
        return self.STATUS_FORMAT.format(name=info_download['name'],
                                         status=info_download['status'].center(
                                             11),
                                         error_msg=info_download['error_msg'],
                                         size=download_size)


if __name__ == '__main__':
    ui = None
    try:
        net = NetworkAdapter()
        ui = UI(net, "/tmp/1.txt")
        ui.run()
    except KeyboardInterrupt as err:
        try:
            ui.close_all_downloads()
        except ConnectionError as err:
            print '\033[93m-- No response from server -- {} \n\033[0m'.format(
                err.message)
            exit(4)
        print '\033[92m-- Shutdown -- {} \n\033[0m'.format(err.message)
    except SDJPError as error:
        if ui:
            ui.close_all_downloads()
        print '\n\033[93mOops... Something wrong --  {}\033[0m\n'.format(error)
        exit(1)
    except Exception as e:
        print "\033[92mFatal Error {} \033[0m".format(e.message)
        exit(2)
