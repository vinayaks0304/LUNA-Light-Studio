import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from mrstar.window import MainWindow

app = QApplication(sys.argv)
app.setApplicationName('LUNA')
app.setOrganizationName('LUNA Light Studio')

# Works both from source and in the self-contained PyInstaller bundle.
resource_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
icon_file = resource_root / 'assets' / 'luna-512.png'
if icon_file.is_file():
    app.setWindowIcon(QIcon(str(icon_file)))
window = MainWindow()
window.show()
sys.exit(app.exec())
