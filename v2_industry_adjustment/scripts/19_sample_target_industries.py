"""
[1단계] "타겟 업종"에 속하는 정상기업 후보를 찾습니다.
       타겟 업종 = 11개 분식기업이 속한 업종 + SK하이닉스가 속한 업종(반도체, 2612)

DART는 "이 업종 회사만 보여줘" 하는 필터가 없어서,
무작위로 회사 후보를 뽑아 하나씩 업종을 확인하며 원하는 업종에 맞는 회사를 찾습니다.

실행 전 준비물: companies_with_industry.csv, dart_corp_code_all.csv
실행하면 -> industry_targeted_candidates.csv 파일이 생성됩니다.
"""

import requests
import pandas as pd
import random
import time

API_KEY = "여기에_본인_DART_API_키를_입력하세요"
URL = "https://opendart.fss.or.kr/api/company.json"

TARGET_PER_INDUSTRY = 4   # 업종당 이만큼의 정상기업을 추가로 채우는 게 목표
MAX_CANDIDATES_TO_TRY = 400  # 시간이 너무 오래 걸리지 않도록 후보 조회 개수에 상한선

random.seed(1)


def fetch_industry_code(corp_code, retries=2):
    """기업개황 API로 업종코드(induty_code)를 조회. 네트워크 오류시 재시도 후 실패하면 None 반환"""
    for attempt in range(retries + 1):
        try:
            params = {"crtfc_key": API_KEY, "corp_code": corp_code}
            resp = requests.get(URL, params=params, timeout=15)
            data = resp.json()
            if data.get("status") == "000":
                return data.get("induty_code")
            return None
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                time.sleep(1.5)  # 살짝 쉬었다가 재시도
                continue
            print(f"    [네트워크 오류로 건너뜀] corp_code={corp_code}: {type(e).__name__}")
            return None


# ---------- 1. 타겟 업종 리스트 만들기 ----------
existing = pd.read_csv("companies_with_industry.csv", dtype={"corp_code": str, "induty_code": str})

fraud_industries = existing[existing["label"] == 1]["induty_code"].dropna().unique().tolist()
SK_HYNIX_INDUSTRY = "2612"
target_industries = list(set(fraud_industries) | {SK_HYNIX_INDUSTRY})
print(f"타겟 업종 목록 ({len(target_industries)}개): {target_industries}")

# ---------- 2. 업종별 현재 정상기업 수 확인 ----------
current_counts = existing[existing["label"] == 0]["induty_code"].value_counts()
needs = {}
for ind in target_industries:
    current = current_counts.get(ind, 0)
    need = max(0, TARGET_PER_INDUSTRY - current)
    needs[ind] = need
    print(f"  업종 {ind}: 현재 {current}개 보유 -> {need}개 더 필요")

# ---------- 3. 무작위 후보 뽑아서 업종 확인 ----------
corp_all = pd.read_csv("dart_corp_code_all.csv", dtype={"corp_code": str, "stock_code": str})
listed = corp_all[corp_all["stock_code"].notna() & (corp_all["stock_code"].str.strip() != "")].copy()

used_codes = set(existing["corp_code"])
exclude_kw = ["은행", "보험", "금융지주", "캐피탈", "저축은행", "증권"]
listed = listed[~listed["corp_name"].str.contains("|".join(exclude_kw), na=False)]
listed = listed[~listed["corp_code"].isin(used_codes)].reset_index(drop=True)

candidates_pool = listed.sample(frac=1, random_state=1).reset_index(drop=True)  # 무작위 순서로 섞기

found_companies = []
tried = 0

for _, row in candidates_pool.iterrows():
    if tried >= MAX_CANDIDATES_TO_TRY:
        print("\n최대 조회 횟수 도달, 종료합니다.")
        break
    if all(v <= 0 for v in needs.values()):
        print("\n모든 타겟 업종 채움, 종료합니다.")
        break

    corp_code = row["corp_code"]
    corp_name = row["corp_name"]
    tried += 1

    code = fetch_industry_code(corp_code)
    time.sleep(0.3)

    if code in needs and needs[code] > 0:
        found_companies.append({
            "corp_name": corp_name,
            "corp_code": corp_code,
            "induty_code": code,
            "year": 2022,
            "label": 0,
        })
        needs[code] -= 1
        print(f"  [발견] {corp_name} -> 업종 {code} (남은 필요 수: {needs[code]})")

print(f"\n총 {tried}개 후보 조회, {len(found_companies)}개 매칭 성공")

found_df = pd.DataFrame(found_companies)
found_df.to_csv("industry_targeted_candidates.csv", index=False, encoding="utf-8-sig")
print("저장 완료 -> industry_targeted_candidates.csv")
