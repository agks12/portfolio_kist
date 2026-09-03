from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime, timedelta
import re
import pandas as pd
import numpy as np
import os
import cv2
import time
from dotenv import load_dotenv
import os


filter_day=1
load_dotenv(dotenv_path='info.env')

oasis_user_id = os.getenv('OASIS_USER_ID')
oasis_user_pw = os.getenv('OASIS_USER_PW')
garak_user_id = os.getenv('GARAK_USER_ID')
garak_user_pw = os.getenv('GARAK_USER_PW')
garak_user_pw_s = os.getenv('GARAK_USER_PW_S')

# 세션 및 URL 설정
STATE_PATH = "state.json"
LOGIN_URL = "https://temp.garak.co.kr:4483/olap/logon.do"
DASHBOARD_URL = "https://temp.garak.co.kr:4483/olap/user/dashboard.do"
def calculate_keyboard(page):
    try:
        print('키보드 위치 정보 계산 시작..')
        image_element = page.locator('#loginpw_imgTwin')
        image_element_title = page.locator('#multiMouseTypeImg')
        # 요소가 보일 때까지 최대 10초 대기
        image_element.wait_for(state="visible", timeout=10000)
        # 전체 키보드 크기 얻기
        #print('가상 키보드 전체')
        full_image_size = image_element.bounding_box()
        full_width = full_image_size['width']
        full_height = full_image_size['height']
        # 크기 출력
        #print(f"Image width: {full_width} px")
        #print(f"Image height: {full_height} px")
        # 전체 키보드 좌표 얻기
        full_image_location = image_element.bounding_box()
        keyboard_x = full_image_location['x']
        keyboard_y = full_image_location['y']
        # 좌표 출력
        #print(f"Image location - X: {keyboard_x}, Y: {keyboard_y}")

        #print('가상 키보드 공백 처리할 수 있는 부분')
        # 키보드 제목 크기 얻기(공백으로 처리할 수 있음 - 계산 정확하게)
        space_image_size = image_element_title.bounding_box()
        space_width = space_image_size['width']
        space_height = space_image_size['height']
        # 크기 출력
        #print(f"Image title width: {space_width} px")
        #print(f"Image title height: {space_height} px")
        # 키보드 제목 위치 얻기
        space_image_location = image_element_title.bounding_box()
        space_x = space_image_location['x']
        space_y = space_image_location['y']
        # 좌표 출력
        #print(f"Image title location - X: {space_x}, Y: {space_y}")

        # 키보드 시작 끝점 절대 좌표 계산
        keyboard_st_x = keyboard_x  # 키보드 시작 좌표는 키보드 좌표와 동일
        keyboard_end_x = keyboard_st_x + full_width  # 키보드 끝 좌표는 시작 좌표 + 키보드 너비

        # 키보드 전체화면에서 공백부분 높이
        keyboard_st_y_to_space = space_y + space_height - keyboard_y  # 시작점에서 이동한 2차 시작 위치 y

        keyboard_st_y = space_y + keyboard_st_y_to_space  # space_height # 키보드 높이 시작 좌표는 '멀티마우스' 태그 끝나는 부분 부터
        keyboard_end_y = keyboard_st_y + full_height - keyboard_st_y_to_space  # 키보드 높이 끝 좌표는 시작 + 키보드 높이

        keyboard_width = keyboard_end_x - keyboard_st_x  # 최종 키보드 너비
        keyboard_height = keyboard_end_y - keyboard_st_y  # 최종 키보드 높이

        width_per_unit = keyboard_width / 14  # 한 칸당 너비
        height_per_unit = keyboard_height / 5  # 한 칸당 높이

        #print(f"최종 크기 - X: {keyboard_width}, Y: {keyboard_height} 최종 단위 크기 x:{width_per_unit} , y:{height_per_unit}")

        return keyboard_st_y, keyboard_end_y, keyboard_width, keyboard_height, width_per_unit, height_per_unit, full_height, keyboard_st_y_to_space, image_element
    except Exception as e:
        print(f"오류 발생: {str(e)}")

def pair_to_coordinate(x,y, width_per_unit, height_per_unit):
    dx = (x-1)*width_per_unit + width_per_unit/2
    dy = (y-1)*height_per_unit + height_per_unit/2
    return dx, dy


