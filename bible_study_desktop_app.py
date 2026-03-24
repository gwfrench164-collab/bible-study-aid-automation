import sys
import threading
import time

from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar
from PySide6.QtGui import QAction
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

from bible_study_search_app import app as flask_app


# -----------------------------
# Start Flask in background
# -----------------------------
def run_flask():
    flask_app.run(port=5055, debug=False, use_reloader=False)


# -----------------------------
# Desktop Window
# -----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Bible Study Aid")
        self.resize(1200, 800)

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("http://127.0.0.1:5055"))

        self.setCentralWidget(self.browser)

        self.create_toolbar()

    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        back_btn = QAction("Back", self)
        back_btn.triggered.connect(self.browser.back)
        toolbar.addAction(back_btn)

        forward_btn = QAction("Forward", self)
        forward_btn.triggered.connect(self.browser.forward)
        toolbar.addAction(forward_btn)

        reload_btn = QAction("Reload", self)
        reload_btn.triggered.connect(self.browser.reload)
        toolbar.addAction(reload_btn)

        home_btn = QAction("Home", self)
        home_btn.triggered.connect(
            lambda: self.browser.setUrl(QUrl("http://127.0.0.1:5055"))
        )
        toolbar.addAction(home_btn)


# -----------------------------
# Main Entry Point
# -----------------------------
def main():
    # Start Flask server
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Give server time to start
    time.sleep(1)

    # Start Qt app
    qt_app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()