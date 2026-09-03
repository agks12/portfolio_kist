# Random Number Analysis & Statistical Validation System

## 01. Overview

광검출기(Photodetector)와 광 입사 시간을 기록하는 카운터 장비를 직접 구성하여 획득한 **실험 데이터(광자 도달 시간 등)를 기반으로** Random Number sequences의 생성, 분석 및 통계적 검증을 수행하는 연구 


> **광검출기 물리 실험 데이터 획득 → Python 기반 통계 분석(자기상관성, 분포, 포아송 검정) → LabVIEW 기반 NIST SP 800-22 (15가지 통계 테스트) 표준 검증**


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
| 표준 검증 | LabVIEW를 활용한 NIST SP 800-22 15가지 통계 테스트 구현 | 1000% |
| 결과 평가 | p-value 기반 무작위성 합격/불합격 판정 및 시각화 | 100% |

---

## 05. Technical Implementation

### 5.1 Python 기반 통계 분석 시스템

광검출기 실험 시퀀스의 기본적인 통계적 특성을 파악하기 위해 전처리 및 커스텀 분석 모델을 구현했습니다.

* **자기상관성 분석 (Autocorrelation Analysis):** 시퀀스 요소 간의 통계적 의존성을 계산하고 95% 신뢰구간을 추정하여 물리적 독립성을 검증합니다.
  
<div align="center">
  <img alt="자기상관" src="https://github.com/user-attachments/assets/9407ff81-1e8a-41c1-b97e-615fce9f3224" width="400" />
  <p><b>[그림 2] 자기상관성 분석결과</b></p>
</b></p>
</div>
  
* **확률분포 분석 (Distribution Analysis):** 16진수 빈도 분포 및 이진 변환에 따른 확률 계산을 수행합니다.

<div align="center">
  <img alt="확률분포" src="https://github.com/user-attachments/assets/8dc9f60f-d230-47e2-abfd-54ad596322eb" width="800" />
  <p><b>[그림 3] 확률분포 분석결과</b></p>
</b></p>
</div>

* **포아송 / 광자 통계 모델 (Poisson / Photon Statistical Model):** 광 입사 데이터의 관측된 분포와 기대 포아송 분포를 비교하고, 카이제곱 검정 및 p-value를 도출합니다.

<div align="right">
  </div><img alt="포아송분포" src="https://github.com/user-attachments/assets/a308e780-d4c8-49fc-a089-e1e5ef511f83" width="400" />
  <p><b>[그림 4] 포아송분포 분석결과</b></p>
</b></p>
</div>


---


### 5.2 LabVIEW 기반 NIST SP 800-22 테스트 스위트 🔥 [Core Highlight]

> **⭐ 본 프로젝트에서 가장 심혈을 기울인 핵심 구현 파트로**, 국제 표준 암호학적 무작위성 검증 기준인 **[NIST SP 800-22 Revision 1a (A Statistical Test Suite for Random and Pseudorandom Number Generators for Cryptographic Applications)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-22r1a.pdf)** 논문을 바탕으로 **15가지 통계 테스트를 LabVIEW 환경에 완벽하게 직접 구현**했습니다.


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
  <img alt="nist" src="https://github.com/user-attachments/assets/ed5b6a36-eda1-49a7-8f19-fbc827e787f1" width="500" />
  <p><b>[그림 5] 랩뷰로 구현한 NIST SP800-22 테스트 UI</b></p>
</b></p>
</div>


---


## 06. Problem Solving

### 6.1 하드웨어 제어와 데이터 분석 환경의 최적 역할 분담

광검출기와 타임 카운터 장비에서 물리 실험 데이터를 실시간으로 안정적으로 수집하기 위해서는 하드웨어 연동에 강력한 장점이 있는 LabVIEW를 활용했습니다. 이후 원시 데이터의 포맷 변환 및 커스텀 통계 분석은 Python을 활용하는 방식으로 역할 분담을 설계하여, 물리 장비 연동성과 데이터 처리의 유연성을 동시에 확보했습니다.

### 6.2 LabVIEW 환경 내 NIST SP 800-22 15개 테스트 직접 구현

일반적으로 난수 검정(NIST SP 800-22)은 C나 Python 환경에서 기존에 구현된 라이브러리나 툴을 사용하는 것이 대중적이지만, LabVIEW 환경에서는 참고할 수 있는 표준 구현체가 전무했습니다. 

이에 안주하지 않고 NIST 공식 표준 문서와 논문을 바탕으로 **15가지 통계 테스트를 LabVIEW 환경에서 처음부터 직접 코딩하여 구현**했습니다. 이 과정에서 각 통계 검정의 수학적 원리와 알고리즘을 깊이 있게 이해할 수 있었으며, LabVIEW 기반의 독창적인 난수 품질 검증 환경을 성공적으로 완성했습니다.

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

> **광검출기 및 타임 카운터 장비 실험을 통해 획득한 물리적 데이터의 전처리부터 커스텀 통계 분석(Python), 기존 구현체가 없는 LabVIEW 환경에서 NIST SP 800-22 15가지 표준 통계 테스트를 전면 직접 구현하여 무작위성 검증 전 과정을 주도적으로 수행한 연구**

