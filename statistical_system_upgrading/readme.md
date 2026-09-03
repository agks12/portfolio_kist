# 통계조사시스템 데이터 고도화

## 01. Overview
기존 Excel 기반 통계 데이터를 표준화·전산화하고, 데이터 적재 및 품질검증 체계를 구축하여 통계조사 홈페이지의 시각화 서비스에 활용될 수 있도록 데이터 파이프라인을 고도화한 프로젝트입니다.

## 02. Background
문제 상황

## 03. Architecture
```text
   ┌────────────────┐             ┌──────────────┐
   │  Excel Source  │             │  Gis Source  │
   └───────┬────────┘             └──────┬───────┘
           │                             │
           └──────────────┬──────────────┘
                          ↓
                  ┌─────────────────┐
                  │   Airflow DAG   │ 
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │   PostgreSQL    │ 
                  └────────┬────────┘
                           ↓
             ┌─────────────┴─────────────┐
             ↓                           ↓
      ┌─────────────┐             ┌─────────────┐
      │  QA Query   │             │  Data Mart  │
      └─────────────┘             └──────┬──────┘
                                         ↓
                                  ┌─────────────┐
                                  │  Dashboard  │
                                  └─────────────┘
```

## 04. My Contribution
- 데이터 적재 구조 및 컬럼 정합성 검증 QA Query 설계(100%)
- Airflow DAG 운영 및 데이터 적재 과정 모니터링(100%)
- Data Mart 적재 결과 검증(100%)
- 데이터 오류 원인 분석 및 수정 요청(100%)
- Dashboard 데이터 정확성 검증(100%)


## 05. Technical Implementation

### 5.1 데이터 검증 및 비교 파이프라인 구현(지표 1)

Excel 및 GIS 등 서로 다른 소스 포맷으로 적재된 원천 데이터를 동일한 스키마와 기준으로 전처리한 뒤, 두 소스 간의 핵심 통계 지표를 교차 검증(`QA Query`)하기 위해 작성한 SQL

* **주요 검증 로직:** 
  * 소스별 상이한 조건(`version_flag`, `batch_id` 패턴 등)을 반영한 공통 집계 모듈 구현
  * 부동소수점 오차를 고려한 안정적인 지표 차이(`Diff`) 연산 처리
  * 이종 포맷 간 카테고리 매핑 조건을 반영한 조인(Join) 검증 체계 구축

> 🔗 **전체 쿼리 확인:** 
> [👉 전체 SQL 쿼리 보기](./data_consistency_validation.sql)


### 5.2 데이터 검증 및 비교 파이프라인 구현(지표 2)

5-1 과 같은 흐름이지만 다른 지표를 검증하는 쿼리

* **주요 검증 로직:** 
  * generate_series와 윈도우 함수를 활용한 결측 구간 복원 및 Forward Fill 처리
  * 단계별(Phase) 누적 값과 이전 단계 간의 차이(Delta Value) 연산 및 시계열 흐름 정합성 검증
  * 독립된 두 데이터 소스(Source A의 전처리/집계 결과 vs External Source) 간의 수치 및 변화량 교차 검증

> 🔗 **전체 쿼리 확인:** 
> [👉 전체 SQL 쿼리 보기](./phase_based_metric_comparison.sql)

## 06. Problem Solving & Validation

### Issue 01: 데이터 파이프라인 및 원천 데이터 오류 검증과 정합성 확보

* **Problem (문제 상황)**
  *  직접 구현한 5번의 검증쿼리를 수행한 결과 데이터 불일치 이슈 탐지

* **Analysis (원인 분석)**
  * **오류 1:** 품목 컬럼 값이 동일하게 잘못 적재됨 $\rightarrow$ Airflow 파이프라인 DAG 로직 문제 확인
  * **오류 2:** 엑셀 원본 데이터 자체에 잘못된 값이 포함됨 $\rightarrow$ 원천 데이터 이상 징후 식별

<br>

<div align="center">
  <img width="80%" src="https://github.com/user-attachments/assets/a7adf6e4-f4c3-4bb0-a7e0-8f6fb6833e81" />
  <p><b>[그림 1] Airflow 파이프라인 로직 오류로 인한 품목 컬럼 값 중복 적재 현상 검증</b></p>
</div>

<br>

<div align="center">
  <img width="80%" src="https://github.com/user-attachments/assets/577f5f01-5ab8-4c99-b1cf-98ac846ec02a" />
  <p><b>[그림 2] QA 쿼리를 통한 검증값 이상치 탐지</b></p>
</div>

<br>

* **Solution (해결 방안)**
  * Airflow 파이프라인 오류 건은 제작 업체에 수정 요청 및 반영 완료
  * 엑셀 원본 데이터 오류 건은 납품 업체에 수정 요청하여 올바른 데이터 확보

* **Result (개선 결과)**
  * 파이프라인 및 원천 데이터 오류를 선제적으로 차단하여 최종 데이터 마트에 신뢰할 수 있는 데이터 적재 체계 확립


## 07. Result

- 오류 사전 탐지
- 데이터 정합성 확보

## 08. Tech Stack

- Python / PostgreSQL / Apache Airflow
