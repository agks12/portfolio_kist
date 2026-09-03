from sentence_transformers import SentenceTransformer
from collections import Counter
from chromadb import PersistentClient
from collections import defaultdict
import pandas as pd
import numpy as np
import re
import openai
from dotenv import load_dotenv
import os
import warnings
import logging
import pdfplumber
import time
import copy


logging.getLogger("pdfminer").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message="CropBox missing from /Page, defaulting to MediaBox")
warnings.filterwarnings(
    "ignore",
    message="The behavior of DataFrame concatenation with empty or all-NA entries is deprecated"
)
t_cnt=0

load_dotenv('api_key.env')
api_key = os.getenv('api_key')

# 품목 코드
crop_dict = {
    # 원예
    'VC': '엽근채소',
    'VS': '양념채소',
    'F': '과일',
    'FV': '과채',
    'VM': '버섯',
    # 축산
    'LK': '한육우',
    'LD': '젖소',
    'LH': '돼지',
    'LL': '산란계',
    'LC': '육계',
    'LO': '오리',
    'WL': '해외축산',
    # 곡물
    'GR': '쌀',
    'GB': '콩',
    'VPO': '감자',
    'WG': '국제곡물'
}

sub_crop_dict = {
    '엽근채소' : ['배추','무','당근','양배추'], # 엽근채소 감자는 예전에 있던거 곡물로 옮겨짐
    '양념채소' : ['건고추','마늘','양파','대파'], # 양념채소
    '과일': ['사과','배','감귤','포도','복숭아','수입과일','단감'], # 과일
    '과채': ['일반토마토','대추형방울토마토','딸기','청양계풋고추','일반풋고추','오이맛고추','파프리카(빨강)','애호박','백다다기오이','취청오이','참외','애호박','수박'], # 과채
    '버섯': ['느타리','양송이','새송이','팽이'] # 버섯
}

model = ''
collection_table = ''
collection_sentence = ''

# 임베딩 모델 설정 1번만 실행
def embedding_model_set(emb_model,save_path):
    global collection_table, collection_sentence
    # 임베딩 모델 설정
    client_path = f"{save_path}/{emb_model}"
    clean_name = emb_model.replace("/", "_")  # 또는 "-" 등으로 대체
    client = PersistentClient(path=client_path)
    # ✅ 1️⃣ 테이블용 폴더
    table_path = f"{save_path}/{clean_name}_table"
    client_table = PersistentClient(path=table_path)

    # ✅ 2️⃣ 문장용 폴더
    sentence_path = f"{save_path}/{clean_name}_sentence"
    client_sentence = PersistentClient(path=sentence_path)

    hnsw_config = {
        "hnsw": {
            "space": "cosine",  # 유클리디안 거리 (L2 distance)
            "ef_construction": 100,  # 인덱스 구축 시 효율성
            "ef_search": 100,  # 검색 시 효율성
            "max_neighbors": 16,  # 최대 이웃 수
            "resize_factor": 1.2,  # 인덱스 크기 조정 비율
            "sync_threshold": 1000  # 동기화 임계값
        }
    }

    metadata = {
        "description": "Embedding collection for model: " + clean_name,
        "embedding_model": emb_model
    }

    # collection 생성
    collection_table = client_table.get_or_create_collection(
        name=f"{clean_name}_table",
        metadata=metadata,  # metadata에는 간단한 값만 넣음
        configuration=hnsw_config  # configuration에 HNSW 설정 전달
    )

    collection_sentence = client_sentence.get_or_create_collection(
        name=f"{clean_name}_sentence",
        metadata=metadata,  # metadata에는 간단한 값만 넣음
        configuration=hnsw_config  # configuration에 HNSW 설정 전달
    )

metadata = {}
# 초기설정 파일 하나당 한번 적용
def file_set(file_path):
    global metadata

    # 파일 정보 설정
    with pdfplumber.open(file_path) as pdf: num_pages = len(pdf.pages)
    #file_name = (file_path.split('\\')[-1]).split('.pdf')[0]
    file_name = re.split(r'\.pdf$', file_path.split('\\')[-1], flags=re.IGNORECASE)[0] # 대소문자 구분없이

    file_state = 0

    try: # 성공하면 월보파일
        crop_code, ym = re.match(r"([A-Za-z]+)(\d+)", file_name).groups()

        if len(ym) == 4: ym = '20' + ym
        year = ym[0:4]
        month = ym[4:]

        crop_name = crop_dict[crop_code]
        metadata = {'연도': year, '월': month, '품목이름': crop_name,'자료구분':'관측월보'}
        print(f'파일 : {crop_name} {year}년 {month}월')
    except Exception as e: # 실패하면 월보형식 아닌파일들
        file_state = 1
        try:
            metadata = {'연도': file_name.split('_')[0],'자료구분':file_name.split('_')[1] , '품목이름': file_name.split('_')[2]}
            print(f"파일 이름 파싱 실패: {file_name} → {e}")
        except Exception as e: # 실패하면 월보형식 아닌파일들
            metadata = {'품목이름': '없음','자료구분':'없음'}


    return file_name, num_pages, file_state


# 표랑 텍스트 데이터프레임 추출
def set_pdfplumber(file_path,page_num, dtype, attribute1,attribute2):
    try:
        with pdfplumber.open(file_path) as pdf:
            page = pdf.pages[page_num]

            # 텍스트랑 표 속성달라서 getattr사용
            list_cr = getattr(page, dtype, None) # list_char = page.chars

            #print(list_cr[0])
            # DataFrame으로 변환
            df_cr = pd.DataFrame([
                {
                    'x0': d['x0'],
                    'x1': d['x1'],
                    'y0': d['top'],
                    'y1': d['bottom'],
                    'attribute1': d[f'{attribute1}'], # 텍스트와 표 다름
                    'attribute2': d[f'{attribute2}']  # 텍스트와 표 다름
                }
                for d in list_cr
            ])
        # 좌표는 음수가 존재할 수 없는데 어째서인지 존재하는거는 어차피 값 없으므로 제거
        df_cr = df_cr.loc[(df_cr['x0']>=3) & (df_cr['x1']>=0)]
        df_cr = df_cr.loc[abs(df_cr['y0'] - df_cr['y1']) < 500] # 칸 하나 높이가 500보다 큰건 말이 안됨
        df_cr = df_cr.loc[(abs(df_cr['y0'] - df_cr['y1']) < 180) & (abs(df_cr['x0'] - df_cr['x1']) < 210)] # 전망 23년 8개 사각형 제거하기

        df_cr['x0'] = df_cr['x0'].round(4)
        df_cr['x1'] = df_cr['x1'].round(4)
        df_cr['y0'] = df_cr['y0'].round(4)
        df_cr['y1'] = df_cr['y1'].round(4)
        df_cr['attribute1'] = df_cr['attribute1'].round(4)
        if dtype == 'rects':
            df_cr = df_cr[df_cr['attribute2'] > 5]  # 3보다 큰 행만 필터링 - 농업전망 파일에 표 높이작은거 많이 인식되는거 - 5로 변경
            df_cr['attribute2'] = df_cr['attribute2'].round(4)  # 소수점 4자리 반올림

        # 칼럼 이름 변경
        df_cr = df_cr.rename(columns={'attribute1':f'{attribute1}','attribute2':f'{attribute2}'})
        return df_cr
    except Exception as e:
        df_cr = pd.DataFrame(columns=['x0', 'x1', 'y0', 'y1', 'attribute1', 'attribute2'])
        df_cr = df_cr.rename(columns={'attribute1':f'{attribute1}','attribute2':f'{attribute2}'})
        print(f"Error occurred: {e}")
        return df_cr # 없으면 none가 아닌 그냥 빈 프레임 반환 => 다음 함수 실행에 none안됨


# 안보이는데 겹쳐진거 많이 인식되는거 제거 - gpt
def find_similar_rows(df, threshold):
    # 행 간의 차이를 계산
    diff_x0 = np.abs(df['x0'].values[:, None] - df['x0'].values)
    diff_x1 = np.abs(df['x1'].values[:, None] - df['x1'].values)
    diff_y0 = np.abs(df['y0'].values[:, None] - df['y0'].values)
    diff_y1 = np.abs(df['y1'].values[:, None] - df['y1'].values)

    # 임계값 이하인 차이만 True
    condition = (diff_x0 <= threshold) & (diff_x1 <= threshold) & (diff_y0 <= threshold) & (diff_y1 <= threshold)

    # 대각선(자기 자신과의 비교)은 제외
    np.fill_diagonal(condition, False)

    # 결과 반환
    return condition
def overlap_remove(result):
    df = result

    df.reset_index(drop=True, inplace=True) # 이전에 필터링으로 인덱스 빈것들 존재 drop쓸 때 행 번호랑 인덱스랑 일치해야함

    # 차이가 작은 기준을 정한다 - 중요 1 과 2 차이로 만들어지고 없어지고 함
    threshold = 2  # x0, x1, y0, y1의 차이가 이 값 이하인 것들만 찾기

    # 비슷한 row들의 인덱스를 찾아냄
    similar_rows = find_similar_rows(df, threshold)

    # 유사한 행들을 제거하기 위해, 유사한 행들의 인덱스를 추출
    rows_to_remove = set()

    # 유사한 행들의 인덱스 찾기
    for i in range(len(similar_rows)):
        similar_indices = np.where(similar_rows[i])[0]  # 현재 row와 비슷한 행들의 인덱스
        rows_to_remove.update(similar_indices)  # 유사한 행들의 인덱스를 집합에 추가

    # 유사한 행을 제외한 DataFrame 생성
    df_cleaned = df.drop(rows_to_remove)

    return df_cleaned

# 서브타이틀 찾기
def find_subtitle(result_text_df):
    upper = result_text_df[(result_text_df['y0']<100) & (result_text_df['size']>10)] # 한글 pdf로 변환하면 글자 크기 작아짐
    if upper.empty:
        return None, None
    else:
        # 공백 특수문자 제거
        sub_title = ''.join(upper['text'])
        sub_title = re.sub(r'[^가-힣a-zA-Z0-9\s,]', '', sub_title) # 컴마 공백 제외 특수문자제거

        matched_items = [item for item in sub_crop_dict[metadata['품목이름']] if item in sub_title] # metadata['품목이름']

        if matched_items:
            sub_crops = '.'.join(matched_items) # 서브타이틀에 품목 있으면 모두 출력
            duplicate_test = ''.join(matched_items)
            if sub_title == duplicate_test:
                sub_title = ''
        else:
            sub_crops = metadata['품목이름']

        return sub_title,sub_crops #


# 세부 품목 이름 정의
sub_crop_name = ''
def set_sub_crop_name(result_text_df,page_num):
    global sub_crop_name
    max_size = result_text_df['size'].max()
    result_size_max = result_text_df.loc[result_text_df['size'] == max_size]

    sub_title, sub_crops = find_subtitle(result_text_df)

    if sub_title is None:
        print(f'{page_num + 1}page crop_name: {sub_crops}')
        return

    # if len(result_size_max) > 10: # 품목이름 10자 이상 없음
    #     print(f'{page_num + 1}page crop_name: {sub_crop_name}', end='')
    #     return
    #
    #
    # # 공백 특수문자 제거
    # text = ''.join(result_size_max['text'])
    # text = re.sub(r'\s+', '', text)
    # text = re.sub(r'[^가-힣a-zA-Z0-9]', '', text)
    #
    # if any(item in text for item in sub_crop_dict[metadata['품목이름']]):
    #     # 지금 추출한 단어가 품목에 해당될 때
    #     sub_crop_name = text
    # else: sub_crop_name = metadata['품목이름']


    metadata['부제목'] = sub_title
    metadata['세부품목이름'] = sub_crops
    print(f'{page_num+1}page crop_name: {sub_crops}', end='')

