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

### 5.1 데이터 검증 및 비교 파이프라인 구현

Excel 및 GIS 등 서로 다른 소스 포맷으로 적재된 원천 데이터를 동일한 스키마와 기준으로 전처리한 뒤, 두 소스 간의 핵심 통계 지표를 교차 검증(`QA Query`)하기 위해 작성한 SQL 파이프라인입니다.

* **주요 검증 로직:** 
  * 소스별 상이한 조건(`version_flag`, `batch_id` 패턴 등)을 반영한 공통 집계 모듈 구현
  * 부동소수점 오차를 고려한 안정적인 지표 차이(`Diff`) 연산 처리
  * 이종 포맷 간 카테고리 매핑 조건을 반영한 조인(Join) 검증 체계 구축

> 🔗 **전체 소스 코드 확인:** 
> [👉 GitHub Repository에서 전체 SQL 쿼리 보기](./sql/data_validation.sql)

### 5.2 ...

[코드]

## 06. Problem Solving

### Issue 01

Problem
↓
Analysis
↓
Solution
↓
Result

[Before / After Image]

## 07. Validation

[QA Result / Test Result]

## 08. Result

- 오류 사전 탐지
- 데이터 정합성 확보
- 36개 소품목 코드 정상 반영
- ...

## 09. Tech Stack

- Python / PostgreSQL / Apache Airflow
