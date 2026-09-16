# Build on each target OS: pyinstaller --clean FlowTextCapture.spec
from pathlib import Path
import platform

root = Path(SPECPATH)
hidden = ["pytesseract"]
data_files = [(str(root / "templates"), "templates"), (str(root / "static"), "static")]
if (root / "tesseract").is_dir():
    data_files.append((str(root / "tesseract"), "tesseract"))
if platform.system() == "Darwin":
    hidden.append("ocrmac")

a = Analysis(
    [str(root / "gui.py")],
    pathex=[str(root)],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden,
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=["easyocr", "torch", "torchvision"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="FlowTextCapture", debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False)
if platform.system() == "Darwin":
    app = BUNDLE(exe, name="FlowTextCapture.app", bundle_identifier="com.flowtextcapture.app")
