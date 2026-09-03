# 농업 통계자료 기반 RAG 챗봇

PDF 형태로 제공되는 농업 관측자료를 구조화하여 사용자가 자연어로 질문하면 관련 데이터를 검색하고, LLM을 통해 답변을 생성할 수 있도록 구축한 RAG 기반 챗봇 프로젝트입니다.

---

## 01. Overview

농업 관련 통계자료가 매월 PDF 형태로 발행되고 있어 특정 기간이나 품목의 데이터를 조회·비교하기 위해서는 여러 PDF 문서를 직접 확인해야 하는 불편함이 있었습니다.

이를 개선하기 위해 농업 관측월보 및 농업전망 보고서의 데이터를 추출하여 벡터 DB에 저장하고, 사용자의 자연어 질문과 유사한 문서를 검색한 뒤 LLM이 검색 결과를 기반으로 답변을 생성하는 RAG 시스템을 구축했습니다.

특히 일반적인 텍스트 기반 Chunking 방식의 한계를 개선하기 위해 **pdfplumber에서 제공하는 PDF 내부 요소의 좌표 정보를 활용하여 표와 문장을 구분하는 위치 기반 Chunking 알고리즘을 직접 설계·구현**했습니다.

### 핵심 목표

* PDF 내 텍스트 및 표 데이터 구조화
* 문서의 의미적 맥락을 보존하는 Chunking 구현
* 추출된 데이터를 벡터화하여 Vector DB에 저장
* 질문과 유사한 문서 검색 및 중복 문서 제거
* 검색 결과를 기반으로 LLM 답변 생성
* Streamlit 기반 RAG 챗봇 구현

---

## 02. Background

### Problem

농업 관련 관측자료는 PDF 형태로 제공되기 때문에 특정 품목이나 기간의 데이터를 확인하기 위해 여러 문서를 직접 열어 검색해야 했습니다.

또한 PDF 문서를 단순한 텍스트로 변환한 뒤 일정 글자 수를 기준으로 Chunking할 경우 다음과 같은 문제가 발생할 수 있습니다.

### ① Context Fragmentation

하나의 표 또는 문장이 여러 Chunk로 분리되면서 데이터의 맥락이 단절되는 문제가 발생합니다.

예를 들어 표의 일부만 다른 Chunk로 분리될 경우 사용자가 질문한 품목의 전체 정보를 검색하지 못할 수 있습니다.

### ② Information Dilution

하나의 Chunk에 너무 많은 정보가 포함될 경우 질문과 직접적으로 관련된 정보의 비중이 낮아져 검색 결과의 정보 밀도가 떨어질 수 있습니다.

따라서 **표는 표 단위, 문장은 문장 단위로 최대한 세분화하여 의미적 맥락을 유지하는 Chunking 방식**을 설계했습니다.

---

## 03. Architecture

### 전체 RAG Process

```text
┌──────────────────────┐
│ 농업 관측월보 / 보고서 │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ PDF 데이터 추출       │
│      pdfplumber      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 위치 기반 구조 분석   │
│ Text / Table 분리    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Chunking             │
│ 문장 / 표 단위 분할   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Embedding            │
│ text-embedding-3-small│
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ ChromaDB             │
│ Vector + Metadata    │
└──────────┬───────────┘
           │
           │ 사용자 질문
           ▼
┌──────────────────────┐
│ Query Embedding      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 유사 문서 검색        │
│ + Metadata Filtering │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 유사 문서 중복 제거   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ OpenAI LLM           │
│ Prompt + Context     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Streamlit UI         │
│ 답변 / 시각화         │
└──────────────────────┘
```
![Uploading image.png…]()

PDF 데이터는 `pdfplumber`를 활용하여 추출하고, OpenAI Embedding API를 이용해 벡터화한 뒤 ChromaDB에 메타데이터와 함께 저장했습니다. 사용자의 질문 역시 임베딩한 후 유사 문서를 검색하고, 검색 결과를 LLM에 전달하여 답변을 생성하는 구조입니다.

---

## 04. My Contribution

