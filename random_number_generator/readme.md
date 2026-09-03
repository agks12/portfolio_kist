# Random Number Analysis & Statistical Validation System

## 01. Overview

광검출기(Photodetector)와 광 입사 시간을 기록하는 카운터 장비를 직접 구성하여 획득한 **실험 데이터(광자 도달 시간 등)를 기반으로** Random Number sequences의 생성, 분석 및 통계적 검증을 수행하는 연구용 파이프라인 시스템입니다. 

기존에는 물리 실험을 통해 얻은 원시 데이터로부터 난수를 추출하고 무작위성을 평가하기 위해 수동으로 데이터를 변환하고 개별 분석 툴을 실행해야 했으나, 이를 **Python 및 LabVIEW 기반의 통합 자동화 분석 시스템**으로 전환했습니다.

이를 통해

> **광검출기 물리 실험 데이터 획득 → Python 기반 통계 분석(자기상관성, 분포, 포아송 검정) → LabVIEW 기반 NIST SP 800-22 (15가지 통계 테스트) 표준 검증**

까지의 복잡한 무작위성 평가 과정을 시스템이 수행하도록 구축했습니다.

데이터 특성과 분석 목적에 맞게 두 가지 핵심 모듈을 연계하고, 커스텀 통계 모델과 국제 표준 크립토그라픽 테스트를 결합하여 **신뢰할 수 있는 물리적 난수(True Random Number) 품질 검증 환경을 운영**했습니다.

---

## 02. Background

### Problem

광검출기와 타임 카운터 장비를 연동한 물리 실험 환경에서 데이터를 수집하고 난수를 생성하는 과정은 정기적·반복적으로 수행되지만 다음과 같은 작업이 지속적으로 필요했습니다.

* 광 입사 시간 기록 및 하드웨어 원시 데이터 수집 후 Hex / Binary 형태 변환
* 물리적 시퀀스 내 데이터 간 통계적 독립성 확인 (자기상관성 분석)
* 1진수/16진수 출현 빈도 및 확률 계산
* 이론적 광자 통계 모델 및 포아송 분포와 관측값 간의 적합도 검정 (카이제곱 검정)
* NIST SP 800-22 표준에 따른 15가지 복잡한 통계 테스트 수행
* 각 테스트별 p-value 산출 및 최종 무작위성 합격/불합격 판정

특히 물리 실험 데이터의 특성상 하드웨어적 노이즈나 환경 변수가 존재할 수 있어, 복잡한 통계 모델링과 표준 검증을 통해 난수의 순도를 객관적으로 증명하는 **체계적인 검증 프로세스 구축이 필수적**이었습니다.

---

## 03. Automation Architecture

두 종류의 분석 엔진을 데이터 처리 및 통계 검증 특성에 맞게 연계했습니다.

```text
                 ┌──────────────────────────────────────┐
                 │ Photodetector & Time Counter         │
                 │ (Hardware Experiment Data Source)    │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ Python Data Preprocessing            │
                 │ - Hex / Binary conversion            │
                 │ - Sequence transformation            │
                 └──────────────────┬───────────────────┘
                                    │
                        ┌───────────┴───────────┐
                        │                       │
                        ▼                       ▼
         ┌──────────────────────────────┐┌──────────────────────────────┐
         │ Statistical Analysis (Python)││ LabVIEW NIST Test Suite      │
         │ - Autocorrelation analysis   ││ - SP 800-22 (15 tests)       │
         │ - Poisson distribution test  ││ - Randomness validation      │
         │ - Hex distribution analysis  ││ - p-value evaluation         │
         └──────────────┬───────────────┘└──────────────┬───────────────┘
                        │                               │
                        └───────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ Comprehensive Validation             │
                 │ - True Random Number Quality Review  │
                 └──────────────────────────────────────┘
```

<div align="center">
  <img width="942" height="277" alt="실험과정" src="https://github.com/user-attachments/assets/68def4f1-d5fc-4f15-b3fc-9db036e8b51d" width="800" />
  <p><b>[그림 1] 실험 구성</b></p>
</b></p>
</div>


---

## 04. My Contribution

| 구분 | 담당 내용 | 기여도 |
| :--- | :--- | ---: |
| 실험 시스템 구축 | 광검출기 및 타임 카운터 장비 구성 및 물리 실험 데이터 수집 환경 구축 | 100% |
| 데이터 처리 | Python을 활용한 실험 원시 데이터(Hex / Binary) 변환 및 전처리 | 100% |
| 통계 분석 | 자기상관성(95% 신뢰구간), 분포, 포아송/카이제곱 검정 구현 | 100% |
| 표준 검증 | LabVIEW를 활용한 NIST SP 800-22 15가지 통계 테스트 구현 | 90% |
| 결과 평가 | p-value 기반 무작위성 합격/불합격 판정 및 시각화 | 100% |

---

## 05. Technical Implementation

### 5.1 Python 기반 통계 분석 시스템

광검출기 실험 시퀀스의 기본적인 통계적 특성을 파악하기 위해 전처리 및 커스텀 분석 모델을 구현했습니다.

* **자기상관성 분석 (Autocorrelation Analysis):** 시퀀스 요소 간의 통계적 의존성을 계산하고 95% 신뢰구간을 추정하여 물리적 독립성을 검증합니다.
  
<div align="center">
  <img width="443" height="296" alt="자기상관" src="https://github.com/user-attachments/assets/9407ff81-1e8a-41c1-b97e-615fce9f3224" width="400" />
  <p><b>[그림 2] 자기상관성 분석결과</b></p>
