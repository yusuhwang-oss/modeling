"""
[2단계] 같은 업종의 "정상기업 평균"을 기준선으로 삼아,
       각 회사의 8개 지표를 "업종 평균 대비 상대값"으로 변환합니다.

계산 방법:
  상대지표 = 원래지표값 / 같은 업종 정상기업들의 평균값

예시: SK하이닉스의 SGI(매출성장률)가 0.60이었는데,
      반도체 업종 정상기업 평균이 0.65였다면
      상대지표 = 0.60 / 0.65 = 0.92  (업종 평균과 비슷한 수준이었다는 뜻)

실행 전 준비물: companies_with_industry.csv (1단계 결과물)
실행하면 -> training_data_final_v2.csv 파일이 생성됩니다.
"""

import pandas as pd

FEATURES = ["DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI", "TATA"]

df = pd.read_csv("companies_with_industry.csv", dtype={"corp_code": str})

# ---------- 업종별 회사 수 확인 (진단용) ----------
print("=== 업종별 정상기업 수 (분포 확인) ===")
industry_counts = df[df["label"] == 0]["induty_code"].value_counts()
print(industry_counts)
print(f"\n총 {df['induty_code'].nunique()}개 서로 다른 업종에 분포")
print(f"정상기업이 1개뿐인 업종: {(industry_counts == 1).sum()}개")
print(f"정상기업이 2개 이상인 업종: {(industry_counts >= 2).sum()}개")
print()

# ---------- 업종별 "정상기업" 평균 계산 (기준선) ----------
normal_df = df[df["label"] == 0]
industry_avg = normal_df.groupby("induty_code")[FEATURES].mean()
print("업종별 정상기업 평균 (일부):")
print(industry_avg.head())

# ---------- 전체 정상기업 평균 (업종 평균이 없을 때 대신 쓸 값) ----------
overall_avg = normal_df[FEATURES].mean()

# ---------- 각 회사에 업종 평균 붙이기 ----------
# 업종 내 정상기업 수가 너무 적으면(3개 미만) "업종 평균"의 신뢰도가 낮으므로 전체 평균 사용
MIN_GROUP_SIZE = 3
industry_group_size = normal_df.groupby("induty_code").size()
reliable_industries = industry_group_size[industry_group_size >= MIN_GROUP_SIZE].index

print(f"신뢰할 수 있는(정상기업 {MIN_GROUP_SIZE}개 이상) 업종: {len(reliable_industries)}개")
print(f"-> 이 업종들만 '업종 평균'을 쓰고, 나머지는 전체 평균으로 대체합니다.\n")


def get_industry_avg(induty_code, feature):
    if induty_code in reliable_industries:
        return industry_avg.loc[induty_code, feature]
    return overall_avg[feature]  # 표본 부족 -> 전체 평균으로 대체


for feature in FEATURES:
    df[feature + "_industry_avg"] = df["induty_code"].apply(lambda x: get_industry_avg(x, feature))
    # 상대지표 = 원래값 / 업종평균값
    df[feature] = df[feature] / df[feature + "_industry_avg"]

# ---------- 몇 개 회사가 진짜 업종평균을 적용받았는지 확인 ----------
df["used_industry_avg"] = df["induty_code"].isin(reliable_industries)
print(f"실제 업종 평균 적용: {df['used_industry_avg'].sum()}개사")
print(f"전체 평균으로 대체: {(~df['used_industry_avg']).sum()}개사")
print(f"  (분식기업 중 업종평균 적용: {df[(df.label==1) & (df.used_industry_avg)].shape[0]}개)")
print()

# ---------- 계산에 쓴 보조 컬럼 정리 ----------
df_final = df[["corp_name", "corp_code", "year", "label", "induty_code"] + FEATURES].copy()

print(f"\n최종 데이터: {len(df_final)}개 (업종 대비 상대지표로 변환 완료)")
df_final.to_csv("training_data_final_v2.csv", index=False, encoding="utf-8-sig")
print("저장 완료 -> training_data_final_v2.csv")
print("\n다음 단계: 노트북 2번 셀에서 파일명을 training_data_final_v2.csv로 바꿔서 재실행하세요.")
