from PySide6.QtGui import QIcon
from PySide6.QtCore import QByteArray, QTemporaryFile, QFile, QDir


def application_icon() -> QIcon:
    return _AppIcon()


class _AppIcon(QIcon):
    _temp_file_path: str

    def __init__(self):
        self._temp_file_path = self._write_temp_file()
        super().__init__(self._temp_file_path)

    def __del__(self):
        QFile.remove(self._temp_file_path)

    def _write_temp_file(self) -> str:
        # We embed the logo.svg file as a base64 string because Nuitka's method of embedding data files
        # causes the macOS app bundle to fail codesigning.
        #
        # See: https://github.com/Nuitka/Nuitka/issues/2906
        svg_data = QByteArray.fromBase64(
            b'PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMTggMjE4IiB4bW'
            b'xuczp2PSJodHRwczovL3ZlY3RhLmlvL25hbm8iPjxkZWZzPjxsaW5lYXJHcmFkaWVudCBpZD0iQSIgeDE9IjEy'
            b'LjAxOCIgeTE9IjIxLjY0MiIgeDI9IjEyLjAwNSIgeTI9IjIuNzk2IiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2'
            b'VPblVzZSI+PHN0b3Agb2Zmc2V0PSIuMDYyIiBzdG9wLWNvbG9yPSIjZThlOGU4Ii8+PHN0b3Agb2Zmc2V0PSIu'
            b'MzU2IiBzdG9wLWNvbG9yPSIjZmZmIi8+PC9saW5lYXJHcmFkaWVudD48bGluZWFyR3JhZGllbnQgaWQ9IkIiIH'
            b'gxPSI5Ny45OTEiIHkxPSIxNS4wOTIiIHgyPSI5OC4wMjciIHkyPSIyMDcuNDI1IiBzcHJlYWRNZXRob2Q9InJl'
            b'ZmxlY3QiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj48c3RvcCBvZmZzZXQ9Ii4xNDEiIHN0b3AtY2'
            b'9sb3I9IiNlMWI2NTEiLz48c3RvcCBvZmZzZXQ9Ii40ODciIHN0b3AtY29sb3I9IiNlMWI2NTEiLz48c3RvcCBv'
            b'ZmZzZXQ9Ii44NzQiIHN0b3AtY29sb3I9IiNkNTkzMTUiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48cGF0aC'
            b'BkPSJNMTA0LjM4MyAxMTYuOTIxQzc2LjI2IDg4Ljc4IDY4LjcxNCA0OC4xMzEgODEuMTY5IDEyLjk0N2MtMTMu'
            b'NjA3IDQuODE0LTI2LjQ3IDEyLjM0Mi0zNy4zNDIgMjMuMjE1LTM5LjAzMyAzOS4wMzItMzkuMDMzIDEwMi4zMD'
            b'UgMCAxNDEuMzEgMzkuMDE0IDM5LjAxNSAxMDIuMjYgMzkuMDM1IDE0MS4yOTMgMCAxMC45MS0xMC44NzEgMTgu'
            b'NDItMjMuNzM1IDIzLjIxNS0zNy4zNC0zNS4xNjUgMTIuNDUzLTc1LjgzMyA0LjkwNi0xMDMuOTU1LTIzLjIxM3'
            b'oiIGZpbGw9InVybCgjQikiIHN0cm9rZT0iIzJjMmMyYyIgc3Ryb2tlLXdpZHRoPSIxLjUiIGltYWdlLXJlbmRl'
            b'cmluZz0iY3Jpc3AtZWRnZXMiLz48ZyBzdHJva2U9IiM0MDQwNDAiPjxnIHN0cm9rZS1saW5lam9pbj0icm91bm'
            b'QiPjxwYXRoIGQ9Ik0xNC40MTIgMi43MzVINi40YTIuMDAzIDEuODc3IDAgMCAwLTIuMDAzIDEuODc3djE1LjAx'
            b'NmEyLjAwMyAxLjg3NyAwIDAgMCAyLjAwMyAxLjg3N2gxMi4wMmEyLjAwMyAxLjg3NyAwIDAgMCAyLjAwMy0xLj'
            b'g3N1Y4LjM2NloiIHRyYW5zZm9ybT0ibWF0cml4KDQuODkwMDUgMCAwIDUuMzQ2NyA1NC45OTQgNDIuNTc2KSIg'
            b'ZmlsbD0idXJsKCNBKSIgc3Ryb2tlLXdpZHRoPSIuMjkzIi8+PHBhdGggZD0iTTEyNS40NTUgNTcuMjY5djMyLj'
            b'A4aDI5LjM0IiBmaWxsPSIjZDlkOWQ5IiBzdHJva2Utd2lkdGg9IjEuNTAxIiBzdHJva2UtbGluZWNhcD0icm91'
            b'bmQiLz48L2c+PGcgZmlsbD0ibm9uZSIgc3Ryb2tlLXdpZHRoPSIxLjUwMSIgc3Ryb2tlLWxpbmVqb2luPSJyb3'
            b'VuZCI+PHBhdGggZD0iTTg5LjYwMyA5Ni4zNzloNTEuNDg2djUxLjA1Mkg4OS42MDN6Ii8+PHBhdGggZD0iTTE0'
            b'MS4wODkgMTEzLjM5Nkg4OS42MDNtNTEuNDg2IDE3LjAxN0g4OS42MDMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZC'
            b'IvPjwvZz48L2c+PC9zdmc+'
        )

        file = QTemporaryFile(QDir.temp().absoluteFilePath('icon_XXXXXX.svg'))
        file.setAutoRemove(False)
        file.open()
        file.write(svg_data)
        file.close()

        return file.fileName()
