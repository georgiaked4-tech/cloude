---
name: us-data-review
description: Разбор макроданных США и политики ФРС - рынок труда (NFP, ADP, JOLTS, claims, unemployment, wages, Challenger), инфляция (CPI, Core CPI, PPI, PCE, Core PCE, inflation expectations), активность (ISM, региональные ФРБ, retail sales, industrial production, GDP, GDPNow, жильё, доверие потребителей) и FOMC (решение, dot plot, пресс-конференция, minutes, Fed funds futures). Определяет режим DOVISH / HAWKISH / NEUTRAL. US macro data and Fed review. Использовать при "NFP", "CPI", "PCE", "ISM", "JOLTS", "claims", "ФРС", "FOMC", "dot plot", "данные США", "инфляция США", "рынок труда".
---

# US Data Review — данные США и ФРС

## 1. Рынок труда

Отслеживай: **NFP, ADP Employment, JOLTS, Initial Jobless Claims, Continuing Claims, unemployment rate, average hourly earnings, labor-force participation, Challenger Job Cuts.**

Для каждого показателя: `факт → прогноз → предыдущее → пересмотр предыдущих значений`. Пересмотры NFP регулярно меняют картину сильнее самого релиза — проверяй их всегда.

**Что читать внутри NFP:** частный сектор против государственного, диффузионный индекс, household survey против establishment survey (расхождение — ранний сигнал), отработанные часы (сокращение часов предшествует сокращению рабочих мест), U-6.

**Сигнал существенного охлаждения рынка труда** — когда совпадают:

```
JOLTS ↓  +  ADP слабеет  +  NFP подтверждает ухудшение  +  unemployment ↑  +  wage growth ↓
```

Это уже не отдельный слабый релиз, а смена режима: рост вероятности снижения ставок, падение 2Y, ослабление доллара, поддержка золота и BTC — до тех пор, пока рынок не переключится с темы «смягчение ФРС» на тему «рецессия».

Continuing claims важнее initial claims для определения фазы: рост continuing при стабильных initial означает, что уволенные перестают находить работу.

Правило Сахма (рост 3-месячной средней безработицы на 0,5 п.п. от минимума за 12 месяцев) — отдельно отмечай приближение к порогу.

## 2. Инфляция

Отслеживай: **CPI, Core CPI, PPI, Core PPI, PCE, Core PCE, inflation expectations, University of Michigan expectations, import/export prices**, а также зарплаты, стоимость жилья и энергоносители.

**Внутри CPI:** shelter (OER и rent of primary residence), core services ex-shelter («supercore» — ключ для ФРС), core goods, energy. Обязательно смотри 3-месячную и 6-месячную аннуализированную динамику, а не только год к году: разворот виден там первым.

**Связка PPI → PCE:** компоненты PPI (portfolio management, healthcare, airfares) напрямую входят в расчёт Core PCE — после PPI уточняй прогноз по Core PCE до его публикации.

Классифицируй режим:

| Режим | Признаки |
|-------|----------|
| **Inflation shock** | инфляция ускоряется одновременно с ростом нефти и доходностей облигаций |
| **Disinflation** | CPI/PCE устойчиво замедляются, особенно core services |
| **Stagflation risk** | рост экономики ↓ + рынок труда ↓ + инфляция ↑ |

Stagflation — худший сценарий для рынков: ФРС не может смягчать, а прибыли компаний падают.

## 3. Экономическая активность

Отслеживай: **ISM Manufacturing, ISM Services, ISM Prices Paid, Chicago PMI, Philadelphia Fed, Empire State, Retail Sales, Industrial Production, Durable Goods, Factory Orders, GDP, GDPNow, Consumer Confidence, University of Michigan Sentiment, housing starts, building permits, existing/new home sales.**

Особое внимание к компонентам:
- **New Orders** — опережающий индикатор спроса; связка new orders / inventories даёт направление цикла;
- **Employment** — подтверждение или опровержение данных по труду;
- **Prices Paid** — опережающий сигнал по инфляции на 1-3 месяца.

В retail sales смотри **control group** (входит в расчёт GDP). В durable goods — **core capital goods orders ex-aircraft** (инвестиционный цикл). В жилье building permits опережают starts.

ISM Services важнее ISM Manufacturing для экономики США в целом, но производство первым разворачивает цикл.

## 4. ФРС

Анализируй: решение FOMC, dot plot, пресс-конференцию председателя, заявления членов FOMC, Minutes, вероятность изменения ставки, Fed Funds Futures, изменение ожиданий рынка.

Определяй режим:

- 🟢 **DOVISH** — смягчение
- 🔴 **HAWKISH** — ужесточение
- 🟡 **NEUTRAL** — нейтрально

**Всегда показывай цепочку из трёх звеньев:**

```
что рынок ожидал → что сказала ФРС → как изменились ожидания ставок
```

Без третьего звена анализ FOMC бесполезен: значение имеет не тон сам по себе, а сдвиг рыночных ожиданий относительно того, что было заложено в цену.

Что проверять в dot plot: медиана на текущий и следующий год, дисперсия точек, изменение longer-run dot. В SEP: пересмотры прогнозов по росту, безработице и Core PCE — они объясняют логику точек.

В пресс-конференции ищи **изменение формулировок** относительно прошлого заседания, а не сами формулировки.

## Формат вывода по релизу

```
📊 [ПОКАЗАТЕЛЬ] — [дата, время ET]

Факт: [ ]  Прогноз: [ ]  Предыдущее: [ ] (пересмотр: [ ])
Отклонение: [ ]
Внутри данных: [2-3 ключевых компонента]
Тренд: [3м / 6м динамика, место в последовательности]

Реакция: 2Y [ ] · 10Y [ ] · DXY [ ] · S&P [ ] · Gold [ ] · BTC [ ]
Сдвиг ожиданий ФРС: [вероятность до → после, число снижений в цене]

ВЫВОД: [подтверждает / ослабляет / ломает текущий сценарий]
RISK LEVEL: 🟢 / 🟡 / 🟠 / 🔴 / 🚨
```
