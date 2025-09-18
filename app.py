
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go

st.set_page_config(page_title="《影響力》傳承策略平台｜永傳家族辦公室", page_icon="logo2.png", layout="wide")

# ---- CJK Font Setup (strong) ----
from pathlib import Path as _Path
import os as _os, glob as _glob
try:
    from matplotlib import font_manager as _fm, rcParams as _rc
    try:
        _home = _os.path.expanduser("~")
        for _p in _glob.glob(_os.path.join(_home, ".cache", "matplotlib", "fontlist*")):
            try: _os.remove(_p)
            except Exception: pass
    except Exception: pass
    _font_path = _Path(__file__).with_name("NotoSansTC-Regular.ttf")
    _FONT_NAME = None
    if _font_path.exists():
        try:
            _fm.fontManager.addfont(str(_font_path))
            try: _fm._load_fontmanager(try_read_cache=False)
            except Exception: pass
            _FONT_NAME = _fm.FontProperties(fname=str(_font_path)).get_name()
            _rc["font.family"] = [_FONT_NAME]
            _rc["font.sans-serif"] = [_FONT_NAME]
            _rc["axes.unicode_minus"] = False
        except Exception as _e:
            print("Matplotlib font load error:", _e)
    try:
        import plotly.io as _pio
        if _FONT_NAME:
            base = _pio.templates.default or "plotly"
            templ = _pio.templates[base]
            templ.layout.font.family = _FONT_NAME
            _pio.templates["with_cjk"] = templ
            _pio.templates.default = "with_cjk"
    except Exception as _e:
        print("Plotly font set error:", _e)
    try:
        from reportlab.pdfbase import pdfmetrics as _pdfm
        from reportlab.pdfbase.ttfonts import TTFont as _TTFont
        if _font_path.exists():
            _pdfm.registerFont(_TTFont("NotoSansTC", str(_font_path)))
            DEFAULT_PDF_FONT = "NotoSansTC"
        else:
            DEFAULT_PDF_FONT = "Helvetica"
    except Exception as _e:
        DEFAULT_PDF_FONT = "Helvetica"
except Exception as _e:
    print("Global font setup error:", _e)

# ---- Session helpers (TTL + user info bar) ----
from datetime import datetime, timedelta
SESSION_TTL_SECS = 3600

def _session_now():
    return datetime.utcnow()

def session_is_expired():
    ts = st.session_state.get("paid_unlocked_at")
    ttl = st.session_state.get("session_ttl_secs", SESSION_TTL_SECS)
    if not ts: return False
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
        if st.session_state.get("paid_unlocked") and session_is_expired():
            for k in ["paid_unlocked","paid_user_meta","paid_unlocked_at","session_ttl_secs"]:
                st.session_state.pop(k, None)
            st.warning("您的進階權限 Session 已逾期（1 小時）。請重新登入。")

# ---- Login-only Gate (authorized_users.*) ----
def _check_user_login(u, p):
    try:
        auth = st.secrets.get("authorized_users", {})
    except Exception:
        auth = {}
    from datetime import datetime as _dt
    for key, rec in (auth.items() if isinstance(auth, dict) else []):
        try:
            username = str(rec.get("username","")).strip()
            password = str(rec.get("password","")).strip()
            if u.strip() == username and p.strip() == password:
                def _parse(d):
                    try:
                        return _dt.strptime(str(d), "%Y-%m-%d").date()
                    except Exception:
                        return None
                today = _dt.utcnow().date()
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

# ---- Helpers ----
DEFAULT_BRACKETS = [(0,0.05),(540000,0.12),(1210000,0.20),(2420000,0.30),(4530000,0.40)]
def indiv_div_tax(dividend, mode, other_income, brackets):
    if mode=="split28":
        return 0.28*dividend
    # integrate: rough progressive model with 8.5% credit cap logic simplified
    taxable = other_income + dividend
    tax = 0.0
    last = 0
    for th, rate in brackets:
        if taxable>th:
            tax = (taxable-th)*rate; last=rate
    credit = min(dividend*0.085, 80000.0)
    return max(0.0, tax - credit)

def _fmt_money(x):
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return x

# ---- UI ----
try:
    from PIL import Image
    logo = Image.open("logo.png")
except Exception:
    logo = None

c1, c2 = st.columns([0.09, 0.91])
with c1:
    if logo: st.image(logo, use_container_width=True)
with c2:
    st.title("《影響力》傳承策略平台｜永傳家族辦公室")
render_user_info_bar()

tab1, tab3 = st.tabs(["模組一｜單年度稅負試算", "模組三｜AI 秒算遺產稅"])