# 1차로 표 만드는 기본적인 틀 잡기 dfs로 y 좌표를 기준으로 연속된 행들을 그룹화
# y값을 기준으로 서로 이어지도록 연결, 약간의 오차도 허용
def set_table_framing(group_row):
    # 표의 각 행을 y0, y1 값으로 그룹화.
    # 이어지는 행들을 DFS 방식으로 찾아서 하나의 표로 묶음.

    # 표를 구분할 수 있는 최소/최대 y0, y1 값을 계산하여 표의 범위를 확정.
    # 해당 표를 좌표 정보와 크기로 구분하여 table_dict에 저장.

    # y0,y1으로 묶은 다음에 키값보고 연속적인 거 묶으면 됨

    rect_row_group_key_list = list(group_row.groups.keys())  # 키값(row)연속된 흐름찾기

    rect_row_group_key = sorted(rect_row_group_key_list, key=lambda x: x[0])  # 첫번쨰튜플(y0)로 정렬

    visited = [0] * len(rect_row_group_key)  # 방문 체크

    group_list = []  # 이어진거 있는 rect_row_group_key의 인덱스를 저장할 리스트

    def rect_row_dfs(key, add_list):
        now_y1 = key[1]
        now_y0 = key[0]
        # y1이 리스트 0 에 있나 y0가 리스트 1에 있나 같음
        current_group = group_row.get_group(key)

        current_x0 = current_group['x0'].min()
        current_x1 = current_group['x1'].max()
        # now_idx = rect_row_group_key.index(key) # 방문 체크 위한인덱스 추출
        # 방문한적 있으면 return인데 여기서 할 필요 없음 어차피 함수 사용하기 전에 검사하므로

        matching_keys = [
            mkey for mkey in rect_row_group_key if
            abs(mkey[0] - now_y1) <= 3 and  # y0 차이가 3 이하
            group_row.get_group(mkey)['x0'].min() <= current_x1 and  # 다음 그룹의 x0가 현재 그룹의 x1보다 작아야 함
            group_row.get_group(mkey)['x1'].max() >= current_x0  # 다음 그룹의 x1이 현재 그룹의 x1보다 커야 함
        ]        # 오차를 제외하더라도 20 11월 1페이지 2번째 표보면 약간 떨어지면서 생긴 표 있음
        # 표가 웬만해선 가까이 없을테니까 10 정도는 하나로 봐도 될듯

        # 찾은키 모두에 대해 방문한적 없는지 검사 / 분할되어 2개 있는 경우도 있음 / 방문 안하면 1에서 마지막 행까지 표 만들고 다시 2에서 마지막, 3에서..됨
        for match_key in matching_keys:
            now_idx = rect_row_group_key.index(match_key)
            if visited[now_idx] == 0:  # 방문한적 없으면서 이어진 경우 /
                # 연결됨
                # print('연결됨',now_idx,'시도하는 키',key,'  이건매치키',match_key,add_list)
                add_list.append(now_idx)
                visited[now_idx] = 1  # 방문설정
                rect_row_dfs(match_key, add_list)
        # 리턴없어도 됨 어차피 리스트에 저장하고 그 리스트를 함수 끝나면 다른 리스트에 저장

    for idx, nkey in enumerate(rect_row_group_key):
        if visited[idx] == 1:  # 이미 사용된거 볼 필요 없음
            continue
        add_list = []  # 함수 하나하나에서 저장할 리스트
        add_list.append(idx)  # 지금거 저장
        visited[idx] = 1
        rect_row_dfs(nkey, add_list)
        #if len(add_list) == 1 and add_list[0] == idx:  # 지금거만 있는 경우 - 0929에 수정 칼럼만 있는 한줄 짜리 통과시키기 위해 주석처리
        #    continue  # 없으면 다음으로
        # print(idx,'함수하나 끝났다',add_list)

        ny_max = 0
        ny_min = 21e8
        nx_max = 0
        nx_min = 21e8
        # 칼럼이 구분되어 있는 경우 방문체크되서 인식못하므로 add_list에서 최대 최소에 속하는 키 값을 넣어야함
        # 지금 구해진 표 리스트에서 y0,y1최대 최소 구하기
        for nindex in add_list:
            now_y0 = rect_row_group_key[nindex][0]
            now_y1 = rect_row_group_key[nindex][1]

            now_x0 = group_row.get_group((now_y0, now_y1))['x0'].min()
            now_x1 = group_row.get_group((now_y0, now_y1))['x1'].max()

            if now_x0 < nx_min:
                nx_min = now_x0
            if now_x1 > nx_max:
                nx_max = now_x1
            if now_y0 < ny_min:
                ny_min = now_y0
            if now_y1 > ny_max:
                ny_max = now_y1

        # 위에서 구한 최대최소 범위에 속하는 키값 있는지 확인하기
        # - 202003 11 페이지 기상지표 표에서 구분 빠진거 넣는 부분
        # - y 값으로 표 나눌때 생육지표 다음 마늘양파로 분류되는 오류 해결하기
        for idx, ntup in enumerate(rect_row_group_key):
            # 이미 들어가있는거 제외 - nkey로 계산된 표에서
            if idx in add_list:
                continue
            now_y0 = rect_row_group_key[idx][0]
            now_y1 = rect_row_group_key[idx][1]
            if now_y0 >= ny_min and now_y1 <= ny_max and group_row.get_group((now_y0, now_y1))['x0'].min()-10 <= nx_max and group_row.get_group((now_y0, now_y1))['x1'].max()+10 >= nx_min : # 포함됨
                visited[idx] = 1 # 0930에 추가 원래 있어야 됨 없으면 중복된거 생김
                add_list.append(idx)  # 전체사각형인 경우 안에 있는 모든 거 포함되게 됨 - 아래서 제거
        # 위 for 구문이 표인데 인식안되고 칼럼 인덱스만 있는거 범위로 다 가져오는거 할 수 있게 최대 최소 범위 구하는거
        group_list.append(add_list)
    return rect_row_group_key, group_list


# 1차로 테이블 시작키값으로 가진 모든 행을 저장하는 딕셔너리 테이블
def set_table_1st(group_row, rect_row_group_key,group_list):
    table_dict = {}
    for nl in group_list:
        # nl 에 있는 키 모두 합치기
        m_df = pd.DataFrame()
        for ne in nl:
            now_key = rect_row_group_key[ne]  # 현재 그룹의 키값
            m_df = pd.concat([m_df, group_row.get_group(now_key)], ignore_index=True)
        # 딕셔너리 키 정해야함 표 좌하단,우상단 좌표 및 길이,높이
        min_x, max_x, min_y, max_y = m_df['x0'].min().round(4), m_df['x1'].max().round(4), m_df['y0'].min().round(4), \
        m_df['y1'].max().round(4)
        width = (max_x - min_x).round(4)
        height = (max_y - min_y).round(4)
        table_dict[min_x, max_x, min_y, max_y, width, height] = m_df
    # 위에서 추출된 테이블 딕셔너리에서 칼럼과 인덱스만 있고 값이 없는 부분을 채우는 거
    # 존재하는거 의 좌상단 우하단의 좌표를 기준으로 안에 있는거 완성시킴
    return table_dict


# 아래 2개는 set_table_2st에 사용되는 함수
# 같은데 오차때문에 2개 생긴거 제거
def remove_diff(t_list):
    return_list = []
    #print(len(t_list),t_list)

    if len(t_list)==0:return t_list
    t_list = sorted(t_list)  # reverse=True)
    return_list.append(t_list[0])
    for idx in range(len(t_list) - 1):
        if abs(t_list[idx] - t_list[idx + 1]) > 2:
            return_list.append(t_list[idx + 1])
        else:
            continue
    return return_list

# 새로만든 표 생성
def make_sub_table(x_list, y_list, vdf):

    new_table = pd.DataFrame()

    # 0922추가 - 2305 9페이지 값에 여러개차지하는 표 나눠서 텍스트 매칭하려는거
    tolerance = 1  # 허용 오차
    tar_v_text = vdf # 표 전체 복사
    include_store = set() # 저장 여러개 차지하는 칸 저장

    for idy, ny in enumerate(y_list):
        if idy == 0: continue # 기존 or idy == 1로 칼럼은 제외했었는데 0925 농업전망 하면서 칼럼도 만들어줌
        # 지금 y값 오차고려 선택 # 지금 행 값들만 추출
        tar_v = vdf.loc[(vdf['y1'] >= ny - 2) & (vdf['y1'] <= ny + 2), ['x0', 'x1', 'y0', 'y1','width','height']]

        # 여기 오면 없는거라서 만들어주기 - 지금 now_max값이 x 시작이고 x_list에 있는 만큼 생성
        for idx, nx in enumerate(x_list):
            if idx==0 or idx==1:continue # 처음거 해당할 수 없음

            # 새로운 행 추가 (기존 테이블에)
            new_row = {
                'x0': x_list[idx - 1],
                'x1': x_list[idx],
                'y0': y_list[idy - 1],
                'y1': y_list[idy],
                'width': abs(x_list[idx] - x_list[idx - 1]),  # x1 - x0
                'height': abs(y_list[idy] - y_list[idy - 1])  # y1 - y0
            }

            # new_row와 동일한 값이 tar_v에 존재하는지 확인 # 0929에 1->1.5로 변경 칼럼만 있는거 생성하는 과정에서(이거 때문인지는 확실x) 오차? 1 넘어감
            row_exists = tar_v[
                (abs(tar_v['x0'] - new_row['x0']) < 1.5) &
                (abs(tar_v['x1'] - new_row['x1']) < 1.5) &
                (abs(tar_v['y0'] - new_row['y0']) < 1.5) &
                (abs(tar_v['y1'] - new_row['y1']) < 1.5) &
                (abs(tar_v['width'] - new_row['width']) < 1.5) &
                (abs(tar_v['height'] - new_row['height']) < 1.5)
                ]

            # 칸 여러개 차지하는거 찾기
            row_include = tar_v_text[
                (tar_v_text['x0'] <= new_row['x0'] + tolerance) &
                (tar_v_text['x1'] >= new_row['x1'] - tolerance) &
                (tar_v_text['y0'] <= new_row['y0'] + tolerance) &
                (tar_v_text['y1'] >= new_row['y1'] - tolerance) &
                (tar_v_text['width'] >= new_row['width'] - tolerance) &
                (tar_v_text['height'] >= new_row['height'] - tolerance)
            ]


            # 칼럼, 인덱스 제외한 모든 테이블 생성하는데 이미 있는거면 버려야함
            if not row_exists.empty: continue

            if not row_include.empty:  # 여기 조건 걸리면 지금 만든 칸(new_row)은 row_include의 text씀 - 포함관계
                now_v = [row_include['x0'].iloc[0],
                         row_include['x1'].iloc[0],
                         row_include['y0'].iloc[0],
                         row_include['y1'].iloc[0],
                         row_include['text'].iloc[0]]
                include_store.add(tuple(now_v))
            # 텍스트 적용
            for i in include_store:
                x0, x1, y0, y1, t = i
                if (x0 <= new_row['x0'] + tolerance) and (x1 >= new_row['x1']- tolerance) and (y0 <= new_row['y0']+ tolerance) and (y1 >= new_row['y1']- tolerance):
                    new_row['text'] = t


            # DataFrame에 새로운 행 추가
            new_table = pd.concat([new_table, pd.DataFrame([new_row])], ignore_index=True)
    return new_table, include_store

