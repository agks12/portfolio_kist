# 통계조사시스템 데이터 고도화

## 프로젝트 소개
기존 Excel 기반 통계 데이터를 표준화·전산화하고, 데이터 적재 및 품질검증 체계를 구축하여 통계조사 홈페이지의 시각화 서비스에 활용될 수 있도록 데이터 파이프라인을 고도화한 프로젝트입니다.

## 프로젝트 기간
- 20**.. ~ 20**..

## 담당 역할 (Role)
- Data Engineering / Data Quality / Testing

## 기여도 (Contribution)
- QA Query: 100%
- Airflow Pipeline: 100%
- Data Mart Validation: 100%
- Dashboard Testing: 30%

## 기술 스택 (Tech Stack)
- Python / PostgreSQL / Apache Airflow

## 시스템 아키텍처
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

My Contribution

- 데이터 적재 구조 및 컬럼 정합성 검증 QA Query 설계
- Airflow DAG 운영 및 데이터 적재 과정 모니터링
- Data Mart 적재 결과 검증
- 데이터 오류 원인 분석 및 수정 요청
- Dashboard 데이터 정확성 검증
