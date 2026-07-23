import streamlit as st
import sqlite3
import pandas as pd
import keiba_app_core

st.set_page_config(page_title="独自競馬予想アプリ", page_icon="🐴", layout="wide")
st.title("🐴 独自調教スコア予想アプリ")
st.caption("JRA-VANデータ連動システム")

tab1, tab2, tab3 = st.tabs(["🏆 出馬表・自動予想", "🔍 馬名検索", "⚙️ データ管理"])

# --- 背景色を自動で塗り分けるためのデザイン関数 ---
def color_rows(row):
    # 行全体の色を初期化（透明）
    bg_color = ""

    # 予想印の文字に合わせて背景色を決定
    if "◎" in str(row["予想印"]):
        bg_color = "background-color: #fff3cd; color: #856404; font-weight: bold;"  # 薄い黄色
    elif "〇" in str(row["予想印"]):
        bg_color = "background-color: #f8d7da; color: #721c24; font-weight: bold;"  # 薄いピンク
    elif "▲" in str(row["予想印"]):
        bg_color = "background-color: #d1ecf1; color: #0c5460; font-weight: bold;"  # 薄い水色
    elif "△" in str(row["予想印"]):
        bg_color = "background-color: #e2e3e5; color: #383d41;"  # 薄いグレー

    return [bg_color] * len(row)

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

            # 【カラフル装飾の適用】
            # .style.apply を使って、各行に色をつける関数を呼び出します
            styled_df = df_race[["予想印", "馬名", "調教スコア"]].style.apply(color_rows, axis=1).format(precision=1)

            st.subheader("📋 予想結果一覧")
            # 装飾したデータを画面に表示
            st.dataframe(styled_df, use_container_width=True)

        except Exception:
            st.error("⚠️ データベースが未作成の可能性があります。『データ管理』タブで更新を行ってください。")

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

with tab3:
    st.header("⚙️ データベース一括更新")
    if st.button("🔄 データを最新にアップデートする"):
        with st.spinner("CSVファイルを読み込み中..."):
            try:
                keiba_app_core.import_and_score_hanro()
                keiba_app_core.import_and_score_wood()
                st.success("🎉 全調教データの更新と再スコア化が完了しました！")
            except Exception as ex:
                st.error(f"❌ エラー: CSVファイルが見つかりません。 (エラー型: {type(ex).__name__})")