# 같은데 2개 생긴거 제거하고 set_table_1st 로 만들어진 딕셔너리 테이블 각각 순회하면서 실제 테이블 구조처럼 만듬
def set_table_2nd(table_dict,state_list):
    for index,(key,vdf) in enumerate(table_dict.items()):

        grouped = group_by_difference(list(set(list(vdf['y0'].unique()) + list(vdf['y1'].unique()))), threshold=7)
        # print(i[1])
        for group in grouped:
            if len(group) <= 1:
                continue
            v, *rest = group  # 첫 번째 값과 나머지를 나눔
            vdf.loc[vdf['y0'].isin(rest), 'y0'] = v

        # grouped = group_by_difference(list(i[1]['y1']), threshold=4)

        for group in grouped:
            if len(group) <= 1:
                continue
            v, *rest = group  # 첫 번째 값과 나머지를 나눔
            vdf.loc[vdf['y1'].isin(rest), 'y1'] = v
        vdf['height'] = vdf['y1'] - vdf['y0']  # 이거 까지 세트임

        # 구분 칼럼아래 y값들 가져오는데 x값 다르면 못가져와서 통일시키기
        grouped = group_by_difference(list(set(list(vdf['x0'].unique()) + list(vdf['x1'].unique()))), threshold=1)
        for group in grouped:
            if len(group) <= 1:
                continue
            v, *rest = group  # 첫 번째 값과 나머지를 나눔
            vdf.loc[vdf['x0'].isin(rest), 'x0'] = v

        for group in grouped:
            if len(group) <= 1:
                continue
            v, *rest = group  # 첫 번째 값과 나머지를 나눔
            vdf.loc[vdf['x1'].isin(rest), 'x1'] = v
        vdf['width'] = vdf['x1'] - vdf['x0']  # 이거 까지 세트임


        now_state = state_list[index]

        x_set = set((list(vdf['x0']) + list(vdf['x1']))) # x0,x1 에서의 고유값들
        y_set = set((list(vdf['y0']) + list(vdf['y1']))) # x0,x1 에서의 고유값들

        if now_state==1: # 오직 칼럼만 있는거는 전체에서 x,y쓰지 않고 인덱스것만 사용함
            x_item = list(x_set)
            x_item.sort()
            y0_index = vdf.loc[(vdf['x0'] == x_item[0]) & (vdf['x1'] == x_item[1])]
            y_set = set((list(y0_index['y0']) + list(y0_index['y1'])))  # x0,x1 에서의 고유값들

        x_list = remove_diff(x_set)
        y_list = remove_diff(y_set)
        new_table, include_store = make_sub_table(x_list, y_list, vdf)

        #원본 표에서 여러칸 차지하는것들 제거하기
        for i in include_store:
            x0, x1, y0, y1, t = i
            table_dict[key] = table_dict[key][~(
                    (table_dict[key]['x0'] == x0) &
                    (table_dict[key]['x1'] == x1) &
                    (table_dict[key]['y0'] == y0) &
                    (table_dict[key]['y1'] == y1)
            )]

        # new_table 원래 table_dict에 추가하기
        table_dict[key] = pd.concat([table_dict[key], new_table], ignore_index=True)
    return table_dict


def is_valid_code(s: str) -> bool:
    #pattern = re.compile(r'^VC(19|20)\d{2}(0[1-9]|1[0-2])$')
    #pattern.match(s))
    #return bool(re.match(r'^[A-Za-z]{2}(19|20)\d{2}(0[1-9]|1[0-2])$', s))
    return bool(re.match(r'^[A-Za-z]', s))
# 위에서 만든 표 테이블양식에 텍스트 집어넣기
def set_match_text(file_name,rect_text, table_dict, state):
    _is_month = is_valid_code(file_name) # 월보인지 전망인지에 따라 tolerance조절
    tolerance = 1  # 허용 오차 # 워드인거는 2로 설정
    if _is_month:tolerance+=1
    #print(tolerance)
    # 2405 10 페이지 표안에 그림 있는거 없애기 위한 리스트
    remove_key = []
    for i,vdf in table_dict.items():
        # df테이블 전체로 찾는거는 없는거 예외 할 수 없어서 일일이 검사하기
        # 머지도 완전 일치하지 않으므로 사용 불가
        flag=0
        for idx,row in vdf.iterrows():
            text_df = rect_text.loc[
            (rect_text['x0']+tolerance > row['x0']) &
            (rect_text['x1']-tolerance < row['x1']) &
            (rect_text['y0']+tolerance > row['y0']) &
            (rect_text['y1']-tolerance < row['y1'])
            ].copy()

            # 2번째 텍스트 매치에서만 적용
            if state==1: # 0번째에는 text성분 없어서 동시에 조건 걸면 안됨
                if pd.notna(row['text']) :continue # 2번째 텍스트 매치할 때는 기존에 있는값 넘기지 않으면 이중칼럼 적용 초기화됨

            if len(set(text_df['y0'])) > 4:flag = 1 # 표 안에 그림 있으면 y축 값 때문에 y0 고유값 많음 이걸로 판별

            # 1행에 1글자라 텍스트 모두 합쳐야함() 순서상관있으므로 정렬
            text_df = text_df.sort_values(by=['y0', 'x0'], ascending=[True, True])

            # 이상한거 처들어오는거 막기 - 0908에 추가 2가지 중 하나 칼럼에 투명값 들어가는거 처리 - 제일 처음 겹쳐있는 글 표 제거해서 이거 필요없음
            if state==0 and len(set(text_df['y0'])) == 2:
                sub_group_text = text_df.groupby(['y0', 'size'])
                for group_idx, group_value in sub_group_text:
                    # 표 중앙 x 값
                    row_center = row['x0'] + ((row['x1'] - row['x0']) / 2)
                    # 지금 텍스트 그룹 중앙값
                    text_center = group_value['x0'].min() + ((group_value['x1'].max() - group_value['x0'].min()) / 2)
                    # 차이 5보다 크면 이상하게 치우쳐 있는거라고 판단
                    if abs(row_center - text_center) > 5:
                        text_df = text_df[~((text_df['y0'] == group_idx[0]) & (text_df['size'] == group_idx[1]))] # 제거


            join_text = ''.join(text_df['text'])# 테이블 행 문자열로 합치기
            table_dict[i].at[idx, 'text'] = join_text # dict의 테이블에 새로운 칼럼에 text추가

        if flag == 1:
            remove_key.append(i)
            continue

        # 정렬하기 행, 칼럼 순으로
        table_dict[i] = table_dict[i].sort_values(by=['x0'],ascending=[True]) # 이거 y0도 했었는데 오차 때문에 순서 이상해짐

    # 그림있는 표 삭제
    for key in remove_key:
        table_dict.pop(key)

    return table_dict


# multi_column_conversion 함수에 사용되는 함수
def div_cr_merge(rc, norc, st, end, p_table):
    # rc로 x,y인지 구분함
    # print(st,end)
    # 먼저 구분에 속하는 칼럼이나 row 찾기
    check_t = p_table.loc[(p_table[f'{rc}0'] + 1 >= st) & (p_table[f'{rc}1'] - 1 <= end)]
    check_t = check_t.sort_values([f'{norc}0'])  # 정렬
    check_t = check_t.iloc[1:]  # 첫 번째 행 삭제 인덱스 정렬안되서 drop안씀

    # print(check_t)
    unique_xy = sorted(check_t[f'{norc}0'].unique())  # , reverse=True) # 불연속 적인 y,x 값들

    # 포함된 행열 합친거 저장할 테이블
    new_rc_t = pd.DataFrame(columns=['x0', 'x1', 'y0', 'y1', 'width', 'height', 'text'])

    # 포함된 행열 찾고 합치기
    for index, xy0 in enumerate(unique_xy):
        one_can = check_t.loc[(check_t[f'{norc}0'] == xy0) | (
                    (check_t[f'{norc}0'] + 1 < xy0) & (check_t[f'{norc}1'] - 1 > xy0))]  # 약간의 오차때매 포함되서 1보완
        # print(xy0,one_can)
        one_text = '_'.join(one_can['text'])  # 포함된 행열 합치기
        # print(one_text)

        rc_min = one_can[f'{rc}0'].min()  # x1 이거나 y1의 최소값 항상 고정
        rc_max = one_can[f'{rc}1'].max()  # x1 이거나 y1의 최대값 항상 고정
        norc_min = unique_xy[index]

        if index + 1 == len(unique_xy):
            norc_max = one_can[f'{norc}1'].max()
        else:
            norc_max = unique_xy[index + 1]

        # 0925추가 원래 잘못된거였는데 발견해서 수정 - 이거 안하면 가로 칼럼 너비랑 높이 바꿔서 들어감
        width = rc_max-rc_min
        height = norc_max-norc_min
        if rc=='y':
            height = rc_max-rc_min
            width = norc_max-norc_min

        # 새로운 통합 칼럼
        new_row = {f'{rc}0': rc_min,
                   f'{rc}1': rc_max,
                   f'{norc}0': norc_min,
                   f'{norc}1': norc_max,
                   'text': one_text,
                   'width': width,
                   'height': height
                   }
        # 새로운 테이블에 추가
        new_rc_t.loc[len(new_rc_t)] = new_row

    return new_rc_t, check_t

# 오차 고려 y0값으로 텍스트 그룹화
def group_by_difference(nums, threshold=2):
    if not nums:
        return []

    nums = sorted(nums)  # 정렬해야 적용가능 순차적으로 비교
    groups = []
    current_group = [nums[0]]

    for i in range(1, len(nums)):
        if abs(nums[i] - current_group[-1]) <= threshold:  # 지금거랑 전거 비교
            current_group.append(nums[i])  # 오차 내면 같은그룹에
        else:
            groups.append(current_group)  # 오차 벗어나면 그룹 끝내고 새 그룹 시작 최소값이라 시작값
            current_group = [nums[i]]

    groups.append(current_group)
    return groups

def multi_column_conversion(table_match_text):
    # 무조건 세로 첫번째는 구분값이 아닐 수 있음 202108pdf, 9페이지
    renew_table_dict = {}
    for index,(idx, val) in enumerate(table_match_text.items()):
        now_table = val

        # 여기 오차 그룹화 수정하는거 추가
        ny0 = now_table['y0'].unique()
        # print(tt)
        grouped = group_by_difference(list(ny0), threshold=1)
        for group in grouped:
            if len(group) <= 1:
                continue
            v, *rest = group  # 첫 번째 값과 나머지를 나눔
            now_table.loc[now_table['y0'].isin(rest), 'y0'] = v

        ny1 = now_table['y1'].unique()
        # print(tt)
        grouped = group_by_difference(list(ny1), threshold=1)
        for group in grouped:
            if len(group) <= 1:
                continue
            v, *rest = group  # 첫 번째 값과 나머지를 나눔
            now_table.loc[now_table['y1'].isin(rest), 'y1'] = v


        # 구분표 좌표 키값에서 x0,y0이 좌상단 좌표 # y는 위에서 0 시작이므로 y0 가 좌상단
        k_x0 = idx[0]
        k_y0 = idx[2]
        # 구분 표 추출
        result_t = now_table.loc[(now_table['x0'] == k_x0) & (now_table['y0'] == k_y0)]

        if len(result_t) != 1:
            # 비어있음
            #print(idx, '비어있거나 2개 이상')
            continue
        else:
            first_row = result_t.iloc[0]  # 첫 번째 행 (Series 타입)

        x_st = first_row['x0']  # row 구분 x 시작
        x_end = first_row['x1']  # row 구분 x 시작
        y_st = first_row['y0']  # row 구분 x 시작
        y_end = first_row['y1']  # row 구분 x 시작
        # print(val)
        # 함수로 포함관계 합치기

        new_rc_x, origin_rc_x = div_cr_merge('x', 'y', x_st, x_end, val)  # 처음 2개 파라미터 적용할 방향, 적용안할 방향
        new_rc_y, origin_rc_y = div_cr_merge('y', 'x', y_st, y_end, val)

        # 기존테이블에 기존칼럼제거하고 포함관계거 넣기

        # 일치하는 행 제거 (origin_rc_x 기준) 새로운거 추가 x에 대해
        cols_x = origin_rc_x.columns.tolist()
        val_copy = val.copy()
        val_copy = val_copy.merge(origin_rc_x[cols_x], on=cols_x, how='left', indicator=True)
        val_copy = val_copy[val_copy['_merge'] == 'left_only'].drop(columns=['_merge'])
        val_copy = pd.concat([val_copy, new_rc_x])  # 새롭게 포함하는거 만든 행 추가

        # 일치하는 행 제거 (origin_rc_x 기준) 새로운거 추가 y에 대해
        cols_y = origin_rc_y.columns.tolist()
        val_copy = val_copy.merge(origin_rc_y[cols_y], on=cols_y, how='left', indicator=True)
        val_copy = val_copy[val_copy['_merge'] == 'left_only'].drop(columns=['_merge'])
        val_copy = pd.concat([val_copy, new_rc_y])  # 새롭게 포함하는거 만든 행 추가

        # 정렬 후 인덱스 재배치
        val_copy = val_copy.sort_values(['y0', 'x0']).reset_index(drop=True)

        # 구분 칼럼 분할되는거 막기 위해 y값 통일
        # 기준값 저장
        base_y0 = val_copy.loc[0, 'y0']
        base_y1 = val_copy.loc[0, 'y1']
        base_height = base_y1 - base_y0

        # 조건 설정
        condition = (val_copy['y0'] >= base_y0) & (val_copy['y1'] <= base_y1)

        # 조건을 만족하는 행들의 y0, y1, height 변경
        val_copy.loc[condition, 'y0'] = base_y0
        val_copy.loc[condition, 'y1'] = base_y1
        val_copy.loc[condition, 'height'] = base_height

        table_match_text[idx] = val_copy
        renew_table_dict[idx] = val_copy

    return renew_table_dict


