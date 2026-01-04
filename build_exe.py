import PyInstaller.__main__
import sys
import os
import face_recognition_models

# Increase recursion depth for deep dependency trees
sys.setrecursionlimit(50000)

# Get the path to face_recognition_models to bundle them explicitly
models_path = os.path.dirname(face_recognition_models.__file__)

print(f"Bundling face_recognition_models from: {models_path}")

PyInstaller.__main__.run([
    'run_desktop.py',
    '--name=SmartAttendance',
    '--onefile',
    '--windowed',
    '--add-data=frontend;frontend',
    '--add-data=serviceAccountKey.json;.',
    '--add-data=.env;.',
    f'--add-data={models_path};face_recognition_models', # Crucial fix for "Unable to open ... dat" error
    '--hidden-import=flask_cors',
    '--clean',
    '--exclude-module=PyQt6',
    '--exclude-module=PyQt5',
    '--exclude-module=PySide6',
    '--exclude-module=PySide2',
])
