---
tags: [gemini, install, vds, nodejs]
date: 2026-04-18
type: note
---

# Шаг 1: Установка и настройка окружения

Вставляй команды в терминал по SSH или локально.

## Prerequisites

- Ubuntu 22.04+ или Debian 12+ (на VDS или локально)
- SSH-доступ с правами root или sudo
- Минимум 1 GB RAM
- Исходящий интернет на сервере

## 1. Обновить систему

```bash
apt update && apt upgrade -y
```

Не пропускай этот шаг: без актуальных пакетов установка Node.js из NodeSource может сломаться.

## 2. Установить Node.js 22

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
```

Проверить версии:

```bash
node -v   # ожидается v22.x.x
npm -v    # ожидается 10.x.x или выше
```

## 3. Установить Gemini CLI и PM2

```bash
npm install -g @google/gemini-cli pm2
```

Проверить:

```bash
gemini --version
pm2 -v
```

## 4. Авторизоваться в Gemini CLI

### Вариант А — Google-аккаунт (рекомендуется для начала)

```bash
gemini login
```

На VDS без GUI: команда покажет URL. Скопируй его и открой в браузере на своём ПК.

### Вариант Б — API Key (для headless/серверного режима)

```bash
export GOOGLE_API_KEY="ВАШ_КЛЮЧ_ИЗ_AI_STUDIO"
```

Ключ берётся на [aistudio.google.com](https://aistudio.google.com/).

## 5. Проверить работу Gemini CLI

```bash
gemini "Ответь одним словом: работает"
```

Если получил короткий ответ — установка прошла успешно.

## 6. Настроить автозапуск PM2

```bash
pm2 startup
# Скопируй и выполни команду, которую вернёт pm2 startup
```

Это нужно сделать один раз. После этого PM2 будет автоматически подниматься после перезагрузки сервера.

## Troubleshooting

**`gemini: command not found`**
Npm не добавил `/usr/local/bin` в PATH. Попробуй:
```bash
export PATH="$PATH:/usr/local/bin"
source ~/.bashrc
```
Или просто открой новый терминал.

**Node version не v22.x**
Удали старую версию и переустанови через NodeSource:
```bash
apt remove -y nodejs
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
```

**`gemini login` зависает или не открывает браузер**
На безголовом сервере команда выведет URL вида `https://accounts.google.com/...`. Скопируй его и открой на любом устройстве с браузером. После авторизации токен сохранится автоматически.

## После этого шага

- [ ] `node -v` возвращает v22.x.x
- [ ] `npm -v` возвращает 10.x.x+
- [ ] `gemini --version` выводит версию
- [ ] `pm2 -v` выводит версию
- [ ] `gemini "Ответь одним словом: работает"` возвращает ответ

Следующий шаг: [[02_AUTH_AND_LIMITS]]