# 오직 칼럼만 인식된 표들 아래 찾기
def make_only_col_table(multi_col_table_dict,result_text_df):
    multi_col_table_dict_copy = multi_col_table_dict.copy() # 원본 변경해야되서 복사본 생성
    state_list = []

    for key,n_table in multi_col_table_dict_copy.items():

        # 칼럼, 인덱스 다 있는거 수정할 필요 없음 넘김
        check_only_col = group_by_difference(list(n_table['y0']),threshold=2)
        if len(check_only_col) > 1:
            state_list.append(0)
            continue

        now_col_center = n_table.iloc[0] # 테이블 칼럼의 첫번째  '구분' 만 가져오기 - 인덱스 칼럼
        now_col_center = now_col_center['x1'] - (now_col_center['x1'] - now_col_center['x0']) / 2
        n_table['x_center'] = now_col_center # 인덱스 칼럼 중심 좌표

        # 인덱스 칼럼 시작 y값 얻기 위한 추출 - 텍스트 테이블에서 지금 칸 아래 좌표로 매칭함
        index_col_first_value = result_text_df.loc[(result_text_df['x0'] >  n_table['x0'].iloc[0]-1 ) &
            (result_text_df['x1'] <  n_table['x1'].iloc[0]+1 ) &
            (result_text_df['y0'] >  n_table['y1'].iloc[0]-1 ) &
            (result_text_df['y1'] <  n_table['y1'].iloc[0]+ n_table['height'].iloc[0]+30)
            ]

        if index_col_first_value.empty:
            state_list.append(0)
            continue

        text_size = index_col_first_value['size'].iloc[0] # 생성하는 칸 사이즈 설정하기 위한 값
        pre_y0 = n_table['y1'].iloc[0] # 시작 , 이전 y0값



        # 1022추가 2107-10페이지 표 아래까지 인식하는거 개선
        st_y0 = n_table.iloc[0, 2]
        st_y1 = n_table.iloc[0, 3]

        col_list = n_table.loc[(n_table['y0'] == st_y0) & (n_table['y1'] == st_y1)]
        x0_list_uni = col_list['x0'].unique()
        x1_list_uni = col_list['x1'].unique()
        y1_list_uni = col_list['y1'].unique()

        x_key_zip = list(zip(x0_list_uni, x1_list_uni))

        y1_st = y1_list_uni[0]

        max_y1 = -1
        last_index_y = -1

        for xkey in x_key_zip:
            col_s = result_text_df.loc[(result_text_df['x0'] > xkey[0] - 1) &
                            (result_text_df['x1'] < xkey[1] + 1) &
                            (result_text_df['y0'] > y1_st)]
            col_s = col_s.loc[col_s['size'] == text_size]

            y_uni = col_s['y0'].unique()
            y_uni.sort()

            # 이상한거 없이 아래 아무것도 없으면 체크 안되서 마지막값 써야함
            if len(y_uni)!=0: # 정상적인거는 이거 없음
                if y_uni[-1] > last_index_y:
                    last_index_y = y_uni[-1]

            for idy in range(1, len(y_uni)):  # indp가 1부터 시작하도록 변경
                if abs(y_uni[idy] - y_uni[idy - 1]) > 40:
                    max_y1 = y_uni[idy - 1]
                    break
        if max_y1==-1:max_y1=last_index_y

        for idx,col in n_table.iterrows(): # 테이블 한 칼럼 씩 순회

            # 지금 칼럼 x 범위 및 y아래 존재하는거 모두 가져옴
            find_table_text = result_text_df.loc[(result_text_df['x0'] >  col['x0']-1 ) &
                (result_text_df['x1'] <  col['x1']+1 ) &
                (result_text_df['y0'] >  pre_y0) & (result_text_df['y0'] <=  max_y1+1) & (result_text_df['size']==text_size)]

            # find_table_text = find_table_text.loc[find_table_text['size'] == text_size] # 위에서 구한 후보군들중 제거할 기준이 필요한데 글자 크기 다르면 제외함 - 시작점부터 제거해야할듯
            # find_table_text = find_table_text.sort_values('y0')  # 정렬된 DataFrame을 다시 저장
            #
            # for line_loc in range(1, len(find_table_text)):  # 표 글자크기 같은 그룹에서 순차적으로 계산해서 멀리 떨어져 있으면 다른표 -> 200에서 100으로 변경
            #     if abs(find_table_text.iloc[line_loc]['y0'] - find_table_text.iloc[line_loc - 1]['y0']) > 150:
            #         find_table_text = find_table_text.iloc[:line_loc]
            #         break
            find_table_text = find_table_text.sort_index() # 다시 인덱스로 정렬안하면 글자 순서 이상해짐

            # y0으로 그룹화 할 때 오차고려하기 위해 만든 함수로 그룹화 하고 오차 수정된거 테이블에 다시 적용
            y0_list = find_table_text['y0'].unique()
            grouped = group_by_difference(list(y0_list), threshold=2)
            for group in grouped:
                if len(group) <= 1:
                    continue
                v, *rest = group  # 첫 번째 값과 나머지를 나눔
                find_table_text.loc[find_table_text['y0'].isin(rest), 'y0'] = v
            table_group_y0 = find_table_text.groupby('y0')


            # 칸에 있는 여러 글자 텍스트 합쳐서 단어로 만들고 새로운 테이블 행 정보로 저장
            x_center_list = []
            for group_key, group_value in table_group_y0:
                # 여기 한칸임
                # 비어있는거 처리할 수 있나
                # 존재하는거 기준으로 상하좌표로 새로만들어서 없는거는 안만들어짐
                # 증감률 정상범위 벗어나는거 처리
                size = group_value['size'].iloc[0]

                # 인덱스 칼럼에 대해서 세로로 있는 줄 한 단어로 만드는 처리
                if idx==0:
                    value_copy = group_value
                    split_list = []
                    check_index = 0

                    for line_idx in range(1, len(value_copy)):  # indp가 1부터 시작하도록 변경
                        if abs(value_copy.iloc[line_idx]['x0'] - value_copy.iloc[line_idx - 1]['x1']) > 5: # 분리된 단어 찾기
                            n_split = value_copy.iloc[check_index:line_idx]
                            check_index = line_idx
                            split_list.append(n_split)
                    split_list.append(value_copy.iloc[check_index:])
                        # split_list에 x 분할된거 들어감 각각루프돌기 x 센터만 달라짐 다른건 같고
                    for split_table in split_list:

                        now_word_center_x = split_table['x1'].iloc[-1] - (split_table['x1'].iloc[-1] - split_table['x0'].iloc[0]) / 2
                        x_center_list.append(now_word_center_x)
                        renew_x0 = col['x0']
                        renew_x1 = col['x1']
                        renew_y0 = split_table['y0'].iloc[0] - size / 2
                        renew_y1 = split_table['y1'].iloc[-1] + size / 2
                        width = renew_x1 - renew_x0
                        join_text = ''.join(split_table['text'])

                        n_table.loc[len(n_table)] = [renew_x0, renew_x1, renew_y0, renew_y1, width, renew_y1 - renew_y0,join_text, now_word_center_x]  # now_word_center_x칼럼 새로 추가
                    continue


                now_word_center_x = group_value['x1'].iloc[-1] - (group_value['x1'].iloc[-1] - group_value['x0'].iloc[0]) / 2
                x_center_list.append(now_word_center_x)
                renew_x0 = col['x0']
                renew_x1 = col['x1']
                renew_y0 = group_value['y0'].iloc[0] - size/2
                renew_y1 = group_value['y1'].iloc[-1] + size/2
                width = renew_x1 - renew_x0

                join_text = ''.join(group_value['text'])

                n_table.loc[len(n_table)] = [renew_x0, renew_x1, renew_y0, renew_y1, width, renew_y1-renew_y0, join_text,now_word_center_x] # now_word_center_x칼럼 새로 추가

            # 새로 추가한 x_center_list 오차 고려 그룹화 후 적용
            grouped = group_by_difference(list(x_center_list), threshold=2)
            for group in grouped:
                if len(group) <= 1:
                    continue
                v, *rest = group  # 첫 번째 값과 나머지를 나눔
                n_table.loc[n_table['x_center'].isin(rest), 'x_center'] = v

            if idx > 0: continue # 여기 위는 없는 칸 만드는 과정이라 테이블 전체 다 하지만 여기부터는 다중인덱스 처리부분이라 인덱스만 처리 idx==0이 인덱스 부분


        # 인덱스 칼럼만 추출 - x_center로 그룹
        index_columns = n_table
        index_columns = index_columns.loc[(index_columns['x0'] == index_columns.iloc[0]['x0']) & (index_columns['x1'] == index_columns.iloc[0]['x1'])]
        index_columns = index_columns.sort_values('y0')
        index_columns = index_columns.groupby('x_center')

        new_table = n_table

        for ic_idx, ic_val in index_columns:
            split_list2 = []
            check_index = 0

            for ic_val_idx in range(1, len(ic_val)):  # ic_val_idx 1부터 시작하도록 변경

                if ic_val.iloc[ic_val_idx]['y0'] - ic_val.iloc[ic_val_idx - 1]['y1'] > 3:  # 일단 다른 칸 분리 기존 5에서 24년 표 23때문에 3으로 변경
                    n_split = ic_val.iloc[check_index:ic_val_idx]
                    check_index = ic_val_idx
                    split_list2.append(n_split)
            split_list2.append(ic_val.iloc[check_index:])

            for n_word in split_list2:

                merge_index_set = set()
                for idx_word in range(1, len(n_word)):  # ic_val_idx 1부터 시작하도록 변경
                    if n_word.iloc[idx_word]['y0'] - n_word.iloc[idx_word - 1]['y1'] < -5.6:  # 일단 다른 칸 분리 - 이거 5일때 실제 세로 한줄아닌데 한줄로 인식하는 경우 있음 -5.5루 변경
                        merge_index_set.add(n_word.index[idx_word])
                        merge_index_set.add(n_word.index[idx_word - 1])

                # ch_list가 없으면 합칠거 없음 합칠거 인덱스 리스트저장
                if len(list(merge_index_set)) == 0: continue

                # 기존 테이블에서 아래 인덱스행들 제거하고 새로 하나 추가
                merge_index_set = sorted(list(merge_index_set))

                multi_row = n_word.loc[merge_index_set]

                new_table = new_table.drop(merge_index_set)

                rw_x0 = multi_row.iloc[0]['x0']
                rw_x1 = multi_row.iloc[0]['x1']
                rw_y0 = multi_row['y0'].min()
                rw_y1 = multi_row['y1'].max()
                rw_width = multi_row.iloc[0]['width']
                rw_height = rw_y1 - rw_y0
                rw_x_center = multi_row.iloc[0]['x_center']
                re_text = ''.join(multi_row['text'])

                new_table.loc[len(new_table)] = [rw_x0, rw_x1, rw_y0, rw_y1, rw_width, rw_height, re_text, rw_x_center]

        pairs = list(zip(new_table['x0'].unique(), new_table['x1'].unique()))

        max_index = -21e8
        for idx_pair, pair in enumerate(pairs):
            if idx_pair == 0: continue
            nx0 = pair[0]
            nx1 = pair[1]

            len_row = len(new_table.loc[(new_table['x0'] == nx0) & (new_table['x1'] == nx1)])
            if len_row > max_index:
                max_index = len_row

        max_index -= 1  # 칼럼 뺴기

        # 이제 이 max_index만큼 상위 하위 x_center, height 뽑아서 인덱스 다중처리
        index_x0 = pairs[0][0]
        index_x1 = pairs[0][1]

        only_index = new_table.loc[(new_table['x0'] == index_x0) & (new_table['x1'] == index_x1)]

        ## 칸 높이 재설정해야함 글자크기 기준이라 넓은거는 칸 그만큼 범위로 안되있음
        if max_index != len(only_index) - 1:  # 다중칼럼있는 경우만 다중처리하기

            ## 칸 설정해야함 글자기준이라 넓은데 글자 별로 없으면 칸 범위만큼 생성안됨

            only_index = only_index.drop(0)  # 구분 칼럼 제거 -

            top_x_center_rows = only_index.nlargest(max_index, 'x_center')  # 남을 index들 max_index 칼럼개수 만큼 차례로 추출

            # 제외한 나머지 행만 추출
            remaining_rows = only_index.drop(top_x_center_rows.index)  # 다중 앞에 적용되고 버려질거

            # 하나씩 보면서 remaining_rows이 테이블에서 합쳐질거 찾아서 합치기
            for index_n, value_t in top_x_center_rows.iterrows():
                n_y0 = value_t['y0']
                n_y1 = value_t['y1']

                cc = remaining_rows.loc[
                    ((remaining_rows['y0'] < n_y0 - 3) & (remaining_rows['y1'] > n_y1 + 3)) |
                    ((remaining_rows['y0'] < n_y1 - 4) & (remaining_rows['y1'] > n_y1 + 4)) |
                    ((remaining_rows['y1'] > n_y0 + 4) & (remaining_rows['y0'] < n_y0 - 4))]
                cc = cc.sort_values('x_center')
                multi_index = '_'.join(cc['text']) + '_' + value_t['text']

                new_table.loc[index_n, 'text'] = multi_index  # 수정 업데이트

            new_table = new_table.drop(remaining_rows.index)



        # y0 , y1 값 오차 없애고 통일하기 위해 그룹화 함수 사용
        grouped = group_by_difference(list(new_table['y0']) + list(new_table['y1']), threshold=7) # 4로 했는데 안 합쳐지는거 있었음 7로 수정
        #print(n_table)
        for group in grouped:
            if len(group) <= 1:
                continue
            v, *rest = group  # 첫 번째 값과 나머지를 나눔
            new_table.loc[new_table['y0'].isin(rest), 'y0'] = v
        #grouped = group_by_difference(list(n_table['y1']), threshold=4)
        for group in grouped:
            if len(group) <= 1:
                continue
            v, *rest = group  # 첫 번째 값과 나머지를 나눔
            new_table.loc[new_table['y1'].isin(rest), 'y1'] = v

        #print(n_table)
        new_table['height'] = new_table['y1'] - new_table['y0']

        # 새로 만든 칸들 새로 업데이트 할 때 키값 x,y,w,h정보 변경된거로 업데이트
        table_x0 = new_table['x0'].min()
        table_x1 = new_table['x1'].max()
        table_y0 = new_table['y0'].min()
        table_y1 = new_table['y1'].max()
        table_width = table_x1 - table_x0
        table_height = table_y1 - table_y0

        new_key = (table_x0, table_x1, table_y0, table_y1, table_width, table_height) # 새로운 키 값

        multi_col_table_dict[key] = new_table

        multi_col_table_dict[new_key] = multi_col_table_dict.pop(key)
        #print(new_table)
        state_list.append(1)

    return multi_col_table_dict,state_list


