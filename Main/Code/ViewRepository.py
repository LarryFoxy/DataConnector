import os
import json
import requests
import hashlib
import sys
from pathlib import Path
from urllib.parse import urljoin, quote

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QLabel,
    QFileDialog,
    QInputDialog,
    QTextEdit,
    QLineEdit,
    QMenu,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QAction, QFont, QPalette, QColor, QIcon


VERSION = "v0.3"
CONFIG_FILE = "config.json"


def load_config():
    if not os.path.isfile(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    if "admin_key" not in config:
        return None
    return config


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    if os.name == "nt":
        os.system('attrib +r +h +s config.json')


def inspect():
    config = load_config()
    if not config:
        return "Не настроен"

    github_user = config["github_user"]
    github_repo = config["github_repo"]
    github_folder = config["github_folder"]

    url = f"https://api.github.com/repos/{github_user}/{github_repo}/contents/{github_folder}"
    headers = {}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return "Есть"
        elif response.status_code == 404:
            return "Не найдено"
        elif response.status_code == 403:
            return "Заблокировано"
        else:
            return "Неизвестно"
    except Exception:
        return "Нет связи"


def get_github_tree_recursive(base_url, path=""):
    """
    base_url уже включает Test_Data_Folder.
    path — относительный путь: Data_TEST или Data_TEST/test_2.
    """
    headers = {}
    if path:
        url = f"{base_url}/{path}"
    else:
        url = base_url

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        items = response.json()
    except Exception as e:
        return f"ERR: {e}"

    result = {}
    for item in items:
        if item["type"] == "file":
            result[item["name"]] = "file"
        elif item["type"] == "dir":
            github_folder = load_config()["github_folder"]
            prefix = f"{github_folder}/"
            rel = item["path"][len(prefix):] if item["path"].startswith(prefix) else item["path"]
            sub = get_github_tree_recursive(base_url, rel)
            if isinstance(sub, dict):
                result[item["name"]] = sub
            else:
                result[item["name"]] = sub
    return result

def build_tree_widget(root_item, tree_dict):
    style = root_item.treeWidget().style()
    icon_file = style.standardIcon(style.StandardPixmap.SP_FileIcon)
    icon_folder = style.standardIcon(style.StandardPixmap.SP_DirIcon)

    for name, children in tree_dict.items():
        # ЧИСТОЕ ИМЯ для пути (без иконок!)
        clean_name = name
        
        item = QTreeWidgetItem(root_item, [clean_name])
        if children == "file":
            item.setIcon(0, icon_file)
        elif isinstance(children, dict):
            item.setIcon(0, icon_folder)
            build_tree_widget(item, children)
        else:
            item.setText(0, f"{clean_name} [Ошибка: {children}]")




# ========== ИСПРАВЛЕННЫЕ ФУНКЦИИ ДЛЯ СКАЧИВАНИЯ ==========
def get_raw_download_url(github_user, github_repo, file_path):
    """Формирует НАДЁЖНУЮ ссылку на raw.githubusercontent.com"""
    # file_path должен быть полным: Test_Data_Folder/subfolder/file.txt
    return f"https://raw.githubusercontent.com/{github_user}/{github_repo}/main/{quote(file_path)}"


def download_single_file(github_item, save_dir, relative_path="", log_func=None):
    """Скачивает файл через raw.githubusercontent.com"""
    try:
        config = load_config()
        if not config:
            return False, "Нет конфига"
        
        github_user = config["github_user"]
        github_repo = config["github_repo"]
        full_path = github_item["path"]  # Полный путь из GitHub API
        
        # Используем НАДЁЖНУЮ ссылку вместо download_url
        file_url = get_raw_download_url(github_user, github_repo, full_path)
        file_name = github_item["name"]
        
        # Формируем путь сохранения
        if relative_path:
            local_path = Path(save_dir) / relative_path / file_name
            local_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            local_path = Path(save_dir) / file_name
        
        if log_func:
            log_func(f"Скачиваю: {full_path} -> {local_path} (URL: {file_url})")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        with requests.get(file_url, headers=headers, stream=True, timeout=15) as r:
            r.raise_for_status()
            
            # Проверяем, что это не HTML (ошибка 404)
            if 'text/html' in r.headers.get('content-type', ''):
                if log_func:
                    log_func(f"Ошибка: файл не найден (HTML вместо содержимого)")
                return False, "Файл не найден"
            
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        
        file_size = local_path.stat().st_size
        if log_func:
            log_func(f"✓ Файл сохранён: {file_name} ({file_size} байт)")
        return True, file_name
        
    except Exception as e:
        error_msg = f"Ошибка скачивания: {str(e)}"
        if log_func:
            log_func(f"✗ {error_msg}")
        return False, error_msg


def download_single_folder(github_user, github_repo, github_folder, path, save_dir, log_func=None):
    """Рекурсивно скачивает папку"""
    config = load_config()
    if not config:
        return False
    
    base_url = f"https://api.github.com/repos/{github_user}/{github_repo}/contents/{github_folder}"
    full_url = f"{base_url}/{path}" if path else base_url
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(full_url, headers=headers, timeout=10)
        response.raise_for_status()
        items = response.json() if isinstance(response.json(), list) else [response.json()]
    except Exception as e:
        if log_func:
            log_func(f"Ошибка запроса папки '{path}': {e}")
        return False

    success_count = 0
    for item in items:
        if item["type"] == "file":
            ok, msg = download_single_file(item, save_dir, path, log_func)
            if ok:
                success_count += 1
        elif item["type"] == "dir":
            # Рекурсивно для подпапок
            sub_path = item["path"].replace(f"{github_folder}/", "")
            download_single_folder(github_user, github_repo, github_folder, 
                                 sub_path, save_dir, log_func)
    
    if log_func:
        log_func(f"Из папки '{path or github_folder}' скачано файлов: {success_count}")
    return True


# ========== Остальной код без изменений (DownloadThread, TreeThread, etc.) ==========
class DownloadThread(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def run(self):
        download_files_recursive(log_func=self.log.emit)
        self.finished.emit()


def download_files_recursive(path="", log_func=None):
    config = load_config()
    if not config:
        if log_func:
            log_func("Конфиг не найден или не настроен.")
        return

    github_user = config["github_user"]
    github_repo = config["github_repo"]
    github_branch = config["github_branch"]
    github_folder = config["github_folder"]
    SAVE_DIR = config["save_dir"]

    BASE_URL = f"https://api.github.com/repos/{github_user}/{github_repo}/contents"
    url = f"{BASE_URL}/{github_folder}/{path}" if path else f"{BASE_URL}/{github_folder}"

    headers = {'User-Agent': 'Mozilla/5.0'}
    os.makedirs(SAVE_DIR, exist_ok=True)

    if log_func:
        log_func(f"GET {url}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        items = response.json() if isinstance(response.json(), list) else [response.json()]
    except Exception as e:
        if log_func:
            log_func(f"Ошибка при запросе к GitHub: {e}")
        return

    for item in items:
        if item["type"] == "file":
            ok, msg = download_single_file(item, SAVE_DIR, path, log_func)
        elif item["type"] == "dir":
            sub_path = item["path"]
            if sub_path.startswith(f"{github_folder}/"):
                save_path = sub_path[len(github_folder) + 1:]
            else:
                save_path = sub_path
            download_files_recursive(save_path, log_func)


# ========== TreeThread и MainWindow остаются ТАКИМИ ЖЕ как в предыдущей версии ==========
class TreeThread(QThread):
    tree = pyqtSignal(object)

    def run(self):
        config = load_config()
        if not config:
            self.tree.emit("Конфиг не настроен")
            return

        github_user = config["github_user"]
        github_repo = config["github_repo"]
        github_folder = config["github_folder"]

        BASE_URL = f"https://api.github.com/repos/{github_user}/{github_repo}/contents/{github_folder}"
        tree = get_github_tree_recursive(BASE_URL)
        self.tree.emit(tree)

# ========== Основное окно =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("View Repository")
        self.setGeometry(300, 100, 700, 500)

        # Устанавливаем стиль Fusion ПЕРЕД созданием виджетов
        QApplication.setStyle('Fusion')

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout()

        top = QHBoxLayout()
        self.status_label = QLabel("Статус: ...")
        top.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.btn_inspect = QPushButton("Проверить подключение")
        self.btn_inspect.clicked.connect(self.do_inspect)

        self.btn_download = QPushButton("Скачать все файлы")
        self.btn_download.clicked.connect(self.start_download)

        btn_layout.addWidget(self.btn_inspect)
        btn_layout.addWidget(self.btn_download)
        top.addLayout(btn_layout)
        layout.addLayout(top)

        # Дерево файлов
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Дерево файлов"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.context_menu_tree)
        layout.addWidget(self.tree)

        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)

        self.central_widget.setLayout(layout)

        # ТЕМНАЯ ТЕМА - после создания виджетов
        self.apply_dark_theme()
        
        self.init_startup()

    def apply_dark_theme(self):
        """Черно-белая тема"""
        # Черно-белая палитра
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(20, 20, 20))      # Темно-серый фон
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255)) # Белый текст
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))         # Темнее для полей
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))      # Белый текст
        palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))       # Серые кнопки
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255)) # Белый текст кнопок
        palette.setColor(QPalette.ColorRole.Highlight, QColor(100, 100, 100)) # Серый выделение
        QApplication.setPalette(palette)

        # Черно-белый QSS
        self.setStyleSheet("""
            QMainWindow {
                background-color: #141414;
                color: #ffffff;
            }
            QTreeWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333333;
                font-family: 'Consolas', monospace;
                font-size: 11pt;
                selection-background-color: #666666;
                alternate-background-color: #222222;
            }
            QTreeWidget::item:hover {
                background-color: #333333;
            }
            QTreeWidget::item:selected {
                background-color: #666666;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333333;
                font-family: 'Consolas', monospace;
                font-size: 10pt;
                padding: 8px;
            }
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 4px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
            QLabel {
                color: #ffffff;
                font-size: 12pt;
                padding: 4px;
                background-color: transparent;
            }
            QLineEdit {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 6px;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border: 1px solid #666666;
            }
        """)

    # Все остальные методы остаются ТАКИМИ ЖЕ
    def log(self, text):
        self.log_text.append(text)
    
    def init_startup(self):
        self.log("View Repository GUI стартует...")

        save_dir = "./Downloads"

        if os.path.isfile(save_dir):
            self.log(f"Удаляю файл {save_dir}, чтобы сделать папкой.")
            os.remove(save_dir)
        elif os.path.isdir(save_dir):
            self.log(f"Папка {save_dir} уже существует.")
        else:
            self.log(f"Папка {save_dir} будет создана.")

        os.makedirs(save_dir, exist_ok=True)

        config = load_config()
        if config:
            self.log("Конфиг найден, загружаю дерево файлов...")
            self.do_inspect()
        else:
            self.log("Файл конфигурации не найден. Создаю новый конфиг.")
            self.create_config_first()

    def create_config_first(self):
        key, ok = QInputDialog.getText(
            self, "Админ‑ключ", "Придумайте админ‑ключ:", QLineEdit.EchoMode.Password
        )
        if not ok or not key.strip():
            self.log("Отмена создания конфига.")
            return

        config = {
            "version": VERSION,
            "github_user": "LarryFoxy",
            "github_repo": "DataConnector",
            "github_branch": "main",
            "github_folder": "Test_Data_Folder",
            "save_dir": "./Downloads",  # ← ИСПРАВЛЕНО
            "admin_key": hashlib.sha256(key.encode()).hexdigest()
        }
        save_config(config)
        self.log("Конфиг создан.")
        self.do_inspect()

    def do_inspect(self):
        config = load_config()
        if not config:
            self.log("Конфиг не настроен.")
            return

        status = inspect()
        self.status_label.setText(f"Статус: {status}")

        self.tree.clear()
        self.log("Запрашиваю дерево файлов...")
        self.tree_thread = TreeThread()
        self.tree_thread.tree.connect(self.on_tree_received)
        self.tree_thread.finished.connect(lambda: self.log("Загрузка дерева завершена."))
        self.tree_thread.start()

    def on_tree_received(self, tree_data):
        self.tree.clear()
        config = load_config()
        if not config:
            self.log("Конфиг не найден при отображении дерева.")
            return

        github_folder = config["github_folder"]
        if isinstance(tree_data, dict) and tree_data:
            root_item = QTreeWidgetItem(self.tree, [github_folder])
            build_tree_widget(root_item, tree_data)
            root_item.setExpanded(True)
        else:
            root_item = QTreeWidgetItem(self.tree, ["Ошибка"])
            if isinstance(tree_data, str):
                root_item.setText(0, f"Ошибка дерева: {tree_data}")
            else:
                root_item.setText(0, "Пустое или повреждённое дерево")

    def start_download(self):
        self.log("Запуск скачивания всех файлов...")
        self.download_thread = DownloadThread()
        self.download_thread.log.connect(self.log)
        self.download_thread.finished.connect(lambda: self.log("Скачивание завершено."))
        self.download_thread.start()

    def context_menu_tree(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        action_download = QAction("Скачать этот элемент", self)
        action_download.triggered.connect(lambda: self.download_tree_item(item))
        menu.addAction(action_download)
        menu.exec(self.tree.mapToGlobal(pos))

    def get_item_path(self, item):
        """Получает относительный путь элемента в дереве"""
        config = load_config()
        if not config:
            return None

        folder = config["github_folder"]
        names = []
        
        # Собираем имена от листа к корню
        current = item
        while current:
            text = current.text(0).strip()
            if text and text != folder:  # исключаем корневую папку
                names.append(text)
            current = current.parent()

        # Переворачиваем и убираем корневую папку если она есть
        names.reverse()
        if names and names[0] == folder:
            names = names[1:]
        
        return "/".join(names)

    def download_tree_item(self, tree_item):
        """Основная функция скачивания выбранного элемента"""
        config = load_config()
        if not config:
            self.log("Конфиг не настроен, скачивание отменено.")
            return

        github_user = config["github_user"]
        github_repo = config["github_repo"]
        github_folder = config["github_folder"]
        SAVE_DIR = config["save_dir"]

        item_name = tree_item.text(0).strip()
        path = self.get_item_path(tree_item)
        
        self.log(f"Скачивание элемента: '{item_name}' (путь: '{path}')")

        # Проверяем является ли это файлом или папкой по иконке
        item_style = tree_item.treeWidget().style()
        is_folder = tree_item.icon(0) == item_style.standardIcon(item_style.StandardPixmap.SP_DirIcon)
        
        if is_folder:
            self.log(f"Скачиваю папку: {path or github_folder}")
            download_single_folder(github_user, github_repo, github_folder, path, SAVE_DIR, self.log)
        else:
            self.log(f"Скачиваю файл: {path or item_name}")
            self._download_file_by_path(github_user, github_repo, github_folder, path or item_name, SAVE_DIR)

    def _download_file_by_path(self, github_user, github_repo, github_folder, path, save_dir):
        """Скачивает конкретный файл по пути"""
        base_url = f"https://api.github.com/repos/{github_user}/{github_repo}/contents/{github_folder}"
        full_url = f"{base_url}/{path}" if path else base_url
        
        try:
            response = requests.get(full_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict) and data["type"] == "file":
                # Это одиночный файл
                success, msg = download_single_file(data, save_dir, "")
                if success:
                    self.log(f"✓ Файл '{data['name']}' успешно скачан")
                else:
                    self.log(f"✗ Ошибка скачивания файла: {msg}")
            else:
                self.log("Элемент не является файлом")
                
        except Exception as e:
            self.log(f"Ошибка при получении информации о файле: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())