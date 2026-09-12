"""Разбор строкового таймфрейма в длительность одной свечи."""

from __future__ import annotations

import re
from decimal import Decimal

# Крипторынок торгуется без выходных, поэтому год считается как 365 суток.
MINUTES_IN_YEAR = Decimal(365 * 24 * 60)
MS_IN_MINUTE = 60_000
_UNIT_MINUTES = {"m": 1, "h": 60, "d": 60 * 24, "w": 60 * 24 * 7}
# Регистр значим: в CCXT "1M" — это месяц, а "1m" — минута. Приведение к
# нижнему регистру превратило бы месячную свечу в минутную, поэтому месяц и
# любые другие неподдерживаемые единицы отвергаются явной ошибкой.
_PATTERN = re.compile(r"^(\d+)([mhdw])$")


def timeframe_minutes(timeframe: str) -> int:
    """Длительность одной свечи в минутах: "1h" → 60, "15m" → 15."""

    match = _PATTERN.match(timeframe.strip())
    if match is None:
        raise ValueError(
            f"Таймфрейм {timeframe!r} не поддерживается: ожидается число и "
            "единица m/h/d/w в нижнем регистре"
        )
    amount, unit = int(match.group(1)), match.group(2)
    if amount <= 0:
        raise ValueError(f"Таймфрейм {timeframe!r} должен быть положительным")
    return amount * _UNIT_MINUTES[unit]


def timeframe_ms(timeframe: str) -> int:
    """Длительность одной свечи в миллисекундах."""

    return timeframe_minutes(timeframe) * MS_IN_MINUTE


def periods_per_year(timeframe: str) -> Decimal:
    """Сколько свечей данного таймфрейма укладывается в год.

    Множитель годового пересчёта Sharpe зависит от длины бара: для "1h" это
    365×24 = 8760 периодов, для "1d" — 365. Хардкод 252 (торговые дни акций)
    завышал бы Sharpe на часовых данных примерно в шесть раз.
    """

    return MINUTES_IN_YEAR / Decimal(timeframe_minutes(timeframe))


def is_closed(candle_ts: int, timeframe: str, now_ms: int) -> bool:
    """Закрыта ли свеча, открытая в `candle_ts`, к моменту `now_ms`.

    Биржа отдаёт последним текущий незакрытый бар: его high/low/close ещё
    меняются, поэтому сигнал по нему перерисовывался бы.
    """

    return candle_ts + timeframe_ms(timeframe) <= now_ms
