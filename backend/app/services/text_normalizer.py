"""Нормализация текста и ЕДИНАЯ функция разбиения на предложения.

Ключевое архитектурное правило проекта: разбиение на предложения выполняется
ТОЛЬКО здесь и обслуживает и `/api/split`, и `/api/tts`. Frontend никогда не
разбивает текст сам — использует только результат `/api/split`. Иначе границы
предложений на фронте и бэке разойдутся, и подсветка/выбор диапазона сломаются.

Смещения char_start/char_end считаются относительно ИСХОДНОГО текста (как его
прислал frontend), а не нормализованного, — чтобы подсветка попадала в тот же
текст, что отображается в textarea.
"""

import re

# Символы-терминаторы предложения.
_TERMINATORS = ".!?…"

# Казахская кириллица (спец. буквы) — для эвристической проверки языка.
_KAZAKH_SPECIFIC = set("әғқңөұүһі")
# Кириллица целиком — блок Unicode U+0400–U+04FF (включает и русские, и
# казах-специфичные буквы ә ғ қ ң ө ұ ү һ і).
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def normalize_text(text: str) -> str:
    """Trim + схлопывание любых пробельных последовательностей в один пробел.

    Используется для нормализации текста перед синтезом и для формирования
    ключа кэша (чтобы «текст  с   пробелами» и «текст с пробелами» совпадали).
    """
    return " ".join(text.split()).strip()


def split_sentences(text: str) -> list[dict]:
    """Разбить текст на предложения с сохранением смещений в исходном тексте.

    Возвращает список словарей: {index, text, char_start, char_end}, где
    text == исходный срез text[char_start:char_end] (обрезанный от пробелов по
    краям), char_end — не включительно.
    """
    result: list[dict] = []
    n = len(text)
    start = 0
    i = 0
    while i < n:
        if text[i] in _TERMINATORS:
            # Захватываем подряд идущие терминаторы (?!, ..., !!).
            j = i + 1
            while j < n and text[j] in _TERMINATORS:
                j += 1
            _append_sentence(result, text, start, j)
            start = j
            i = j
        else:
            i += 1
    # Хвост без завершающего знака препинания.
    if start < n:
        _append_sentence(result, text, start, n)
    return result


def _append_sentence(result: list[dict], text: str, raw_start: int, raw_end: int) -> None:
    """Добавить предложение, обрезав пробелы по краям сырого диапазона."""
    s, e = raw_start, raw_end
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    if e <= s:
        # Пустой диапазон (только пробелы/знаки без содержимого) — пропускаем.
        return
    result.append(
        {
            "index": len(result),
            "text": text[s:e],
            "char_start": s,
            "char_end": e,
        }
    )


def looks_like_kazakh(text: str) -> bool:
    """Грубая эвристика: похож ли текст на казахскую кириллицу.

    True, если в тексте есть кириллица и присутствует хотя бы одна
    казах-специфичная буква ИЛИ кириллица составляет заметную долю букв.
    """
    letters = [c for c in text.lower() if c.isalpha()]
    if not letters:
        return False
    cyrillic = [c for c in letters if _CYRILLIC.match(c)]
    if not cyrillic:
        return False
    has_kazakh = any(c in _KAZAKH_SPECIFIC for c in letters)
    cyrillic_ratio = len(cyrillic) / len(letters)
    return has_kazakh or cyrillic_ratio >= 0.8


def kazakh_warning(text: str) -> str | None:
    """Вернуть текст предупреждения, если ввод не похож на казахскую кириллицу."""
    if not looks_like_kazakh(text):
        return (
            "Текст не похож на казахскую кириллицу — модель KazakhTTS2 "
            "работает только с казахским текстом на кириллице."
        )
    return None
