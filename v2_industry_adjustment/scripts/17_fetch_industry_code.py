"""
[1단계] 87개 회사(분식+정상) 각각의 업종코드를 DART '기업개황' API로 조회.

DART는 회사마다 업종코드(induty_code)를 갖고 있어요.
예: 반도체 제조업, 식료품 제조업 등으로 회사를 분류하는 코드입니다.
이걸 알아야 "같은 업종끼리" 평균을 비교할 수 있어요.

실행 전 준비물: training_data_final.csv (기존 87개 회사 데이터)
실행하면 -> companies_with_industry.csv 파일이 생성됩니다.
"""

import requests
import pandas as pd
import time

API_KEY = "여기에_본인_DART_API_키를_입력하세요"
URL = "https://opendart.fss.or.kr/api/company.json"


def fetch_industry_code(corp_code, debug=False):
    """기업개황 API로 업종코드(induty_code)를 조회"""
    params = {"crtfc_key": API_KEY, "corp_code": corp_code}
    resp = requests.get(URL, params=params, timeout=15)
    data = resp.json()
    if debug:
        print("  [디버그] 전체 응답:", data)
    if data.get("status") == "000":
        return data.get("induty_code")
    else:
        print(f"  [실패] status={data.get('status')}, message={data.get('message')}")
    return None


# ---------- 기존 87개 회사 리스트 불러오기 ----------
df = pd.read_csv("training_data_final.csv", dtype={"corp_code": str})
df["corp_code"] = df["corp_code"].str.zfill(8)

industry_codes = []
for i, row in df.iterrows():
    corp_code = row["corp_code"]
    corp_name = row["corp_name"]
    code = fetch_industry_code(corp_code, debug=(i == 0))  # 첫 번째 회사만 전체 응답 출력
    print(f"{corp_name}: 업종코드 = {code}")
    industry_codes.append(code)
    time.sleep(0.3)

df["induty_code"] = industry_codes

missing = df["induty_code"].isna().sum()
print(f"\n업종코드 조회 실패: {missing}개 (수작업 확인 필요할 수 있음)")

df.to_csv("companies_with_industry.csv", index=False, encoding="utf-8-sig")
print("저장 완료 -> companies_with_industry.csv")
