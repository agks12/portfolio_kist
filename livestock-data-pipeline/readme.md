# 🐄 축산물 가격·유통 데이터 통합 시스템

> 공공데이터 API 및 Excel 데이터를 수집·가공하여 축산물 가격, 재고, 거래정보를 통합하고  
> 서비스 조회에 최적화된 Data Mart를 구축한 데이터 처리 프로젝트

## 📌 프로젝트 개요

- 공공데이터 API 및 Excel 기반 축산물 데이터 수집
- 수집 데이터를 SQLite Raw DB에 저장
- `JOIN`, `CASE WHEN`, `MAX`, `UNION`을 활용한 데이터 정제 및 변환
- 축종·품목·등급·거래종류 기준 Dynamic Pivot 구현
- 현재 가격과 평년 가격을 결합하여 비교 데이터 구성
- 일/주/월/연도 단위의 통합 Data Mart 구축
- API를 통한 신규 데이터 주기적 갱신 구조 구현

## 🏗️ 데이터 파이프라인

```text
공공데이터 API / Excel
        ↓
   Data Collection
        ↓
      Raw DB
     (SQLite)
        ↓
 Data Cleaning / Transform
        ↓
 Dynamic Pivot / JOIN
        ↓
   Pivot Data Mart
        ↓
 Overall Data Mart
 (일 / 주 / 월 / 연도)
        ↓
   서비스 / API 조회
🗄️ 데이터 구조
data.db
├── Code Tables
│   ├── judgekind_code
│   ├── item_code
│   ├── grd_code
│   └── unit_code
│
├── Raw Tables
│   ├── daily_livestock_product_prices
│   ├── monthly_livestock_product_prices
│   ├── annual_livestock_product_prices
│   ├── livestock_product_inventory_trends
│   ├── pig_representative_price
│   ├── broilers_farm_gate_prices
│   ├── broilers_wholesale_prices
│   ├── egg_prices
│   └── duck_prices
│
├── Pivot Data Mart
│   ├── pivot_daily_livestock_product_prices
│   ├── pivot_pig_representative_price
│   ├── pivot_egg_prices
│   └── ...
│
└── Overall Data Mart
    ├── daily_overall
    ├── weekly_overall
    ├── monthly_overall
    └── yearly_overall
⚙️ 주요 구현
Dynamic Pivot
CASE WHEN + MAX()를 활용하여 행 형태의 원본 데이터를 조회에 적합한 컬럼 형태로 변환했습니다.

축종 + 품목 + 등급
        ↓
소_안심_1등급
소_등심_1등급
돼지_삼겹살_1등급
반복되는 Pivot 로직은 dynamic_pivot() 함수로 일반화하여 재사용성을 높였습니다.

Dynamic SQL
SQLite의 PRAGMA table_info()를 활용하여 테이블 및 컬럼 정보를 동적으로 조회하고,

SELECT 생성

UNION 생성

LEFT JOIN 생성

Overall Data Mart 생성

과정을 자동화했습니다.

🔄 데이터 업데이트
API 호출
  ↓
신규 데이터 수집
  ↓
Raw DB 업데이트
  ↓
Pivot / Transform
  ↓
Overall Data Mart 갱신
  ↓
서비스 반영
🛠️ Tech Stack
구분	기술
Language	Python
Database	SQLite
Data Processing	Pandas
Data Source	공공데이터 API / Excel
SQL	SQLite SQL
주요 기술	Dynamic SQL, Pivot, JOIN
🎯 기대 효과
다양한 축산물 데이터를 하나의 DB에서 통합 관리

원본 데이터와 가공 데이터를 계층별로 분리

반복적인 Pivot 작업을 공통 함수로 자동화

현재 가격과 평년 가격의 편리한 비교

일/주/월/연도 단위의 통합 조회

서비스에서 복잡한 데이터 가공 없이 바로 조회 가능

신규 데이터 수집 및 갱신 과정 재사용 가능
