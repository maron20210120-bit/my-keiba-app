import sqlite3
import pandas as pd


def import_and_score_hanro(csv_file="坂路調教データ.csv"):
    """坂路調教CSVを読み込み、クレンジング・スコア化してDBに保存する関数"""
    try:
        df = pd.read_csv(csv_file, encoding="shift_jis")

        # タイムデータを数値に変換
        time_cols = ["Time1", "Lap2", "Lap1"]
        for col in time_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # データクレンジング（正常な坂路調教のみに限定、ハーレムライン等の異常値も排除）
        df = df[
            (df["Time1"] >= 45.0)
            & (df["Time1"] <= 60.0)
            & (df["Lap2"] <= 20.0)
            & (df["Lap1"] >= 10.0)
            & (df["Lap1"] <= 20.0)
        ]

        # スコア計算（ベース100点 ＋ 全体時計ボーナス ＋ 加速ボーナス）
        df["acceleration"] = df["Lap2"] - df["Lap1"]
        df["training_score"] = (
            100 + ((55.0 - df["Time1"]) * 5) + (df["acceleration"] * 10)
        )
        df["training_score"] = df["training_score"].round(1)

        # データベースに保存
        conn = sqlite3.connect("keiba_training.db")
        df.to_sql(
            "scored_hanro_training", conn, if_exists="replace", index=False
        )
        conn.close()
        print("✅ 坂路調教データの更新・スコア化が完了しました。")
    except Exception as e:
        print(f"❌ 坂路データの処理中にエラーが発生しました: {e}")


def import_and_score_wood(csv_file="ウッド調教データ.csv"):
    """ウッド調教CSVを読み込み、クレンジング・スコア化してDBに保存する関数"""
    try:
        df_wood = pd.read_csv(csv_file, encoding="shift_jis")

        # タイムデータを数値型に変換
        time_cols = ["5F", "Lap2", "Lap1"]
        for col in time_cols:
            df_wood[col] = pd.to_numeric(df_wood[col], errors="coerce")

        # データクレンジング（正常な5Fウッド調教のみに限定）
        df_wood = df_wood[
            (df_wood["5F"] >= 60.0)
            & (df_wood["5F"] <= 75.0)
            & (df_wood["Lap2"] >= 10.0)
            & (df_wood["Lap2"] <= 20.0)
            & (df_wood["Lap1"] >= 10.0)
            & (df_wood["Lap1"] <= 20.0)
        ]

        # スコア計算（ベース100点 ＋ 5F全体の時計ボーナス ＋ 加速ボーナス）
        df_wood["acceleration"] = df_wood["Lap2"] - df_wood["Lap1"]
        df_wood["training_score"] = (
            100
            + ((68.0 - df_wood["5F"]) * 3)
            + (df_wood["acceleration"] * 10)
        )
        df_wood["training_score"] = df_wood["training_score"].round(1)

        # データベースに保存
        conn = sqlite3.connect("keiba_training.db")
        df_wood.to_sql(
            "scored_wood_training", conn, if_exists="replace", index=False
        )
        conn.close()
        print("✅ ウッド調教データの更新・スコア化が完了しました。")
    except Exception as e:
        print(f"❌ ウッドデータの処理中にエラーが発生しました: {e}")


def get_latest_score(horse_name):
    """指定した馬の直近の調教スコアをDBから探して返す関数"""
    conn = sqlite3.connect("keiba_training.db")
    query = f"""
        SELECT training_score FROM scored_hanro_training WHERE 馬名 = '{horse_name}'
        UNION ALL
        SELECT training_score FROM scored_wood_training WHERE 馬名 = '{horse_name}'
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if not df.empty:
        return df["training_score"].max()
    return 100.0  # データがない馬は基準点


def generate_race_prediction(race_name, horse_list):
    """馬名リスト（出馬表）を受け取り、調教スコア順に予想印を打つメイン関数"""
    race_data = []
    for horse in horse_list:
        score = get_latest_score(horse)
        race_data.append({"馬名": horse, "調教スコア": score})

    df_race = pd.DataFrame(race_data)
    df_race = df_race.sort_values(by="調教スコア", ascending=False).reset_index(
        drop=True
    )

    df_race["予想印"] = "・"
    if len(df_race) > 0:
        df_race.loc[0, "予想印"] = "◎ (本命)"
    if len(df_race) > 1:
        df_race.loc[1, "予想印"] = "〇 (対抗)"
    if len(df_race) > 2:
        df_race.loc[2, "予想印"] = "▲ (単穴)"
    for i in range(3, min(5, len(df_race))):
        df_race.loc[i, "予想印"] = "△ (連下)"

    print(f"\n🏆 【{race_name}】 独自調教スコア・自動予想新聞 🏆")
    print("======================================================")
    print(df_race[["予想印", "馬名", "調教スコア"]].to_string(index=False))
    print("======================================================")


# --- スクリプトが直接実行された場合のテスト動作 ---
if __name__ == "__main__":
    print("--- 競馬予想アプリ：コアエンジン一括処理を開始 ---")
    import_and_score_hanro()
    import_and_score_wood()

    # 動作確認用の模擬レース実行
    test_race = "調教G1・チャンピオンシップ"
    test_horses = ["レッドロスタム", "エヒト", "マクアケ", "ルクスノア", "リオサラ"]
    generate_race_prediction(test_race, test_horses)
