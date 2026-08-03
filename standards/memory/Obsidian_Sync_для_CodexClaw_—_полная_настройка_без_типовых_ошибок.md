---
date: 2026-03-28
type: guide
tags: [guide, obsidian, obsidian-sync, codexclaw, claudeclaw, agents, setup]
---

# Obsidian Sync для CodexClaw — полная настройка без типовых ошибок

> Это рабочая инструкция по итогам реальной настройки на сервере `YLCODECCLAW`. Читать перед подключением Obsidian к новому агенту.

---

## Главный принцип

Агенту нужен не GUI Obsidian, а локальная папка vault.

Цель настройки:
- получить рабочий sync в `~/obsidian-vault`
- дать агенту доступ к markdown-файлам
- не ломать сервер системными апгрейдами ради одной утилиты

---

## Что сработало по факту

На этом сервере рабочая схема такая:

1. Установить `obsidian-headless`
2. Использовать отдельный локальный `Node 22`
3. Авторизоваться через `ob login`
4. Настроить sync на `/root/obsidian-vault`
5. Запустить постоянный sync через `systemd`

Именно это заработало стабильно.

---

## Что НЕ сработало

### 1. Копирование чужого `auth_token`

Попытка использовать токен с другого сервера привела к ошибке:

`Failed to authenticate: Not logged in`

Вывод:
- один аккаунт Obsidian поддерживает несколько устройств
- но каждому серверу лучше получать свой собственный токен через `ob login`

### 2. Обычный `scp` со старого сервера

Команды были правильные, но доступ упёрся в:

`Permission denied (publickey)`

Вывод:
- если между серверами нет рабочего SSH-доступа, не тратить на это время
- быстрее сделать новый `ob login`

### 3. Системный `Node 20`

`obsidian-headless` на этом сервере не работал нормально с системным `Node v20.20.1`.

Были реальные ошибки:
- `ReferenceError: WebSocket is not defined`
- `ReferenceError: navigator is not defined`
- несовместимость `better-sqlite3` по `NODE_MODULE_VERSION`

Вывод:
- для этого стека нужен отдельный `Node 22`
- не обязательно менять системный `Node`, лучше поставить локальный

### 4. Запуск systemd до завершения ручного sync

Если сначала руками запущен sync, а потом включается `systemd`, сервис падает с ошибкой:

`Another sync instance is already running for this vault.`

Вывод:
- перед запуском systemd нужно убить ручной sync-процесс

---

## Финальная рабочая схема

### Шаг 1. Создать папку vault

```bash
mkdir -p /root/obsidian-vault
mkdir -p /root/.config/obsidian-headless/sync
```

### Шаг 2. Установить локальный Node 22

Не трогаем системный `Node`.

```bash
mkdir -p /root/.local/node22
curl -fsSL https://nodejs.org/dist/latest-v22.x/node-v22.22.2-linux-x64.tar.xz -o /tmp/node-v22.22.2-linux-x64.tar.xz
tar -xJf /tmp/node-v22.22.2-linux-x64.tar.xz -C /root/.local/node22 --strip-components=1
```

Проверка:

```bash
/root/.local/node22/bin/node -v
```

Ожидаемо:

```bash
v22.22.2
```

### Шаг 3. Установить `obsidian-headless` под Node 22

```bash
mkdir -p /root/.local/obsidian-headless22
PATH=/root/.local/node22/bin:$PATH npm install --prefix /root/.local/obsidian-headless22 obsidian-headless
PATH=/root/.local/node22/bin:$PATH npm rebuild --prefix /root/.local/obsidian-headless22 better-sqlite3
```

Проверка:

```bash
PATH=/root/.local/node22/bin:$PATH /root/.local/node22/bin/node /root/.local/obsidian-headless22/node_modules/obsidian-headless/cli.js --help
```

### Шаг 4. Авторизоваться заново

Если есть старый невалидный токен, удалить:

```bash
rm -f /root/.config/obsidian-headless/auth_token
```

