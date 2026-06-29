#!/usr/bin/env python3

import os
import sys
import json
import time
import threading
import subprocess
from urllib.request import urlretrieve
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

LAUNCHER_DIR = os.path.expanduser("~/.palmlauncher")
VERSIONS_DIR = os.path.join(LAUNCHER_DIR, "versions")
LIBS_DIR = os.path.join(LAUNCHER_DIR, "libraries")
NICK_FILE = os.path.join(LAUNCHER_DIR, "nick.txt")
CONFIG_FILE = os.path.join(LAUNCHER_DIR, "config.json")
MD_FILE = "minecraft-server-jar-downloads.md"

for p in [LAUNCHER_DIR, VERSIONS_DIR, LIBS_DIR]:
    if not os.path.exists(p):
        os.makedirs(p)

def parse_md():
    v = {}
    if not os.path.exists(MD_FILE):
        return v
    with open(MD_FILE, 'r', encoding='utf-8') as f:
        for l in f:
            if 'client.jar' in l and '|' in l:
                p = [x.strip() for x in l.split('|')]
                if len(p) >= 4:
                    ver = p[1].replace('**', '').replace('`', '').strip()
                    url = p[3].strip()
                    if ver and url.startswith('http'):
                        v[ver] = url
    return v

def save_cache(d):
    with open(os.path.join(LAUNCHER_DIR, "versions_cache.json"), 'w') as f:
        json.dump(d, f, indent=2)

def load_cache():
    f = os.path.join(LAUNCHER_DIR, "versions_cache.json")
    if os.path.exists(f):
        try:
            with open(f, 'r') as fp:
                return json.load(fp)
        except:
            return {}
    return {}

def load_cfg():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_cfg(c):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(c, f, indent=2)

def load_nick():
    if os.path.exists(NICK_FILE):
        try:
            with open(NICK_FILE, 'r') as f:
                return f.read().strip()
        except:
            pass
    return "Player"

def save_nick(n):
    with open(NICK_FILE, 'w') as f:
        f.write(n.strip() or "Player")

def download_libraries(version):
    lib_dir = os.path.join(LIBS_DIR, version)
    if not os.path.exists(lib_dir):
        os.makedirs(lib_dir)

    libs = [
        ("net.sf.jopt-simple", "jopt-simple", "5.0.4"),
        ("com.google.guava", "guava", "31.1-jre"),
        ("com.google.code.gson", "gson", "2.10.1"),
        ("org.apache.commons", "commons-lang3", "3.12.0"),
        ("commons-logging", "commons-logging", "1.2"),
        ("org.slf4j", "slf4j-api", "1.7.36"),
        ("org.slf4j", "slf4j-simple", "1.7.36"),
        ("org.lwjgl", "lwjgl", "3.3.1"),
        ("org.lwjgl", "lwjgl-glfw", "3.3.1"),
        ("org.lwjgl", "lwjgl-opengl", "3.3.1"),
        ("org.lwjgl", "lwjgl-stb", "3.3.1"),
        ("org.lwjgl", "lwjgl-tinyfd", "3.3.1"),
        ("org.lwjgl", "lwjgl-openal", "3.3.1"),
        ("org.lwjgl", "lwjgl-jemalloc", "3.3.1"),
        ("com.mojang", "brigadier", "1.0.18"),
        ("com.mojang", "datafixerupper", "5.0.28"),
        ("com.mojang", "authlib", "3.11.49"),
        ("org.apache.logging.log4j", "log4j-api", "2.17.1"),
        ("org.apache.logging.log4j", "log4j-core", "2.17.1"),
        ("it.unimi.dsi", "fastutil", "8.5.9"),
        ("com.google.code.findbugs", "jsr305", "3.0.2"),
        ("com.mojang", "text2speech", "1.17.9"),
        ("org.jetbrains", "annotations", "23.0.0"),
    ]
    for group, artifact, ver in libs:
        filename = f"{artifact}-{ver}.jar"
        jar_path = os.path.join(lib_dir, filename)
        if not os.path.exists(jar_path):
            url = f"https://repo1.maven.org/maven2/{group.replace('.', '/')}/{artifact}/{ver}/{filename}"
            try:
                urlretrieve(url, jar_path)
            except:
                pass

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    log = pyqtSignal(str)
    done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, ver, url):
        super().__init__()
        self.ver = ver
        self.url = url

    def run(self):
        try:
            vd = os.path.join(VERSIONS_DIR, self.ver)
            if not os.path.exists(vd):
                os.makedirs(vd)
            jp = os.path.join(vd, f"{self.ver}.jar")
            self.status.emit(f"Downloading {self.ver}")
            def rep(b, s, t):
                if t > 0:
                    p = int(b * s * 100 / t)
                    self.progress.emit(min(p, 100))
            urlretrieve(self.url, jp, rep)
            self.progress.emit(100)
            self.status.emit(f"{self.ver} ready")
            self.log.emit(f"Downloaded {self.ver}")
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))

