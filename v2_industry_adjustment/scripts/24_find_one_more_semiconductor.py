"""
[마지막 보충] SK하이닉스 그룹(261)을 3개까지 채우기 위해
             반도체 관련 회사 후보를 몇 개 더 확인 + 재무데이터까지 한 번에 조회합니다.

실행하면 -> semiconductor_scores_v2.csv 파일이 생성됩니다.
(이 파일이 기존 semiconductor_scores.csv를 대체합니다)
"""

import requests
import pandas as pd
import time

API_KEY = "여기에_본인_DART_API_키를_입력하세요"
COMPANY_URL = "https://opendart.fss.or.kr/api/company.json"
FS_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

# 추가 반도체 관련 상장사 후보들
MORE_CANDIDATES = [
    "LX세미콘", "어보브반도체", "SFA반도체", "아이에이", "텔레칩스",
    "제주반도체", "유니테스트", "프로텍", "미래산업", "케이씨텍",
    "원익QnC", "티에스이",
]

TARGET_PREFIX = "261"  # SK하이닉스(2612), DB하이텍/하나마이크론(2611)과 같은 반도체 제조업군

ACCOUNT_KEYWORDS = {
    "sales": ["매출액", "수익(매출액)", "영업수익"],
    "cogs": ["매출원가"],
    "receivables": ["매출채권", "외상매출금"],
    "current_assets": ["유동자산"],
    "ppe": ["유형자산"],
    "total_assets": ["자산총계"],
    "sga": ["판매비와관리비", "판매비와 관리비"],
    "total_liabilities": ["부채총계"],
    "current_liabilities": ["유동부채"],
    "cash": ["현금및현금성자산"],
    "depreciation": ["감가상각비"],
}


def fetch_industry_code(corp_code, retries=2):
    for attempt in range(retries + 1):
        try:
            params = {"crtfc_key": API_KEY, "corp_code": corp_code}
            resp = requests.get(COMPANY_URL, params=params, timeout=15)
            data = resp.json()
            if data.get("status") == "000":
                return data.get("induty_code")
            return None
        except requests.exceptions.RequestException:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return None


def find_account_value(items, keywords, amount_key):
    for kw in keywords:
        for it in items:
            if kw in it.get("account_nm", ""):
                val = it.get(amount_key, "")
                val = val.replace(",", "") if val else ""
                if val not in ("", None):
                    try:
                        return float(val)
                    except ValueError:
                        continue
    return None


def fetch_financial_year(corp_code, year, fs_div="CFS", retries=2):
    for attempt in range(retries + 1):
        try:
            params = {
                "crtfc_key": API_KEY, "corp_code": corp_code, "bsns_year": str(year),
                "reprt_code": "11011", "fs_div": fs_div,
            }
            resp = requests.get(FS_URL, params=params, timeout=15)
            data = resp.json()
            if data.get("status") != "000":
                return None, None
            items = data.get("list", [])
            t_data, t1_data = {}, {}
            for key, kws in ACCOUNT_KEYWORDS.items():
                t_data[key] = find_account_value(items, kws, "thstrm_amount")
                t1_data[key] = find_account_value(items, kws, "frmtrm_amount")
            return t_data, t1_data
        except requests.exceptions.RequestException:
            if attempt < retries:
                time.sleep(1.5)
                continue
            return None, None


