# 파일명: main.py

# 1. 만들어둔 모듈 불러오기 (확장자 .py는 생략합니다)
import data_calc

# 처리할 데이터 리스트
my_data = [15, 42, 88, 23, 55]

# 2. '모듈이름.함수이름()' 형태로 모듈 내부의 기능 사용하기
avg_result = data_calc.get_average(my_data)
max_result = data_calc.get_max(my_data)

print(f"데이터 원본: {my_data}")
print(f"평균값: {avg_result}")
print(f"최댓값: {max_result}")