import os, shutil, datetime, requests
import pandas as pd, matplotlib.pyplot as plt
import yfinance as yf

TODAY = datetime.date.today()
START = TODAY - datetime.timedelta(days=90)

# --- Brent (Yahoo Finance) ---
# yfinance auto_adjust=True ile 'Close' döndürür; 'Adj Close' yok.
brent_df = yf.download("BZ=F", start=START, end=TODAY, auto_adjust=True, progress=False, threads=False)
if brent_df.empty:
    raise RuntimeError("Brent data could not be downloaded")
brent = brent_df["Close"].rename("Brent")
brent.index = pd.to_datetime(brent.index).tz_localize(None)


# --- JKM (Platts, opsiyonel) ---
token = os.getenv("PLATTS_TOKEN", "")
jkm = pd.Series(dtype=float, name="JKM")
if token:
    try:
        url = "https://api.platts.com/energy/v1/Prices?$filter=Symbol%20eq%20'JKM1'"
        r = requests.get(url, headers={"Authorization": f"Bearer {token}", "accept":"application/json"}, timeout=20)
        r.raise_for_status()
        df = pd.json_normalize(r.json()["data"])
        jkm = pd.Series(df["Price"].astype(float).values,
                        index=pd.to_datetime(df["PriceDate"]), name="JKM").sort_index()
        jkm = jkm.loc[str(START): str(TODAY)]
    except Exception as e:
        print("JKM alınamadı:", e)

# --- Birleştir & normalize (=100) ---
df = pd.concat([brent, jkm], axis=1).dropna(how="all")
if "JKM" in df and df["JKM"].notna().sum() > 0:
    df_norm = df.div(df.iloc[0]).mul(100)
    subtitle = "Brent vs JKM – 90 gün (Normalized = 100)"
else:
    df_norm = df[["Brent"]].div(df["Brent"].iloc[0]).mul(100)
    subtitle = "Brent – 90 gün (JKM beklemede)"

# --- Çiz & kaydet ---
plt.figure(figsize=(8,4))
df_norm.plot(ax=plt.gca(), linewidth=2)
plt.title(subtitle)
plt.ylabel("Index (first day = 100)")
plt.grid(True, alpha=.3); plt.tight_layout()

out_dir = "docs/img"; os.makedirs(out_dir, exist_ok=True)
out = f"{out_dir}/brent_jkm_{TODAY}.png"
plt.savefig(out, dpi=200)
shutil.copy(out, f"{out_dir}/brent_jkm_latest.png")
print("Saved:", out)
