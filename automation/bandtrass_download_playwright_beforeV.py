from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from calendar import monthrange
from dotenv import load_dotenv
from datetime import datetime
import zipfile
import time
import os
import pandas as pd

load_dotenv(dotenv_path='info.env')

bandtrass_user_id = os.getenv('BANDTRASS_USER_ID')
bandtrass_user_pw = os.getenv('BANDTRASS_USER_PW')
oasis_user_id = os.getenv('OASIS_USER_ID')
oasis_user_pw = os.getenv('OASIS_USER_PW')
file_pw = os.getenv('FILE_PW')

#os.environ['PLAYWRIGHT_BROWSERS_PATH'] = 'C:/Users/user/AppData/Local/ms-playwright' 윈도우에서 실행 시

download_dir = os.path.dirname(os.path.abspath(__file__))  # 원하는 다운로드 경로로 수정 - 절대경로
print(download_dir)
# 다운로드 폴더가 존재하지 않으면 생성
if not os.path.exists(download_dir):
    os.makedirs(download_dir)

def find_last_day_prev_month(year, month):
    # 전월 계산 (1월일 경우, 12월로 변경)

    if month == "01":
        prev_month = 12
        prev_year = int(year) - 1
    else:
        prev_month = int(month) - 1
        prev_year = int(year)

    # 전월의 마지막 날짜 구하기
    last_day_prev_month = monthrange(prev_year, prev_month)[1]
    return prev_year,prev_month,last_day_prev_month


# 년, 월, 일 추출
def find_day(latest_day):
    year = latest_day.split('-')[0]  # 연도
    month = latest_day.split('-')[1]  # 월
    day = latest_day.split('-')[2]  # 일

    st_day = str(int(day) - 5).zfill(2)  # 시작일은 기준일보다 5일 전
    end_day = str(int(day) - 1).zfill(2)  # 종료일은 기준일보다 1일 전
    # 1일에는 26~30or31인 예외
    prev_year,prev_month,last_day_prev_month = find_last_day_prev_month(year, month)

    # 1일에는 예외
    if day == "01":
        st_day = "26"
        end_day = last_day_prev_month
        # 여기 들어오면 month무조건 prev_month로
        #month = str(prev_month)
        if month=="01":# 새해인 경우 년도도 전년거로
            year = str(prev_year)
        month = str(prev_month).zfill(2)
    return year, month, day, st_day, end_day


def oasis_current_std_day_compare(std_day_ymd):
    # year = std_day[-10:].split('-')[0]
    # month = std_day[-10:].split('-')[1]
    # day = std_day[-10:].split('-')[2]

    current_date = datetime.now().date()  # 현재 날짜
    print(f'현재 날짜 : {current_date}')
    std_day_ymd = datetime.strptime(std_day_ymd, "%Y-%m-%d")  # 오아시스 등록 기준일
    diff_day = (current_date - std_day_ymd.date()).days  # 날짜 차이

    max_diff_day = 5  # 업로드 안되는 최대 기간(31일인 경우 +1)

    last_day_prev_month = find_last_day_prev_month(current_date.year,
                                                   current_date.month)  # 전월 마지막 일, 31일 or 30일 판단 # 현재 날짜 기준
    if int(current_date.day) < 6 and last_day_prev_month == 31: max_diff_day += 1

    # print(diff_day,max_diff_day)
    if diff_day > max_diff_day:  # 업데이트 되어야 하는데 안되면 6일 이상 차이생김
        # 업데이트 해야되는데 메일보내기?
        print(f'오아시스 업데이트 필요, 업로드 안된 기간 {diff_day}일')
        return False
    else:
        print('업데이트 정상')
        return True