# 표 비어있거나 칼럼이 공백이거나 인덱스만 있는데 공백이라 값 있어서 비어있는거 인식못하는  표 아닌 경우들 제거
def is_visually_empty(df):
    if df.shape[0] == 0 or df.shape[1] == 0:
        return True  # 행/열 0개

    if all(str(col).strip() == '' for col in df.columns):
        return True  # 컬럼명이 전부 공백

    # 모든 값이 공백 또는 NaN일 경우
    values = df.values.astype(str)
    stripped_values = np.char.strip(values)
    if np.all((stripped_values == '') | pd.isna(df.values)):
        return True

    return False

# 표 최종 결과물
def get_final_table(multi_col_table_dict):
    # pd 테이블로 출력
    result_table_dict = {}
    for idx, val in multi_col_table_dict.items():
        flag = 0

        #### 0724에 수정 2105 3페이지 표 오차때문에 그룹화 못하는거 처리
        val['y0_rounded'] = val['y0'].round(1)  # 소수점 1자리 반올림 - 오차 때문에 안묶기는 경우 있음
        group_std_y0 = val.groupby('y0_rounded')

        ##### 0829에 추가 2405 10 페이지 5월 가격전망처럼 칼럼 1열인데 이중인 경우
        # y값으로 그룹화한거
        group_cnt = group_std_y0.size().reset_index(name="count")
        line1_cnt = group_cnt['count'][0]

        if len(group_cnt) == 1: continue  # 칼럼만 사각형으로 인식해서(병합 후) 1줄만 있는거 존재 group_cnt['count'][1]이거 하면 오류남 어차피 칼럼만 있으면 의미 없으므로 버림

        line2_cnt = group_cnt['count'][1]

        # 칼럼을 1번 열의 개수만큼 늘려야함
        if line1_cnt != line2_cnt:
            line1_val = val.iloc[0:line1_cnt]  # 2행부터 6행까지, 7은
            line2_val = val.iloc[line1_cnt:line1_cnt + line2_cnt]  # 2행부터 6행까지, 7은

            # 칼럼을 1번 열의 개수만큼 늘려야함
            line2_val = line2_val[['x0', 'x1']]
            diff = line1_val.merge(line2_val, on=['x0'], how='right')
            diff = diff.drop(columns=['x1_x'])
            diff = diff.rename(columns={'x1_y': 'x1'})
            diff = diff.sort_values(by='x0', ascending=True)
            diff = diff.ffill()
            key_ = diff['y0_rounded'][0]
            # 기존 그룹 삭제
            val = val[val['y0_rounded'] != key_].copy()
            # diff 추가
            val = pd.concat([val, diff], ignore_index=True)
            group_std_y0 = val.groupby('y0_rounded')
        #######################################################


        table_pd = pd.DataFrame()

        index_col = ''

        # 하나의 그룹은 하나의 행
        # 행 검사에서 x축 값이 이어져 있지 않으면 표 아닌걸로 간주
        for i, (y0_val, group) in enumerate(group_std_y0):

            if i == 0:
                index_col = group['text'].iloc[0]
                table_pd = pd.DataFrame(columns=group['text'].tolist())
                continue
            try:
                # 열 개수 안 맞으면 에러 발생 → except로 넘어감
                table_pd.loc[len(table_pd)] = group['text'].tolist()
            except ValueError as e:
                # 여기서 테이블 아닌것들 판단할 수 있나
                # 열 개수 안맞는 표 있을 수도 - 없다고 가정
                #print(f"[{idx}] {i}번째 그룹 추가 실패 (열 개수 불일치):", e)
                flag = 1
                break
                # continue
        if flag == 1:
            continue

        if is_visually_empty(table_pd): continue  # 표 아닌거 제거

        # 인덱스 설정
        if index_col in table_pd.columns:
            table_pd = table_pd.set_index(index_col)

        # table_pd.to_excel(f'{idx}.xlsx')
        table_pd = table_pd[~(table_pd == '').all(axis=1)]

        # 빈 테이블 쓸모없음
        if table_pd.empty:continue

        result_table_dict[idx] = table_pd
    return result_table_dict


# 가까이 있는거 하나의 테이블로 만들기
def closed_merge_table(result_final_table):
    copy_in_table = copy.deepcopy(result_final_table)
    sorted_dict = dict(sorted(result_final_table.items(), key=lambda item: item[0][2]))
    merge_table_list = [] # 합칠 테이블 키값 리스트로 저장

    pre_y1 = 0
    pre_key = 1
    add_list = set()

    try:
        for idx, (key, value) in enumerate(sorted_dict.items()):

            #print(key[2],key[3])
            if idx == 0:
                pre_key = key
                pre_y1 = key[3]  # 수정: i[3] → i[2] (기준값이 3번째 값이면)
                continue

            if abs(pre_y1 - key[2]) < 10: # 거리 10이하면 같은 표
                add_list.add(key)
                add_list.add(pre_key)
            else:
                if len(add_list)==0:
                    pre_y1 = key[3]
                    pre_key = key
                    continue
                # 현재 그룹 저장
                merge_table_list.append(list(add_list))
                # 새 그룹 시작
                add_list = set()
            pre_key= key
            pre_y1 = key[3]  # 다음 비교를 위한 값 업데이트
        # 루프 후 마지막 그룹이 남아 있으면 추가
        if add_list:
            merge_table_list.append(sorted(list(add_list)))

        # 합칠 테이블 합치고 키 제거 키 갱신
        if len(merge_table_list)!=0:
            merge_table_list[0].sort(key=lambda x: x[2]) # 정렬 무조건 첫번째 칼럼 따름

        for group in merge_table_list:
            frames = []
            # 해당 그룹의 DataFrame들을 frames 리스트에 모은다.

            key_x0 = group[0][0]
            key_x1 = group[0][1]
            min_y0 = 21e8
            max_y1 = -21e8
            key_width = group[0][4]
            key_height = 0
            for idx in group:
                # 여기 idx가 키 하나

                df = result_final_table[idx]

                df = df.reset_index(drop=False)  # 인덱스 초기화
                frames.append(df)

                if idx[2] < min_y0:
                    min_y0 = idx[2]

                if idx[3] > max_y1:
                    max_y1 = idx[3]
            for idx in group:
                # 딕셔너리에서 특정 키를 삭제
                try:
                    del result_final_table[idx]
                except Exception as e:
                    # 오류가 발생했을 때 처리할 코드
                    print(f" 테이블 키 없음: {e}")


            # frames 리스트에 담긴 DataFrame들을 하나로 합친다.
            columns_first = frames[0].columns
            df_first = pd.DataFrame(frames[0], columns=columns_first)

            dfs = []
            for i, data in enumerate(frames):
                if i == 0:
                    dfs.append(df_first)
                else:
                    data_col = list(data.columns)
                    # 리스트를 데이터프레임으로 만들 때 컬럼명 지정
                    new_row_df = pd.DataFrame([data_col], columns=columns_first)
                    data.columns = columns_first
                    df = pd.concat([new_row_df, data], ignore_index=True)
                    dfs.append(df)

            # 모두 concat
            merge_table = pd.concat(dfs, ignore_index=True)


            # merge_table = pd.concat(frames, ignore_index=True)  # ignore_index=True로 새 인덱스 지정
            # merge_table = merge_table.reset_index(drop=True)
            key_height = max_y1 - min_y0

            group_key = (key_x0, key_x1, min_y0, max_y1, key_width, key_height)

            # 합친 결과를 딕셔너리에 다시 추가
            result_final_table[group_key] = merge_table

        return result_final_table
    except Exception as e:
        print(f'근접 테이블 병합 실패{e}')
        return copy_in_table