| Task                     | Contribution |
| ------------------------ | -----------: |
| PDF 데이터 추출               |         100% |
| 위치 기반 데이터 추출 알고리즘        |         100% |
| PDF Chunking 설계 및 구현     |         100% |
| 표 구조 복원 및 데이터 매칭         |         100% |
| Embedding / Vector DB 적재 |         100% |
| 유사 문서 검색 로직              |         100% |
| 유사 문서 중복 제거 로직           |         100% |
| LLM 연동                   |         100% |
| Streamlit UI             |            - |

### 핵심 기여

프로젝트에서 가장 중점적으로 담당한 부분은 **PDF 문서의 구조를 분석하고 검색에 적합한 형태로 데이터를 Chunking하는 과정**입니다.

기존의 단순 글자 수 기반 Chunking 방식 대신 `pdfplumber`에서 제공하는 PDF 요소의 좌표 정보를 활용하여 텍스트와 표를 구분하고, 표의 행·열 구조를 복원하는 알고리즘을 직접 설계했습니다.

---

## 05. Technical Implementation

[👉 직접 설계한 Chunking 코드 보러가기](./pdf_parsing_embedding.py)

### 5.1 PDF 위치 기반 데이터 추출

`pdfplumber`를 이용하여 PDF 내부의 텍스트와 표를 추출하고 각각의 위치 정보를 활용했습니다.

```text
PDF
 │
 ├── Text → char 요소
 │
 └── Table → rect 요소
             │
             ▼
        좌표 정보 추출
        x / y / width / height
```

추출한 요소의 좌표 정보를 기반으로 PDF 내에서 각 요소가 어느 위치에 존재하는지 분석했습니다.

---

### 5.2 표 구조 복원

PDF에서 추출한 표의 좌표 정보를 기반으로 행과 열을 구성하고, 텍스트 요소와 표의 좌표를 매칭하여 표 구조를 복원했습니다.

```text
PDF Table
   │
   ▼
Rect 요소 좌표 추출
   │
   ▼
X / Y 좌표 분석
   │
   ▼
행 / 열 그룹화
   │
   ▼
Text ↔ Table 좌표 매칭
   │
   ▼
최종 Table 생성
```

PDF의 모든 `x, y` 좌표 조합을 이용하여 누락된 셀을 보완하고, 최종적으로 표 형태가 아닌 데이터는 제거하여 구조화된 표를 생성했습니다.

---

### 5.3 문장 단위 Chunking

텍스트 데이터는 `Y 좌표`와 `글자 크기`를 기준으로 그룹화한 뒤 `X 좌표`를 이용하여 같은 줄의 데이터를 연결했습니다.

PDF의 좌표 오차로 인해 실제로는 한 줄인 문장이 여러 그룹으로 분리되는 경우를 보완하여 하나의 문단으로 재구성했습니다.

```text
Text Elements
     │
     ▼
Y 좌표 + 글자 크기 그룹화
     │
     ▼
X 좌표 기준 정렬
     │
     ▼
동일 Line 결합
     │
     ▼
문단 구성
```

---

### 5.4 표 제목 / 주석 / 단위 매칭

표 데이터와 별도로 추출된 텍스트 중 표의 제목, 주석, 단위 등을 표와 연결했습니다.

표 제목의 경우 다음 조건을 활용하여 해당 표와의 연관성을 판단했습니다.

* 표보다 위쪽에 위치
* 표와 일정 거리 이내
* 표의 최소 X 좌표보다 뒤에 위치

이를 통해 표 자체의 데이터뿐만 아니라 해당 표를 설명하는 제목 및 관련 정보까지 하나의 문서 구조로 구성했습니다.

---

### 5.5 Embedding & ChromaDB

최종적으로 정제된 문서를 Embedding하여 ChromaDB에 저장했습니다.

```text
구조화된 PDF 데이터
       │
       ▼
Markdown Table 변환
       │
       ▼
Metadata 생성
       │
       ▼
OpenAI Embedding
text-embedding-3-small
       │
       ▼
ChromaDB
 ├── ID
 ├── Vector
 ├── Metadata
 └── Original Document
```