def bandtrass_download():
    with sync_playwright() as p:
        try:
            # Chromium 브라우저 실행 (headless 모드)
            browser = p.chromium.launch(headless=False,slow_mo=250)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()


            #page.set_viewport_size({"width": 1920, "height": 1080})  # 원하는 해상도로 설정 가능

            #BANDTRASS 로그인 페이지로 이동
            page.goto("https://www.bandtrass.or.kr/login.do?returnPage=M")

            # 로그인 버튼 클릭
            #page.locator("//a[@onclick='loginLocalID();']").click()

            # 로그인 정보 입력
            page.locator('//*[@id="id"]').fill(bandtrass_user_id)  # 아이디 입력
            page.locator('//*[@id="pw"]').fill(bandtrass_user_pw)  # 비밀번호 입력
            page.locator("//button[normalize-space(text())='아이디로 로그인']").click()

            # 비밀번호 변경 알림 처리 (셀레니움에서의 try-except를 Playwright로 변환)
            try:
                page.locator("//button[normalize-space(text())='다음에 변경하기']").click()
                print('비밀번호 변경 기간')
            except Exception as e:
                print('비밀번호 변경 기간 아님')

            print('BANDTRASS 로그인 성공')

            time.sleep(2)  # 페이지 로딩을 위한 잠시 대기

            # 마이페이지 버튼이 나타날 때까지 기다리기
            #page.locator("//a[contains(@class, 'dropdown-toggle') and contains(@class, 'count-info')]").click()
            # 또는 a만 선택
            page.locator("//*[@id='landing_navigation']/div/div[3]/div/ul[2]/a[2]/li").click()

            # '나의 주문내역' 클릭
            #page.locator("//div[contains(@class, 'text-center') and contains(., '나의 주문내역')]").click()

            print('BANDTRASS 마이페이지 접속')

            time.sleep(2)  # 페이지 로딩을 위한 잠시 대기

            # 마우스 휠 내리기
            #page.wait_for_load_state("load")
            #page.mouse.wheel(0, 2000)  # x, y 좌표로 마우스 휠 내리기
            page.keyboard.press("PageDown")
            time.sleep(1)


            # 자료 나타날 때까지 기다리기 (두번째 테이블 행을 찾을 때까지)
            table_row = page.locator('//*[@id="page-wrapper"]/div/div/div[3]/div/div/table/tbody/tr[2]')

            # 테이블 행의 셀 찾기
            cells = table_row.locator('td')
            latest_day = cells.nth(1).text_content()  # 최신 날짜

            year, month, day, st_day, end_day = find_day(latest_day)  # 년,월,일 찾기
            file_name_format_zip = f"농촌경제연구원({year}{month}{st_day}-{year}{month}{end_day}).zip"  # 이름 형식
            excel_file_dir = download_dir + f"/kreinet_{year}{month}{st_day}-{year}{month}{end_day}.xlsx"
            file_dir = download_dir + '/' + file_name_format_zip  # 최종 경로+이름

            # 다운로드 프로세스 시작
            if not os.path.exists(file_dir):
                # 다운로드 버튼 클릭 - 다운로드 경로 설정 이걸로 함
                with page.expect_download() as download_info:
                    # 다운로드를 유발하는 버튼 클릭
                    download_button = cells.nth(3)  # 4번째 셀은 인덱스 3에 해당
                    download_button.click()
                download = download_info.value
                download.save_as(file_dir)

                # 다운로드가 완료될 때까지 대기
                timeout = 10  # 대기 시간 (초)
                while timeout > 0:
                    if os.path.exists(file_dir):
                        print(f"{file_dir} 다운로드 완료!")
                        break
                    else:
                        print("파일 다운로드 중...")
                        time.sleep(1)
                        timeout -= 1

                if timeout == 0:
                    print("다운로드 시간 초과")
                    browser.close()
                    return None  # 다운로드 실패 시 None 반환

                # 다운로드 완료 후 압축 풀기
                time.sleep(2)

                # 알집 파일 압축 풀기
                with zipfile.ZipFile(file_dir, 'r') as zip_ref:
                    zip_ref.setpassword(file_pw.encode())  # 비밀번호를 설정 - 바이트형식으로
                    zip_ref.extractall(download_dir)  # 다운로드 경로에 압축 해제
                print(f"{file_dir} 압축이 {download_dir}에 풀렸습니다.")

                # 알집 파일 삭제
                if os.path.exists(file_dir):
                    os.remove(file_dir)  # 알집 삭제
                    print(f"{file_dir} 알집 파일이 삭제되었습니다.")

                browser.close()

                ################### 260715수정  전자상거래로 인한 도착 적재항 빈칸 생김 예외 처리
                tmp_dir = download_dir + r'\kreinet_tmp.xlsx'
                li = ['수입', '수출']
                with pd.ExcelWriter(tmp_dir, engine='openpyxl') as writer:
                    for i in li:
                        df = pd.read_excel(
                            excel_file_dir,
                            skiprows=3,
                            sheet_name=i,
                            dtype=str,  # 모든 데이터를 문자열로 읽어옴
                            na_values=['', 'NULL', 'N/A'],  # NA는 널값이 아닌 국가코드임 NA제외 null로 판단
                            keep_default_na=False
                        )
                        df = df.dropna(subset=[df.columns[3]])  # 적재항, 도착국 기준 null값 제외(전자상거래 해당)
                        df.to_excel(writer, sheet_name=i, index=False, startrow=3)
                print(f'원본 파일 정제 완료')

                os.remove(excel_file_dir)
                print(f'{excel_file_dir} 원본파일 삭제')
                os.rename(
                    tmp_dir,
                    excel_file_dir
                )
                print(f'{tmp_dir} 임시파일 이름 변경')

                return excel_file_dir  # 압축 풀린 파일 경로 반환
            else:
                print('이미 존재하는 파일입니다.')
                browser.close()
                return ""
        except Exception as e:
            print(f"오류 발생: {str(e)}")