with tab1:
    st.subheader("單年度稅負試算（公司層 × 股東層）")
    st.caption("以單一年度盈餘與分配行為為基礎，將稅負拆為公司層與股東層，清楚呈現本年錢的去向。")

    colA, colB, colC = st.columns([1.1, 1.1, 1.2])

    with colA:
        pretax = st.number_input("當年度稅前盈餘", 0, 2_000_000_000, 20_000_000, 1_000_000)
        init_capital = st.number_input("期初資本額（法定公積上限）", 0, 2_000_000_000, 1_000_000, 100_000)
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

    # ---- 計算 ----
    corp_tax = max(pretax*corp_tax_rate, pretax*corp_amt_min)
    after_tax = max(0.0, pretax - corp_tax)
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
    undist_tax = keep * undist_rate
    if shareholder_kind=="corporate_resident":
        sh_tax = 0.0
    elif shareholder_kind=="individual_resident":
        sh_tax = indiv_div_tax(cash+stock, indiv_mode, other_income, DEFAULT_BRACKETS)
    else:
        sh_tax = (cash+stock) * withhold

    company_tax_total = corp_tax + undist_tax
    total_all = company_tax_total + sh_tax

    # ---- 結果（公司層 / 股東層 / 總結）----
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🏢 公司層")
        df_company = pd.DataFrame([
            {"項目":"稅前盈餘","金額":pretax},
            {"項目":"公司所得稅 / AMT","金額":corp_tax},
            {"項目":"稅後盈餘","金額":after_tax},
            {"項目":"提列法定盈餘公積","金額":to_legal},
            {"項目":"可分配盈餘","金額":dist_base},
            {"項目":"保留盈餘（未分配）","金額":keep},
            {"項目":"未分配盈餘稅","金額":undist_tax},
            {"項目":"公司層合計稅","金額":company_tax_total},
        ])
        df_company["金額"] = df_company["金額"].map(_fmt_money)
        st.dataframe(df_company, use_container_width=True, hide_index=True)

    with c2:
        st.markdown("#### 👤 股東層")
        df_sh = pd.DataFrame([
            {"項目":"發放現金股利","金額":cash},
            {"項目":"發放股票股利","金額":stock},
            {"項目":"股東層所得稅","金額":sh_tax},
            {"項目":"股東實領淨額（含股利）","金額":cash+stock-sh_tax},
        ])
        df_sh["金額"] = df_sh["金額"].map(_fmt_money)
        st.dataframe(df_sh, use_container_width=True, hide_index=True)

    st.markdown("#### 總結")
    df_total = pd.DataFrame([{
        "公司層合計稅": company_tax_total,
        "股東層稅": sh_tax,
        "本年總稅負": total_all,
        "有效稅率(總稅/稅前盈餘)": (total_all/pretax) if pretax else 0.0
    }])
    for col in df_total.columns:
        df_total[col] = df_total[col].map(lambda v: f"{v:,.0f}" if isinstance(v,(int,float)) and not str(col).startswith("有效稅率") else (f"{v:.2%}" if str(col).startswith("有效稅率") else v))
    st.dataframe(df_total, use_container_width=True)

    # ---- 互動圖（Plotly）----
    g1, g2 = st.columns(2)
    with g1:
        labels1 = ["公司稅", "未分配盈餘稅"]
        values1 = [corp_tax, undist_tax]
        fig1 = go.Figure(data=[go.Bar(x=labels1, y=values1, text=[f"{v:,.0f}" for v in values1], textposition="auto")])
        fig1.update_layout(title="公司層稅負", yaxis_title="金額（元）", margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig1, use_container_width=True)
    with g2:
        labels2 = ["股東層稅"]
        values2 = [sh_tax]
        fig2 = go.Figure(data=[go.Bar(x=labels2, y=values2, text=[f"{v:,.0f}" for v in values2], textposition="auto")])
        fig2.update_layout(title="股東層稅負", yaxis_title="金額（元）", margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("AI秒算遺產稅（原生頁面整合）")
    import importlib.util as _ilu, sys as _sys
    mod_path = str(_Path(__file__).with_name("estate_tax_app.py"))
    spec = _ilu.spec_from_file_location("estate_mod", mod_path)
    estate_mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(estate_mod)
    calc = estate_mod.EstateTaxCalculator(estate_mod.TaxConstants())
    sim = estate_mod.EstateTaxSimulator(calc)
    ui = estate_mod.EstateTaxUI(calc, sim)
    # 傳遞主程式的解鎖狀態給子模組
    paid3 = st.session_state.get('paid_unlocked', False)
    try:
        estate_mod.PAID_UNLOCKED = paid3
    except Exception:
        pass
    if not paid3:
        st.info('🔒 進階功能（保險／贈與模擬）需登入解鎖。以下為基本遺產稅估算功能；進階功能請使用本頁內置登入框登入。')
    ui.render_ui()

