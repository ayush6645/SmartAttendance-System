import PyInstaller.__main__
import sys

sys.setrecursionlimit(10000)

PyInstaller.__main__.run([
    'run_desktop.py',
    '--name=SmartAttendance',
    '--onefile',
    '--windowed',
    '--add-data=frontend;frontend',
    '--add-data=serviceAccountKey.json;.',
    '--add-data=.env;.',
    '--hidden-import=flask_cors',
    '--clean',
    '--exclude-module=PyQt6',
    '--exclude-module=PyQt5',
    '--exclude-module=PySide6',
    '--exclude-module=PySide2',
])
