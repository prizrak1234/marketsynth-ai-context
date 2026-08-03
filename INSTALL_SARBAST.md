# Установка в `C:\Users\Сарбаст\Мой проект\botfazer`

Cursor-агент на этом ПК работает под учёткой **User** и не может писать в профиль **Сарбаст** напрямую.

## Вариант A — вы уже открыли `Мой проект` в Cursor под Сарбаст

Скопируйте папку вручную один раз:

```powershell
robocopy "C:\Users\User\.cursor\projects\c-Users\botfazer" "C:\Users\Сарбаст\Мой проект\botfazer" /E /XD .venv .pytest_cache .mypy_cache .ruff_cache __pycache__
```

Затем:

```powershell
cd "C:\Users\Сарбаст\Мой проект\botfazer"
uv sync --extra dev
copy .env.example .env
uv run uvicorn app.main:app --reload
```

## Вариант B — скрипт из репозитория

```powershell
cd "C:\Users\Сарбаст\Мой проект\botfazer"
powershell -ExecutionPolicy Bypass -File scripts\copy_to_moy_proekt.ps1
```

(если файлы уже лежат в `Мой проект`, этот шаг не нужен)