</b></p>
</div>
  
* **확률분포 분석 (Distribution Analysis):** 16진수 빈도 분포 및 이진 변환에 따른 확률 계산을 수행합니다.

<div align="center">
  <img width="956" height="307" alt="확률분포" src="https://github.com/user-attachments/assets/8dc9f60f-d230-47e2-abfd-54ad596322eb" width="800" />
  <p><b>[그림 3] 확률분포 분석결과</b></p>
</b></p>
</div>

* **포아송 / 광자 통계 모델 (Poisson / Photon Statistical Model):** 광 입사 데이터의 관측된 분포와 기대 포아송 분포를 비교하고, 카이제곱 검정 및 p-value를 도출합니다.

<div align="center">
  </div><img width="587" height="459" alt="포아송분포" src="https://github.com/user-attachments/assets/a308e780-d4c8-49fc-a089-e1e5ef511f83" width="500" />
  <p><b>[그림 4] 포아송분포 분석결과</b></p>
</b></p>
</div>
---

### 5.2 LabVIEW 기반 NIST SP 800-22 테스트 스위트

국제 표준 암호학적 무작위성 검증 기준인 NIST SP 800-22의 **15가지 통계 테스트를 LabVIEW 환경에 전면 구현**했습니다.

주요 검정 항목은 다음과 같습니다.
* Frequency Test
* Block Frequency Test
* Runs Test
* Longest Run of Ones Test
* Binary Matrix Rank Test
* Discrete Fourier Transform Test
* Non-overlapping Template Test
* Overlapping Template Test
* Universal Statistical Test
* Approximate Entropy Test
* Random Excursions Test
* Random Excursions Variant Test
* Serial Test
* Linear Complexity Test
* Cumulative Sums Test

위 항목들을 바탕으로 각 테스트별 p-value를 산출하여 통계적 유의성을 검증하고 최종 무작위성 합격 여부를 판정합니다.

<div align="center">
  <img width="551" height="915" alt="nist" src="https://github.com/user-attachments/assets/ed5b6a36-eda1-49a7-8f19-fbc827e787f1" width="500" />
  <p><b>[그림 5] 랩뷰로 구현한 NIST SP800-22 테스트 UI</b></p>
</b></p>

---

## 06. Problem Solving

### 6.1 이질적 환경 간 데이터 연동 및 전처리

Python 기반의 유연한 데이터 처리 환경과 LabVIEW 기반의 정밀 측정·검증 환경 간에 대용량 시퀀스 데이터를 손실 없이 주고받을 수 있도록 데이터 파이프라인을 정비했습니다. Hex와 Binary 포맷 간의 상호 변환 과정에서 발생하는 정밀도 저하 문제를 해결하여 분석 결과의 신뢰성을 확보했습니다.

### 6.2 대규모 통계 테스트의 연산 효율화

15가지에 달하는 NIST SP 800-22 테스트와 슬라이딩 윈도우 기반의 커스텀 통계 분석을 병행하면서 발생하는 연산 부하를 최적화했습니다. NumPy와 SciPy의 벡터 연산을 활용해 처리 속도를 개선하고 대규모 데이터셋에서도 안정적인 실행이 가능하도록 구현했습니다.

---

## 07. Validation

분석 및 검증 과정에서 단계별 검증을 수행하도록 구성했습니다.

### 전처리 단계
* 시퀀스 데이터 정규화 및 포맷 변환 확인
* 누락 데이터 및 이상치 검사

### 통계 분석 단계 (Python)
* 자기상관성 신뢰구간 유효성 확인
* 포아송 분포 적합도 및 카이제곱 검정 검증

### 표준 검증 단계 (LabVIEW)
* NIST SP 800-22 15개 테스트 정상 수행 여부 확인
* 테스트별 p-value 임계값 평가 및 패스/페일 판정

---

## 08. Result

커스텀 수학적 모델과 표준화된 암호학적 무작위성 테스트를 결합한 통합 검증 체계를 구축했습니다.

### 연구 측면의 개선
* 광검출기 실험 기반 난수 시퀀스의 자기상관성 및 분포 일관성 정밀 분석
* NIST SP 800-22 15개 항목의 자동화된 표준 검증 완료
* 양자 및 물리적 난수 연구를 위한 신뢰성 있는 평가 지표 확보

---

## 09. Tech Stack

### Programming Language & Core
* Python
* LabVIEW

### Hardware & Equipment
* Photodetector (광검출기)
* Time Counter (시간 기록 카운터)

### Data & Statistical Processing (Python)
* NumPy
* Pandas
* SciPy

### Standard & Framework
* NIST SP 800-22 Standard
* Statistical Modeling & Cryptographic Randomness Testing

---

## 10. Project Summary

> **광검출기 및 타임 카운터 장비 실험을 통해 획득한 물리적 데이터의 전처리부터 커스텀 통계 분석(Python), 그리고 NIST SP 800-22 15가지 표준 통계 테스트(LabVIEW)까지의 무작위성 검증 전 과정을 시스템화한 프로젝트**

단순 통계 계산을 넘어,

**실험 장비 연동 + 시퀀스 전처리 + 커스텀 통계 모델 + 국제 표준 무작위성 검증 + p-value 평가**

를 하나의 파이프라인으로 연결하여 **실제 연구 수준의 물리적 난수 품질 검증 환경을 구축**했습니다.
