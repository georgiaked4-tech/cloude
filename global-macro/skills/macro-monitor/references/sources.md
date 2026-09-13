# Источники и их приоритет

## Иерархия доверия

1. **Центральные банки** — Fed, ECB, BOJ, BOE, PBOC, SNB, BOC, RBA, RBNZ, BOK, ЦБ РФ
2. **Государственные статистические ведомства** — BLS, BEA, Census, Eurostat, Destatis, INSEE, ISTAT, ONS, NBS China, Statistics Japan, KOSTAT
3. **Министерства финансов / долговые агентства** — US Treasury, MOF Japan, AFT (Франция), Tesoro (Италия), UK DMO, Finanzagentur (Германия)
4. **Биржи** — CME, ICE, TSE, HKEX, KRX
5. **Официальные регуляторы** — SEC, FCA, ESMA, FSA Japan
6. **Reuters / Bloomberg / FT / WSJ**
7. **Крупные финансовые платформы** — данные и котировки

Социальные сети — **только источник раннего сигнала**, никогда не окончательное подтверждение.

## Ключевые первоисточники по темам

### США — данные
| Показатель | Первоисточник |
|-----------|---------------|
| NFP, unemployment, AHE, JOLTS, CPI, PPI, реальные заработки | BLS — bls.gov |
| GDP, PCE, Core PCE, доходы/расходы | BEA — bea.gov |
| Retail Sales, Durable Goods, жильё (starts/permits/new home sales) | Census — census.gov |
| Initial / Continuing Claims | DOL — dol.gov/ui/data.pdf |
| ADP Employment | ADP Research |
| Challenger Job Cuts | Challenger, Gray & Christmas |
| ISM Manufacturing / Services | ISM — ismworld.org |
| Empire State / Philly Fed / Chicago PMI | ФРБ Нью-Йорка, ФРБ Филадельфии, MNI |
| Consumer Confidence | Conference Board |
| U. Michigan sentiment и inflation expectations | sca.isr.umich.edu |
| GDPNow | ФРБ Атланты |
| Existing home sales | NAR |

### США — ФРС и ликвидность
| Показатель | Первоисточник |
|-----------|---------------|
| Решение FOMC, statement, dot plot, SEP, Minutes | federalreserve.gov |
| Баланс ФРС (H.4.1) | federalreserve.gov/releases/h41 — публикуется по четвергам |
| Банковские резервы, M2 (H.6), H.8 по банкам | federalreserve.gov + FRED |
| TGA (Treasury General Account) | fiscaldata.treasury.gov — Daily Treasury Statement |
| Reverse Repo (RRP), SRF, SOFR | ФРБ Нью-Йорка — newyorkfed.org |
| Treasury issuance, refunding, аукционы | treasurydirect.gov, TBAC quarterly refunding |
| Вероятности ставки | CME FedWatch / Fed Funds futures |
| Агрегированные ряды | FRED — fred.stlouisfed.org |

### Япония
| Показатель | Первоисточник |
|-----------|---------------|
| Решение BOJ, Outlook Report, purchases operations | boj.or.jp |
| CPI, Tokyo CPI, GDP, wages | stat.go.jp, MHLW (зарплаты) |
| JGB yields, аукционы JGB, интервенции на FX | mof.go.jp (в т.ч. ежемесячные данные по валютным интервенциям) |
| Nikkei / TOPIX | JPX |

### Китай
| Показатель | Первоисточник |
|-----------|---------------|
| PMI (официальный), CPI, PPI, GDP, retail sales, IP, FAI, цены на жильё | NBS — stats.gov.cn |
| Caixin PMI | S&P Global / Caixin |
| Exports / imports | GACC — customs.gov.cn |
| TSF, new loans, M1, M2, credit impulse | PBOC — pbc.gov.cn |
| RRR, ставки MLF/LPR, CNY fixing | PBOC |

### Европа
| Показатель | Первоисточник |
|-----------|---------------|
| Решение ECB, TLTRO, PEPP/APP, балансы | ecb.europa.eu |
| HICP, GDP еврозоны | Eurostat |
| Bund yields, аукционы | Deutsche Finanzagentur, Bundesbank |
| OAT yields, аукционы, дефицит Франции | AFT — aft.gouv.fr, INSEE |
| BTP, долг и дефицит Италии | Dipartimento del Tesoro, ISTAT |
| Рейтинговые решения | S&P, Moody's, Fitch — календари пересмотра |

### Великобритания
| Показатель | Первоисточник |
|-----------|---------------|
| Решение BOE, QT-программа | bankofengland.co.uk |
| CPI, wage growth, GDP | ONS — ons.gov.uk |
| Gilt-аукционы и remit | UK DMO — dmo.gov.uk |

### Южная Корея
| Показатель | Первоисточник |
|-----------|---------------|
| Экспорт (в т.ч. первые 20 дней месяца), полупроводники | Korea Customs Service |
| CPI, GDP | KOSTAT, Bank of Korea |
| Решение BOK, KRW | Bank of Korea |

### Нефть и сырьё
| Показатель | Первоисточник |
|-----------|---------------|
| Запасы США, добыча, EIA STEO | eia.gov (среда 10:30 ET), API — вторник |
| Решения OPEC+ | opec.org |
| Буровые | Baker Hughes (пятница) |

### Золото и Bitcoin
| Показатель | Первоисточник |
|-----------|---------------|
| Покупки ЦБ, ETF-потоки по золоту | World Gold Council |
| Spot BTC ETF flows | эмитенты ETF, Farside/сводные трекеры |
| Stablecoin supply, BTC dominance | on-chain агрегаторы |

## Правила проверки

- Для важного события проверяй **первоисточник**, а не пересказ.
- Проверяй **время публикации** и отличай дату статьи от даты самого события.
- Если первоисточник недоступен — минимум **два независимых надёжных источника**.
- Не выдавай слух за факт. Неподтверждённое маркируй как **НЕПОДТВЕРЖДЕНО**.
- После публикации revised data (пересмотренных данных) обновляй вывод и запись в журнале.