# 표에 사용된 텍스트 제거
def remove_table_text(result_final_table,result_text_df):
    keys = result_final_table.keys()
    for nkey in keys:
        n_x0 = nkey[0]
        n_x1 = nkey[1]
        n_y0 = nkey[2]
        n_y1 = nkey[3]

        # 표 범위 텍스트 제거
        result_text_df = result_text_df.loc[~((result_text_df['x0'] >= n_x0) &
                                              (result_text_df['x1'] <= n_x1) &
                                              (result_text_df['y0'] >= n_y0) &
                                              (result_text_df['y1'] <= n_y1))]

    return result_text_df

# 텍스트 추출 함수 시작
def text_group_split_check_sub1(group_df_sort,split_index_list,error_list):
    pre_x1 = 21e8  # 시작값은 x0보다 커야됨
    pre_x0 = 21e8
    for row in group_df_sort.itertuples():  # iterrows보다 빠름
        now_x0 = row.x0
        now_x1 = row.x1

        #### 0710에 추가
        # 202003 9페이지 농▶업 인 경우 처리
        # 64.4619   75.8594  176.8642  189.3642    농  12.5
        # 64.9469   69.1906  176.8642  189.3642    ▶  12.5
        # 75.3744   86.7719  176.8642  189.3642    업  12.5
        if now_x0 > pre_x0 and now_x1 < pre_x1:
            # 새로운 행 추가 (기존 테이블에)
            new_row = {
                'x0': now_x0,
                'x1': now_x1,
                'y0': row.y0,
                'y1': row.y1,
                'text': row.text,
                'size': row.size
            }
            # DataFrame에 새로운 행 추가
            error_list = pd.concat([error_list, pd.DataFrame([new_row])], ignore_index=True)
        #################################################################################

        # now_x0 -1 > pre_x1 이거 약간 떨어진 경우도 있어서 1의 오차 추가 # 1넘는경우 있어서 1.5로 변경 -> 다시 3로 변경 -> 다시 12로 변경
        if now_x0 - 12 > pre_x1:  # 지금 문자 시작점이 이전 문자 끝 값보다 크면(크기만 하면 되나 얼마나 떨어진지 상관있을텐데) 다른 줄임
            # 끊어짐
            split_index_list.append(row.Index - 1)  # 분할할 인덱스 저장
        pre_x1 = row.x1  # 이어졌으면 순차적으로 진행하기 위해 저장
        pre_x0 = row.x0
    # 하나의 그룹 검사끝, 딕셔너리에 저장하기
    return group_df_sort,split_index_list,error_list

def text_group_split_check_sub2(text_split_dict,group_df_sort,split_index_list,error_list,y0_value):

    st_index = 0
    for now_index in split_index_list:  # 마지막거 안들어감
        now_df = group_df_sort.iloc[st_index:now_index + 1, :]

        ### 0710에 추가
        # error_list를 돌면서 now_df에서 동일한 행을 제거
        for _, e_row in error_list.iterrows():
            condition = (
                    (now_df['x0'] == e_row['x0']) &
                    (now_df['x1'] == e_row['x1']) &
                    (now_df['y0'] == e_row['y0']) &
                    (now_df['y1'] == e_row['y1']) &
                    (now_df['text'] == e_row['text']) &
                    (now_df['size'] == e_row['size'])
            )
            # 조건에 맞는 행 제거
            now_df = now_df.loc[~condition]
        now_df = now_df.reset_index(drop=True)

        # 시작 한글 나올때 까지 계속 제거
        if not re.search(r'[A-Za-z가-힣0-9]', now_df.loc[0, 'text']) or now_df.loc[0, 'text'] == ' ':
            while len(now_df) > 0:
                text_val = now_df.loc[0, 'text']

                # 한글/영어 없거나 공백이면 제거
                if not re.search(r'[A-Za-z가-힣0-9]', text_val) or text_val.strip() == '':
                    now_df = now_df.drop(index=0).reset_index(drop=True)
                else:
                    break  # 조건 안 맞으면 탈출
        if len(now_df) == 0: continue

        text_split_dict[(now_df.iloc[0]['x0'], now_df['x1'].iloc[-1], y0_value[0], y0_value[1])] = now_df
        # print(now_df)
        st_index = now_index + 1
    return text_split_dict

# 위 그룹에서 그룹만들 y0값들 변경
def y0_coherence(grouped_diff,origin_text):
    for group in grouped_diff:
        if len(group) <= 1:
            continue
        v, *rest = group  # 첫 번째 값과 나머지를 나눔
        origin_text.loc[origin_text['y0'].isin(rest), 'y0'] = v
    return origin_text

# 같은 그룹(같은 y값)이여도 다른 문단인 경우 분리 하는 함수 및 에러(농▶업 같은거 분리 되는거 막기)
def text_group_split_check(grouped):
    text_split_dict = {} # sub2_text_group_split_check 함수에서 계속 채워짐
    for y0_value, group_df in grouped:
        # 각 y0 size 그룹에서 한줄 아니면 나눠야 됨

        # 끊어진 부분 구분할 인덱스
        split_index_list = []

        # x0기준으로 정렬
        group_df_sort = group_df.sort_values('x0')

        # 인덱스 1부터 시작하게 하기
        group_df_sort.index = range(0, len(group_df_sort))

        # 순차적으로 있는지 즉 한줄 인지 검사
        error_list = pd.DataFrame()# 0710에 추가

        group_df_sort,split_index_list,error_list = text_group_split_check_sub1(group_df_sort,split_index_list,error_list)

        split_index_list.append(len(group_df_sort) - 1)

        text_split_dict = text_group_split_check_sub2(text_split_dict,group_df_sort,split_index_list,error_list,y0_value)

    return text_split_dict

# 한 단어로 된 각각을 한줄로 묶음 같은 y값과 x값 오차 범위내 존재 및 사이즈 동일 조건
def one_word_merge_oneline(text_split_dict):
    keys = list(text_split_dict.keys())
    for i, key1 in enumerate(keys):
        x0_1 = key1[0]
        y0_1 = key1[2]
        size1 = key1[3]
        for j, key2 in enumerate(keys):
            if i == j:  # <= 하면 안됨 순서가 어떤거 부터 시작 하는지가 중요 모든 경우 다 해봐야함
                continue  # 같은 항목 비교하지 않기
            x1_2 = key2[1]
            y0_2 = key2[2]
            size2 = key2[3]
            # print(size1,size2,'\n')
            if key1 in text_split_dict and key2 in text_split_dict:  # i<j 인 경우 제외 안해서 ab에서 제거된거 ba에서 할려면 오류나는데 체크하기
                if x0_1 == x1_2 and size1 == size2 and abs(y0_1 - y0_2) < 1:
                    merge_df = pd.concat([text_split_dict[key2], text_split_dict[key1]], axis=0)  # y다른데 한줄인거 합치기

                    # y다른 2개 한줄로 합친거 추가했으므로 기존 2개 없애야함 지금 바로 없애야 다음 거 찾을때 중복 안됨
                    # i<j 인거  contunue해서 나중에 해도 될듯
                    del text_split_dict[key1]
                    del text_split_dict[key2]

                    min_x0 = merge_df['x0'].min()
                    max_x1 = merge_df['x1'].max()
                    min_y0 = merge_df['y0'].min()
                    max_y1 = merge_df['y1'].max()
                    merge_df = merge_df.reset_index(drop=True)

                    merge_df['y0'] = min_y0  # 값
                    merge_df['y1'] = max_y1  # 마찬가지

                    # my_dict에 합쳐진거 추가
                    text_split_dict[min_x0, max_x1, min_y0, size1] = merge_df
                    # print('머지된거',merge_df)
    return text_split_dict

# set_sentence_history_matrix함수의 기본값 세팅
def set_sentence_history_matrix_sub(key_list):
    grouped_by_size = defaultdict(list) # defaultdict 사용해서 size 기준으로 묶기

    for x0, x1, y0, size in key_list:
        grouped_by_size[size].append((x0, x1, y0, size))

    size_list = grouped_by_size.keys()

    # 줄 제일 많이 갖고 있는애 (y0값) 찾기
    max_len = 0
    for i in size_list:
        if len(grouped_by_size[i]) > max_len:
            max_len = len(grouped_by_size[i])

    # 칼럼이 size값이고 각 size에서 행에 들어가는 번호가 다음줄에 해당
    history_matrix = pd.DataFrame(0, index=range(max_len), columns=size_list)
    # 12.5 12.0 ..
    #   1    nan
    #   2     2
    #  위처럼 되있느면 12.5 사이즈인거 0,1번 인덱스 한줄
    return grouped_by_size,history_matrix,max_len,size_list


def set_sentence_history_matrix(key_list,result_final_table):
    # 여기 루프에 들어가서 검사하는 애들은 1문단 될 수 도 있는 애들
    # 사이즈가 같으면서 y값이 차이가 안나는애들을 같은 문단이라고 봄 그래서 y0값과 size를 변수로
    # 무조건 사이즈 기준으로 구분해서 사이즈 다르면 한 문단 될 수 없음

    grouped_by_size,history_matrix,max_len,size_list = set_sentence_history_matrix_sub(key_list)

    # 1027 워드 to pdf후 추가
    table_y0_elements = [key[2] for key in result_final_table.keys()]
    for size, group in grouped_by_size.items():
        target_size = size * 2  # 지금 글자 사이즈 = size
        len_group = len(group) - 1  # 개수

        group.sort(key=lambda x: x[2])  # 원본 리스트를 정렬 / 아래 재귀에서 탐색할때 grouped_by_size에서 찾는데 순서로 찾으므로 순서 같아야함

        sorted_data = group
        # 4 번  n개의 루프가 있고 각 루프는 n-1씩 감소
        for i in range(len_group):  # n 번 돔  #

            # 곱할거 선택
            row_target = sorted_data[i][2]  # y값
            row_target_x0 = sorted_data[i][0]  # x값
            row_target_x1 = sorted_data[i][1]  # x값
            # 워드 pdf로 변환한다음 추가한 부분 표 위에 위치한거는 이어지지 않음
            table_flag = 0
            for vars in table_y0_elements:
                if abs(row_target - vars) < 20:
                    table_flag = 1
                    break
            if table_flag == 1: continue
            # 앞에있는 모든거랑 곱하기 i개 만큼
            for j in range(len_group - i):  # n-1...번 반복
                # 타겟이랑 차례차례 앞에 있는 거랑 곱하기

                # 곱해질 거
                target_re = sorted_data[1 + i + j][2]
                target_re_x0 = sorted_data[1 + i + j][0]
                target_re_x1 = sorted_data[1 + i + j][1]




                # 한문단인지 검사
                # y거리차이 사이즈2배 이하이면서 x시작위치는 위 줄 끝 보다 앞이면서 x 끝위치는 위줄 시작보다 뒤에 있어야함
                if ((abs(row_target - target_re) <= target_size) and (row_target_x1 >= target_re_x0) and (
                        row_target_x0 <= target_re_x1)):
                    # 여기 오면 한문단
                    history_matrix.loc[i, size] = 1 + i + j  # i가 지금 선택된 타겟이면서 행번호
                    break
                    # 이거 제일 마지막거 선택됨 y0가 10인 상태에서 거리가20이하인거 1개 아니라 여러개면 제일 먼거 선택됨 첫번쨔거만 하려고 break

    history_matrix.sort_index(inplace=True)
    return history_matrix,grouped_by_size,max_len,size_list


