# 파일명: data_calc.py

def get_average(data_list):
    """리스트 내부 숫자들의 평균을 구하는 함수"""
    if len(data_list) == 0:
        return 0
    return sum(data_list) / len(data_list)

def get_max(data_list):
    """리스트 내부 숫자들 중 최댓값을 구하는 함수"""
    if len(data_list) == 0:
        return None
    return max(data_list)