def search_en_img(keyboard_st_y_to_space,page):
    print('opencv 시작..')
    # 특정 요소 찾기 (예: id가 'some_element'인 요소)
    try:
        element = page.locator('#loginpw_imgTwin')
        # 요소가 보일 때까지 최대 10초 대기
        element.wait_for(state="visible", timeout=10000)
        # 특정 요소 캡처 (스크린샷을 PNG 형식으로 저장)
        element.screenshot(path='element_screenshot.png')
        # 큰 이미지와 찾고자 하는 작은 이미지 로드
        big_image = cv2.imread('element_screenshot.png')  # 큰 이미지
        small_image = cv2.imread('element_screenshot_only_en.png')  # 작은 이미지 # 만들어 놓은거

        # 템플릿 매칭 수행
        result = cv2.matchTemplate(big_image, small_image, cv2.TM_CCOEFF_NORMED)

        # 임계값 설정 (0~1 범위, 1에 가까울수록 정확한 매칭)
        threshold = 0.8  # 일치도 80% 이상을 찾겠다는 의미

        # 매칭된 위치 찾기
        locations = np.where(result >= threshold)

        # 최대 개수 설정
        max_matches = 8  # 찾을 매칭 개수 제한
        en_center_dir = []
        # 결과 이미지에 작은 이미지가 나타나는 위치에 사각형을 그리기
        count = 0  # 찾은 매칭 개수
        for pt in zip(*locations[::-1]):  # locations는 (y, x) 형태이므로 (x, y)로 변경
            if count >= max_matches:
                break  # 최대 개수에 도달하면 반복문 종료
            top_left = pt
            height, width = small_image.shape[:2]
            bottom_right = (top_left[0] + width, top_left[1] + height)
            cv2.rectangle(big_image, top_left, bottom_right, (0, 255, 0), 2)  # 사각형 그리기
            count += 1
            #print(f"Match {count}: Top-left corner = {top_left}, Bottom-right corner = {bottom_right}")
            center_x = (top_left[0] + bottom_right[0])/2
            center_y = (top_left[1] + bottom_right[1])/2
            en_center_dir.append([float(center_x),float(center_y)-keyboard_st_y_to_space])
        #print(en_center_dir)
        #결과 이미지 저장
        cv2.imwrite('result_image.png', big_image)

        if os.path.exists('element_screenshot.png'):
            os.remove('element_screenshot.png')  # 알집 삭제
            print("'element_screenshot.png' 이미지 파일이 삭제되었습니다.")
        if os.path.exists('result_image.png'):
            os.remove('result_image.png')  # 알집 삭제
            print("'result_image.png' 이미지 파일이 삭제되었습니다.")

        return en_center_dir
    except Exception as e:
        print(f"오류 발생: {str(e)}")

def calculate_en_key(en_key_pair, width_per_unit, height_per_unit):
    # 비밀번호 키보드 순서 좌표
    print('키보드 비밀번호 입력 시작..')
    pw_pair = eval(garak_user_pw) # en이 제일 끝에 있을때 설정
    sorted_data = sorted(en_key_pair, key=lambda x: (x[1], x[0])) # y값 으로 오름 차순 정렬 후 x 값으로 오름 차순 정렬
    remove_data = sorted_data[:-2] # y값 가장 작은 2쌍 버림 - 불필요
    left_data = remove_data[::2] # 인덱스 2칸 간격으로 추출 - 홀수번째만 - 각 줄에 대칭으로 위치해서 1개만 보면됨

    for en_idx, (en_x,en_y) in enumerate(left_data):
        x_point = en_x//width_per_unit + 1 # 좌표(길이)를 단위 길이로 나눈 몫 만큼 칸에 위치 1부터 시작이므로 1더하기
        y_point = en_y//height_per_unit
        # pw_pair중 y가 1,2,3인거만 보면 됨
        for pw_idx, (pw_x,pw_y) in enumerate(pw_pair):
            now_pw_x = pw_x
            if pw_y != en_idx+1:continue # 같은 라인 아니면 버림
            if pw_x > 7: now_pw_x = 15-pw_x # 대칭구조에서 오른쪽에 있는거 왼쪽인덱스로 변경
            if x_point < now_pw_x:continue # en키 보다 오른쪽에 있으면 괜찮
            #print('하나 밀린다', pw_pair[pw_idx]) # 이거
            # 여기 오면 en에 밀려서 왼쪽으로 한칸 이동
            if pw_x > 7: pw_pair[pw_idx][0] += 1
            else: pw_pair[pw_idx][0] -= 1
    #print(pw_pair)
    return pw_pair

