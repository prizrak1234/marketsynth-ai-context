---
name: visual-generation
description: >
  Готовит инструкции для генерации коммерческих изображений social_post_image
  внутри Content Director. Используй при VisualRequest, image variants,
  social post visuals. Не публикует и не редактирует пиксели вручную.
---

# Скилл: Visual Generation

## Как работать

1. Прочитай `resources/system_prompt.md` — правила промпта для изображения.
2. Генерация выполняется адаптером Visual Director (не скриптами пакета).
3. Результат — 1..N ImageCandidate; approval остаётся за пользователем.

## Не делать

- Не запускать произвольные скрипты
- Не публиковать изображения
- Не менять связанный TextAsset
- Не имитировать результат mock-картинкой в customer path
