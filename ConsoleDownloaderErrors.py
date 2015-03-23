class ConsoleDownloadBaseException(Exception):
    pass


class DownloadError(ConsoleDownloadBaseException):
    pass


class FilePathError(ConsoleDownloadBaseException):
    pass

