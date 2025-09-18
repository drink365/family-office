
# app.py — 家族辦公室評估平台 v5
# 模組一：股利決策與稅負（兩階段＋AMT＋未分配稅＋個人二擇一）
# 模組二：傳承與移轉規劃（遺產／贈與／保險／信託示意）
# 模組三：AI秒算遺產稅（整合你上傳的 estate_tax_app.py）
# © 永傳家族辦公室｜教學示意（非法律／稅務意見）

import streamlit as st

import base64, pathlib

# ---- Branding: favicon & font ----
# Set page icon if file exists
from pathlib import Path
page_icon_path = Path(__file__).with_name("logo2.png")
if page_icon_path.exists():
    try:
        st.set_page_config(page_title="家族辦公室評估平台 v6", page_icon=str(page_icon_path), layout="wide")
    except Exception:
        pass
else:
    try:
        st.set_page_config(page_title="家族辦公室評估平台 v6", layout="wide")
    except Exception:
        pass

# Load custom font and inject CSS
font_path = Path(__file__).with_name("NotoSansTC-Regular.ttf")
if font_path.exists():
    try:
        font_data = font_path.read_bytes()
        font_b64 = base64.b64encode(font_data).decode()
        st.markdown(f"""
            <style>
            @font-face {{
                font-family: 'NotoSansTC';
                src: url(data:font/ttf;base64,{font_b64}) format('truetype');
                font-weight: normal;
                font-style: normal;
            }}
            html, body, [class^="css"]  {{
                font-family: 'NotoSansTC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, 'Noto Sans TC', 'PingFang TC', 'Heiti TC', sans-serif !important;
            }}
            .branding-header {{
                display: flex; align-items: center; gap: 12px;
            }}
            .branding-title {{
                font-size: 22px; font-weight: 700; letter-spacing: .5px;
            }}
            </style>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.write("Font load error:", e)

# Header with logo
logo_path = Path(__file__).with_name("logo.png")
if logo_path.exists():
    st.markdown('<div class="branding-header">', unsafe_allow_html=True)
    st.image(str(logo_path), width=140)
    st.markdown('<div class="branding-title">《影響力》傳承策略平台｜永傳家族辦公室</div></div>', unsafe_allow_html=True)
else:
    st.title("《影響力》傳承策略平台｜永傳家族辦公室")

# ---- Paywall helper ----

# ---- Enhanced Paywall: also accept secrets-based user login ----

# ---- Session helpers (TTL + user info bar) ----
from datetime import datetime, timedelta

SESSION_TTL_SECS = 3600  # 1 hour

def _session_now():
    try:
        # use UTC for consistency
        return datetime.utcnow()
    except Exception:
        return datetime.now()

def session_is_expired():
    ts = st.session_state.get("paid_unlocked_at")
    ttl = st.session_state.get("session_ttl_secs", SESSION_TTL_SECS)
    if not ts:
        return False
    try:
        started = datetime.fromisoformat(ts)
        return _session_now() > started + timedelta(seconds=int(ttl))
    except Exception:
        return False

def render_user_info_bar():
    if st.session_state.get("paid_unlocked") and not session_is_expired():
        meta = st.session_state.get("paid_user_meta", {})
        name = meta.get("name") or meta.get("role") or "已登入使用者"
        start = meta.get("start_date", "-")
        end = meta.get("end_date", "-")
        via = meta.get("via", "user")
        # Remaining time
        try:
            started = datetime.fromisoformat(st.session_state.get("paid_unlocked_at"))
            ttl = int(st.session_state.get("session_ttl_secs", SESSION_TTL_SECS))
            remain = (started + timedelta(seconds=ttl) - _session_now()).total_seconds()
            mins = max(0, int(remain // 60))
        except Exception:
            mins = "-"
        cols = st.columns([0.85, 0.15])
        with cols[0]:
            st.info(f"👤 {name}｜有效期：{start} ➜ {end}｜登入方式：{via}｜Session 剩餘：約 {mins} 分鐘")
        with cols[1]:
            if st.button("登出", use_container_width=True):
                for k in ["paid_unlocked","paid_user_meta","paid_unlocked_at","session_ttl_secs"]:
                    st.session_state.pop(k, None)
                st.success("已登出。")
                st.experimental_rerun()
    else:
        # If expired, auto lock and prompt
        if st.session_state.get("paid_unlocked") and session_is_expired():
            for k in ["paid_unlocked","paid_user_meta","paid_unlocked_at","session_ttl_secs"]:
                st.session_state.pop(k, None)
            st.warning("您的進階權限 Session 已逾期（1 小時）。請重新解鎖或登入。")

from datetime import datetime

def _check_user_login(u, p):
    try:
        auth = st.secrets.get("authorized_users", {})
    except Exception:
        auth = {}
    # auth is expected to be a dict of sections: { "admin": {...}, "user1": {...} }
    for key, rec in (auth.items() if isinstance(auth, dict) else []):
        try:
            username = str(rec.get("username","")).strip()
            password = str(rec.get("password","")).strip()
            if u.strip() == username and p.strip() == password:
                # Date window check (YYYY-MM-DD)
                start = rec.get("start_date")
                end = rec.get("end_date")
                today = datetime.utcnow().date()
                ok_date = True
                def _parse(d):
                    try:
                        return datetime.strptime(d, "%Y-%m-%d").date()
                    except Exception:
                        return None
                if start:
                    s = _parse(str(start))
                    if s and today < s: ok_date = False
                if end:
                    e = _parse(str(end))
                    if e and today > e: ok_date = False
                meta = {"role": key, "name": rec.get("name", key), "valid": ok_date}
                return ok_date, meta
        except Exception:
            continue
    return False, {}

def paid_gate():
    st.subheader("專業版解鎖")
    tabs = st.tabs(["輸入啟用碼", "帳號登入"])
    unlocked = st.session_state.get("paid_unlocked", False)
    meta_info = st.session_state.get("paid_user_meta")

    with tabs[0]:
        st.caption("方式一：輸入付費啟用碼以解鎖（支援多組碼）")
        code = st.text_input("啟用碼（不分大小寫）", type="password", key="code_unlock")
        # Read from secrets
        paid_codes = []
        try:
            sc = st.secrets.get("PAID_CODES")
            if isinstance(sc, list):
                paid_codes = [str(x).strip().lower() for x in sc]
            elif isinstance(sc, str):
                paid_codes = [sc.strip().lower()]
        except Exception:
            pass
        if not paid_codes:
            paid_codes = ["demo-1234"]  # fallback demo
        if code:
            if code.strip().lower() in paid_codes:
                st.success("已用啟用碼解鎖進階功能。")
                st.session_state["paid_unlocked"] = True
                st.session_state["paid_user_meta"] = {"via": "code"}
                st.session_state["paid_unlocked_at"] = _session_now().isoformat()
                st.session_state["session_ttl_secs"] = SESSION_TTL_SECS
                unlocked = True

    with tabs[1]:
        st.caption("方式二：使用管理者提供的帳號密碼登入（依有效期限啟用）。")
        u = st.text_input("帳號", key="login_user")
        p = st.text_input("密碼", type="password", key="login_pass")
        if st.button("登入", use_container_width=True):
            ok, meta = _check_user_login(u, p)
            if ok:
                st.success(f"歡迎 {meta.get('name','')}！進階功能已解鎖。")
                st.session_state["paid_unlocked"] = True
                st.session_state["paid_user_meta"] = meta
                st.session_state["paid_unlocked_at"] = _session_now().isoformat()
                st.session_state["session_ttl_secs"] = SESSION_TTL_SECS
                unlocked = True
            else:
                st.error("帳號或密碼錯誤，或不在有效期間內。")

    if unlocked:
        mi = st.session_state.get("paid_user_meta", {})
        note = f"（解鎖來源：{mi.get('via','user')}）" if mi else ""
        st.caption("目前狀態：✅ 已解鎖進階功能 " + note)
    return unlocked

import pandas as pd
import matplotlib.pyplot as plt

# ====== 模組三整合：載入外部 estate_tax_app.py（避免重複 set_page_config） ======
import importlib.util, types, sys, os

def load_estate_module(module_path: str):
    spec = importlib.util.spec_from_file_location("estate_tax_app", module_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["estate_tax_app"] = mod
    spec.loader.exec_module(mod)
    # 將 st.set_page_config 改為 no-op，避免在分頁內二次呼叫
    mod.st.set_page_config = lambda *args, **kwargs: None
    return mod

estate_mod = load_estate_module(os.path.join(os.path.dirname(__file__), "estate_tax_app.py"))

# ====== 模組一：股利決策與稅負（採 v3 核心） ======
DEFAULT_BRACKETS = [
    (540000,   0.05,      0),
    (1210000,  0.12,  37800),
    (2420000,  0.20, 134600),
    (4530000,  0.30, 376600),
    (10310000, 0.40, 829600),
    (float("inf"), 0.45, 1345100),
]
DIVIDEND_CREDIT_RATE = 0.085
DIVIDEND_CREDIT_CAP  = 80_000

def prog_tax_quick(taxable, brackets):
    for upper, rate, quick in brackets:
        if taxable <= upper:
            return max(0.0, taxable * rate - quick)
    return max(0.0, taxable * brackets[-1][1] - brackets[-1][2])

def indiv_div_tax(amount, mode, other_income=0.0, brackets=DEFAULT_BRACKETS):
    if amount <= 0: return 0.0
    if mode == "split28": return amount * 0.28
    tax_with = prog_tax_quick(other_income + amount, brackets)
    tax_wo   = prog_tax_quick(other_income, brackets)
    incr = max(0.0, tax_with - tax_wo)
    credit = min(amount * DIVIDEND_CREDIT_RATE, DIVIDEND_CREDIT_CAP)
    return max(0.0, incr - credit)

def simulate_dividend_policy(
    years=30, pretax_profit=20_000_000.0, corp_tax_rate=0.20, corp_amt_min_rate=0.12,
    undistributed_tax_rate=0.05, init_capital=1_000_000.0,
    legal_reserve_on=True, legal_reserve_rate=0.10, legal_reserve_cap=0.25,
    phase1_years=10, phase1_cash_pct=0.0, phase1_stock_pct=0.0,
    phase2_cash_pct=0.0, phase2_stock_pct=0.0,
    shareholder_kind="individual_resident", indiv_tax_mode="split28",
    indiv_other_income=0.0, nonresident_withholding=0.21, capital_surplus_to_capital=0.0,
):
    rows=[]; capital=init_capital; retained_earnings=0.0; legal_reserve=0.0; cap_surplus=0.0
    for y in range(1, years+1):
        corp_tax = max(pretax_profit*corp_tax_rate, pretax_profit*corp_amt_min_rate)
        after_tax = max(0.0, pretax_profit - corp_tax)
        to_legal=0.0
        if legal_reserve_on:
            target=capital*legal_reserve_cap
            room=max(0.0, target-legal_reserve)
            to_legal=min(after_tax*legal_reserve_rate, room)
        dist_base = after_tax - to_legal
        cash_pct = phase1_cash_pct if y<=phase1_years else phase2_cash_pct
        stock_pct= phase1_stock_pct if y<=phase1_years else phase2_stock_pct
        cash=dist_base*cash_pct; stock=dist_base*stock_pct
        keep=max(0.0, dist_base - cash - stock)
        capital += stock
        retained_earnings += keep
        legal_reserve += to_legal
        if capital_surplus_to_capital>0 and cap_surplus>0:
            take=min(cap_surplus, capital_surplus_to_capital); capital+=take; cap_surplus-=take
        undist_tax = keep*undistributed_tax_rate
        if shareholder_kind=="corporate_resident":
            sh_tax=0.0
        elif shareholder_kind=="individual_resident":
            sh_tax=indiv_div_tax(cash+stock, indiv_tax_mode, indiv_other_income, DEFAULT_BRACKETS)
        else:
            sh_tax=(cash+stock)*nonresident_withholding
        total_co = corp_tax+undist_tax; total = total_co+sh_tax
        rows.append({
            "年度":y,"公司稅(含AMT)":corp_tax,"稅後盈餘":after_tax,"提列法定公積":to_legal,
            "現金股利":cash,"股票股利":stock,"本年留存":keep,"未分配盈餘稅":undist_tax,"股東層稅":sh_tax,
            "公司本年合計稅":total_co,"本年總稅負":total,"期末資本額":capital,"期末保留盈餘":retained_earnings,
            "期末法定盈餘公積":legal_reserve,"期末股東權益(概算)":capital+retained_earnings+legal_reserve
        })
    df=pd.DataFrame(rows)
    totals={
        "合計—公司稅(含未分配稅)":float(df["公司本年合計稅"].sum()),
        "合計—股東層稅":float(df["股東層稅"].sum()),
        "合計—總稅負":float(df["本年總稅負"].sum()),
        "期末資本額":float(df["期末資本額"].iloc[-1]),
        "期末保留盈餘":float(df["期末保留盈餅"].iloc[-1]) if "期末保留盈餅" in df.columns else float(df["期末保留盈餘"].iloc[-1]),
        "期末法定盈餘公積":float(df["期末法定盈餘公積"].iloc[-1]),
        "期末股東權益(概算)":float(df["期末股東權益(概算)"].iloc[-1]),
    }
    return {"per_year":df,"totals":totals}

# ====== 模組二：傳承與移轉（簡化自 v4） ======
def tax_progressive(amount, brackets):
    for upper, rate, quick in brackets:
        if amount <= upper:
            return max(0.0, amount*rate - quick)
    return max(0.0, amount*brackets[-1][1] - brackets[-1][2])

def estate_and_gift_simulator(
    equity_value=500_000_000.0,
    personal_assets=50_000_000.0,
    personal_liabilities=0.0,
    estate_exemption=13_330_000.0,
    estate_brackets=[(50_000_000,0.10,0),(100_000_000,0.15,2_500_000),(float("inf"),0.20,7_500_000)],
    annual_exclusion=0.0,
    gift_brackets=[(25_000_000,0.10,0),(50_000_000,0.15,1_250_000),(float("inf"),0.20,3_750_000)],
    insurance_sum=0.0,
    insurance_to_heirs=True,
    years_of_gifting=5,
    annual_gift=10_000_000.0,
    heirs=None,
    trust_toggle=False,
):
    if heirs is None or len(heirs)==0:
        heirs=[{"name":"A","share":0.5},{"name":"B","share":0.5}]
    total_share=sum([h["share"] for h in heirs]) or 1.0
    heirs=[{"name":h["name"],"share":h["share"]/total_share} for h in heirs]

    gross_A = equity_value + personal_assets - personal_liabilities + (0.0 if insurance_to_heirs else insurance_sum)
    taxable_A = max(0.0, gross_A - estate_exemption)
    estate_A = tax_progressive(taxable_A, estate_brackets)
    net_A = gross_A - estate_A + (insurance_sum if insurance_to_heirs else 0.0)

    total_gift_tax_B=0.0; gifted_total=0.0
    for _ in range(int(years_of_gifting)):
        taxable_gift=max(0.0, annual_gift - annual_exclusion)
        total_gift_tax_B += tax_progressive(taxable_gift, gift_brackets)
        gifted_total += annual_gift
    gross_B = max(0.0, equity_value + personal_assets - personal_liabilities - gifted_total) + (0.0 if insurance_to_heirs else insurance_sum)
    taxable_B = max(0.0, gross_B - estate_exemption)
    estate_B = tax_progressive(taxable_B, estate_brackets)
    net_B = gross_B - estate_B + gifted_total + (insurance_sum if insurance_to_heirs else 0.0) - total_gift_tax_B

    gross_C = equity_value + personal_assets - personal_liabilities + (0.0 if insurance_to_heirs else insurance_sum)
    taxable_C = max(0.0, gross_C - estate_exemption)
    estate_C = tax_progressive(taxable_C, estate_brackets)
    net_C = gross_C - estate_C + (insurance_sum if insurance_to_heirs else 0.0)

    if trust_toggle:
        gross_D = max(0.0, equity_value + personal_assets - personal_liabilities - gifted_total)
    else:
        gross_D = gross_B
    taxable_D = max(0.0, gross_D - estate_exemption)
    estate_D = tax_progressive(taxable_D, estate_brackets)
    net_D = gross_D - estate_D + gifted_total - total_gift_tax_B + (insurance_sum if insurance_to_heirs else 0.0)

    summary = pd.DataFrame([
        {"情境":"A 保留至過世","總遺產":gross_A,"遺產稅":estate_A,"贈與稅":0.0,"繼承人最終可得":net_A},
        {"情境":"B 分年贈與","總遺產":gross_B,"遺產稅":estate_B,"贈與稅":total_gift_tax_B,"繼承人最終可得":net_B},
        {"情境":"C 壽險等額補償","總遺產":gross_C,"遺產稅":estate_C,"贈與稅":0.0,"繼承人最終可得":net_C},
        {"情境":"D 信託（示意）","總遺產":gross_D,"遺產稅":estate_D,"贈與稅":total_gift_tax_B,"繼承人最終可得":net_D},
    ])
    allocations=[]
    for _, row in summary.iterrows():
        for h in heirs:
            allocations.append({"情境":row["情境"],"繼承人":h["name"],"比率":h["share"],"分得金額(概算)":row["繼承人最終可得"]*h["share"]})
    return summary, pd.DataFrame(allocations)

# ====== Streamlit UI ======
st.set_page_config(page_title="家族辦公室評估平台 v5", layout="wide")
st.title("家族辦公室評估平台 v5（股利 × 傳承 × AI秒算遺產稅）")

tab1, tab2, tab3 = st.tabs(["模組一｜股利決策與稅負", "模組二｜傳承與移轉規劃", "模組三｜AI秒算遺產稅"])

with tab1:
    st.subheader("兩階段分配＋AMT＋未分配盈餘稅＋個人二擇一")
    col = st.columns(3)
    with st.sidebar:
        st.header("模組一：參數")
        years = st.number_input("年度數", 1, 60, 30, 1)
        pretax = st.number_input("每年稅前盈餘", 0, 2_000_000_000, 20_000_000, 1_000_000)
        corp_tax_rate = st.number_input("公司稅率", 0.0, 0.5, 0.20, 0.01)
        corp_amt_min = st.number_input("公司最低稅負（AMT）", 0.0, 0.5, 0.12, 0.01)
        undist_rate = st.number_input("未分配盈餘稅率", 0.0, 0.2, 0.05, 0.01)
        init_capital = st.number_input("初始資本額", 0, 2_000_000_000, 1_000_000, 100_000)
        lr_on = st.checkbox("啟用法定盈餘公積", True)
        lr_rate = st.slider("提列比例", 0.0, 0.2, 0.10, 0.01)
        lr_cap = st.slider("上限（資本×）", 0.0, 1.0, 0.25, 0.05)
        phase1_years = st.number_input("階段一年數", 0, 60, 10, 1)
        p1_cash = st.slider("階段一：現金股利 %", 0.0, 1.0, 0.0, 0.05)
        p1_stock= st.slider("階段一：股票股利 %", 0.0, 1.0, 0.0, 0.05)
        p2_cash = st.slider("階段二：現金股利 %", 0.0, 1.0, 0.0, 0.05)
        p2_stock= st.slider("階段二：股票股利 %", 0.0, 1.0, 0.0, 0.05)
        kind = st.selectbox("最終股東型別", ["本國個人","本國法人","非居民（外資）"])
        if kind=="本國個人":
            indiv_mode_ch = st.radio("個人課稅模式", ["28% 分開課稅","併入綜所稅（含8.5%抵減）"])
            indiv_mode = "split28" if indiv_mode_ch.startswith("28%") else "integrate"
            other_income = st.number_input("其他綜所稅所得額", 0, 2_000_000_000, 0, 10_000)
            shareholder_kind="individual_resident"; withhold=0.0
        elif kind=="本國法人":
            shareholder_kind="corporate_resident"; indiv_mode="split28"; other_income=0.0; withhold=0.0
        else:
            shareholder_kind="nonresident"; indiv_mode="split28"; other_income=0.0
            withhold = st.number_input("非居民股利扣繳率（條約）", 0.0, 0.30, 0.21, 0.01)
        cap_surplus_to_cap = st.number_input("資本公積轉增資（每年）", 0, 100_000_000, 0, 100_000)
    res = simulate_dividend_policy(
        years=int(years), pretax_profit=float(pretax), corp_tax_rate=float(corp_tax_rate),
        corp_amt_min_rate=float(corp_amt_min), undistributed_tax_rate=float(undist_rate),
        init_capital=float(init_capital), legal_reserve_on=bool(lr_on),
        legal_reserve_rate=float(lr_rate), legal_reserve_cap=float(lr_cap),
        phase1_years=int(phase1_years), phase1_cash_pct=float(p1_cash), phase1_stock_pct=float(p1_stock),
        phase2_cash_pct=float(p2_cash), phase2_stock_pct=float(p2_stock),
        shareholder_kind=shareholder_kind, indiv_tax_mode=indiv_mode,
        indiv_other_income=float(other_income), nonresident_withholding=float(withhold),
        capital_surplus_to_capital=float(cap_surplus_to_cap),
    )
    st.write("**總結**"); st.write(pd.DataFrame([res["totals"]]))
    st.write("**年度明細**"); st.dataframe(res["per_year"])
    fig = plt.figure(); plt.plot(res["per_year"]["年度"], res["per_year"]["期末股東權益(概算)"]); plt.xlabel("年度"); plt.ylabel("期末股東權益(概算)"); st.pyplot(fig)

with tab2:
    paid = st.session_state.get('paid_unlocked', False)
    st.subheader("遺產／贈與／保險／信託示意（簡化）")
    c1, c2 = st.columns(2)
    with c1:
        equity_value = st.number_input("公司股權價值", 0, 5_000_000_000, 500_000_000, 1_000_000)
        personal_assets = st.number_input("個人其他資產", 0, 2_000_000_000, 50_000_000, 1_000_000)
        personal_liab = st.number_input("個人負債", 0, 2_000_000_000, 0, 1_000_000)
        estate_exempt = st.number_input("遺產稅免稅額", 0, 100_000_000, 13_330_000, 10_000)
        annual_excl = st.number_input("贈與年免稅額", 0, 10_000_000, 0, 10_000)
        if not paid:
        st.info("🔒 進階功能（分年贈與模擬）需付費解鎖")
        years_gift = 0
    else:
        years_gift = st.number_input("分年贈與年數", 0, 60, 5, 1)
        if not paid:
        annual_gift = 0
    else:
        annual_gift = st.number_input("每年贈與總額", 0, 2_000_000_000, 10_000_000, 1_000_000)
    with c2:
        st.markdown("**稅率級距（可於程式內自訂）**")
        estate_brackets=[(50_000_000,0.10,0),(100_000_000,0.15,2_500_000),(float('inf'),0.20,7_500_000)]
        gift_brackets=[(25_000_000,0.10,0),(50_000_000,0.15,1_250_000),(float('inf'),0.20,3_750_000)]
        if not paid:
            st.info("🔒 進階功能（保險模擬）需付費解鎖")
            insurance_sum = 0
        else:
            insurance_sum = st.number_input("壽險理賠金", 0, 2_000_000_000, 0, 1_000_000)
        if not paid:
            insurance_to_heirs = True
        else:
            insurance_to_heirs = st.checkbox("壽險不入遺產（受益人直達）", True)
        trust_toggle = st.checkbox("信託示意：提前移轉不入遺產", False)
    st.markdown("**繼承人名單（姓名：比率）**")
    heirs = [{"name":"A","share":0.5},{"name":"B","share":0.5}]
    summary, alloc = estate_and_gift_simulator(
        equity_value=float(equity_value), personal_assets=float(personal_assets), personal_liabilities=float(personal_liab),
        estate_exemption=float(estate_exempt), estate_brackets=estate_brackets,
        annual_exclusion=float(annual_excl), gift_brackets=gift_brackets,
        insurance_sum=float(insurance_sum), insurance_to_heirs=bool(insurance_to_heirs),
        years_of_gifting=int(years_gift), annual_gift=float(annual_gift), heirs=heirs, trust_toggle=bool(trust_toggle),
    )
    st.write("**情境摘要**"); st.dataframe(summary)
    st.write("**各繼承人分配（概算）**"); st.dataframe(alloc)
    if not paid:
        with st.expander('解鎖進階功能（保險／贈與模擬）'):
            paid_gate()

with tab3:
    st.subheader("AI秒算遺產稅（原生頁面整合）")
    # 直接呼叫你提供的 UI 類別
    calc = estate_mod.EstateTaxCalculator(estate_mod.TaxConstants())
    sim = estate_mod.EstateTaxSimulator(calc)
    ui = estate_mod.EstateTaxUI(calc, sim)
    paid3 = st.session_state.get('paid_unlocked', False)
    # 若未付費，覆寫 UI 的進階模擬區：讓保險/贈與欄位不可用
    try:
        estate_mod.PAID_UNLOCKED = paid3
    except Exception:
        pass
    if not paid3:
        st.info('🔒 進階功能（保險／贈與模擬）需付費解鎖。您仍可使用基本遺產稅估算。')
        # 直接渲染，進階控件由 estate_tax_app 內部識別 PAID_UNLOCKED 控制
        ui.render_ui()
        with st.expander('輸入付費啟用碼以解鎖'):
            paid_gate()
    else:
        ui.render_ui()

st.caption("《影響力》傳承策略平台｜永傳家族辦公室")