def login_with_playwright(p):
    try:
        browser = p.chromium.launch(headless=True, slow_mo=250)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(DASHBOARD_URL, wait_until="load")
        print('로그인 페이지 접속')
        time.sleep(1)
        # XPath 사용할 때는 'xpath=' 접두사 필요
        page.locator('xpath=/html/body/div[1]/div[2]/div[1]/form/div/div[1]/div[1]/input').fill(garak_user_id)
        time.sleep(1)
        page.locator('xpath=/html/body/div[1]/div[2]/div[1]/form/div/div[1]/div[2]/input').click()

        # 가상키보드 안뜨면 바로 비번 치기
        try:
            locator = page.locator('xpath=/html/body/div[1]/div[2]/div[1]/form/div/div[1]/div[2]/input')

            # 5초 동안 활성화되기를 기다림
            #locator.wait_for(state="enabled", timeout=5000)  # 5초 대기 # 이거 쓰면 안되네

            # 값 입력
            locator.fill(garak_user_pw_s)

            print('가상키보드 없음 바로 비번 치기')
        except Exception as e:
            print(f"가상키보드 있음: {str(e)}")

            time.sleep(1)
            keyboard_st_y, keyboard_end_y, keyboard_width, keyboard_height, width_per_unit, height_per_unit, full_height, keyboard_st_y_to_space, image_element = calculate_keyboard(
                page)

            en_key_pair = search_en_img(keyboard_st_y_to_space, page)

            pw_pair = calculate_en_key(en_key_pair, width_per_unit, height_per_unit)

            image_locator = page.locator("#loginpw_imgTwin")
            image_locator.wait_for(state="visible", timeout=10000)
            box = image_locator.bounding_box()
            start_x = box['x'] + box['width'] / 2 - keyboard_width / 2
            start_y = box['y'] + box['height'] / 2 - full_height / 2 + keyboard_st_y_to_space

            for pair_x, pair_y in pw_pair:
                dx, dy = pair_to_coordinate(pair_x, pair_y, width_per_unit, height_per_unit)
                page.mouse.move(start_x + dx, start_y + dy)  # 절대 좌표이므로 바로 이동
                # page.mouse.click() 로 하면 안됨 - Playwright에서는 셀레니움처럼 브라우저 마우스 움직이는게 아닌 DOM이벤트~하는거라 가상 키보드 없어짐
                page.mouse.down()  # 마우스 누른 상태
                page.mouse.up()  # 마우스 떼기 = 클릭
                time.sleep(0.1)

            page.locator('xpath=/html/body/div[1]/div[2]/div[1]/form/div/div[1]/div[1]/input').click()  # 키보드 없애기, 로그인 버튼 가려져서
        page.locator('xpath=/html/body/div[1]/div[2]/div[1]/form/div/div[1]/div[3]/button').click()  # 로그인
        time.sleep(1)

        return browser, context, page # 로그인 된 페이지에서 작업 이어감
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return None, None, None


def set_condition_row(ctx, index: int, *, name_value: str, keyword: str, oper_value: str = "4"):
    """
    조회조건 한 줄 설정
    name_value : 컬럼 (1 = 부류)
    keyword    : 검색 키워드
    oper_value : 연산자 (4 = 같지 않은)
    """
    print(f"[STEP] 조건 행 {index} 설정: name={name_value}, keyword={keyword}, oper={oper_value}")
    rows = ctx.locator("#conditionArea .data-condition-form")
    row = rows.nth(index)
    row.locator(".data-condition-name-select").select_option(name_value)
    row.locator(".data-condition-value-select").fill(keyword)
    row.locator(".data-condition-oper-select").select_option(oper_value)