# dfs_history_matrix의 dfs
def dfs_history_matrix_sub(i,col,check_list,grouped_by_size,history_matrix,visited):
    #print(i,col,grouped_by_size[col])
    check_list.append(grouped_by_size[col][i])
    visited.loc[i,col] = -1
    if history_matrix.loc[history_matrix.loc[i,col],col] == 0:
        check_list.append(grouped_by_size[col][history_matrix.loc[i,col]])
        visited.loc[history_matrix.loc[i,col],col] = -1
        #print('반환전 마지막\n',check_list)
        return check_list
    return dfs_history_matrix_sub(history_matrix.loc[i,col], col, check_list,grouped_by_size,history_matrix,visited)

# 위에서 만든 history_matrix에 저장된 문장성분 잇기
def dfs_history_matrix(history_matrix,grouped_by_size,max_len,size_list):
    visited = history_matrix.copy() # 테이블 틀 복사
    visited.loc[:, :] = 0 # 모든 셀  값 0으로
    result_line_text = []
    for col in size_list:
        for i in range(max_len):
            if history_matrix.loc[i, col] == 0 or visited.loc[i, col] == -1:
                continue
            check_list = []
            return_list = dfs_history_matrix_sub(i, col, check_list,grouped_by_size,history_matrix,visited)
            # print('반환후 처흠\n 지금 행 번호는',i,return_list)
            if return_list is None or len(return_list) == 0:
                continue
            result_line_text.append(return_list)
    return result_line_text

# 2줄이상의 문단 추출
def get_final_sentence(result_line_text,text_oneline_dict):
    under10size = {}  # 표의 출처 주석 저장하기 위한
    result_word_list = []  # 최종 문장 저장

    for now_key_list in result_line_text:
        flag = 0
        flag_anno = 0 # 주석긴거는 제일 처음줄 y값을 키로 사용해야됨 - 이걸로 처음거만 선택
        size10key = ''

        now_context = ''
        for now_key in now_key_list:
            now_text_df = text_oneline_dict[now_key]
            now_text_df.sort_values('x0')
            if now_key[3] <= 10 and flag_anno==0:  # 표에 단위 매치할려고 위에서 필터링한거 없애서 여기에 적용
                size10key = now_key
                flag = 1
                flag_anno = 1
            #    break
            sub_str = ' '  # 문단 이어붙일때 구분 하기위한 공백추가
            sub_str += ''.join(now_text_df['text'])

            now_context += sub_str
        now_context = now_context.replace("▶", " ")  # 공백대체 2020년3월1페이지의 경우
        now_context = now_context.replace("■", " ")  # 공백대체 2020년3월1페이지의 경우

        now_context = now_context.lstrip()  # 제일 앞 공백 제거
        if flag == 1:
            under10size[size10key] = now_context
            continue

        if len(now_context) < 10:  # 짧은거는 문장 아닐 가능성 높으므로 버림
            continue
        result_word_list.append(now_context)

        #print(now_context)
        # with open("output.txt", "a", encoding="utf-8") as f:
        #     f.write(now_context + "\n")  # 각 문단 뒤에 줄 바꿈 추가
    return under10size,result_word_list

# 한줄 텍스트  - 표 제목 추출
def get_final_oneline(result_line_text,text_oneline_dict):
    # 표 제목 찾기 위한 딕셔너리
    # 한줄인것들은 모두 표 제목으로만 사용
    result_oneline_dict = {}

    # result_line_text 리스트 1차로 만들기
    one_list = []
    for sub_list in result_line_text:
        for value in sub_list:
            one_list.append(value)

    for key, value in text_oneline_dict.items():
        if key in one_list: continue  # 위에서 문단 만드는데 사용한 단어 버리기
        # 길이가 1이거나 띄어쓰기 없는거는 줄로 안치고 단어인경우라 없애도 될듯?
        # result_str = re.sub(r"[^가-힣a-zA-Z0-9\s\(\)]", "", result_str)    # 특수기호 제거
        result_str = ''.join(value['text'])  # 테이블 행 문자열로 합치기
        result_str = result_str.replace("▶", " ")
        result_str = result_str.replace("■", " ")
        result_str = result_str.lstrip()  # 앞에 공백제거
        result_oneline_dict[key] = result_str

        #print(result_str)
    return result_oneline_dict


# 표 제목과 단위 매칭하기
def table_title_unit_match(result_table_dict,result_oneline_dict):
    # 최종 표 테이블 제목, 단위 매칭하기 -
    sorted_items = sorted(result_oneline_dict.items(), key=lambda item: (item[0][2], item[0][3]), reverse=True)
    result_oneline_dict_des = dict(sorted_items)
    #print(result_oneline_dict)
    match_title_table = []

    # 제목 단위 매칭 표 위에있음 / 한줄텍스트에서 추출
    for table_key, value in result_table_dict.items():  # 표 하나씩 순회
        now_table_y0 = table_key[2]
        unit = ''
        flag=0
        for text_key, text_value in result_oneline_dict_des.items():  # 각 표에 대해 텍스트 하나씩 검사
            now_text_y0 = text_key[2]
            # x 조건도 걸어야 함
            if now_table_y0 > now_text_y0:  # 표 위에 처음 등장하는 한줄
                # 0829에 추가 - 표 제목 없는 경우도 있음 이전까지는 위에 처음 등장하는거 해서 제목아닌것들도 추출됨 하지만 이런게 제외라기 위해 거리 제한 넣기
                #print(text_value)
                #print('너무멈222222222', now_table_y0, now_text_y0, table_key)

                if abs(now_table_y0 - now_text_y0) > 38: # 36에서 38로 수정 전망 22년 부록 표 5
                    #print('너무멈',now_table_y0,now_text_y0,table_key)
                    text_value = ''
                #------------------
                if text_key[1] < table_key[0] or text_key[0] > table_key[1]:  # 텍스트의 x 끝값이 테이블의 시작값보다 전에 있으면 버림 or 텍스트 x의 시작값이 테이블의 끝값 보다 뒤에 있으면 버림
                    continue
                if text_value[0:2] == '단위':  # 단위인 경우
                    unit = text_value
                    continue
                match_title_table.append({'title': text_value, 'table': value, 'unit': unit, 'annotation': ''})
                flag=1
                break  # 발견하면 바로 끝

        if flag == 1: continue # 제목 없는것들은 위 루프 안돌아서 테이블 추가 안됨 그래서 임의로 넣기
        match_title_table.append({'title': '', 'table': value, 'unit': unit, 'annotation': ''})

    return match_title_table


# 자료 및 출처 매치
def table_annotation_match(result_table_dict,result_oneline_dict,match_title_table,under10size):
    # 자료 / 주석 매칭
    add_result_oneline_dict_under10size = result_oneline_dict.copy()
    add_result_oneline_dict_under10size.update(under10size)

    # 정렬
    #sorted_items = sorted(add_result_oneline_dict_under10size.items(), key=lambda item: item[0][2])
    sorted_items = sorted(result_oneline_dict.items(), key=lambda item: (item[0][2], item[0][3]), reverse=True) # y값 같은 경우 글자크기 큰거 우선 - 21년 전망 표번호 - 제목 y같은데 크기 다름

    result_oneline_dict_asc = dict(sorted_items)

    remove_key_list = set() # 중복 제거하기 위해 set

    for table_key, value in result_table_dict.items():  # 표 하나씩 순회
        now_table_y1 = table_key[3]
        for text_key, text_value in result_oneline_dict_asc.items():  # 각 표에 대해 텍스트 하나씩 검사
            now_text_y0 = text_key[2]
            # x 조건도 걸어야 함
            if now_table_y1 < now_text_y0:  # 표 아래에 처음 등장하는 한줄
                if text_key[1] < table_key[0] or text_key[0] > table_key[1]:  # 텍스트의 x 끝값이 테이블의 시작값보다 전에 있으면 버림
                    continue
                if abs(now_table_y1 - now_text_y0) > 35:  # 너무 멀리 떨어진거는 자료주석아님
                    continue
                if text_key[3] > 10:continue # 출처 주석은 글씨 크기 작음 큰거 필터링
                for item in match_title_table:
                    if value.equals(item['table']):
                        item['annotation'] = text_value
                        remove_key_list.add(text_key) # 삭제할 키값들 저장 # 바로 삭제하면 동일 키 가진거 다음턴에 오류
                break  # 발견하면 바로 끝

    for r_key in remove_key_list:
        del add_result_oneline_dict_under10size[r_key]

    return match_title_table, add_result_oneline_dict_under10size


# 10이하 사이즈 글에서 필요한 정보 분류 - gpt
def count_types_in_string(text):
    # 정규 표현식으로 숫자, 특수문자, 한글을 각각 찾기
    numbers = re.findall(r'\d', text)  # 숫자
    special_chars = re.findall(r'[^\w\s]', text)  # 특수문자
    hangul = re.findall(r'[가-힣]', text)  # 한글

    # Counter로 각 개수 세기
    counts = Counter({
        '숫자': len(numbers) ,
        '특수문자':+ len(special_chars),
        '한글': len(hangul)
    })

    return counts

# 크기 10 이하인것들중 주석 출처 제외하고 쓸만한 정보 추출
def get_under10size_word(under10size,text_len):

    add_word_list = []

    for key,text in under10size.items():
        counts = count_types_in_string(text)
        if len(text)>text_len and counts['한글'] > counts['숫자']:
            add_word_list.append(text)

    return add_word_list

# 최종 텍스트에서 숫자 많은거 제거
def remove_num_word(result_word_list,text_len):
    add_word_list = []

    for text in result_word_list:
        counts = count_types_in_string(text)
        if len(text)>text_len and counts['한글'] > counts['숫자']:
            add_word_list.append(text)

    return add_word_list
# db저장
def db_format_request_table(docs,embeds,meta,ids):
    try:
        collection_table.add(
            documents=docs,
            embeddings=embeds,
            metadatas=meta,
            ids=ids
        )
        #print("Documents successfully inserted into the database.")
    except Exception as e:
        print(f"Error occurred: {e}")
def db_format_request_sentence(docs,embeds,meta,ids):
    try:
        collection_sentence.add(
            documents=docs,
            embeddings=embeds,
            metadatas=meta,
            ids=ids
        )
        #print("Documents successfully inserted into the database.")
    except Exception as e:
        print(f"Error occurred: {e}")

token = 0

api_client = openai.OpenAI(api_key=api_key)  # ← API 키를 여기 넣으세요
def openai_embedding_fn(texts):
    response = api_client.embeddings.create(
        model="text-embedding-3-small",  # 예: "text-embedding-3-small"
        input=texts
    )
    return [d.embedding for d in response.data]

# 표,텍스트 포맷후 request
table_cnt = 0
text_cnt = 0
model = SentenceTransformer('intfloat/multilingual-e5-base')

