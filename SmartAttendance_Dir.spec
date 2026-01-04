import sys
from PyInstaller.utils.hooks import collect_all

# Increase recursion depth significantly
sys.setrecursionlimit(50000)

a = Analysis(
    ['run_desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('frontend', 'frontend'), 
        ('serviceAccountKey.json', '.'), 
        ('.env', '.')
    ],
    hiddenimports=[
        'engineio.async_drivers.threading', 
        'flask_cors',
        'geopy',
        'face_recognition',
        'cv2',
        'PIL',
        'numpy',
        'dns.dnssec',
        'dns.e164',
        'dns.hash',
        'dns.namedict',
        'dns.tsigkeyring',
        'dns.update',
        'dns.version',
        'dns.zone'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# Collect all data for face_recognition and dlib just in case
tmp_ret = collect_all('face_recognition')
a.datas += tmp_ret[0]; a.binaries += tmp_ret[1]; a.hiddenimports += tmp_ret[2]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SmartAttendance',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SmartAttendance',
)
