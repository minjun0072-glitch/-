from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# 1. 브라우저 설정
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

try:
    # 2. 페이지 접속
    url = "https://comic.naver.com/webtoon"
    driver.get(url)
    
    # 3. '이달의 신규 웹툰' 영역이 로드될 때까지 대기
    wait = WebDriverWait(driver, 10)
    # 신규 웹툰 섹션의 컨테이너 요소를 찾습니다.
    new_webtoons_section = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "AsideList__aside_list--u36_I"))) 

    print("=== 이달의 신규 웹툰 정보 ===")

    # 4. 각 웹툰 아이템 추출 (리스트 형태)
    items = driver.find_elements(By.CLASS_NAME, "AsideList__item--S_p9l")

    for item in items:
        try:
            # 제목 추출
            title = item.find_element(By.CLASS_NAME, "ContentTitle__title--eijm6").text
            # 작가 추출
            author = item.find_element(By.CLASS_NAME, "ContentAuthor__author--CT_nI").text
            
            # 내용을 보려면 마우스를 올리거나 상세 페이지에 가야 할 수도 있지만, 
            # 메인에 요약이 있다면 해당 클래스를 가져옵니다.
            # (네이버 메인 구조상 요약은 보통 상세 페이지에 있으므로 여기서는 제목/작가 중심)
            
            print(f"제목: {title} | 작가: {author}")
        except Exception as e:
            continue

finally:
    time.sleep(3)
    driver.quit()