def oasis_upload(excel_file_dir):
    with sync_playwright() as p:
        # 브라우저 시작


        browser = p.chromium.launch(headless=True, slow_mo=250)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        try:
            # OASIS 로그인 페이지로 이동
            page.goto("https://oasis.krei.re.kr/com/cmmn/loginForm.do")

            # 로그인 정보 입력
            page.fill('//*[@id="empId-input"]', oasis_user_id)
            page.fill('//*[@id="password-input"]', oasis_user_pw)
            page.click("//input[@value='로그인']")
            print('OASIS 로그인 성공')
            time.sleep(5)
            # 관리자 페이지로 이동
            #page.wait_for_selector("//a[text()='관리자']", timeout=15000)  # 최대 1초 기다리기

            try:
                page.locator("/html/body/div/div[1]/div[2]/div/div/div[1]/a[3]").click()
            except Exception as e:
                print(f"/html/body/div/div[1]/div[2]/div/div/div[1]/a[3] 위치 찾을 수 없음 a[text()='관리자']로 선택: {str(e)}")
                page.locator("//a[text()='관리자']").click()

            #page.click("//a[text()='관리자']")
            print('OASIS 관리자 페이지 접속')

            # 자료수동입력 페이지로 이동
            #page.wait_for_selector("//span[text()='자료수동입력']", timeout=5000)
            #page.click("//span[text()='자료수동입력']")
            page.locator("//span[normalize-space(text())='자료수동입력']").click()

            #page.wait_for_selector("//a[text()='유관기관자료등록']", timeout=5000)
            #page.click("//a[text()='유관기관자료등록']")
            page.locator("//a[text()='유관기관자료등록']").click()

            # 페이지 맨 아래로 스크롤
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # '가락시장 반입량(잠정치)' 선택
            page.select_option("//select[@id='inoutId']", label="수출입(통관)자료")
            time.sleep(1)

            # 파일 업로드 (Excel 파일 경로 지정)
            page.set_input_files("#iaFile", excel_file_dir)
            time.sleep(1)


            # 업로드 버튼 클릭
            # page.click("//a[@href='javascript:goFTP();']")
            # print('업로드 중...')
            # time.sleep(60)  # 업로드 시간 대기
            with page.expect_navigation():
                page.click("//a[@href='javascript:goFTP();']")
            #print("업로드 완료!")

            print('OASIS 수출입(통관)자료 업로드 완료')

        except Exception as e:
            print(f"오류 발생: {str(e)}")

        finally:
            # 브라우저 닫기
            browser.close()


# 1차 등록
if __name__ == "__main__":
    excel_file_dir = bandtrass_download()
    if excel_file_dir is not None:
        oasis_upload(excel_file_dir)
        if os.path.exists(excel_file_dir):
            os.remove(excel_file_dir)  # 알집 삭제
            print(f"{excel_file_dir} 엑셀 파일이 삭제되었습니다.")