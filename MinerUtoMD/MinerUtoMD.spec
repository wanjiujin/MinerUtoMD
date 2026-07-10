# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui_simple.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.yaml', '.'),
        ('config_presets.yaml', '.'),
        ('mineru_local_models.json', '.'),
        ('doc_workflow.py', '.'),
        ('mineru_extractor.py', '.'),
        ('pandoc_converter.py', '.'),
        ('markdown_optimizer.py', '.'),
        ('watermark_remover.py', '.'),
        ('quality_checker.py', '.'),
        ('task_manifest.py', '.'),
        ('environment_diagnostics.py', '.'),
    ],
    hiddenimports=[
        'quality_checker',
        'task_manifest',
        'environment_diagnostics',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MinerUtoMD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