문서에는 연도, 월, 품목 정보를 기반으로 문서명을 구성하고 메타데이터를 함께 저장했습니다. ChromaDB에는 원문, 벡터, 메타데이터, ID를 저장하여 이후 검색 과정에서 활용할 수 있도록 구성했습니다.

---

### 5.6 Query Embedding & Similarity Search

사용자가 자연어로 질문하면 질문을 Embedding하여 Vector DB에서 유사한 문서를 검색합니다.

```text
User Query
    │
    ▼
Query Embedding
    │
    ▼
ChromaDB Similarity Search
    │
    ├── Table Documents
    └── Text Documents
    │
    ▼
Top-K Documents
```

필요한 경우 연도, 월, 품목 등의 메타데이터 조건을 적용하여 검색 범위를 제한할 수 있도록 구성했습니다.

---

### 5.7 Similar Document Removal

검색된 문서 중 서로 유사한 문서가 여러 개 포함되는 문제를 해결하기 위해 유사 문서를 그룹화하고 중복 데이터를 제거하는 로직을 구현했습니다.

```text
검색 결과 K개
     │
     ▼
문서 간 유사도 비교
     │
     ▼
유사 문서 그룹화
     │
     ▼
그룹 내 대표 문서 선택
     │
     ▼
중복 문서 제거
     │
     ▼
최종 문서 리스트
```

각 문서 쌍의 유사도를 비교하여 유사한 문서를 하나의 그룹으로 묶고, 그룹 내에서는 문서 길이가 가장 긴 문서를 대표 문서로 선택하여 중복 정보를 제거했습니다.

또한 검색 문서 수 `K`가 너무 크면 LLM에 전달되는 데이터와 토큰 비용 및 처리 시간이 증가하고, 반대로 너무 작으면 정보 부족으로 정확도가 떨어질 수 있기 때문에 `K` 값을 검색 품질과 비용 사이의 주요 파라미터로 고려했습니다.

---

### 5.8 LLM Answer Generation

중복 제거된 검색 결과를 질문과 함께 LLM에 전달하여 답변을 생성했습니다.

```text
User Question
      +
Retrieved Documents
      │
      ▼
Prompt
      │
      ▼
OpenAI API
      │
      ▼
LLM Response
      │
      ▼
Answer
```

Prompt에는 검색된 문서와 사용자의 질문을 함께 전달하고, 지정된 답변 형식에 따라 결과를 생성하도록 구성했습니다. API 응답에서 최종 답변을 추출하여 사용자에게 전달했습니다.

---

## 06. Problem Solving

### Issue 01. 단순 텍스트 기반 Chunking의 맥락 단절

**Problem**

PDF 데이터를 단순 텍스트로 변환한 후 일정 글자 수를 기준으로 분할하면 하나의 표 또는 문장이 여러 Chunk로 나뉘어 데이터의 의미적 맥락이 단절될 수 있었습니다.

**Analysis**

```text
기존 방식

PDF
 ↓
Text Extraction
 ↓
일정 글자 수 기준 분할
 ↓
Chunk #1
Chunk #2
Chunk #3

문제
→ 하나의 표가 여러 Chunk로 분리
→ 질문에 필요한 정보가 서로 다른 Chunk에 존재
```

**Solution**

PDF 내부 요소의 좌표 정보를 활용하여 표와 문장을 구분하고, 가능한 한 **표 1개 / 문장 1개 단위로 Chunk를 생성**하도록 알고리즘을 설계했습니다.

**Result**

```text
개선 방식

PDF
 ↓
좌표 정보 추출
 ↓
Layout 분석
 ↓
┌──────────────┐
│ Table        │
└──────────────┘

┌──────────────┐
│ Sentence     │
└──────────────┘
 ↓
Semantic Chunk
```

문서의 구조적 맥락을 유지하면서 Embedding할 수 있도록 개선했습니다.

---

### Issue 02. PDF 표 구조의 좌표 정보 불완전

**Problem**

일부 PDF 표에서는 모든 셀에 `rect` 요소가 존재하지 않아 표 구조가 완전하게 추출되지 않는 문제가 발생했습니다.

**Analysis**

