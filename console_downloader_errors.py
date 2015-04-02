class ConsoleDownloadBaseException(Exception):
    pass


class DownloadError(ConsoleDownloadBaseException):
    pass


class FilePathError(ConsoleDownloadBaseException):
    pass


class EmptyInputData(ConsoleDownloadBaseException):
    pass


class WrongIndex(ConsoleDownloadBaseException):
    pass