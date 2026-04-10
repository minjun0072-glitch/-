from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# 1. 브라우저 옵션 설정
options = Options()
options.add_experimental_option("detach", True) # 실행 완료 후 브라우저 유지
# options.add_argument("--headless") # 창을 띄우지 않고 실행하고 싶을 때 주석 해제

# 2. 드라이버 실행
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    # 3. 웹툰 페이지 접속
    url = "https://comic.naver.com/webtoon" # 월요일 웹툰 예시
    driver.get(url)

    # 4. 명시적 대기 (페이지의 특정 요소가 나타날 때까지 최대 10초 대기)
    wait = WebDriverWait(driver, 10)
    # 웹툰 목록을 담고 있는 리스트 요소가 로드될 때까지 기다림
    webtoon_list = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ContentList__content_list--q59bc")))

    print("=== 인기 웹툰 목록 추출 시작 ===")
    
    # 5. 데이터 추출
    # 각 웹툰 아이템들을 찾습니다. (클래스 명은 사이트 업데이트에 따라 변할 수 있습니다)
    webtoons = driver.find_elements(By.CLASS_NAME, "Poster__link--sop9C")

    for i, webtoon in enumerate(webtoons[:10]): # 상위 10개만 출력
        title = webtoon.find_element(By.CLASS_NAME, "ContentTitle__title--eijm6").text
        link = webtoon.get_attribute("href")
        print(f"{i+1}위: {title}")
        print(f"   링크: {link}")

finally:
    # 6. 종료 (테스트 중이라면 잠시 대기 후 닫기)
    time.sleep(5)
    driver.quit()