
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


# ---- Login-only Gate (authorized_users.*) ----
from datetime import datetime

def _check_user_login(u, p):
    try:
        auth = st.secrets.get("authorized_users", {})
    except Exception:
        auth = {}
    for key, rec in (auth.items() if isinstance(auth, dict) else []):
        try:
            username = str(rec.get("username","")).strip()
            password = str(rec.get("password","")).strip()
            if u.strip() == username and p.strip() == password:
                # Date window check (YYYY-MM-DD)
                def _parse(d):
                    try:
                        return datetime.strptime(str(d), "%Y-%m-%d").date()
                    except Exception:
                        return None
                today = datetime.utcnow().date()
                start = _parse(rec.get("start_date"))
                end = _parse(rec.get("end_date"))
                ok_date = True
                if start and today < start: ok_date = False
                if end and today > end: ok_date = False
                meta = {"role": key, "name": rec.get("name", key), "start_date": rec.get("start_date","-"), "end_date": rec.get("end_date","-"), "via":"user"}
                return ok_date, meta
        except Exception:
            continue
    return False, {}

def login_gate(prefix: str = "gate"):
    unlocked = st.session_state.get("paid_unlocked", False)
    if unlocked:
        return True
    st.warning("進階功能需登入使用者帳號")
    with st.form(key=f"login_form_{prefix}", clear_on_submit=False):
        u = st.text_input("帳號", key=f"login_user_{prefix}")
        p = st.text_input("密碼", type="password", key=f"login_pass_{prefix}")
        colA, colB = st.columns([0.4,0.6])
        with colA:
            submit = st.form_submit_button("登入")
        with colB:
            st.caption("＊帳號由管理者提供，具有效期控管")
    if 'submit' in locals() and submit:
        ok, meta = _check_user_login(u, p)
        if ok:
            st.success(f"歡迎 {meta.get('name','')}！進階功能已解鎖。")
            st.session_state["paid_unlocked"] = True
            st.session_state["paid_user_meta"] = meta
            st.session_state["paid_unlocked_at"] = _session_now().isoformat()
            st.session_state["session_ttl_secs"] = SESSION_TTL_SECS
            st.experimental_rerun()
        else:
            st.error("帳號或密碼錯誤，或不在有效期間內。")
    return st.session_state.get("paid_unlocked", False)

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
    st.subheader("單年度稅負試算（公司＋股東）")
    st.caption("說明：以**單一年度**的盈餘與分配行為為基礎，計算公司層稅負、未分配盈餘稅與股東層稅，避免以長期假設誤導判斷。")

    colA, colB, colC = st.columns([1.1, 1.1, 1.2])

    with colA:
        pretax = st.number_input("當年度稅前盈餘", 0, 2_000_000_000, 20_000_000, 1_000_000)
        init_capital = st.number_input("期初資本額（用於法定盈餘公積上限）", 0, 2_000_000_000, 1_000_000, 100_000)
        corp_tax_rate = st.number_input("公司稅率", 0.0, 0.5, 0.20, 0.01)
        corp_amt_min = st.number_input("最低稅負（AMT）", 0.0, 0.5, 0.12, 0.01)

    with colB:
        legal_on = st.checkbox("提列法定盈餘公積", True)
        lr_rate = st.slider("法定盈餘公積提列率", 0.0, 0.2, 0.10, 0.01)
        lr_cap = st.slider("法定盈餘公積上限（資本×）", 0.0, 1.0, 0.25, 0.05)
        undist_rate = st.number_input("未分配盈餘稅率", 0.0, 0.2, 0.05, 0.01)

    with colC:
        st.markdown("**分配政策（% 以稅後盈餘扣除法定公積後為基礎）**")
        cash_pct = st.slider("現金股利 %", 0.0, 1.0, 0.0, 0.05)
        stock_pct = st.slider("股票股利 %", 0.0, 1.0, 0.0, 0.05)

        kind = st.selectbox("股東型別", ["本國個人","本國法人","非居民（外資）"])
        if kind=="本國個人":
            indiv_mode_ch = st.radio("個人課稅模式", ["28% 分開課稅","併入綜所稅（含8.5%抵減）"], horizontal=True)
            indiv_mode = "split28" if indiv_mode_ch.startswith("28%") else "integrate"
            other_income = st.number_input("其他綜所稅所得額", 0, 2_000_000_000, 0, 10_000)
            shareholder_kind="individual_resident"; withhold=0.0
        elif kind=="本國法人":
            shareholder_kind="corporate_resident"; indiv_mode="split28"; other_income=0.0; withhold=0.0
        else:
            shareholder_kind="nonresident"; indiv_mode="split28"; other_income=0.0
            withhold = st.number_input("非居民股利扣繳率（條約）", 0.0, 0.30, 0.21, 0.01)

    # ---- 單年度計算邏輯 ----
    corp_tax = max(pretax*corp_tax_rate, pretax*corp_amt_min)
    after_tax = max(0.0, pretax - corp_tax)
    # 法定盈餘公積：以期初資本額的上限判斷（本年提列不使資本額變動）
    to_legal = 0.0
    legal_reserve = 0.0
    if legal_on:
        target = init_capital * lr_cap
        room = max(0.0, target - legal_reserve)
        to_legal = min(after_tax * lr_rate, room)

    dist_base = max(0.0, after_tax - to_legal)
    cash = dist_base * cash_pct
    stock = dist_base * stock_pct
    keep = max(0.0, dist_base - cash - stock)

    # 未分配盈餘稅
    undist_tax = keep * undist_rate

    # 股東層稅
    if shareholder_kind=="corporate_resident":
        sh_tax = 0.0
    elif shareholder_kind=="individual_resident":
        sh_tax = indiv_div_tax(cash+stock, indiv_mode, other_income, DEFAULT_BRACKETS)
    else:
        sh_tax = (cash+stock) * withhold

    total_co = corp_tax + undist_tax
    total_all = total_co + sh_tax

    st.markdown("### 結果總結")
    res_df = pd.DataFrame([{
        "稅前盈餘": pretax,
        "公司稅(含AMT)": corp_tax,
        "稅後盈餘": after_tax,
        "提列法定公積": to_legal,
        "現金股利": cash,
        "股票股利": stock,
        "保留盈餘": keep,
        "未分配盈餘稅": undist_tax,
        "股東層稅": sh_tax,
        "公司本年合計稅": total_co,
        "本年總稅負": total_all,
        "有效稅率(總稅/稅前盈餘)": (total_all/pretax) if pretax else 0.0
    }])
    st.dataframe(res_df)

    # 視覺化：稅負拆解
    fig = plt.figure()
    labels = ["公司稅", "未分配盈餘稅", "股東層稅"]
    values = [corp_tax, undist_tax, sh_tax]
    plt.bar(labels, values)
    from matplotlib.font_manager import FontProperties as _FP
    from pathlib import Path as _Path
    _fp = _FP(fname=str(_Path(__file__).with_name("NotoSansTC-Regular.ttf"))) if _Path(__file__).with_name("NotoSansTC-Regular.ttf").exists() else None
    if _fp:
        plt.ylabel("金額（元）", fontproperties=_fp)
    else:
        plt.ylabel("金額（元）")
    st.pyplot(fig)

with tab2:
    paid = st.session_state.get('paid_unlocked', False)
    st.markdown("### 傳承與移轉：操作說明")
    st.caption("左側輸入參數，右側即時顯示結果。帶 🔒 的欄位需登入後解鎖。")
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
            annual_gift = 0
        else:
            years_gift = st.number_input("分年贈與年數", 0, 60, 5, 1)
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
            login_gate("m2")

with tab3:

    st.subheader("AI秒算遺產稅（原生頁面整合）")
    # 直接呼叫你提供的 UI 類別
    calc = estate_mod.EstateTaxCalculator(estate_mod.TaxConstants())
    sim = estate_mod.EstateTaxSimulator(calc)
    ui = estate_mod.EstateTaxUI(calc, sim)
    paid3 = st.session_state.get('paid_unlocked', False)
    try:
        estate_mod.PAID_UNLOCKED = paid3
    except Exception:
        pass
    if not paid3:
        st.info('🔒 進階功能（保險／贈與模擬）需登入解鎖。以下為基本遺產稅估算功能；進階功能請使用本頁內置登入框登入。')
        ui.render_ui()
    else:
        ui.render_ui()