class LaunchThread(QThread):
    status = pyqtSignal(str)
    log = pyqtSignal(str)
    done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, ver, nick, ram):
        super().__init__()
        self.ver = ver
        self.nick = nick
        self.ram = ram

    def run(self):
        try:
            download_libraries(self.ver)

            jp = os.path.join(VERSIONS_DIR, self.ver, f"{self.ver}.jar")
            cp = [jp]
            ld = os.path.join(LIBS_DIR, self.ver)
            if os.path.exists(ld):
                for f in os.listdir(ld):
                    if f.endswith('.jar'):
                        cp.append(os.path.join(ld, f))
            cmd = [
                "java",
                f"-Xmx{self.ram}M",
                "-cp",
                os.pathsep.join(cp),
                "net.minecraft.client.main.Main",
                "--username", self.nick,
                "--version", self.ver,
                "--gameDir", os.path.join(LAUNCHER_DIR, "game"),
                "--assetsDir", os.path.join(LAUNCHER_DIR, "assets"),
                "--assetIndex", self.ver,
                "--uuid", "00000000-0000-0000-0000-000000000000",
                "--accessToken", "nope",
                "--userType", "mojang"
            ]
            for d in [os.path.join(LAUNCHER_DIR, "game"), os.path.join(LAUNCHER_DIR, "assets")]:
                if not os.path.exists(d):
                    os.makedirs(d)
            self.status.emit("Game running")
            self.log.emit(f"Starting {self.ver}")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in proc.stdout:
                self.log.emit(f"[MC] {line.strip()}")
            proc.wait()
            self.status.emit("Game closed")
            self.log.emit(f"Exit code: {proc.returncode}")
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 650, 500)
        self.setStyleSheet(parent.styleSheet())
        self.setup_ui()
        self.load_versions()

    def setup_ui(self):
        layout = QVBoxLayout()

        gb = QGroupBox("Version List")
        gb.setStyleSheet("QGroupBox { color: white; }")
        gbl = QVBoxLayout()

        hb = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh from MD")
        self.refresh_btn.clicked.connect(self.refresh)
        self.cnt_lbl = QLabel("Versions: 0")
        self.cnt_lbl.setStyleSheet("color: white;")
        hb.addWidget(self.refresh_btn)
        hb.addWidget(self.cnt_lbl)
        hb.addStretch()
        gbl.addLayout(hb)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.itemDoubleClicked.connect(self.select_version)
        gbl.addWidget(self.list)

        gb.setLayout(gbl)
        layout.addWidget(gb)

        ram_gb = QGroupBox("Memory")
        ram_gb.setStyleSheet("QGroupBox { color: white; }")
        ram_l = QHBoxLayout()
        ram_l.addWidget(QLabel("RAM:"))
        self.ram_spin = QSpinBox()
        self.ram_spin.setRange(512, 16384)
        self.ram_spin.setSingleStep(512)
        self.ram_spin.setSuffix(" MB")
        self.ram_spin.setValue(int(self.parent.ram))
        ram_l.addWidget(self.ram_spin)
        ram_l.addStretch()
        ram_gb.setLayout(ram_l)
        layout.addWidget(ram_gb)

        btn_l = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_l.addWidget(save_btn)
        btn_l.addWidget(close_btn)
        layout.addLayout(btn_l)

        self.setLayout(layout)

    def load_versions(self):
        vers = load_cache()
        self.list.clear()
        for v in sorted(vers.keys(), reverse=True):
            self.list.addItem(v)
        self.cnt_lbl.setText(f"Versions: {len(vers)}")
        if self.parent.selected:
            items = self.list.findItems(self.parent.selected, Qt.MatchFlag.MatchExactly)
            if items:
                self.list.setCurrentItem(items[0])

    def select_version(self, item):
        ver = item.text()
        self.parent.selected = ver
        c = load_cfg()
        c["version"] = ver
        save_cfg(c)
        self.parent.version_info.setText(f"Version: {ver}")
        self.parent.log(f"Selected version: {ver}")

    def refresh(self):
        vers = parse_md()
        if vers:
            save_cache(vers)
            self.load_versions()
            self.parent.versions = vers
            QMessageBox.information(self, "Success", f"Loaded {len(vers)} versions")
        else:
            QMessageBox.warning(self, "Error", f"Could not parse {MD_FILE}")

    def save(self):
        self.parent.ram = str(self.ram_spin.value())
        c = load_cfg()
        c["ram"] = self.parent.ram
        save_cfg(c)
        QMessageBox.information(self, "Saved", "Settings saved")
        self.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        self.versions = load_cache()
        self.selected = self.cfg.get("version", list(self.versions.keys())[0] if self.versions else "")
        self.ram = self.cfg.get("ram", "2048")
        self.nick = load_nick()
        self.dl_thread = None
        self.launch_thread = None
        self.setup_ui()
        self.setup_style()
        self.setup_bg()
        self.log("Ready")
        if self.selected:
            self.version_info.setText(f"Version: {self.selected}")
            self.log(f"Selected version: {self.selected}")

    def setup_ui(self):
        self.setWindowTitle("PalmLauncher")
        self.setGeometry(100, 100, 900, 650)
        self.setMinimumSize(800, 600)

        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.bg_label = QLabel(self)
        self.bg_label.setGeometry(self.rect())
        self.bg_label.lower()
        self.bg_blur = None
        self.bg_clear = None

        main_w = QWidget()
        main_w.setStyleSheet("background: transparent;")
        main_l = QVBoxLayout(main_w)
        main_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_l.setSpacing(15)

        title = QLabel("PALM LAUNCHER")
        title.setStyleSheet("font-size: 44px; font-weight: bold; color: white; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_l.addWidget(title)

        nl = QHBoxLayout()
        nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nl.setSpacing(10)
        nl.addWidget(QLabel("Nick:"))
        self.nick_edit = QLineEdit()
        self.nick_edit.setText(self.nick)
        self.nick_edit.setFixedWidth(200)
        nl.addWidget(self.nick_edit)
        main_l.addLayout(nl)

        self.version_info = QLabel("Version: not set")
        self.version_info.setStyleSheet("color: #8f8faf; background: transparent; font-size: 12px;")
        self.version_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_l.addWidget(self.version_info)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color: #8f8faf; background: transparent; font-size: 12px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_l.addWidget(self.status_lbl)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(350)
        self.progress.setFixedHeight(20)
        self.progress.setTextVisible(False)
        main_l.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)

        bl = QHBoxLayout()
        bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.setSpacing(15)
        self.launch_btn = QPushButton("Launch")
        self.launch_btn.setFixedSize(150, 50)
        self.launch_btn.clicked.connect(self.launch)
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setFixedSize(120, 40)
        self.settings_btn.clicked.connect(self.open_settings)
        bl.addWidget(self.launch_btn)
        bl.addWidget(self.settings_btn)
        main_l.addLayout(bl)

        main_l.addStretch()

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(130)
        layout.addWidget(main_w)
        layout.addWidget(self.console)

    def setup_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QLabel { color: white; font-family: Segoe UI; background: transparent; }
            QLineEdit {
                background: rgba(44,44,62,200);
                color: white;
                border: 2px solid #3d3d5c;
                border-radius: 15px;
                padding: 8px 15px;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #6a5a9a; }
            QPushButton {
                background: #4a3a7a;
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #6a5a9a; }
            QPushButton:pressed { background: #3a2a6a; }
            QPushButton:disabled { background: #3a3a4a; color: #6a6a7a; }
            QProgressBar {
                background: rgba(44,44,62,200);
                border: none;
                border-radius: 10px;
                height: 20px;
            }
            QProgressBar::chunk {
                background: #6a5a9a;
                border-radius: 10px;
            }
            QTextEdit {
                background: rgba(10,10,26,220);
                color: #88bbff;
                border: 2px solid #1a1a3a;
                border-radius: 10px;
                font-family: Consolas;
                font-size: 10px;
            }
            QDialog {
                background-color: #1a1a2e;
            }
            QGroupBox {
                color: white;
                border: 1px solid #3d3d5c;
                border-radius: 10px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QListWidget {
                background: rgba(44,44,62,200);
                color: white;
                border: 2px solid #3d3d5c;
                border-radius: 10px;
                padding: 5px;
            }
            QListWidget::item:selected {
                background: #6a5a9a;
            }
            QSpinBox {
                background: rgba(44,44,62,200);
                color: white;
                border: 2px solid #3d3d5c;
                border-radius: 10px;
                padding: 5px;
            }
        """)

    def setup_bg(self):
        if not os.path.exists("main.png"):
            return
        pix = QPixmap("main.png")
        if pix.isNull():
            return
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        for child in self.bg_label.findChildren(QLabel):
            child.deleteLater()

        blurred = pix.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        blur_lbl = QLabel(self.bg_label)
        blur_lbl.setPixmap(blurred)
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(60)
        blur_lbl.setGraphicsEffect(blur_effect)
        blur_lbl.setGeometry(0, 0, w, h)
        blur_lbl.show()

        clear_pix = pix.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        clear_lbl = QLabel(self.bg_label)
        clear_lbl.setPixmap(clear_pix)

        mask = QPixmap(w, h)
        mask.fill(Qt.GlobalColor.transparent)
        painter = QPainter(mask)
        grad = QRadialGradient(w/2, h/2, min(w, h)/2)
        grad.setColorAt(0.0, Qt.GlobalColor.white)
        grad.setColorAt(0.5, Qt.GlobalColor.white)
        grad.setColorAt(0.85, Qt.GlobalColor.white)
        grad.setColorAt(1.0, Qt.GlobalColor.black)
        painter.fillRect(0, 0, w, h, grad)
        painter.end()

        opacity = QGraphicsOpacityEffect()
        opacity.setOpacityMask(QBrush(mask))
        clear_lbl.setGraphicsEffect(opacity)
        clear_lbl.setGeometry(0, 0, w, h)
        clear_lbl.show()

        self.bg_blur = blur_lbl
        self.bg_clear = clear_lbl

    def resizeEvent(self, e):
        self.setup_bg()
        super().resizeEvent(e)

    def log(self, msg):
        self.console.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def set_status(self, txt, col="#8f8faf"):
        self.status_lbl.setText(txt)
        self.status_lbl.setStyleSheet(f"color: {col}; background: transparent; font-size: 12px;")

    def set_prog(self, v):
        self.progress.setValue(v)

    def open_settings(self):
        d = SettingsDialog(self)
        d.exec()
        self.version_info.setText(f"Version: {self.selected if self.selected else 'not set'}")

    def download_version(self, ver):
        self.launch_btn.setEnabled(False)
        self.set_status(f"Downloading {ver}...", "#afaf5f")
        url = self.versions.get(ver)
        if not url:
            self.handle_error(f"No URL for {ver}")
            return
        self.dl_thread = DownloadThread(ver, url)
        self.dl_thread.progress.connect(self.set_prog)
        self.dl_thread.status.connect(lambda s: self.set_status(s, "#afaf5f"))
        self.dl_thread.log.connect(self.log)
        self.dl_thread.done.connect(self.on_download_done)
        self.dl_thread.error.connect(self.handle_error)
        self.dl_thread.start()

    def on_download_done(self):
        self.launch_btn.setEnabled(True)
        self.set_status("Ready", "#5faf5f")

    def launch(self):
        nick = self.nick_edit.text().strip()
        if not nick:
            QMessageBox.warning(self, "Warning", "Enter nickname")
            return
        save_nick(nick)

        ver = self.selected
        if not ver:
            QMessageBox.warning(self, "Warning", "Select version in Settings")
            return

        jp = os.path.join(VERSIONS_DIR, ver, f"{ver}.jar")
        if not os.path.exists(jp):
            reply = QMessageBox.question(self, "Download", f"Version {ver} not downloaded. Download now?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.download_version(ver)
            return

        self.launch_btn.setEnabled(False)
        self.set_status("Launching...", "#5fafaf")
        self.set_prog(50)

        self.launch_thread = LaunchThread(ver, nick, self.ram)
        self.launch_thread.status.connect(lambda s: self.set_status(s, "#5fdf5f" if s == "Game running" else "#8f8faf"))
        self.launch_thread.log.connect(self.log)
        self.launch_thread.done.connect(self.on_launch_done)
        self.launch_thread.error.connect(self.handle_error)
        self.launch_thread.start()

    def on_launch_done(self):
        self.launch_btn.setEnabled(True)
        self.set_status("Ready", "#8f8faf")
        self.set_prog(0)

    def handle_error(self, e):
        self.set_status("Error", "#af5f5f")
        self.log(f"Error: {e}")
        self.launch_btn.setEnabled(True)
        self.set_prog(0)
        QMessageBox.critical(self, "Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
