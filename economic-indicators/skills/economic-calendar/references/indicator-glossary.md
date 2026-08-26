# Indicator Glossary (RU ↔ EN)

Calendar exports in Russian use names that do not translate one-to-one. This
maps the common ones and notes what each release is actually read for.

## Activity

| Russian | English | Read for |
|---------|---------|----------|
| Индекс деловой активности в производственном секторе PMI | Manufacturing PMI | 50 = expansion/contraction line; new orders sub-index leads |
| Индекс деловой активности в сфере услуг PMI | Services PMI | Dominant for developed economies; services prices sub-index is the inflation tell |
| Сводный индекс деловой активности PMI | Composite PMI | Weighted whole-economy read |
| Предварительные / Итоговые данные | Flash / Final | Flash moves markets; final rarely does unless it revises hard |
| Темпы роста ВВП (кв/кв) / (г/г) | GDP growth QoQ / YoY | Level and composition both matter |
| Промышленное производство | Industrial production | Volatile; watch the 3-month trend |
| Розничные продажи | Retail sales | Control group excludes autos/gas and is the cleaner consumption signal |
| Заказы на товары длительного пользования | Durable goods orders | Ex-transport, ex-defense core capex is the useful cut |
| Объём заводских заказов | Factory orders | Confirms durables |

## Prices

| Russian | English | Read for |
|---------|---------|----------|
| Годовая инфляция | Inflation rate YoY | Headline |
| Инфляция в месяц | Inflation rate MoM | The number that actually sets the trend |
| Базовый уровень инфляции | Core inflation | Ex-food and energy |
| Гармонизированный уровень инфляции | HICP (harmonized) | The euro-area comparable measure; differs from national CPI |
| Индекс цен производителей / ИПЦ год к году (в контексте PPI) | Producer price index | Pipeline pressure |
| Ожидания потребительской инфляции | Consumer inflation expectations | Central banks watch the 5y series closely |

Beware: Russian exports abbreviate several distinct series to **ИПЦ**. Context
decides whether it is the consumer price index, the producer price index, or an
index level rather than a rate. Check the units and the previous value.

## Labor

| Russian | English | Read for |
|---------|---------|----------|
| Уровень безработицы | Unemployment rate | Level, plus participation to interpret it |
| Количество новых рабочих мест вне с/х сектора | Nonfarm payrolls | The single biggest scheduled US mover |
| Число открытых вакансий (JOLTS) | Job openings (JOLTS) | Vacancy-to-unemployed ratio = labor tightness |
| Изменения занятости от ADP | ADP employment change | Weak predictor of payrolls; do not treat as a preview |
| Первичные заявки на пособие по безработице | Initial jobless claims | Weekly, high-frequency turn signal |
| Число повторных заявок | Continuing claims | Hiring rate, not firing rate |
| Уровень участия | Participation rate | Reframes the unemployment print |
| Почасовая заработная плата | Average hourly earnings | Wage-inflation link |

## Policy and rates

| Russian | English |
|---------|---------|
| Решение по процентной ставке | Interest rate decision |
| Ставка по депозитным средствам | Deposit facility rate |
| Маржинальная кредитная ставка | Marginal lending rate |
| Базовая ставка по кредиту (LPR) | Loan prime rate |
| Протокол заседания / Резюме обсуждения | Minutes / policy summary |
| Бежевая книга ФРС | Fed Beige Book |
| Экономические прогнозы FOMC | FOMC projections (dot plot) |

## External

| Russian | English | Read for |
|---------|---------|----------|
| Торговый баланс | Trade balance | Level and the export/import split |
| Счет текущих операций | Current account | External financing need |
| Международные резервы | Foreign exchange reserves | FX intervention evidence |
| Чистый объём частного кредитования | Net lending to individuals | Credit impulse |

## Sentiment

| Russian | English |
|---------|---------|
| Индекс доверия потребителей | Consumer confidence |
| Деловая уверенность | Business confidence |
| Индекс делового оптимизма от IFO | Ifo business climate |
| Индекс экономических настроений ZEW | ZEW economic sentiment |
| Индекс деловой активности ФРБ [города] | [City] Fed manufacturing index |

## Non-events

Rows that fill most of a calendar and move nothing on their own: bond and bill
auctions (`аукцион`, `размещение`, `торги по ... счетам`), rig counts, weekly
API/EIA inventories outside energy desks, and vehicle registration counts. They
matter to the desks that trade them and are noise to everyone else — which is
why the parser scores them `low` rather than dropping them.