Логин:

```bash
PATH=/root/.local/node22/bin:$PATH /root/.local/node22/bin/node /root/.local/obsidian-headless22/node_modules/obsidian-headless/cli.js login
```

Или неинтерактивно:

```bash
PATH=/root/.local/node22/bin:$PATH /root/.local/node22/bin/node /root/.local/obsidian-headless22/node_modules/obsidian-headless/cli.js login --email "EMAIL" --password "PASSWORD"
```

Успешный результат:

```bash
Logged in as Igor ()
```

### Шаг 5. Подключить vault

Если `config.json` уже есть, проверить:

```bash
PATH=/root/.local/node22/bin:$PATH /root/.local/node22/bin/node /root/.local/obsidian-headless22/node_modules/obsidian-headless/cli.js sync-list-local
```

Если vault ещё не подключён:

```bash
PATH=/root/.local/node22/bin:$PATH /root/.local/node22/bin/node /root/.local/obsidian-headless22/node_modules/obsidian-headless/cli.js sync-list-remote
PATH=/root/.local/node22/bin:$PATH /root/.local/node22/bin/node /root/.local/obsidian-headless22/node_modules/obsidian-headless/cli.js sync-setup --path /root/obsidian-vault --remote <VAULT_ID>
```

### Шаг 6. Первый запуск руками

Первый sync лучше один раз запустить руками и убедиться, что реально качаются файлы:

```bash
PATH=/root/.local/node22/bin:$PATH /root/.local/node22/bin/node /root/.local/obsidian-headless22/node_modules/obsidian-headless/cli.js sync --path /root/obsidian-vault
```

Ожидаемые строки:

```bash
Connecting...
Connection successful. Detecting changes...
Downloading ...
Downloaded ...
Accepted ...
```

### Шаг 7. Запустить через systemd

Файл:

`/etc/systemd/system/obsidian-headless.service`

Содержимое:

```ini
[Unit]
Description=Obsidian Headless Sync
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
Environment=PATH=/root/.local/node22/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/root/.local/node22/bin/node /root/.local/obsidian-headless22/node_modules/obsidian-headless/cli.js sync --path /root/obsidian-vault --continuous
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
systemctl daemon-reload
systemctl enable --now obsidian-headless
```

Проверка:

```bash
systemctl status obsidian-headless --no-pager
journalctl -u obsidian-headless -n 50 --no-pager
```

---

## Обязательная проверка перед systemd

Если до этого запускался ручной sync, проверить что его больше нет:

```bash
ps -ef | grep obsidian-headless
```

Если есть ручной процесс sync, убить его:

```bash
kill <PID>
```

И только потом запускать `systemd`.

Иначе сервис уйдёт в рестарт с ошибкой:

`Another sync instance is already running for this vault.`

---

## Где теперь лежит vault

Рабочий путь для агента:

`/root/obsidian-vault`

Там агент ищет:
- заметки
- архив контента
- session notes
- research
- guides
- папку `СВАЛКА`

---

## Стандарт для новых агентов

Если подключается новый агент:

1. Не ставить GUI Obsidian на headless-сервер без крайней нужды
2. Не тратить время на перенос чужого токена, если он не взлетел сразу
3. Сразу использовать локальный `Node 22`
4. Делать собственный `ob login`
5. Первый sync запускать руками
6. Только потом включать `systemd`

---

## Быстрый чек-лист

- Есть `/root/obsidian-vault`
- Есть `/root/.local/node22/bin/node`
- Есть `/root/.local/obsidian-headless22/node_modules/obsidian-headless/cli.js`
- `ob login` успешен
- `sync-list-local` показывает vault
- ручной `sync` реально качает файлы
- `systemd` работает без рестарт-лупа

---

## Связанные заметки

- [[Obsidian Vault — архитектура и возможности (2026-03)]]
- [[Obsidian агент — принцип работы и экономия токенов]]
- [[Работа с памятью и сессиями — гайд]]
