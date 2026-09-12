# CLAUDE.md — правила проекта `crypto-research-agent`

Этот файл читается Claude Code при каждом запуске. Соблюдать безусловно.

---

## 1. Что это за проект

Research- и сигнальный агент по криптовалютному рынку.
Область: **этапы 1–2** (research + бумажные сигналы). Реальная торговля вне области.

Владелец проекта не пишет код вручную. Поэтому:
- каждый модуль должен быть коротким и читаемым;
- каждая функция, влияющая на деньги или размер позиции, снабжается комментарием на русском языке с объяснением формулы;
- не использовать «умные» однострочники, метапрограммирование, динамический импорт.

---

## 2. Запреты (нарушение = переписать)

1. **НИКОГДА не писать код, отправляющий ордера на биржу.** Ни `create_order`, ни `place_order`, ни их обёрток — даже закомментированных, даже «на будущее». Только публичные read-only эндпоинты.
2. **НИКОГДА не ставить LLM в контур принятия торгового решения.** Claude API используется только для текстового research-слоя (новости, регуляторка, дайджесты). Сигнал формирует детерминированный код стратегии.
3. **НИКОГДА не хранить ключи в коде, конфигах в git, логах или сообщениях Telegram.** Только `.env`, только через `src/core/config.py`.
4. **НИКОГДА не использовать `float` для цен, объёмов, комиссий и PnL.** Только `decimal.Decimal`.
5. **НИКОГДА не подгонять бэктест.** Если стратегия убыточна — сообщить об этом, а не менять параметры до красивого результата.
6. Не добавлять зависимости сверх списка в §5 без явного разрешения.

---

## 3. Технические инварианты

- Python 3.11+. Все публичные функции с type hints.
- Время — **всегда UTC**, в БД хранится как timestamp в миллисекундах (int).
- Комиссии и проскальзывание учитываются **всегда**: taker 0.055%, проскальзывание 0.05% от цены в худшую сторону. Значения берутся из `config.yaml`, не хардкодятся.
- Любой сетевой вызов — с таймаутом, ретраями (экспоненциальный backoff, максимум 3) и обработкой rate limit.
- Логирование структурное (`structlog`), уровень из конфига. Секреты маскируются.
- Бэктест и paper-режим используют **один и тот же** код стратегии. Никакого дублирования логики.

---

## 4. Структура проекта

```
crypto-research-agent/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── .env.example
├── config.yaml
├── data/agent.db                 # SQLite, в .gitignore
├── src/
│   ├── core/
│   │   ├── config.py             # загрузка .env + config.yaml
│   │   ├── db.py                 # схема, миграции, подключение
│   │   ├── timeframe.py          # длительность свечи, признак закрытой свечи
│   │   └── log.py
│   ├── data/
│   │   ├── market.py             # ccxt: OHLCV, тикеры, стакан (read-only)
│   │   └── news.py               # RSS + фильтрация
│   ├── research/
│   │   ├── agent.py              # вызовы Claude API
│   │   └── prompts/digest.md
│   ├── strategy/
│   │   ├── base.py               # BaseStrategy
│   │   └── ema_cross.py          # референсная стратегия
│   ├── backtest/
│   │   ├── engine.py
│   │   └── metrics.py
│   ├── paper/
│   │   └── broker.py             # симулятор исполнения
│   ├── risk/
│   │   └── limits.py
│   └── bot/
│       └── telegram.py           # только отправка + /status, /report, /stop
├── tests/
└── scripts/
    ├── backfill.py               # загрузка исторических свечей
    ├── run_backtest.py
    ├── run_paper.py
    └── run_digest.py             # новости + дайджест research-слоя
```

---

## 5. Разрешённые зависимости

`ccxt`, `pandas`, `numpy`, `aiogram`, `anthropic`, `pydantic`, `pydantic-settings`, `pyyaml`, `structlog`, `feedparser`, `httpx`, `pytest`, `pytest-asyncio`, `ruff`.

Биржа по умолчанию — **Bybit** (через ccxt). Смена биржи должна быть вопросом одной строки в `config.yaml`.

---

## 6. Схема БД

```sql
candles(symbol TEXT, timeframe TEXT, ts INTEGER, open TEXT, high TEXT,
        low TEXT, close TEXT, volume TEXT, PRIMARY KEY(symbol, timeframe, ts));

signals(id INTEGER PK, ts INTEGER, symbol TEXT, strategy TEXT, side TEXT,
        price TEXT, reason TEXT, status TEXT);          -- new|opened|skipped

paper_trades(id INTEGER PK, signal_id INTEGER, symbol TEXT, side TEXT,
        qty TEXT, entry_price TEXT, entry_ts INTEGER, exit_price TEXT,
        exit_ts INTEGER, fee TEXT, pnl TEXT, pnl_pct TEXT, exit_reason TEXT);

equity(ts INTEGER PK, balance TEXT, open_value TEXT);

news_items(id INTEGER PK, ts INTEGER, source TEXT, url TEXT UNIQUE,
        title TEXT, summary TEXT, relevance INTEGER);

digests(date TEXT PK, content TEXT, sent_ts INTEGER);
```

Денежные величины хранятся как TEXT (строковое представление Decimal).

---

## 7. Риск-модуль (`src/risk/limits.py`)

Применяется и в бэктесте, и в paper-режиме, до открытия любой позиции:

- `max_position_pct` — максимальная доля депозита в одной позиции (по умолчанию 2%);
- `max_open_positions` — максимум одновременных позиций (по умолчанию 3);
- `daily_loss_limit_pct` — при достижении дневного убытка агент прекращает открывать позиции до следующего дня UTC и шлёт уведомление;
- `stop_loss_pct` / `take_profit_pct` — обязательны для каждой позиции, позиция без стопа не открывается;
- плечо отсутствует, только спот.

`tests/test_limits.py` и `tests/test_broker.py` обязательны. Каждый лимит покрыт тестом.

---

## 8. Метрики (`src/backtest/metrics.py`)

Total return, max drawdown, Sharpe, win rate, profit factor, expectancy, average trade, число сделок, суммарные комиссии.
Отчёт всегда показывает результат **до и после** комиссий — разница должна быть видна явно.

---

## 9. Порядок работы

Перед изменениями — короткий план. После изменений — `ruff check` и `pytest`.
Объяснения и комментарии на русском, идентификаторы и коммиты на английском.

Если задача требует нарушить §2 — остановиться и сообщить, а не искать обход.
