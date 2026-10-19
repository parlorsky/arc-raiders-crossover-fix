# YouTube guide — recording notes

Короткая инструкция для записи видео по этому репозиторию.

## 1. Подготовка

- Запиши две версии запуска: **до фикса** (ярлык `Launch BEFORE demo.command`, baseline-режим) и **после** (обычный `Launch ARC Raiders.command`).
- Держи на экране плашку с версиями: macOS, CrossOver, сборка игры, версия DAC. Не показывай серийники, e-mail и путь к аккаунту.
- Пиши в 1080p или 1440p, 60 fps. OBS: `Display Capture` + отдельная дорожка под голос.
- Заранее закрой лишние окна, уведомления и Discord.
- Первый запуск долгий — вырежи ожидание или ускорь в 4–8 раз.

## 2. Сцены

| Время | Что на экране | Что говоришь |
|---|---|---|
| 0:00 | Крупно логотип ARC Raiders / рабочий стол | Вступление: «получилось запустить на Mac» |
| 0:15 | Плашка с версиями | Какое железо и версии |
| 0:30 | Ярлык `Launch BEFORE demo.command` | «Сначала — как ведёт себя без фикса» |
| 0:50 | Ошибка/меню без фикса | Покажи проблему, не объясняй механику |
| 1:05 | `Install.command` в Terminal | «Локальный установщик, пароль админа не нужен» |
| 1:30 | Прогресс установки, затем Finder с ярлыком | «Создаётся приватная копия» |
| 1:45 | `Launch ARC Raiders.command` | «Запускаем пропатченную версию» |
| 2:05 | Warning про GPU → OK | «Просто нажимаем OK» |
| 2:20 | Главное меню | «Меню открылось, ошибки нет» |
| 2:35 | Дисклеймер + ссылка | Короткое предупреждение |
| 2:50 | Конец | Ссылка на репозиторий в описании |

## 3. Финальный текст озвучки (EN)

> I’ve managed to get ARC Raiders running on a Mac. In this video I’ll show the initial environment, the installation of the fix, and the final result.
>
> For this test, I’m using a Mac with an M5 Pro chip and 24 GB of memory. The exact versions of macOS, CrossOver, and the game are shown on screen.
>
> First, I’ll launch a separate demo instance using the standard, unmodified CrossOver libraries. This shows how the game behaves before any fixes are applied.
>
> Next, I’ll run a local installer. It creates a dedicated private environment, verifies the library checksums, and applies the compatibility tweaks. No administrator password is required.
>
> Now I’ll launch the patched version. If a warning about minimum graphics card requirements appears, just click OK. Once it loads, the ARC Raiders main menu will open.
>
> A quick note before we continue: this is an unofficial community experiment. Use it at your own risk. It is not endorsed by Embark, Steam, or CodeWeavers, and modifying game or anti-cheat components may conflict with the game’s terms of service. No bans were observed in testing, but no guarantees are given.
>
> You can find the source files and the local installer via the link in the description. To replicate this, you will need your own licensed copies of CrossOver and ARC Raiders on Steam. And maybe you can even adapt this approach for Whisky or Wine.

## 4. Описание под видео

```
ARC Raiders on Apple silicon — CrossOver 26.3 compatibility fix (ARAV1011 solved on the tested setup).

⚠️ Unofficial community experiment. Use at your own risk. Not endorsed by Embark, Steam or CodeWeavers. Modifying game/anti-cheat components may conflict with the game's terms of service. No bans were observed in testing; no guarantees.

You need your own licensed copies of CrossOver and ARC Raiders on Steam.
Source + installer: https://github.com/parlorsky/arc-raiders-crossover-fix

Chapters:
00:00 Intro
00:15 Test setup
00:30 Before the fix
01:05 Installing
01:45 Launching the patched version
02:20 Result
02:35 Disclaimer
```

## 5. Титры и предупреждение

- На экране с установкой добавь мелким шрифтом: `Use at your own risk. Unofficial fix.`
- Не показывай содержимое античит-файлов и не объясняй, что именно меняется — просто «local compatibility tweak».
- Не обещай «100% без бана» и не называй фикс «обходом античита». Формулировка: «compatibility experiment / local tweak».
- В закреплённом комментарии продублируй дисклеймер и ссылку.
