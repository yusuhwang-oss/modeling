"""
[2단계] 1단계에서 찾은 타겟 업종 정상기업 후보들의 재무데이터를 조회하고
       8개 재무비율을 계산합니다.

실행 전 준비물: industry_targeted_candidates.csv (1단계 결과물)
실행하면 -> industry_targeted_scores.csv 파일이 생성됩니다.
"""

import requests
import pandas as pd
import time

API_KEY = "여기에_본인_DART_API_키를_입력하세요"
BASE_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

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
            resp = requests.get(BASE_URL, params=params, timeout=15)
            data = resp.json()
            if data.get("status") != "000":
                return None, None
            items = data.get("list", [])
            t_data, t1_data = {}, {}
            for key, kws in ACCOUNT_KEYWORDS.items():
                t_data[key] = find_account_value(items, kws, "thstrm_amount")
                t1_data[key] = find_account_value(items, kws, "frmtrm_amount")
            return t_data, t1_data
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                time.sleep(1.5)
                continue
            print(f"    [네트워크 오류로 건너뜀] corp_code={corp_code}: {type(e).__name__}")
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


candidates = pd.read_csv("industry_targeted_candidates.csv", dtype={"corp_code": str})

results = []
for _, row in candidates.iterrows():
    corp_code, corp_name, year = row["corp_code"], row["corp_name"], row["year"]
    print(f"조회 중: {corp_name} ({year}년)")
    t, t1 = fetch_financial_year(corp_code, year, fs_div="CFS")
    if t is None or all(v is None for v in t.values()):
        t, t1 = fetch_financial_year(corp_code, year, fs_div="OFS")
    if t is None:
        print("  -> 데이터 조회 실패")
        time.sleep(0.3)
        continue
    ratios = compute_ratios(t, t1)
    result_row = {
        "corp_name": corp_name, "corp_code": corp_code, "year": year,
        "label": 0, "induty_code": row["induty_code"],
    }
    result_row.update(ratios)
    results.append(result_row)
    time.sleep(0.3)

out = pd.DataFrame(results)
out.to_csv("industry_targeted_scores.csv", index=False, encoding="utf-8-sig")
print(f"\n완료. {len(out)}건 처리 -> industry_targeted_scores.csv 저장")