def safe_div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def compute_ratios(t, t1):
    r1 = safe_div(t["receivables"], t["sales"])
    r2 = safe_div(t1["receivables"], t1["sales"])
    dsri = safe_div(r1, r2) or 1.0
    if t["cogs"] is not None and t1["cogs"] is not None and t["sales"] and t1["sales"]:
        gm_t = safe_div(t["sales"] - t["cogs"], t["sales"])
        gm_t1 = safe_div(t1["sales"] - t1["cogs"], t1["sales"])
        gmi = safe_div(gm_t1, gm_t) or 1.0
    else:
        gmi = 1.0
    if None not in (t["current_assets"], t["ppe"], t["total_assets"],
                     t1["current_assets"], t1["ppe"], t1["total_assets"]):
        aqi_t = safe_div(t["total_assets"] - t["current_assets"] - t["ppe"], t["total_assets"])
        aqi_t1 = safe_div(t1["total_assets"] - t1["current_assets"] - t1["ppe"], t1["total_assets"])
        aqi = safe_div(aqi_t, aqi_t1) or 1.0
    else:
        aqi = 1.0
    sgi = safe_div(t["sales"], t1["sales"]) or 1.0
    depi = None
    if t["depreciation"] and t1["depreciation"] and t["ppe"] and t1["ppe"]:
        dep_rate_t = safe_div(t["depreciation"], t["depreciation"] + t["ppe"])
        dep_rate_t1 = safe_div(t1["depreciation"], t1["depreciation"] + t1["ppe"])
        depi = safe_div(dep_rate_t1, dep_rate_t)
    depi = depi or 1.0
    s1 = safe_div(t["sga"], t["sales"])
    s2 = safe_div(t1["sga"], t1["sales"])
    sgai = safe_div(s1, s2) or 1.0
    l1 = safe_div(t["total_liabilities"], t["total_assets"])
    l2 = safe_div(t1["total_liabilities"], t1["total_assets"])
    lvgi = safe_div(l1, l2) or 1.0
    tata = None
    if None not in (t["current_assets"], t["cash"], t["current_liabilities"], t["total_assets"],
                     t1["current_assets"], t1["cash"], t1["current_liabilities"]) and t["total_assets"]:
        dep_for_tata = t["depreciation"] if t["depreciation"] else 0
        wc_t = (t["current_assets"] - t["cash"]) - t["current_liabilities"]
        wc_t1 = (t1["current_assets"] - t1["cash"]) - t1["current_liabilities"]
        tata = safe_div(wc_t - wc_t1 - dep_for_tata, t["total_assets"])
    tata = tata if tata is not None else 0.0
    return {"DSRI": dsri, "GMI": gmi, "AQI": aqi, "SGI": sgi,
            "DEPI": depi, "SGAI": sgai, "LVGI": lvgi, "TATA": tata}


corp_all = pd.read_csv("dart_corp_code_all.csv", dtype={"corp_code": str, "stock_code": str})

# ---------- 기존에 이미 찾은 DB하이텍, 하나마이크론 불러오기 ----------
existing_semi = pd.read_csv("semiconductor_scores.csv", dtype={"corp_code": str, "induty_code": str})
results = existing_semi.to_dict("records")

print(f"기존 확보: {len(results)}개 (DB하이텍, 하나마이크론)\n")

for name in MORE_CANDIDATES:
    if len(results) >= 3:
        print("이미 3개 확보됨, 추가 탐색 중단합니다.")
        break

    hit = corp_all[corp_all["corp_name"] == name]
    if len(hit) == 0:
        print(f"[매칭 실패] {name} -> 이름 없음")
        continue

    corp_code = hit.iloc[0]["corp_code"]
    code = fetch_industry_code(corp_code)
    time.sleep(0.3)

    if code is None or not code.startswith(TARGET_PREFIX):
        print(f"{name}: 업종코드 = {code} (반도체군 아님, 건너뜀)")
        continue

    print(f"{name}: 업종코드 = {code} -> 반도체군 일치! 재무데이터 조회 중...")
    year = 2022
    t, t1 = fetch_financial_year(corp_code, year, fs_div="CFS")
    if t is None or all(v is None for v in t.values()):
        t, t1 = fetch_financial_year(corp_code, year, fs_div="OFS")
    if t is None:
        print("  -> 데이터 조회 실패, 건너뜀")
        time.sleep(0.3)
        continue

    ratios = compute_ratios(t, t1)
    row = {"corp_name": name, "corp_code": corp_code, "year": year,
           "label": 0, "induty_code": code}
    row.update(ratios)
    results.append(row)
    print(f"  -> 추가 완료! (현재 {len(results)}개 확보)")
    time.sleep(0.3)

out = pd.DataFrame(results)
print(f"\n최종 반도체군 표본: {len(out)}개")
out.to_csv("semiconductor_scores_v2.csv", index=False, encoding="utf-8-sig")
print("저장 완료 -> semiconductor_scores_v2.csv")
