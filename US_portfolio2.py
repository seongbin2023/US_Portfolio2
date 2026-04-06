import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="소수점 적립식 투자 대시보드", page_icon="💰", layout="wide")

st.title("🇺🇸 미국 우량주 소수점 적립식 투자 대시보드")
st.markdown("최근 3개월(90일) 모멘텀을 분석하여 한정된 예산을 가장 효율적인 비율로 배분합니다.")

# --- 사이드바: 투자 설정 ---
st.sidebar.header("⚙️ 투자 설정")
total_investment_usd = st.sidebar.number_input(
    "이번 달 총 투자금 ($)", 
    min_value=10, 
    max_value=10000, 
    value=50, 
    step=10,
    help="매월 투자할 총 금액을 달러 단위로 입력하세요."
)

# 1. 관리 중인 관심 종목
tickers = {
    "유나이티드헬스": "UNH",
    "팔란티어": "PLTR",
    "아이온큐": "IONQ",
    "캐터필러": "CAT", 
    "템퍼스AI": "TEM",
    "비자": "V",
    "로켓랩": "RKLB",
    "일라이릴리": "LLY",
    "비스트라에너지": "VST",
    "코인베이스": "COIN",
    "넥스트에라 에너지": "NEE"
}

# --- 데이터 수집 및 분석 함수 (캐싱 적용) ---
@st.cache_data(ttl=3600) # 1시간 동안 데이터 캐싱
def get_portfolio_data():
    end_date = datetime.today()
    start_date = end_date - timedelta(days=90)
    
    df_list = []
    
    for name, ticker in tickers.items():
        try:
            stock = fdr.DataReader(ticker, start_date, end_date)
            if not stock.empty and len(stock) > 40:
                start_price = float(stock['Close'].iloc[0])
                end_price = float(stock['Close'].iloc[-1])
                return_rate = (end_price - start_price) / start_price
                
                df_list.append({
                    "종목명": name,
                    "수익률(%)": round(return_rate * 100, 2)
                })
        except Exception as e:
            pass # UI 상에서는 에러를 숨기고 조용히 넘어갑니다
            
    return pd.DataFrame(df_list)

# --- 메인 로직 실행 ---
with st.spinner('미국 주식 시장 데이터를 불러와 수익률을 계산하는 중입니다...'):
    df = get_portfolio_data()

if not df.empty:
    # 상위 5개 종목 추출 및 정규화
    df_top5 = df.sort_values(by="수익률(%)", ascending=False).head(5).copy()
    min_return = df_top5["수익률(%)"].min()
    df_top5["조정_수익률"] = df_top5["수익률(%)"] - min_return + 1
    total_adj_return = df_top5["조정_수익률"].sum()
    
    # 투자금 배분 (최대 잔여수 방법)
    exact_amounts = (df_top5["조정_수익률"] / total_adj_return) * total_investment_usd
    df_top5["투자금($)"] = exact_amounts.astype(int)
    remainders = exact_amounts - df_top5["투자금($)"]
    deficit = int(total_investment_usd - df_top5["투자금($)"].sum())
    
    if deficit > 0:
        top_remainder_indices = remainders.nlargest(deficit).index
        df_top5.loc[top_remainder_indices, "투자금($)"] += 1

    df_top5["투자 비율(%)"] = round((df_top5["조정_수익률"] / total_adj_return) * 100, 2)
    
    # 최종 데이터프레임 정리 (컬럼 순서 변경: 투자금 -> 투자 비율 -> 수익률)
    df_final = df_top5[["종목명", "투자금($)", "투자 비율(%)", "수익률(%)"]].reset_index(drop=True)
    df_final.index = df_final.index + 1 # 인덱스를 1부터 시작

    st.success(f"분석 완료! 총 **${df_final['투자금($)'].sum()}** 단위로 최적의 배분이 완료되었습니다.")
    
    st.divider()

    # --- 화면 출력 (UI 구성) ---
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.subheader("📋 이번 달 매수 리스트")
        # 데이터프레임 깔끔하게 출력 (포맷팅 순서도 맞춤 정렬)
        st.dataframe(
            df_final.style.format({
                "투자금($)": "${}",
                "투자 비율(%)": "{:.2f}%",
                "수익률(%)": "{:.2f}%"
            }),
            use_container_width=True
        )
        
        # CSV 다운로드 버튼
        csv = df_final.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 매수 계획 CSV 다운로드",
            data=csv,
            file_name=f"소수점투자_계획_{datetime.today().strftime('%Y%m%d')}.csv",
            mime='text/csv',
        )

    with col2:
        st.subheader("📊 종목별 투자금 배분 비율")
        # 투자금 기준 바 차트 시각화
        chart_data = df_final.set_index("종목명")[["투자금($)"]]
        st.bar_chart(chart_data)

else:
    st.error("분석할 수 있는 데이터가 없습니다. 네트워크 상태나 티커 설정을 확인해 주세요.")
