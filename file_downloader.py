import os
import urllib2
import ConsoleDownloaderErrors as CDE


class DownloadFile():
    """
    :arg url, path to save dir
    """
    DOWNLOAD_BLOCK_SIZE = 8192

    def __init__(self, url, path_to_dir):
        self._url = url
        self._path_to_dir = path_to_dir
        self._downloaded = None

    def is_valid_input_data(self):
        #TODO: valid URL by regexp
        """
        if input data (url and path_to_dir) valid return True else False
        :return: bool
        """
        if self._url != "" and os.path.isdir(self._path_to_dir):
            return True
        else:
            return False

    def get_file_name(self):
        file_name = self._url.split('/')
        if not file_name[-1]:
            return file_name[-2]
        else:
            return file_name[-1]

    def get_block_data(self):
        pass

    def start(self):
        if self.is_valid_input_data():
            with open(self._path_to_dir, "wb") as out_file:
                while True:
                    data = urllib2.urlopen(self._url).read(self.DOWNLOAD_BLOCK_SIZE)
                    if not data:
                        break
                    out_file.write(data)
                    self._downloaded += self.DOWNLOAD_BLOCK_SIZE
        else:
            raise CDE.FilePathError("Invalid path or URL")