def db_format_request_agri_report(result_word_list,match_title_annotation_table,page_num):
    global table_cnt,text_cnt, token
    page_table_cnt = 0
    page_text_cnt = 0

    try:
        now_crop = metadata['품목이름'] if metadata['품목이름'] == metadata['세부품목이름'] else metadata['품목이름'] + ' ' + metadata['세부품목이름']
    except:
        now_crop = metadata['품목이름']

    data_info = f"[{metadata['연도']}년 {metadata['월']}월 전망 {now_crop}]"# \n{metadata['부제목']}"

    #표 데이터
    for tidx, item in enumerate(match_title_annotation_table):
        # 표를 마크다운 형식으로 변환
        table_md = item['table'].to_markdown()

        # 제목과 표 결합
        #full_markdown = f"{data_info}\n\n{item['title']}\n\n{table_md}\n\n{item['unit']}\n{item['annotation']}"
        full_markdown = f"{item['title']}\n\n{table_md}\n\n{item['unit']}\n{item['annotation']}" # 이걸로 수정

        token +=len(full_markdown)# token계산하기 위한 글자수 세기
        #embeds = model.encode(full_markdown)
        #embeds = openai_embedding_fn(f"{data_info}\n\n{item['title']}\n\n{table_md}") # 마크다운 형식 안하기
        str_em = f"{data_info}\n\n{item['title']}\n\n{table_md}"
        embeds = model.encode(str_em)

        #embeds = embeds / np.linalg.norm(embeds) # 거리계산할 때  코사인 , 내적에서는 필요 어차피 정규화된거 출력됨

        metadata['제목'] = item['title']
        metadata['단위'] = item['unit']
        metadata['출처'] = item['annotation']
        metadata['타입'] = '표'
        ids = metadata['품목이름'] + metadata['연도'] + metadata['월'] + str(page_num) + 'table' + str(tidx)

        db_format_request_table(full_markdown, embeds, metadata, ids)
        page_table_cnt += 1

    metadata['제목'] = ''  # 널값 불가
    metadata['단위'] = ''
    metadata['출처'] = ''
    metadata['타입'] = '문자'

    #텍스트 데이터
    for widx, word in enumerate(result_word_list):
        if len(word) <= 20:continue
        #embeds = model.encode(word)

        #word_em = f'{data_info}\n\n{word}'
        word_em = f'{word}' # 이걸로 수정

        #embeds = openai_embedding_fn(word_em)
        embeds = model.encode(word)

        token +=len(word)# token계산하기 위한 글자수 세기
        #embeds = embeds / np.linalg.norm(embeds) # 정규화
        ids = metadata['품목이름'] + metadata['연도'] + metadata['월'] + str(page_num) + 'text' + str(widx)
        #db_format_request_sentence(word_em, embeds, metadata, ids)
        db_format_request_table(word_em, embeds, metadata, ids) # 이거로 수정 이것도 표 db에 추가

        page_text_cnt += 1

    table_cnt += page_table_cnt
    text_cnt += page_text_cnt
    print(f' ▶ table{page_table_cnt} sentence{page_text_cnt}')

def db_format_request_others(file_name,result_word_list,match_title_annotation_table,page_num):
    global table_cnt,text_cnt, token
    page_table_cnt = 0
    page_text_cnt = 0

    metadata['연도'] = file_name.split('_')[0]

    #표 데이터
    for tidx, item in enumerate(match_title_annotation_table):
        # 표를 마크다운 형식으로 변환
        table_md = item['table'].to_markdown()

        # 제목과 표 결합
        full_markdown = f"[{file_name}]\n\n{item['title']}\n\n{table_md}\n\n{item['unit']}\n{item['annotation']}"
        token +=len(full_markdown)# token계산하기 위한 글자수 세기
        embeds = openai_embedding_fn(f"{file_name}\n{item['title']}\n\n{table_md}") # 마크다운 형식 안하기

        metadata['제목'] = item['title']
        metadata['단위'] = item['unit']
        metadata['출처'] = item['annotation']
        metadata['타입'] = '표'
        ids = file_name + metadata['연도'] + str(page_num) + 'table' + str(tidx)

        db_format_request_table(full_markdown, embeds, metadata, ids)
        page_table_cnt += 1

    metadata['제목'] = ''  # 널값 불가
    metadata['단위'] = ''
    metadata['출처'] = ''
    metadata['타입'] = '문자'

    #텍스트 데이터
    for widx, word in enumerate(result_word_list):
        if len(word) <= 20:continue
        word_em = f'[{file_name}]\n\n{word}'
        embeds = openai_embedding_fn(word_em)

        token +=len(word)# token계산하기 위한 글자수 세기

        ids = file_name + metadata['연도']+ str(page_num) + 'text' + str(widx)
        db_format_request_sentence(word_em, embeds, metadata, ids)
        page_text_cnt += 1

    table_cnt += page_table_cnt
    text_cnt += page_text_cnt
    print(f' {page_num}페이지 ▶ table{page_table_cnt} sentence{page_text_cnt}')


# 전체 함수 실행
def run_all(file_name,file_path,page_num,file_state):
    # 여기서부터 텍스트들 문장이나 한줄로 구분하는것 이거오기전에 표부터 처리해야됨
    # 메타데이터 기간 품목에서 기간은 하기 파일이름이고 품목은 전역변수로해서 페이지들릴때마다 제일큰 글자로 설정 품목아닌거로 적용되면 실측이나기상같은정보들

    # 텍스트 추출 & 표 데이터 프레임으로
    result_text_df = set_pdfplumber(file_path,page_num,'chars','size','text')
    result_table_df = set_pdfplumber(file_path,page_num,'rects','width','height')
    #result_text_df.to_excel('sadasdasfasf.xlsx',index=False)
    # 안보이는데 겹쳐진것들 제거
    result_text_df = overlap_remove(result_text_df)
    result_table_df = overlap_remove(result_table_df)

    # 세부 품목 이름 구하기 없으면 파일품목이름 그대로 - 월보만 해당
    if file_state==0:set_sub_crop_name(result_text_df,page_num)

    # 표 하나의 그룹으로 x가 이어진 애들 잇기 , y가 이어진 애들 잇기
    group_row = result_table_df.groupby(['y0','y1'])

    # y0 그룹 키값, 표로 인식되는 이어진 행들 rect_row_group_key의 인덱스 리스트 반환
    rect_row_group_key, group_list = set_table_framing(group_row)

    # 반환된 인덱스 정보들로 딕셔너리 테이블 만듬 키값은 처음시작하는 좌표, 테이블의 행은 표의 행과 일치
    table_dict = set_table_1st(group_row, rect_row_group_key, group_list)

    # 텍스트와 매치시키기
    table_match_text = set_match_text(file_name,result_text_df, table_dict,0)

    # 다중 칼럼 하나로 만들기
    multi_col_table_dict = multi_column_conversion(table_match_text)

    # 오직 칼럼만 있는 한줄 짜리 아래 강제로 인식시키는 부분
    success_empty_table, state_list = make_only_col_table(multi_col_table_dict,result_text_df)
    #success_empty_table = multi_column_conversion(success_empty_table,state_list) # 새로만든 인덱스부분 다중인덱스처리 - 위함수에서 다중인덱스 처리 해서 이거 할 필요없음

    # 위 딕셔너리안의 테이블들을 실제 표처럼 만듬 - 데이터 프레임
    table_dict_2nd = set_table_2nd(success_empty_table,state_list)

    # 텍스트와 매치시키기
    table_match_text = set_match_text(file_name,result_text_df, table_dict_2nd,1)

    # 최종 표 출력  표 형식 아닌거 버림
    result_final_table = get_final_table(table_match_text) # 원래이름 result_table_dict

    result_final_table = closed_merge_table(result_final_table) # 가까이 있는 표 실제 하나이거나 하나로 봐도 될 표들 합치기

    # 여기까지 표 추출과정 아래부터 텍스트 추출과정

    # 표에 사용된 텍스트 제거해야함
    result_text_df = remove_table_text(result_final_table,result_text_df)

    # 사이즈 별로 나누기 33이상은 제목들
    result_size_all = result_text_df
    result_size33 = result_size_all.loc[result_size_all['size']<33]

    grouped_f = result_size33.groupby(['y0'])

    # 그냥 그룹화 하면 오차 때문에 분리되는 경우 생김 오차고려해서 그룹화 - 0924 농업전망 적용하면서 수정 - 원래도 문제였던거
    first_keys = grouped_f.groups.keys() # y0 키값들
    grouped_diff = group_by_difference(first_keys, threshold=2) # 그룹화 함수
    origin_renew = y0_coherence(grouped_diff,result_size33) # 원본 text에 y0수정
    grouped = origin_renew.groupby(['y0','size']) # 수정된 y0값들로 그룹화

    # 텍스트 같은 y값인데 같은 줄 아닌거 분리
    text_split_dict = text_group_split_check(grouped)

    # 한줄로 만들기 - 실제 한줄인데 오차로 인해 한줄아닌것들 한줄로
    text_oneline_dict = one_word_merge_oneline(text_split_dict)

    key_list = text_oneline_dict.keys() # 딕셔너리의 키값

    # 이어진 문장 만들때 기록하는 매트릭스
    history_matrix,grouped_by_size,max_len,size_list = set_sentence_history_matrix(key_list,result_final_table) # 줄 이어져 있는거 표현할 수 있는 테이블 구성

    # 재귀로 연속된거 이어버리기
    result_line_text = dfs_history_matrix(history_matrix,grouped_by_size,max_len,size_list)

    # 최종 텍스트 추출
    under10size,result_word_list = get_final_sentence(result_line_text,text_oneline_dict) # 2줄이상의 문단 추출
    # 텍스트에서 제목 추출
    result_oneline_dict = get_final_oneline(result_line_text,text_oneline_dict) # 한줄인것들만 추출 / 오직 표 제목

    # 한줄 텍스트 결과에서 표 제목과 단위 매치 추출
    match_title_table = table_title_unit_match(result_final_table,result_oneline_dict)

    # 자료 주석 매칭(문장과 한줄 전체에서)
    match_title_annotation_table, filter_10size = table_annotation_match(result_final_table,result_oneline_dict,match_title_table,under10size)

    # 최종 텍스트에서 숫자가 더많은 문장 제거
    result_word_list = remove_num_word(result_word_list,20)

    # 크기 10 이하인 글자중 자료 주석 매칭하고 남은것들 중 쓸만한거 추출 22년 월보 마지막 담당자 정보
    result_word_list += get_under10size_word(filter_10size,80)

    global t_cnt
    # for ssadwawa in match_title_annotation_table:
    #       print(ssadwawa)
    t_cnt+=len(match_title_annotation_table)
    #print(f'{page_num}페이지 {len(match_title_annotation_table)} 개 테이블')
    # 최종 결과물 포맷후 db저장 - pdf파일형식에 따라 메타데이터 달라서 다르게 저장
    if file_state==0: db_format_request_agri_report(result_word_list,match_title_annotation_table,page_num)
    if file_state==1: db_format_request_others(file_name,result_word_list,match_title_annotation_table,page_num)


# 폴더내 모든 파일 실행
def process_all_pdfs(root_folder):
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith('.pdf'):
                pdf_file_path = os.path.join(dirpath, filename)

                print(f"🔍 Processing: {pdf_file_path}")

                try: # 파일 열 수 없는 오류 같은거 있음
                    file_name, num_pages, file_state = file_set(pdf_file_path)
                except Exception as e:
                    print(f"File Error: {e}")
                    continue

                for page in range(num_pages):
                    run_all(file_name, pdf_file_path, page, file_state)

    print(f'table{table_cnt} sentence{text_cnt}  {table_cnt+text_cnt}')

if __name__ == "__main__":
    st_t = time.time()
    pdf_folder_path = "C:\\Users\\user\\Downloads\\VS_VC_20_24\\vs_20_24"#text_1f"onion_5year//VS_VC_20_24
    embedding_model = 'intfloat/multilingual-e5-base'#'intfloat/multilingual-e5-base' #
    save_folder_path = 'chroma_db_folder/graph_test_intfloat_model'#'#'#VS_VC_20_25_table_1023'
    embedding_model_set(embedding_model,save_folder_path)
    process_all_pdfs(pdf_folder_path)
    end_t = time.time()
    elapsed_time_min = (end_t - st_t) / 60  # 초 → 분 변환
    print(f"총 실행 시간: {elapsed_time_min:.2f}분")
    print(f'token : {token}')
    print(t_cnt)