def set_orderby_row(ctx, index: int, *, name_value: str, order_value: str = "0"):
    """
    정렬 한 줄 설정
    name_value : 정렬 기준 컬럼 (1=부류, 2=품목명 등)
    order_value: 0=오름차순, 1=내림차순
    """
    print(f"[STEP] 정렬 행 {index} 설정: name={name_value}, order={order_value}")
    rows = ctx.locator("#orderbyArea .data-orderby-form")
    row = rows.nth(index)
    row.locator(".data-orderby-name").select_option(name_value)
    row.locator(".data-orderby-value").select_option(order_value)


def find_object_select_context(page):
    """
    page 및 모든 frame을 돌면서 #formControlObjectSelect1 이 존재하는 컨텍스트(Page/Frame)를 찾는다.
    """
    selector = "#formControlObjectSelect1"
    contexts = [("page(main)", page)] + [
        (f"frame[{idx}] ({frame.url})", frame) for idx, frame in enumerate(page.frames)
    ]
    print(f"[DEBUG] 컨텍스트 개수: {len(contexts)}")
    for name, ctx in contexts:
        print(f"[DEBUG] 컨텍스트 검사: {name}")
        try:
            ctx.wait_for_selector(selector, timeout=1000)
            print(f"[INFO] {name} 에서 {selector} 를 찾았습니다.")
            return ctx
        except TimeoutError as e:
            # sync_api.TimeoutError 가 아니라 playwright._impl TimeoutError 와 구분위해
            print(f"[DEBUG] {name} 에는 {selector} 가 없음 (timeout)")
            continue
        except PlaywrightTimeoutError:
            print(f"[DEBUG] {name} 에는 {selector} 가 없음 (PlaywrightTimeoutError)")
            continue
        except Exception as e:
            print(f"[WARN] {name} 검사 중 예외 발생: {e}")
            continue
    print("[ERROR] 어느 컨텍스트에서도 #formControlObjectSelect1 를 찾지 못했습니다.")
    return None

def oasis_upload(excel_file_dir):

    with sync_playwright() as p:
        # 브라우저 시작
        browser = p.chromium.launch(headless=True)  # headless=True로 설정하면 브라우저가 보이지 않음
        page = browser.new_page()

        try:
            # OASIS 로그인 페이지로 이동
            page.goto("https://oasis.krei.re.kr/com/cmmn/loginForm.do")

            # 로그인 정보 입력
            page.fill('//*[@id="empId-input"]', oasis_user_id)
            page.fill('//*[@id="password-input"]', oasis_user_pw)
            page.click("//input[@value='로그인']")
            print('OASIS 로그인 성공')

            # 관리자 페이지로 이동
            page.wait_for_selector("//a[text()='관리자']", timeout=1000)  # 최대 1초 기다리기
            page.click("//a[text()='관리자']")
            print('OASIS 관리자 페이지 접속')

            # 자료수동입력 페이지로 이동
            page.wait_for_selector("//span[text()='자료수동입력']", timeout=1000)
            page.click("//span[text()='자료수동입력']")
            page.wait_for_selector("//a[text()='유관기관자료등록']", timeout=1000)
            page.click("//a[text()='유관기관자료등록']")

            # 페이지 맨 아래로 스크롤
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # '가락시장 반입량(잠정치)' 선택
            page.select_option("//select[@id='inoutId']", label="가락시장 반입량(잠정치)")
            time.sleep(2)

            # 파일 업로드 (Excel 파일 경로 지정)
            page.set_input_files("#iaFile", excel_file_dir)
            time.sleep(2)
            print('업로드 중...')

            # 업로드 버튼 클릭
            page.click("//a[@href='javascript:goFTP();']")
            time.sleep(2)  # 업로드 시간 대기

            print('OASIS 가락시장 반입량(잠정치) 자료 업로드 완료')

        except Exception as e:
            print(f"오류 발생: {str(e)}")

        finally:
            # 브라우저 닫기
            browser.close()

