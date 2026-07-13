"""
[3단계] 기존 87개 회사 + 새로 찾은 타겟업종 정상기업들을 합쳐서
       업종 평균 대비 상대지표를 계산하고 최종 training_data_final_v2.csv를 만듭니다.

실행 전 준비물: companies_with_industry.csv, industry_targeted_scores.csv
"""

import pandas as pd

FEATURES = ["DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA"]

existing = pd.read_csv("companies_with_industry.csv", dtype={"corp_code": str, "induty_code": str})
new_companies = pd.read_csv("industry_targeted_scores.csv", dtype={"corp_code": str, "induty_code": str})
semiconductor = pd.read_csv("semiconductor_scores_v2.csv", dtype={"corp_code": str, "induty_code": str})

# ---------- 1. 합치기 ----------
df = pd.concat([existing, new_companies, semiconductor], ignore_index=True)
df = df.drop_duplicates(subset=["corp_code"])
print(f"합산 후 전체 표본: {len(df)}개 "
      f"(기존 {len(existing)} + 타겟업종 신규 {len(new_companies)} + 반도체군 {len(semiconductor)})")

# ---------- 2. 업종별 정상기업 수 재확인 ----------
print("\n=== 업종별 정상기업 수 (표본 보강 후) ===")
industry_counts = df[df["label"] == 0]["induty_code"].value_counts()
print(industry_counts.head(15))

# ---------- 3. 3단계 기준선 계산 ----------
# 1순위: 정확히 같은 업종코드 (정상기업 3개 이상)
# 2순위: 앞 3자리가 같은 "업종군" (정상기업 3개 이상) - 예: 2611, 2612 모두 '261' 그룹
# 3순위: 전체 정상기업 평균
normal_df = df[df["label"] == 0].copy()
normal_df["induty_group"] = normal_df["induty_code"].str[:3]  # 앞 3자리만 추출
df["induty_group"] = df["induty_code"].str[:3]

industry_avg = normal_df.groupby("induty_code")[FEATURES].mean()
group_avg = normal_df.groupby("induty_group")[FEATURES].mean()
overall_avg = normal_df[FEATURES].mean()

MIN_GROUP_SIZE = 3
exact_size = normal_df.groupby("induty_code").size()
group_size = normal_df.groupby("induty_group").size()

reliable_exact = exact_size[exact_size >= MIN_GROUP_SIZE].index
reliable_group = group_size[group_size >= MIN_GROUP_SIZE].index

print(f"\n1순위(정확 업종, {MIN_GROUP_SIZE}개 이상) 신뢰 가능: {len(reliable_exact)}개")
print(f"2순위(업종군 3자리, {MIN_GROUP_SIZE}개 이상) 신뢰 가능: {len(reliable_group)}개")


def get_baseline(induty_code, induty_group, feature):
    if induty_code in reliable_exact:
        return industry_avg.loc[induty_code, feature], "정확업종"
    elif induty_group in reliable_group:
        return group_avg.loc[induty_group, feature], "업종군(3자리)"
    else:
        return overall_avg[feature], "전체평균"


baseline_source_log = []
for feature in FEATURES:
    values, sources = [], []
    for _, row in df.iterrows():
        val, src = get_baseline(row["induty_code"], row["induty_group"], feature)
        values.append(val)
        sources.append(src)
    df[feature + "_baseline"] = values
    if feature == FEATURES[0]:
        baseline_source_log = sources  # 대표로 하나만 기록해서 요약용으로 사용
    df[feature] = df[feature] / df[feature + "_baseline"]

df["baseline_type"] = baseline_source_log
print("\n=== 기준선 적용 방식 분포 ===")
print(df["baseline_type"].value_counts())
print(f"\n분식기업 기준 적용 방식:")
print(df[df["label"] == 1][["corp_name", "baseline_type"]].to_string(index=False))

# ---------- 4. 저장 ----------
df_final = df[["corp_name", "corp_code", "year", "label", "induty_code"] + FEATURES].copy()
df_final.to_csv("training_data_final_v2.csv", index=False, encoding="utf-8-sig")
print(f"\n저장 완료 -> training_data_final_v2.csv (총 {len(df_final)}개)")
print("이제 노트북 2번 셀에서 파일명을 training_data_final_v2.csv로 바꿔서 재실행하세요.")