```text
PDF Table
 ├── Cell 1 ✓
 ├── Cell 2 ✓
 ├── Cell 3 ✕
 └── Cell 4 ✓
```

**Solution**

추출된 좌표 정보를 분석하고 가능한 `X, Y` 좌표 조합을 기반으로 누락된 셀을 생성하여 표 구조를 보완했습니다.

**Result**

```text
Fill Function

적용 전
┌────┬────┬────┐
│ ✓  │ ✓  │    │
├────┼────┼────┤
│ ✓  │    │ ✓  │
└────┴────┴────┘

        ↓

적용 후
┌────┬────┬────┐
│ ✓  │ ✓  │ ✓  │
├────┼────┼────┤
│ ✓  │ ✓  │ ✓  │
└────┴────┴────┘
```

이후 텍스트 요소와 좌표를 매칭하여 최종 표를 생성했습니다.

---

### Issue 03. 검색 결과의 중복 문서

**Problem**

Vector DB에서 유사 문서를 검색할 경우 동일하거나 매우 유사한 내용의 문서가 여러 개 반환되어 LLM에 불필요하게 많은 정보가 전달될 수 있었습니다.

**Solution**

문서 간 유사도를 다시 계산하여 유사 문서를 그룹화하고, 그룹 내 대표 문서를 선택하여 중복 결과를 제거했습니다.

**Result**

```text
Top-K Search
     ↓
Similarity Check
     ↓
Similar Document Grouping
     ↓
Representative Document Selection
     ↓
Final Context
     ↓
LLM
```

이를 통해 LLM에 전달되는 문서 수와 불필요한 중복 정보를 줄일 수 있도록 구성했습니다.

---

## 07. Validation

### PDF 데이터 추출 검증

PDF 원문과 추출된 데이터를 비교하여 다음 항목을 확인했습니다.

* 텍스트 추출 여부
* 표 구조 복원 여부
* 행 / 열 정렬 여부
* 표 제목 및 주석 매칭 여부
* 문장 단위 그룹화 여부
* 불필요한 데이터 제거 여부

### Vector DB 검증

ChromaDB에 다음 정보를 정상적으로 저장하도록 확인했습니다.

```text
Document ID
Vector
Metadata
Original Document
```

### Retrieval 검증

질문에 대해 다음 과정을 확인했습니다.

```text
Question
   ↓
Query Embedding
   ↓
Similarity Search
   ↓
Top-K Retrieval
   ↓
Duplicate Removal
   ↓
LLM Context
```

특히 `K` 값에 따라 검색되는 정보량과 LLM 입력 토큰이 달라지므로 검색 정확도와 처리 비용을 함께 고려했습니다.

---

## 08. Result

### 주요 성과

* PDF 문서의 텍스트 및 표 데이터를 구조화
* PDF 좌표 정보를 활용한 위치 기반 데이터 추출 알고리즘 구현
* 표 / 문장 단위의 Chunking 방식 설계
* 표의 누락된 셀 및 구조 보완 로직 구현
* 표 제목 / 주석 / 단위 정보 매칭
* OpenAI Embedding 기반 벡터화
* ChromaDB 기반 Vector DB 구축
* 질문 기반 유사 문서 검색 구현
* 검색 결과의 유사 문서 중복 제거 로직 구현
* 검색 결과를 기반으로 한 LLM 답변 생성
* Streamlit 기반 RAG 챗봇 구현

### 핵심 기술적 기여

> **단순한 RAG 파이프라인 구축이 아니라, PDF의 문서 구조를 분석하여 검색에 적합한 데이터 형태로 변환하는 Chunking 알고리즘을 직접 설계·구현했습니다.**

이를 통해 PDF의 표와 문장을 의미 단위로 분리하고, 검색 과정에서 필요한 문맥을 최대한 보존할 수 있도록 데이터 전처리 구조를 개선했습니다.

---

## 09. Tech Stack

### Language

* Python

### PDF Processing

* pdfplumber

### Embedding

* OpenAI API
* `text-embedding-3-small`

### Vector Database

* ChromaDB

### LLM

* OpenAI API

### RAG / Framework

* LangChain

### Web UI

* Streamlit