def run():
    url = DASHBOARD_URL

    # 어제 ~ 오늘 (필터링 기준용)
    today_dt = datetime.today()
    yesterday_dt = today_dt - timedelta(days=filter_day)
    today_int = int(today_dt.strftime("%Y%m%d"))
    yesterday_int = int(yesterday_dt.strftime("%Y%m%d"))

    print(f"[INFO] 필터링 기준: {yesterday_int} ~ {today_int}")

    with sync_playwright() as p:
        # 1) 세션 적용 + 로그인 상태 확보
        browser, context, page = login_with_playwright(p)
        if browser is None:
            return

        # 2) 사용자가 메뉴 클릭해서 원하는 화면까지 들어가도록 안내
        # print(
        #     "\n[ACTION] 브라우저에서 '정보객체 선택 / 조회 조건 / 기간 / 조건추가 / 정렬추가' 화면까지 이동한 뒤,\n"
        #     "        이 콘솔로 돌아와서 Enter 를 눌러주세요.\n"
        # )
#        input()

        # 현재 page 는 이미 그 화면에 떠 있다고 가정
        print("[INFO] 현재 URL:", page.url)
        print("[INFO] page title:", page.title())

        # 3) 정보객체 select 가 있는 컨텍스트 찾기
        print("[STEP] 정보객체 select 가 있는 컨텍스트 찾는 중...")
        ctx = find_object_select_context(page)
        if ctx is None:
            print("[FATAL] 자동화를 계속 진행할 수 없습니다.")
            browser.close()
            return

        download_filename = None

        try:
            # 3-1. 정보객체 선택: 가락_법인정산물량 (M_BJQ_GR)
            print("[STEP] 정보객체 선택: M_BJQ_GR")
            ctx.locator("#formControlObjectSelect1").select_option("M_BJQ_GR")

            # 3-2. 상세항목 체크: 일자 / 부류 / 품목명 / 합계물량
            def check_detail(text: str) -> None:
                print(f"[STEP] 상세항목 체크: {text}")
                form = ctx.locator("#objectDetailInfo1 .form-check").filter(has_text=text)
                form.locator("label").click()

            check_detail("일자")
            check_detail("부류")
            check_detail("품목명")
            check_detail("합계물량")

            # 3-3. 날짜는 화면 기본값 그대로 사용 (사이트에서 1개월 구간 지정)
            start_val = ctx.locator("#datepicker_start").input_value()
            end_val = ctx.locator("#datepicker_end").input_value()
            print(f"[INFO] 화면에 설정된 조회기간(사이트 기준): {start_val} ~ {end_val}")

            # 3-4. 조건: 부류 != [건어류, 선어류, 패류, 연체류, 갑각류, 건어기타, 젓갈류]
            keywords = ["건어류", "선어류", "패류", "연체류", "갑각류", "건어기타", "젓갈류"]
            rows = ctx.locator("#conditionArea .data-condition-form")
            current_count = rows.count()
            print(f"[DEBUG] 현재 조건 행 개수: {current_count}")

            while current_count < len(keywords):
                print("[STEP] 조건 추가 버튼 클릭 (행 개수 증가시키기)")
                ctx.locator("#conditionAdd").click()
                current_count = rows.count()
                print(f"[DEBUG] 조건 행 개수 갱신: {current_count}")

            for idx, kw in enumerate(keywords):
                set_condition_row(ctx, idx, name_value="1", keyword=kw, oper_value="4")

            # 3-5. 정렬: 부류 → 품목명
            needed_orders = 2
            order_rows = ctx.locator("#orderbyArea .data-orderby-form")
            order_count = order_rows.count()
            print(f"[DEBUG] 현재 정렬 행 개수: {order_count}")

            while order_count < needed_orders:
                print("[STEP] 정렬 추가 버튼 클릭 (행 개수 증가시키기)")
                ctx.locator("#orderbyAdd").click()
                order_count = order_rows.count()
                print(f"[DEBUG] 정렬 행 개수 갱신: {order_count}")

            set_orderby_row(ctx, 0, name_value="1", order_value="0")  # 부류
            set_orderby_row(ctx, 1, name_value="2", order_value="0")  # 품목명

            # 3-6. 조회 버튼 클릭
            print("[STEP] 조회 버튼 클릭")
            ctx.locator("#objectSelectActionBtn").click()

            # 3-7. 엑셀 다운로드
            print("[STEP] 엑셀 다운로드 버튼 클릭 대기")
            with page.expect_download() as download_info:
                ctx.get_by_role("button", name=re.compile("엑셀")).click()

            download = download_info.value
            original_filename  = download.suggested_filename
            
            # 날짜를 파싱해서 input_YYYY_MM_DD.xlsx 형식으로 변환
            date_part = re.findall(r"\d{4}_\d{2}_\d{2}", original_filename)
            if date_part:
                new_filename = f"input_{date_part[0]}.xlsx"
            else:
                # fallback: 오늘 날짜로

                today_str = datetime.today().strftime("%Y_%m_%d")
                new_filename = f"input_{today_str}.xlsx"
                
            download.save_as(new_filename)
            print(f"[INFO] 엑셀 다운로드 완료 → {new_filename}")

            download_filename = new_filename

        except Exception as e:
            print("[ERROR] 자동화 중 예외 발생:", e)
            print("[INFO] 브라우저를 닫습니다.")
            browser.close()
            return

        print("[INFO] 브라우저를 닫습니다.")
        browser.close()

    # ─────────────────────────────────────
    # 4. pandas 로 어제~오늘만 필터링
    # ─────────────────────────────────────
    if download_filename is None or not os.path.exists(download_filename):
        print("[ERROR] 다운로드된 엑셀 파일을 찾을 수 없습니다.")
        return

    print(f"[INFO] 엑셀 필터링 시작: {download_filename}")
    df = pd.read_excel(download_filename)

    print("[DEBUG] 원본 컬럼 목록:", list(df.columns))
    print("[DEBUG] '일자' 컬럼 dtype:", df["일자"].dtype)

    # '일자' → YYYYMMDD 문자열 → datetime 변환
    df["일자_str"] = df["일자"].astype(str)
    df["일자_dt"] = pd.to_datetime(df["일자_str"], format="%Y%m%d", errors="coerce")

    print("[DEBUG] '일자_dt' 변환 후 유효값 개수:", df["일자_dt"].notna().sum())
    print("[DEBUG] '일자_dt' 최소/최대:",
        df["일자_dt"].min(), "~", df["일자_dt"].max())

    # 어제~오늘 기준 필터링
    start_date = yesterday_dt.date()
    end_date = today_dt.date()
    print(f"[INFO] 필터링 기준 (date): {start_date} ~ {end_date}")

    mask = (df["일자_dt"].dt.date >= start_date) & (df["일자_dt"].dt.date <= end_date)
    df_filtered = df[mask].copy()

    # 🔥 불필요한 컬럼 제거
    drop_cols = ["일자_str", "일자_dt"]
    df_filtered = df_filtered.drop(columns=drop_cols, errors="ignore")

    # 1. 파일 이름에서 날짜 추출 (정규식 사용)
    match = re.search(r'(\d{4}_\d{2}_\d{2})', download_filename)
    if match:
        # 날짜 부분 추출
        date_str = match.group(0)
        print(f"추출된 날짜: {date_str}")

        # 2. 날짜 문자열을 datetime 객체로 변환
        date_obj = datetime.strptime(date_str, "%Y_%m_%d")

        # 3. 날짜에서 1일을 빼기
        new_date_obj = date_obj - timedelta(days=1)

        # 4. 새 날짜로 파일 이름 생성
        new_date_str = new_date_obj.strftime("%Y_%m_%d")
        filtered_name = f"input_{new_date_str}.xlsx"

        print(f"새로운 파일 이름: {filtered_name}")
        df_filtered.to_excel(filtered_name, index=False)

        print(f"[INFO] 필터링 완료 → {filtered_name}")
        print(f"[INFO] 행 개수: 원본={len(df)}, 필터링 후={len(df_filtered)}")
        print("[DEBUG] 필터링 후 상위 5행:")
        print(df_filtered.head())
        oasis_upload(filtered_name)

        if os.path.exists(filtered_name):
            os.remove(filtered_name)  # 알집 삭제
            print(f"{filtered_name} 필터링 파일이 삭제되었습니다.")

        if os.path.exists(download_filename):
            os.remove(download_filename)  # 알집 삭제
            print(f"{download_filename} 원본 파일이 삭제되었습니다.")
    else:
        print("날짜를 추출할 수 없습니다.")

if __name__ == "__main__":
    run()