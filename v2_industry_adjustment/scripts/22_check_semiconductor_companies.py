"""
[보충] 무작위로는 SK하이닉스 업종(2612)을 못 찾았으므로,
      이미 알려진 반도체 관련 회사들을 직접 지정해서 업종이 맞는지 확인합니다.

실행하면 -> semiconductor_candidates.csv 파일이 생성됩니다.
(맞는 회사가 있으면 이후 20/21번과 유사한 방식으로 데이터에 합칩니다)
"""

import requests
import pandas as pd
import time

API_KEY = "여기에_본인_DART_API_키를_입력하세요"
URL = "https://opendart.fss.or.kr/api/company.json"

# 국내 반도체 관련 상장사 후보 (직접 알만한 회사들 위주로 지정)
CANDIDATE_NAMES = [
    "DB하이텍", "하나마이크론", "원익IPS", "티씨케이", "네패스",
    "리노공업", "isc", "한미반도체", "동진쎄미켐", "SK스퀘어",
]

TARGET_INDUSTRY = "2612"


def fetch_industry_code(corp_code, retries=2):
    for attempt in range(retries + 1):
        try:
            params = {"crtfc_key": API_KEY, "corp_code": corp_code}
            resp = requests.get(URL, params=params, timeout=15)
            data = resp.json()
            if data.get("status") == "000":
                return data.get("induty_code")
            return None
        except requests.exceptions.RequestException:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return None


corp_all = pd.read_csv("dart_corp_code_all.csv", dtype={"corp_code": str, "stock_code": str})

found = []
for name in CANDIDATE_NAMES:
    hit = corp_all[corp_all["corp_name"] == name]
    if len(hit) == 0:
        print(f"[매칭 실패] {name} -> dart_corp_code_all.csv에 이름 없음")
        continue
    corp_code = hit.iloc[0]["corp_code"]
    code = fetch_industry_code(corp_code)
    print(f"{name}: 업종코드 = {code}")
    if code == TARGET_INDUSTRY:
        found.append({
            "corp_name": name, "corp_code": corp_code,
            "induty_code": code, "year": 2022, "label": 0,
        })
    time.sleep(0.3)

found_df = pd.DataFrame(found)
print(f"\n{TARGET_INDUSTRY} 업종(반도체 소자 제조업) 일치: {len(found_df)}개")
found_df.to_csv("semiconductor_candidates.csv", index=False, encoding="utf-8-sig")
print("저장 완료 -> semiconductor_candidates.csv")
