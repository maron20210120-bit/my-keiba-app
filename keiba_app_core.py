import sqlite3
import pandas as pd

def safe_read_csv(csv_file):
    """Shift-JIS, CP932, UTF-8 の順に試して確実にCSVを読み込む関数"""
    encodings = ["shift_jis", "cp932", "utf-8"]
    for enc in encodings:
        try:
            return pd.read_csv(csv_file, encoding=enc)
        except Exception:
            continue
    # すべて失敗した場合は、エラーを無視して強制的に読み込む
    return pd.read_csv(csv_file, encoding="shift_jis", errors="ignore")

def import_and_score_hanro(csv_file="坂路調教データ.csv"):
    df = safe_read_csv(csv_file)
    time_cols = ["Time1", "Lap2", "Lap1"]
    for col in time_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[
        (df["Time1"] >= 45.0) & (df["Time1"] <= 60.0) & 
        (df["Lap2"] <= 20.0) & (df["Lap1"] >= 10.0) & (df["Lap1"] <= 20.0)
    ]
    df["acceleration"] = df["Lap2"] - df["Lap1"]
    df["training_score"] = (100 + ((55.0 - df["Time1"]) * 5) + (df["acceleration"] * 10)).round(1)

    conn = sqlite3.connect("keiba_training.db")
    df.to_sql("scored_hanro_training", conn, if_exists="replace", index=False)
    conn.close()

def import_and_score_wood(csv_file="ウッド調教データ.csv"):
    df_wood = safe_read_csv(csv_file)
    time_cols = ["5F", "Lap2", "Lap1"]
    for col in time_cols:
        df_wood[col] = pd.to_numeric(df_wood[col], errors="coerce")

    df_wood = df_wood[
        (df_wood["5F"] >= 60.0) & (df_wood["5F"] <= 75.0) & 
        (df_wood["Lap2"] >= 10.0) & (df_wood["Lap2"] <= 20.0) & 
        (df_wood["Lap1"] >= 10.0) & (df_wood["Lap1"] <= 20.0)
    ]
    df_wood["acceleration"] = df_wood["Lap2"] - df_wood["Lap1"]
    df_wood["training_score"] = (100 + ((68.0 - df_wood["5F"]) * 3) + (df_wood["acceleration"] * 10)).round(1)

    conn = sqlite3.connect("keiba_training.db")
    df_wood.to_sql("scored_wood_training", conn, if_exists="replace", index=False)
    conn.close()

def get_latest_score(horse_name):
    conn = sqlite3.connect("keiba_training.db")
    try:
        query = f"SELECT training_score FROM scored_hanro_training WHERE 馬名='{horse_name}' UNION ALL SELECT training_score FROM scored_wood_training WHERE 馬名='{horse_name}'"
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty: return df["training_score"].max()
    except Exception:
        pass
    return 100.0
