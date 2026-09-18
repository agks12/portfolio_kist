## ⚙️ 주요 데이터 처리

### 1. 데이터 수집

공공데이터 API 및 Excel 파일을 통해 축산물 가격 및 재고 관련 데이터를 수집하고,
수집한 원천 데이터는 SQLite의 Raw Table에 저장하여 원본 데이터를 보존했습니다.

주요 수집 데이터는 다음과 같습니다.

- 축산물 일별 / 월별 / 순별 / 연도별 가격
- 축산물 소비자가격
- 돈육 대표가격
- 육계 산지 / 도매가격
- 계란 가격
- 토종닭 및 오리 가격
- 산란계 가격
- 축산물 재고동향


### 2. 데이터 정제 및 변환

Raw DB의 데이터를 서비스에서 조회하기 적합한 형태로 변환했습니다.

- 날짜 및 데이터 타입 정규화
- 코드 테이블 JOIN
- 불필요한 데이터 제거 및 컬럼 정리
- 현재 가격과 평년 가격 JOIN
- 축종 / 품목 / 등급 / 거래종류 기준 데이터 Pivot


### 데이터 베이스 계층 구조
```text

data.db
│
├── 📁 Code Tables
│   ├── judgekind_code
│   ├── item_code
│   ├── grd_code
│   └── unit_code
│
├── 📁 Raw Tables (Source)
│   ├── pig_representative_price
│   ├── livestock_product_inventory_trends
│   ├── monthly_livestock_product_prices
│   ├── interval_10day_livestock_product_prices
│   ├── annual_livestock_product_prices
│   ├── daily_livestock_product_prices
│   ├── korean_chickens_prices
│   ├── laying_hens_spent_hens_prices
│   ├── laying_hens_chicks_prices
│   ├── broilers_farm_gate_prices
│   ├── broilers_wholesale_prices
│   ├── egg_prices
│   └── duck_prices
│
├── 📁 Pivot / Data Mart Tables
│   ├── pivot_pig_representative_price
│   ├── pivot_korean_chickens_prices
│   ├── pivot_broilers_farm_gate_prices
│   ├── pivot_broilers_wholesale_prices
│   ├── pivot_egg_prices
│   ├── pivot_interval_10day_livestock_product_prices
│   ├── pivot_livestock_product_inventory_trends
│   ├── pivot_daily_livestock_product_prices
│   └── pivot_annual_livestock_product_prices
│
└── 📁 Overall Data Mart (Service Ready)
    ├── daily_overall
    ├── weekly_overall
    ├── monthly_overall
    └── yearly_overall
```

### 3. Dynamic Pivot



### 3. Dynamic Pivot
원본 데이터의 행(Row) 형태 데이터를 조회에 편리한 컬럼(Column) 형태로 변환했습니다.

```text
원본 데이터

날짜          거래종류    가격
2026-09-01    일반        100
2026-09-01    특수        120

        ↓ Pivot

날짜          일반_가격    특수_가격
2026-09-01    100         120
```


`CASE WHEN`과 `MAX()`를 활용하여 Pivot을 구현하고, 반복되는 Pivot 로직은 `dynamic_pivot()` 함수로 일반화하여 여러 데이터셋에서 재사용할 수 있도록 구성했습니다.

또한 축종 + 품목 + 등급 등의 여러 기준을 조합하여 동적으로 컬럼을 생성할 수 있도록 구현했습니다.



축종 + 품목 + 등급
        ↓
소_안심_1등급
소_등심_1등급
돼지_삼겹살_1등급
돼지_목심_1등급

### 4. 평년 데이터 결합

현재 가격 데이터와 평년 가격 데이터를 동일한 기준으로 `JOIN`하여 한 번의 조회로 현재 가격과 평년 가격을 함께 확인할 수 있도록 구성했습니다.

## 📊 Data Mart 구성

정제된 데이터는 `pivot_*` 테이블로 생성하고, 이를 다시 기간별 Overall Data Mart로 통합했습니다.

### Pivot Data Mart

원본 데이터를 서비스 조회에 적합한 형태로 변환한 중간 데이터 계층입니다.

