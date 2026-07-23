import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import keiba_app_core

st.set_page_config(page_title="独自競馬予想アプリ", page_icon="🐴", layout="wide")
st.title("🐴 独自調教スコア予想アプリ")
st.caption("JRA-VANデータ連動システム")

tab1, tab2, tab3, tab4 = st.tabs(["🏆 出馬表・自動予想", "🔍 馬名検索", "📈 的中・回収率検証", "⚙️ データ管理"])

def color_rows(row):
    bg_color = ""
    if "◎" in str(row["予想印"]): bg_color = "background-color: #fff3cd; color: #856404; font-weight: bold;"
    elif "〇" in str(row["予想印"]): bg_color = "background-color: #f8d7da; color: #721c24; font-weight: bold;"
    elif "▲" in str(row["予想印"]): bg_color = "background-color: #d1ecf1; color: #0c5460; font-weight: bold;"
    elif "△" in str(row["予想印"]): bg_color = "background-color: #e2e3e5; color: #383d41;"
    return [bg_color] * len(row)

# タブ1: 出馬表・自動予想
with tab1:
    st.header("今週末のレース予想")
    default_horses = "エヒト, レッドロスタム, リオサラ, ルクスノア, マクアケ"
    input_horses = st.text_area("出走馬リスト", value=default_horses)
    if st.button("📊 予想印を自動計算する", type="primary"):
        try:
            horse_list = [h.strip() for h in input_horses.split(",") if h.strip()]
            race_data = []
            for horse in horse_list:
                score = keiba_app_core.get_latest_score(horse)
                race_data.append({"馬名": horse, "調教スコア": score})
            df_race = pd.DataFrame(race_data).sort_values(by="調教スコア", ascending=False).reset_index(drop=True)
            df_race["予想印"] = "・"
            if len(df_race) > 0: df_race.loc[0, "予想印"] = "◎ (本命)"
            if len(df_race) > 1: df_race.loc[1, "予想印"] = "〇 (対抗)"
            if len(df_race) > 2: df_race.loc[2, "予想印"] = "▲ (単穴)"
            for i in range(3, min(5, len(df_race))): df_race.loc[i, "予想印"] = "△ (連下)"
            styled_df = df_race[["予想印", "馬名", "調教スコア"]].style.apply(color_rows, axis=1).format(precision=1)
            st.subheader("📋 予想結果一覧")
            st.dataframe(styled_df, use_container_width=True)
        except Exception:
            st.error("⚠️ データベースを『データ管理』タブで更新してください。")

# タブ2: 馬名検索
with tab2:
    st.header("🔍 調教履歴個別検索")
    search_name = st.text_input("調べたい馬の名前を入力してください", value="レッドロスタム")
    if st.button("検索実行"):
        try:
            conn = sqlite3.connect("keiba_training.db")
            df_hanro = pd.read_sql(f"SELECT 年月日, '坂路' AS コース, Time1 AS 全体タイム, Lap2, Lap1, training_score FROM scored_hanro_training WHERE 馬名='{search_name}'", conn)
            df_wood = pd.read_sql(f"SELECT 年月日, 'ウッド' AS コース, [5F] AS 全体タイム, Lap2, Lap1, training_score FROM scored_wood_training WHERE 馬名='{search_name}'", conn)
            conn.close()
            df_combined = pd.concat([df_hanro, df_wood], ignore_index=True)
            if df_combined.empty: st.warning(f"「{search_name}」の調教データが見つかりませんでした。")
            else: st.dataframe(df_combined.sort_values(by="年月日", ascending=False), use_container_width=True)
        except Exception:
            st.error("⚠️ まだデータが登録されていません。")

# タブ3: 的中・回収率検証
with tab3:
    st.header("📈 独自調教スコア 回収率検証シミュレーター")
    score_threshold = st.slider("検証する最低調教スコア", min_value=100.0, max_value=140.0, value=115.0, step=0.5)

    if st.button("🚀 シミュレーションを実行する", type="primary"):
        try:
            conn = sqlite3.connect("keiba_training.db")
            query = f"""
                SELECT h.年月日, h.馬名, h.training_score, r.着順, r.単勝オッズ 
                FROM scored_hanro_training h
                INNER JOIN race_results r ON h.馬名 = r.馬名 AND h.年月日 = r.年月日
                WHERE h.training_score >= {score_threshold}
                UNION ALL
                SELECT w.年月日, w.馬名, w.training_score, r.着順, r.単勝オッズ 
                FROM scored_wood_training w
                INNER JOIN race_results r ON w.馬名 = r.馬名 AND w.年月日 = r.年月日
                WHERE w.training_score >= {score_threshold}
            """
            df_v = pd.read_sql(query, conn)
            conn.close()

            if df_v.empty:
                st.warning("指定したスコア以上の馬が、過去のレース結果データ内に見つかりませんでした。")
            else:
                df_v["単勝オッズ"] = pd.to_numeric(df_v["単勝オッズ"], errors="coerce").fillna(0)
                df_v["is_win"] = df_v["着順"].astype(str).str.strip().isin(["1", "01", "１"])
                df_v["payback"] = df_v.apply(lambda r: r["単勝オッズ"] * 100 if r["is_win"] else 0, axis=1)

                total_bets = len(df_v)
                win_counts = df_v["is_win"].sum()
                total_investment = total_bets * 100
                total_return = df_v["payback"].sum()

                hit_rate = (win_counts / total_bets * 100) if total_bets > 0 else 0
                recovery_rate = (total_return / total_investment * 100) if total_investment > 0 else 0

                col1, col2, col3 = st.columns(3)
                col1.metric("総買い目（頭数）", f"{total_bets} 頭")
                col2.metric("🎯 単勝的中率", f"{hit_rate:.1f} %")
                col3.metric("💰 単勝回収率", f"{recovery_rate:.1f} %")

                df_v = df_v.sort_values(by="年月日").reset_index(drop=True)
                df_v["累計投資"] = (df_v.index + 1) * 100
                df_v["累計払戻"] = df_v["payback"].cumsum()
                df_v["累計回収率"] = (df_v["累計払戻"] / df_v["累計投資"]) * 100

                st.subheader("📉 回収率の資産推移グラフ")
                fig = px.line(df_v, x="年月日", y="累計回収率", title=f"スコア {score_threshold} 以上の馬を買い続けた場合の累計回収率推移")
                fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="回収率100%ライン")
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"⚠️ 検証中にエラーが発生しました。 (詳細: {e})")

# タブ4: データ管理
with tab4:
    st.header("⚙️ データベース一括更新")
    if st.button("🔄 データを最新にアップデートする"):
        with st.spinner("サーバー上でCSVファイルをスキャンしてDBを構築中..."):
            try:
                # サーバー側での初期化・流し込み処理を安全に実行
                keiba_app_core.import_and_score_hanro()
                keiba_app_core.import_and_score_wood()
                st.success("🎉 スマホ用のデータベース構築が100%大成功しました！「的中・回収率検証」タブに戻ってシミュレーションを実行してください！")
            except Exception as ex:
                st.error(f"❌ 読み込みエラー: {ex}")
