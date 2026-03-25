# ViewRepository • Просмотр и загрузка данных GitHub

## Основные возможности:

- 📁 **Интерактивное дерево файлов** — просмотр всей структуры папок GitHub
- ⬇️ **Выборочная загрузка** — скачивайте отдельные файлы
- 🚀 **Без токенов** — работает с публичными репозиториями

## Для чего нужно

```
Скачивает данные с GitHub → сохраняет локально в ./Downloads
┌─────────────────────────────────────┐
│  📁 Repository                  ㅤㅤ│
│  ├─ 📄 Data.csv           ㅤ     ㅤ │ ← ПКМ → Скачать файл
│  ├─ 📁 Folder               ㅤ   ㅤ │
│  │  └─ 📄 File.py           ㅤ ㅤ   │ ← ПКМ → Скачать файл
│  └─ ...           ㅤㅤㅤㅤㅤ         │
└─────────────────────────────────────┘
```

## Быстрый старт

```bash
# 1. Установите зависимости
pip install PyQt6

# 2. Запустите
python ViewRepository.py
# Или консольный расширенный вариант
python debag.py

# 3. Введите админ-ключ (любой пароль)
# 4. Выберите файлы → "Скачать этот элемент" или скачайте все!
```

## 📋 Настройка для класса

1. **Создайте публичный репозиторий** `LarryFoxy/DataConnector`
2. **Добавьте папку** `Test_Data_Folder` с учебными данными
3. **Скопируйте** `data_c.py` всем ученикам
4. **Запустите** — автоматическая настройка под ваш репозиторий

**config.json создается автоматически и защищается:**
```json
{
    "github_user": "LarryFoxy",
    "github_repo": "DataConnector", 
    "github_folder": "Test_Data_Folder",
    "save_dir": "./Downloads",
    "admin_key": "sha256_хэш"
}
```

## 🖥️ Скриншот

```
[Дерево файлов GitHub]  [Статус: Есть]  [Проверить] [Скачать все]
📁 Test_Data_Folder           
├─ 📄 data1.csv              
├─ 📁 Data_TEST              
│  └─ 📄 test2.py           
└─ ...                       
[Лог: DATA-C GUI стартует... ✓ Файл сохранён...]
```

## 🔧 Технические детали

- **PyQt6** — современный GUI framework
- **GitHub Contents API** — tree/listing + raw.githubusercontent.com для скачивания
- **Черно-белая тема** — Fusion style + QSS
- **Асинхронная загрузка** — QThread, не блокирует интерфейс
- **Защита config** — `attrib +r +h +s` на Windows

## 📁 Структура проекта

```
DataConnector/
├── Test_Data_Folder/     # Данные для класса
│   ├── data1.csv
│   └── Data_TEST/
│       └── test2.py
├── data_c.py            # ← Эта программа
├── config.json          # Автосоздается
└── Downloads/           # Результат скачивания
```

## 👥 Для школьного класса (30+ учеников)

1. **Один репозиторий** — все работают с одними данными
2. **Без GitHub токенов** — публичный доступ
3. **Локальная работа** — каждый качает в `./Downloads`
4. **Простая раздача** — `data_c.py + pip install`

## 📞 Поддержка

- **Проблемы с 403?** → Репозиторий должен быть публичным
- **Не видит папку?** → Проверьте `Test_Data_Folder` в корне repo
- **Две папки?** → `del config.json` + перезапуск

## 🙌 Благодарности

Создано для **школьных уроков информатики** • LarryFoxy • 2026

<div align="center">
  
[![Star](https://img.shields.io/github/stars/LarryFoxy/DataConnector?style=social)](https://github.com/LarryFoxy/DataConnector)
[![Fork](https://img.shields.io/github/forks/LarryFoxy/DataConnector?style=social)](https://github.com/LarryFoxy/DataConnector)

</div>
```

**Скопируйте в `README.md`** — готово для GitHub! 🚀