`Raw Table → JOIN / Pivot / Transform → pivot_* Table`

### Overall Data Mart

여러 Pivot 테이블을 날짜 기준으로 통합하여 최종 조회용 테이블을 생성했습니다.

- `daily_overall` : 일별 데이터
- `weekly_overall` : 주별 데이터
- `monthly_overall` : 월별 데이터
- `yearly_overall` : 연도별 데이터

## 🔗 Overall Data Mart 생성

각 테이블의 기준 날짜를 `ymd` 컬럼으로 통일한 후, `UNION`을 이용하여 전체 날짜 목록을 생성하고 각각의 데이터를 `LEFT JOIN`했습니다.

이를 통해 여러 데이터셋에 존재하는 날짜를 하나의 기준으로 통합하고, 특정 데이터가 존재하지 않는 날짜도 전체 기준 날짜를 유지할 수 있도록 구성했습니다.

## 🧩 Dynamic SQL

Overall Data Mart 생성 과정은 테이블의 컬럼을 직접 작성하지 않고, SQLite의 `PRAGMA table_info()`를 활용하여 테이블 구조를 동적으로 조회하도록 구현했습니다.

조회한 테이블 및 컬럼 정보를 기반으로 `SELECT`, `UNION`, `LEFT JOIN` SQL을 자동 생성하여 Overall Data Mart를 구성했습니다.

이를 통해 종합 대상 테이블이 추가되거나 컬럼 구조가 변경되는 경우에도 SQL을 직접 수정해야 하는 작업을 최소화했습니다.

## 🔄 데이터 업데이트

신규 데이터는 API를 주기적으로 호출하여 수집하며, 초기 구축과 동일한 ETL 과정을 통해 최종 Data Mart까지 갱신합니다.

`API 호출 → 신규 데이터 수집 → Raw DB 업데이트 → 데이터 정제 / 변환 → Pivot Data Mart 갱신 → Overall Data Mart 갱신 → 서비스 반영`

신규 데이터가 추가되더라도 기존 데이터 처리 로직을 재사용할 수 있도록 구성했습니다.

## 🛠️ 기술 스택

| 구분 | 기술 |
|---|---|
| Language | Python |
| Database | SQLite |
| Data Processing | Pandas |
| Data Source | 공공데이터 API / Excel |
| SQL | SQLite SQL |
| 주요 기술 | Dynamic SQL, Dynamic Pivot, JOIN |
| 주요 라이브러리 | pandas, sqlite3, pathlib, json, re, os |

## 💡 주요 구현 포인트

### Raw 데이터 보존

- API 및 Excel 원본 데이터를 별도 Raw Table에 저장
- 데이터 검증 및 재처리 가능하도록 구성

### Dynamic Pivot

- `CASE WHEN + MAX()` 기반의 Pivot 구현
- `dynamic_pivot()` 공통 함수로 재사용성 확보

### Dynamic SQL

- `PRAGMA table_info()`를 활용하여 테이블 구조를 동적으로 분석
- `SELECT / UNION / JOIN` SQL 자동 생성

### Data Mart 구성

- `Raw → Pivot → Overall` 단계로 데이터 계층 분리
- 서비스 조회에 필요한 데이터를 미리 가공

### 기간별 통합

- 일 / 주 / 월 / 연도 단위의 Overall Data Mart 구성
- 다양한 축산물 데이터를 기간 기준으로 통합 조회

### 자동 갱신 구조

- 신규 API 데이터 수집 후 동일한 처리 파이프라인을 재사용
- Raw DB부터 최종 Data Mart까지 일관된 데이터 처리

## 🎯 기대 효과

- 다양한 축산물 데이터를 하나의 SQLite DB에서 통합 관리
- 원본 데이터와 가공 데이터를 단계별로 분리하여 관리
- 복잡한 Pivot 및 JOIN 과정을 사전에 처리하여 조회 편의성 향상
- 현재 가격과 평년 가격을 한 번에 비교 가능
- 일 / 주 / 월 / 연도별 통합 조회 가능
- 서비스에서는 복잡한 데이터 가공 없이 Data Mart를 바로 조회 가능
