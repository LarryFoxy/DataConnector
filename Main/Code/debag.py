import os
import json
import requests
import hashlib
from pathlib import Path

VERSION = "v0.3"
CONFIG_FILE = "config.json"

class github_data:
    def __init__(self, user, repo, branch, folder):
        self.user = user
        self.repo = repo
        self.branch = branch
        self.folder = folder

def generate_admin_key():
    import secrets
    return secrets.token_hex(16)

def load_config():
    if not os.path.isfile(CONFIG_FILE):
        print("Файл настроек не найден. Создаю новый конфиг...")
        admin_key = input("Придумайте админ‑ключ (пароль): ").strip()
        if not admin_key:
            print("Ключ пустой. Выход.")
            exit(1)

        config = {
            "version": VERSION,
            "github_user": "LarryFoxy",
            "github_repo": "DataConnector",
            "github_branch": "main",
            "github_folder": "Test_Data_Folder",
            "save_dir": "./Downloads",
            "admin_key": hashlib.sha256(admin_key.encode()).hexdigest()
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print("Конфиг создан.")

    else:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        if "admin_key" not in config:
            admin_key = input("Конфиг без admin_key.\nПридумайте админ‑ключ: ").strip()
            if not admin_key:
                print("Ключ пустой. Выход.")
                exit(1)
            config["admin_key"] = hashlib.sha256(admin_key.encode()).hexdigest()
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

    return config

def reset_config():
    config = load_config()
    admin_input = input("Введите админ‑ключ для сброса настроек: ").strip()
    hashed = hashlib.sha256(admin_input.encode()).hexdigest()

    os.system('attrib -r -h -s config.json')

    if hashed == config["admin_key"]:
        os.remove(CONFIG_FILE)
        print("Файл настроек удалён. При следующем запуске будет создан заново.")
    else:
        print("Неправильный админ‑ключ.")

def inspect():
    url = f"https://api.github.com/repos/{config['github_user']}/{config['github_repo']}/contents/{config['github_folder']}"
    headers = {}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("GitHub отвечает")
        return "Есть"
    elif response.status_code == 404:
        print("Папка/репозиторий не найден (404)")
        return "Не найдено"
    elif response.status_code == 403:
        print("Доступ запрещён (403)")
        return "Заблокировано"
    else:
        print(f"Неожиданный статус: {response.status_code}")
        print("Текст ответа:", response.text[:500])
        return "Неизвестно"

def download_files_recursive(path=""):
    github = github_data(
        config["github_user"],
        config["github_repo"],
        config["github_branch"],
        config["github_folder"]
    )

    BASE_URL = f"https://api.github.com/repos/{github.user}/{github.repo}/contents"
    url = f"{BASE_URL}/{github.folder}/{path}" if path else f"{BASE_URL}/{github.folder}"
    SAVE_DIR = config["save_dir"]

    headers = {}
    os.makedirs(SAVE_DIR, exist_ok=True)

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    items = response.json()

    for item in items:
        # Если это файл
        if item["type"] == "file":
            file_name = item["name"]
            file_url = item["download_url"]

            if path:
                local_path = Path(f"{SAVE_DIR}/{path}/{file_name}")
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
            else:
                local_path = Path(f"{SAVE_DIR}/{file_name}")

            print(f"Скачиваю: {item['path']} -> {local_path}")

            with requests.get(file_url, stream=True) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

        # Если это папка — рекурсивно заходим в неё
        elif item["type"] == "dir":
            sub_path = item["path"]

            # режем путь от корня Test_Data_Folder
            relative_sub = sub_path.replace(f"{github.folder}/", "", 1)

            download_files_recursive(relative_sub)


    print("Готово: все файлы скачаны.")

def edit_repository():
    config = load_config()
    admin_input = input("Введите админ‑ключ для редактирования репозитория: ").strip()
    hashed = hashlib.sha256(admin_input.encode()).hexdigest()

    if hashed != config["admin_key"]:
        print("Неправильный админ‑ключ.")
        return

    print("Текущие настройки репозитория:")
    print(f"  Пользователь: {config['github_user']}")
    print(f"  Репозиторий: {config['github_repo']}")
    print(f"  Ветка: {config['github_branch']}")
    print(f"  Папка: {config['github_folder']}")
    print(f"  Локальная папка: {config['save_dir']}")

    print("\nВводите новые значения (ENTER = оставить как есть):")

    user = input(f"Пользователь [{config['github_user']}]: ").strip()
    repo = input(f"Репозиторий [{config['github_repo']}]: ").strip()
    branch = input(f"Ветка [{config['github_branch']}]: ").strip()
    folder = input(f"Папка на GitHub [{config['github_folder']}]: ").strip()
    save_dir = input(f"Локальная папка [{config['save_dir']}]: ").strip()

    if user:   config["github_user"]    = user
    if repo:   config["github_repo"]    = repo
    if branch: config["github_branch"]  = branch
    if folder: config["github_folder"]  = folder
    if save_dir:
        config["save_dir"] = save_dir

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print("Настройки репозитория обновлены.")


def main_menu():
    os.system("cls" if os.name == "nt" else "clear")

    public = f"DATA-C {VERSION} --------------------------------------"
    public_connect = f"Подключение: {inspect()}; Репозиторий: {config['github_repo']}"

    structur = len(public) - len(public_connect)
    public_ = "" if structur % 2 == 0 else "-"
    public += public_

    if public_ == "":
        public_connect = " " * (structur // 2) + public_connect
    else:
        public_connect = " " * ((structur + 1) // 2) + public_connect

    print(f"{public}\n{public_connect}\n")

    print("1. Скачать файлы")
    print("2. Диагностика")
    print("3. Изменить репозиторий")
    print("4. Сброс настроек")
    print("\n[Введите цифру команды и нажмите Enter]")

    hdrl = input("//: ")
    match hdrl:
        case "1":
            download_files_recursive()
        case "2":
            inspect()
        case "3":
            edit_repository()
        case "4":
            reset_config()
        case _:
            print("No Command")

    input(">> Нажмите Enter ")

config = load_config()

os.system('attrib +r +h +s config.json')

while True:
    try:
        main_menu()
    except Exception as e:
        print(f"log: {e}")