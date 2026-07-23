import streamlit as st
import sqlite3
import pandas as pd
import keiba_app_core  # 先ほど作ったコアエンジンを読み込み

st.set_page_config(page_title="独自競馬予想アプリ", page_icon="🐴", layout="wide")

st.title("🐴 独自調教スコア予想アプリ")
st.caption("JRA-VANデータ連動システム")

tab1, tab2, tab3 = st.tabs(["🏆 出馬表・自動予想", "🔍 馬名検索", "⚙️ データ管理"])

# タブ1: 出馬表・自動予想画面
with tab1:
    st.header("今週末のレース予想")
    st.write("出走する馬の名前をカンマ（,）区切りで入力してください。")
    default_horses = "エヒト, レッドロスタム, リオサラ, ルクスノア, マクアケ"
    input_horses = st.text_area("出走馬リスト", value=default_horses)

    if st.button("📊 予想印を自動計算する", type="primary"):
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
        for i in range(3, min(5, len(df_race))):
            df_race.loc[i, "予想印"] = "△ (連下)"

        st.subheader("📋 予想結果一覧")
        st.dataframe(df_race[["予想印", "馬名", "調教スコア"]], use_container_width=True)

# タブ2: 馬名検索画面
with tab2:
    st.header("🔍 調教履歴個別検索")
    search_name = st.text_input("調べたい馬の名前を入力してください", value="レッドロスタム")

    if st.button("検索実行"):
        conn = sqlite3.connect("keiba_training.db")
        query_hanro = f"SELECT 年月日, '坂路' AS コース, Time1 AS 全体タイム, Lap2, Lap1, training_score FROM scored_hanro_training WHERE 馬名 = '{search_name}'"
        df_hanro = pd.read_sql(query_hanro, conn)
        query_wood = f"SELECT 年月日, 'ウッド' AS コース, [5F] AS 全体タイム, Lap2, Lap1, training_score FROM scored_wood_training WHERE 馬名 = '{search_name}'"
        df_wood = pd.read_sql(query_wood, conn)
        conn.close()

        df_combined = pd.concat([df_hanro, df_wood], ignore_index=True)
        if df_combined.empty:
            st.warning(f"「{search_name}」の調教データが見つかりませんでした。")
        else:
            df_combined = df_combined.sort_values(by="年月日", ascending=False)
            st.success(f"「{search_name}」の調教履歴が {len(df_combined)} 件見つかりました。")
            st.dataframe(df_combined, use_container_width=True)

# タブ3: データ管理画面
with tab3:
    st.header("⚙️ データベース一括更新")
    if st.button("🔄 データを最新にアップデートする"):
        with st.spinner("CSVファイルを読み込み中..."):
            keiba_app_core.import_and_score_hanro()
            keiba_app_core.import_and_score_wood()
        st.success("🎉 全調教データの更新と再スコア化が完了しました！")
