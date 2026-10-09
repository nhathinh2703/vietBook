import streamlit as st
import os
import html
import hmac
import urllib3
import xml.etree.ElementTree as ET
import downloader
import sync_manager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ADMIN_PASSWORD = os.environ.get("VIETBOOK_ADMIN_PASSWORD", "")
EXAMPLE_URL = "https://taphuan.nxbgd.vn/tap-huan/doc-sach/sgk-tin-hoc-12-dinh-huong-tin-hoc-ung-dung.4719365396#page=0"


def h(text):
    return html.escape(str(text or ""), quote=True)


def render_html(html_str):
    cleaned = "\n".join(line.strip() for line in html_str.strip().splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)


# ==========================================
# 1. CẤU HÌNH TỪ config.xml
# ==========================================
@st.cache_data
def load_config(xml_path="config.xml"):
    config = {
        "master_name": "vietApps",
        "app_name": "vietBook",
        "badge": "Miễn phí",
        "tagline": "Hệ sinh thái ứng dụng miễn phí phục vụ cộng đồng",
        "app_title": "Trình tải sách giáo khoa gốc & Kho Google Drive",
        "copyright": "© 2026 vietApps • vietBook",
        "support_email": "vietapps.official@gmail.com",
        "connect_message": "Kết nối cộng đồng vietApps",
        "drive_link": "https://drive.google.com/drive/folders/1iXlCFyOBZdM5AfOojn4h3WCVP-mAXdSp?usp=sharing",
        "drive_date": "05/10/2026",
        "storage_dir": r"D:\DuLieu\SachDienTu" if os.path.exists(r"D:\DuLieu\SachDienTu") else (
            r"D:\SachDienTu" if os.path.exists(r"D:\SachDienTu") else "downloaded_books"),
        "ecosystem": [],
        "socials": [],
        "grade_items": [],
    }

    def default_grades():
        return [{"grade": str(i), "name": f"Lớp {i}", "url": ""} for i in range(1, 13)]

    if not os.path.exists(xml_path):
        config["grade_items"] = default_grades()
        return config

    try:
        root = ET.parse(xml_path).getroot()

        brand = root.find("brand")
        if brand is not None:
            for key, tag in [
                ("master_name", "masterName"), ("app_name", "appName"), ("badge", "badge"),
                ("tagline", "tagline"), ("app_title", "appTitle"), ("copyright", "copyright"),
                ("support_email", "supportEmail"), ("connect_message", "connectMessage"),
            ]:
                config[key] = brand.findtext(tag, config[key])
            config["drive_link"] = (brand.findtext("driveLink", config["drive_link"]) or "").strip()
            config["drive_date"] = (brand.findtext("driveDate", config["drive_date"]) or "").strip()
            config["storage_dir"] = brand.findtext("booksStorageDir", config["storage_dir"]) or config["storage_dir"]

        eco = root.find("ecosystem")
        if eco is not None:
            for item in eco.findall("app"):
                config["ecosystem"].append({
                    "name": item.findtext("name", ""),
                    "description": item.findtext("description", ""),
                    "url": item.findtext("url", "#"),
                })

        socials_node = root.find("socials")
        if socials_node is not None:
            for s in socials_node.findall("social"):
                if s.findtext("enabled", "false").strip().lower() == "true":
                    config["socials"].append({
                        "id": s.get("id", ""),
                        "name": s.findtext("name", ""),
                        "title": s.findtext("title", s.findtext("name", "")),
                        "url": s.findtext("url", "#"),
                        "color": s.findtext("color", "#0f766e"),
                    })

        dl_node = root.find("driveLinks")
        grade_map = {}
        if dl_node is not None:
            all_g = dl_node.find("allGrades")
            if all_g is not None:
                config["drive_link"] = (all_g.get("url") or config["drive_link"]).strip()
                config["drive_date"] = all_g.get("date", config["drive_date"]).strip()
            for item in dl_node.findall(".//item"):
                g = item.get("grade", "").strip()
                if g:
                    grade_map[g] = {
                        "grade": g,
                        "name": item.get("name", f"Lớp {g}"),
                        "url": (item.get("url") or "").strip(),
                    }
        config["grade_items"] = [
            grade_map.get(str(i), {"grade": str(i), "name": f"Lớp {i}", "url": ""}) for i in range(1, 13)
        ]
    except Exception as e:
        print(f"Lỗi đọc config.xml: {e}")
        config["grade_items"] = config["grade_items"] or default_grades()

    return config


CFG = load_config()

# ==========================================
# 2. TRANG & CSS
# ==========================================
st.set_page_config(
    page_title=f"{CFG['app_name']} – {CFG['app_title']}",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #f6f8fa;
    --card: #ffffff;
    --line: #e5e9f0;
    --ink: #0f172a;
    --muted: #64748b;
    --brand: #0f766e;
    --brand-dark: #115e59;
    --brand-soft: #ecfdf5;
    --radius: 16px;
}

html, body, [class*="css"], .stApp {
    font-family: 'Be Vietnam Pro', -apple-system, 'Segoe UI', Roboto, sans-serif !important;
}
.stApp { background: var(--bg); }
#MainMenu, footer, header { visibility: hidden; }

.block-container {
    max-width: 1200px !important;
    padding: 96px 1.5rem 110px !important;
}

/* ── Header cố định ── */
.vb-topbar {
    position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
    background: rgba(255,255,255,.92); backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--line);
    box-shadow: 0 1px 8px rgba(15,23,42,.05);
}
.vb-nav {
    max-width: 1200px; margin: 0 auto; padding: 12px 1.5rem;
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.vb-logo { display: flex; align-items: center; gap: 12px; }
.vb-logo-mark {
    width: 42px; height: 42px; border-radius: 12px;
    background: linear-gradient(135deg, #14b8a6, #0f766e);
    display: grid; place-items: center; font-size: 21px;
    box-shadow: 0 4px 12px rgba(15,118,110,.3);
}
.vb-logo-text { font-weight: 800; font-size: 20px; color: var(--ink); letter-spacing: -.02em; }
.vb-logo-text small {
    font-size: 11px; font-weight: 700; color: #047857; background: var(--brand-soft);
    border: 1px solid #a7f3d0; padding: 2px 8px; border-radius: 999px; margin-left: 8px;
    vertical-align: middle; letter-spacing: 0;
}
.vb-nav-tag { font-size: 13px; color: var(--muted); }

/* ── Hero ── */
.vb-hero {
    background: linear-gradient(135deg, #0f766e 0%, #0d9488 55%, #14b8a6 100%);
    border-radius: 16px; padding: 24px 30px; color: #fff; margin-bottom: 22px;
    position: relative; overflow: hidden;
    box-shadow: 0 8px 24px rgba(15,118,110,.2);
    display: flex; align-items: center; justify-content: space-between; gap: 20px; flex-wrap: wrap;
}
.vb-hero-content { flex: 1; min-width: 280px; }
.vb-hero::after {
    content: ""; position: absolute; right: -40px; top: -40px; width: 160px; height: 160px;
    border-radius: 50%; background: rgba(255,255,255,.1);
}
.vb-hero h1 {
    margin: 0 0 6px; font-size: 22px; font-weight: 800; letter-spacing: -.02em;
    color: #fff !important; padding: 0;
}
.vb-hero p { margin: 0; font-size: 14px; line-height: 1.5; color: rgba(255,255,255,.88); max-width: 500px; }
.vb-stats { display: flex; gap: 10px; flex-direction: row; flex-wrap: wrap; align-items: center; justify-content: flex-end; }
.vb-stat {
    background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.25);
    border-radius: 8px; padding: 6px 12px; font-size: 13px;
}
.vb-stat b { font-weight: 700; }
@media (max-width: 640px) {
    .vb-stats { justify-content: flex-start; }
}

/* ── Grade Buttons ── */
.vb-grade-row {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; justify-content: center;
}
.vb-grade-btn {
    flex: 1; min-width: 65px; text-align: center; background: #fff;
    border: 1px solid var(--line); border-radius: 8px; padding: 8px 4px;
    font-size: 13px; font-weight: 600; color: var(--ink) !important; text-decoration: none !important;
    transition: all .15s;
}
.vb-grade-btn:hover {
    border-color: var(--brand); color: var(--brand) !important; box-shadow: 0 2px 6px rgba(15,118,110,.1);
}

/* ── Tabs dạng pill ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 12px; background: #e8edf3; padding: 8px; border-radius: 16px; margin-bottom: 24px;
}
.stTabs [data-baseweb="tab"] {
    flex: 1; height: 54px; border-radius: 12px; font-weight: 600; font-size: 16px;
    color: #475569; justify-content: center; padding: 0 24px;
}
.stTabs [aria-selected="true"] {
    background: #fff !important; color: var(--brand) !important;
    box-shadow: 0 2px 8px rgba(15,23,42,.08);
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* ── Card ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--card) !important; border: 1px solid var(--line) !important; 
    border-radius: var(--radius) !important; padding: 22px 24px !important; 
    margin-bottom: 16px !important; box-shadow: 0 1px 3px rgba(15,23,42,.04) !important;
}
.vb-eyebrow {
    font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    color: var(--brand); margin-bottom: 6px;
}
.vb-card h3 { margin: 0 0 6px; font-size: 19px; font-weight: 700; color: var(--ink); padding: 0; }
.vb-card .sub { font-size: 14px; color: var(--muted); line-height: 1.55; }

/* ── Kết quả sách ── */
.vb-book {
    display: flex; align-items: center; gap: 16px;
    background: var(--brand-soft); border: 1px solid #a7f3d0; border-radius: 14px;
    padding: 16px 18px; margin: 14px 0;
}
.vb-book-ico {
    width: 48px; height: 48px; border-radius: 12px; background: #fff; display: grid;
    place-items: center; font-size: 24px; flex-shrink: 0; border: 1px solid #a7f3d0;
}
.vb-book-title { font-weight: 700; font-size: 16px; color: var(--ink); line-height: 1.35; }
.vb-book-meta { font-size: 13px; color: #047857; margin-top: 3px; }

.vb-edition {
    display: flex; align-items: center; gap: 10px; min-height: 46px;
    padding: 8px 14px; background: #fff; border: 1px solid var(--line); border-radius: 12px;
}
.vb-tag {
    color: #fff; font-size: 11px; font-weight: 700; padding: 3px 9px;
    border-radius: 6px; white-space: nowrap;
}
.vb-ed-title { font-weight: 600; font-size: 14px; color: #1e293b; flex: 1; }
.vb-ed-ok { font-size: 12px; color: #059669; font-weight: 600; white-space: nowrap; }

/* ── Input & nút ── */
div[data-testid="stHorizontalBlock"] { align-items: center !important; }
.stTextInput > div > div {
    height: 46px !important; border-radius: 12px !important; border: 1px solid #cbd5e1 !important; background: #fff !important;
}
.stTextInput input { height: 44px !important; font-size: 15px !important; }
.stTextInput > div > div:focus-within {
    border-color: var(--brand) !important; box-shadow: 0 0 0 3px rgba(13,148,136,.15) !important;
}
.stButton > button, .stDownloadButton > button, .stLinkButton > a {
    height: 46px !important; min-height: 46px !important; border-radius: 12px !important;
    font-weight: 600 !important; font-size: 15px !important; transition: all .15s ease;
    display: inline-flex; align-items: center; justify-content: center;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"],
.stLinkButton > a[kind="primary"] {
    background: var(--brand) !important; border: 1px solid var(--brand) !important; color: #fff !important;
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover,
.stLinkButton > a[kind="primary"]:hover {
    background: var(--brand-dark) !important; box-shadow: 0 6px 14px rgba(15,118,110,.28);
    transform: translateY(-1px);
}
.stButton > button:not([kind="primary"]), .stLinkButton > a:not([kind="primary"]) {
    background: #fff !important; border: 1px solid var(--line) !important; color: #334155 !important;
}
.stButton > button:not([kind="primary"]):hover, .stLinkButton > a:not([kind="primary"]):hover {
    border-color: var(--brand) !important; color: var(--brand) !important;
}
.stProgress > div > div > div > div { background: var(--brand) !important; }

.vb-steps { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
.vb-step {
    flex: 1; min-width: 180px; background: #f8fafc; border: 1px dashed #cbd5e1;
    border-radius: 12px; padding: 12px 14px; font-size: 13px; color: #475569; line-height: 1.5;
}
.vb-step b { color: var(--brand); display: block; margin-bottom: 2px; }

.vb-section-title { font-size: 14px; font-weight: 700; color: #334155; margin: 18px 0 10px; }

/* ── Footer ── */
.vb-footer {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 1000;
    background: rgba(255,255,255,.94); backdrop-filter: blur(10px);
    border-top: 1px solid var(--line); box-shadow: 0 -1px 8px rgba(15,23,42,.05);
}
.vb-footer-inner {
    max-width: 1200px; margin: 0 auto; padding: 8px 1.5rem;
    display: flex; flex-direction: row; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
}
.vb-row1 { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.vb-icons { display: flex; gap: 8px; align-items: center; }
.vb-icon {
    width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center;
    color: #fff !important; text-decoration: none !important; transition: all .15s;
    font-size: 11px; font-weight: 800;
}
.vb-icon svg { width: 16px; height: 16px; fill: currentColor; }
.vb-icon:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(15,23,42,.2); }
.vb-eco { font-size: 12.5px; color: var(--muted); }
.vb-eco a { color: var(--brand) !important; text-decoration: none; }
.vb-eco a:hover { text-decoration: underline; }
.vb-copy { font-size: 12px; color: #94a3b8; }
.vb-copy a { color: #64748b !important; text-decoration: none; }

@media (max-width: 640px) {
    .block-container { padding: 84px .8rem 110px !important; }
    .vb-nav { padding: 10px .8rem; }
    .vb-hero { padding: 24px 20px; }
    .vb-hero h1 { font-size: 23px; }
    .vb-nav-tag, .vb-eco { display: none; }
    .stTabs [data-baseweb="tab"] { font-size: 14px; padding: 0 10px; }
}
</style>
""")

# ==========================================
# 3. STATE
# ==========================================
st.session_state.setdefault("current_url_input", "")
st.session_state.setdefault("analyzed_data", None)
st.session_state.setdefault("pdf_cache", {})

# ==========================================
# 4. THANH TRÊN + HERO
# ==========================================
render_html(f"""
<div class="vb-topbar">
    <div class="vb-nav">
        <div class="vb-logo">
            <div class="vb-logo-mark">📖</div>
            <div class="vb-logo-text">{h(CFG['app_name'])}<small>{h(CFG['badge'])}</small></div>
        </div>
        <div class="vb-nav-tag">{h(CFG['tagline'])}</div>
    </div>
</div>

<div class="vb-hero">
    <div class="vb-hero-content">
        <h1>Sách giáo khoa bản gốc, tải về trong vài giây</h1>
        <p>Tải sách chất lượng cao từ taphuan.nxbgd.vn hoặc lấy trọn bộ sách giáo khoa, sách giáo viên, sách bài tập trên Google Drive.</p>
    </div>
    <div class="vb-stats">
        <div class="vb-stat">📦 <b>52 GB</b> dữ liệu</div>
        <div class="vb-stat">📚 <b>1.700+</b> đầu sách</div>
        <div class="vb-stat">⏱️ Cập nhật <b>{h(CFG['drive_date'])}</b></div>
    </div>
</div>
""")

# ==========================================
# 5. TẢI SÁCH TỪ LINK
# ==========================================
with st.container(border=True):
    render_html("""
    <div>
        <div class="vb-eyebrow">Công cụ tải sách</div>
        <h3 style="display:inline-block; margin:0 8px 12px 0;">Dán link để tải PDF bản gốc NXB Giáo dục</h3>
        <span class="sub" style="display:inline-block;">Hỗ trợ link đọc sách và môn học từ <a href="https://taphuan.nxbgd.vn" target="_blank" style="color:var(--brand); text-decoration:none; font-weight:600;">taphuan.nxbgd.vn</a></span>
        <div class="vb-steps">
            <div class="vb-step"><b>1. Dán link</b>Sao chép đường dẫn trang đọc sách.</div>
            <div class="vb-step"><b>2. Kiểm tra</b>Hệ thống đọc thông tin và số trang.</div>
            <div class="vb-step"><b>3. Tải PDF</b>Ghép các trang gốc thành một file PDF.</div>
        </div>
    </div>
    """)

    col_inp, col_btn = st.columns([4, 1.2], gap="small")
    with col_inp:
        user_url = st.text_input(
            "Link taphuan.nxbgd.vn",
            value=st.session_state["current_url_input"],
            placeholder="https://taphuan.nxbgd.vn/tap-huan/doc-sach/...",
            label_visibility="collapsed",
        )
    with col_btn:
        analyze_btn = st.button("Tải sách", type="primary", use_container_width=True)

if analyze_btn or (user_url and user_url != st.session_state.get("last_analyzed_url")):
    st.session_state["current_url_input"] = user_url
    st.session_state["last_analyzed_url"] = user_url
    parsed = downloader.parse_taphuan_url(user_url)

    if not parsed["valid"]:
        st.error(parsed["message"])
        st.session_state["analyzed_data"] = None
    else:
        with st.spinner("Đang lấy thông tin sách..."):
            if parsed["type"] == "doc_sach":
                info, err = downloader.fetch_reader_info(parsed["url"])
                kind = "doc_sach"
            else:
                info, err = downloader.fetch_detail_editions(parsed["url"])
                kind = "chi_tiet_sach"
        if err:
            st.error(err)
            st.session_state["analyzed_data"] = None
        else:
            st.session_state["analyzed_data"] = {"type": kind, "data": info}

res = st.session_state.get("analyzed_data")

# ── Sách đơn lẻ ──
if res and res["type"] == "doc_sach":
    book = res["data"]
    title = book["title"]
    page_urls = book["page_urls"]
    total_pages = book["total_pages"]
    storage = CFG.get("storage_dir")

    render_html(f"""
    <div class="vb-book">
        <div class="vb-book-ico">📘</div>
        <div>
            <div class="vb-book-title">{h(title)}</div>
            <div class="vb-book-meta">{total_pages} trang • Bản gốc NXB Giáo dục</div>
        </div>
    </div>
    """)

    offline_path, offline_sz = downloader.find_offline_pdf(title, storage)
    cached = st.session_state["pdf_cache"].get(title)

    if offline_path and os.path.exists(offline_path):
        try:
            with open(offline_path, "rb") as f:
                file_data = f.read()
            st.download_button(
                f"💾  Tải ngay PDF có sẵn ({offline_sz:.1f} MB)",
                data=file_data, file_name=os.path.basename(offline_path),
                mime="application/pdf", type="primary", use_container_width=True,
            )
        except Exception as e:
            st.error(f"Lỗi đọc file: {e}")
    elif cached:
        st.success(f"✅ Đã xử lý xong ({cached[1]:.1f} MB)")
        st.download_button(
            f"💾  Lưu file PDF về máy ({cached[1]:.1f} MB)",
            data=cached[0], file_name=f"{downloader.sanitize_filename(title)}.pdf",
            mime="application/pdf", type="primary", use_container_width=True,
        )
    else:
        if st.button(f"📥  Bắt đầu tải PDF ({total_pages} trang)", type="primary", use_container_width=True):
            p_bar = st.progress(0)
            p_label = st.empty()

            def progress_cb(current, total, msg):
                p_bar.progress(min(int(current / total * 100), 100) if total else 0)
                p_label.caption(f"{msg} ({current}/{total})")

            target_save = None
            if storage and os.path.exists(storage):
                target_save = os.path.join(storage, downloader.sanitize_filename(title) + ".pdf")

            pdf_bytes, sz_mb, dl_err = downloader.download_pages_and_build_pdf(
                page_urls=page_urls, title=title, progress_callback=progress_cb,
                save_path=target_save, max_workers=8,
            )
            if dl_err:
                st.error(dl_err)
            else:
                st.session_state["pdf_cache"][title] = (pdf_bytes, sz_mb)
                st.rerun()

# ── Môn học nhiều ấn bản ──
elif res and res["type"] == "chi_tiet_sach":
    detail = res["data"]
    st.markdown(f"<div class='vb-section-title'>📚 {h(detail['main_title'])} · {len(detail['editions'])} ấn bản</div>",
                unsafe_allow_html=True)

    for i, ed in enumerate(detail["editions"]):
        off_path, off_sz = downloader.find_offline_pdf(ed["title"], CFG.get("storage_dir"))
        ok = f"✓ Có sẵn {off_sz:.1f} MB" if off_path else ""
        c1, c2 = st.columns([4, 1.2], gap="small")
        with c1:
            render_html(f"""
            <div class="vb-edition">
                <span class="vb-tag" style="background:{h(ed['badge_color'])};">{h(ed['type_label'])}</span>
                <span class="vb-ed-title">{h(ed['title'])}</span>
                <span class="vb-ed-ok">{ok}</span>
            </div>
            """)
        with c2:
            if st.button("Chọn tải", key=f"sel_ed_{i}", use_container_width=True):
                st.session_state["current_url_input"] = ed["doc_url"]
                st.session_state["last_analyzed_url"] = ""
                st.rerun()

# ==========================================
# 6. KHO GOOGLE DRIVE
# ==========================================
with st.container(border=True):
    render_html(f"""
    <div>
        <div class="vb-eyebrow">Kho Google Drive</div>
        <h3>Trọn bộ sách bản gốc chất lượng cao</h3>
        <div class="sub" style="margin-bottom:16px;">
            Sách giáo khoa, sách giáo viên và sách bài tập từ lớp 1 đến lớp 12.
            Tốc độ cao, không quảng cáo, cập nhật liên tục (lần cuối {h(CFG['drive_date'])}).
        </div>
        <a href="{h(CFG['drive_link'])}" target="_blank" style="display:flex; align-items:center; justify-content:center; background:var(--brand); color:#fff; border-radius:12px; height:46px; font-weight:600; text-decoration:none; transition:all 0.15s; width:100%;">☁️ Mở kho sách trọn bộ (52 GB) ↗</a>
    </div>
    """)

    st.markdown("<div class='vb-section-title' style='text-align:center;'>Hoặc chọn theo khối lớp</div>", unsafe_allow_html=True)

    grades = CFG["grade_items"]
    grade_html = '<div class="vb-grade-row">'
    for g in grades:
        if g["url"]:
            grade_html += f'<a class="vb-grade-btn" href="{h(g["url"])}" target="_blank" rel="noopener noreferrer">{h(g["name"])}</a>'
        else:
            grade_html += f'<a class="vb-grade-btn" style="opacity:0.5; pointer-events:none;" title="Chưa cập nhật">{h(g["name"])}</a>'
    grade_html += '</div>'
    render_html(grade_html)

# ==========================================
# 7. QUẢN TRỊ (nếu có mật khẩu)
# ==========================================
if ADMIN_PASSWORD:
    with st.expander("⚙️ Quản trị viên", expanded=False):
        if not st.session_state.get("admin_ok"):
            pwd = st.text_input("Mật khẩu quản trị", type="password", key="admin_pwd")
            if st.button("Xác nhận", key="btn_admin_login"):
                if hmac.compare_digest(pwd.encode(), ADMIN_PASSWORD.encode()):
                    st.session_state["admin_ok"] = True
                    st.rerun()
                else:
                    st.error("Sai mật khẩu.")
        else:
            st.caption("Kiểm tra và cập nhật cơ sở dữ liệu sách từ NXB Giáo dục.")
            if st.button("Bắt đầu quét dữ liệu", key="btn_check_sync"):
                p_bar = st.progress(0)
                p_text = st.empty()
                st.session_state["sync_res"] = sync_manager.check_for_new_books(
                    lambda msg, pct: (p_bar.progress(pct), p_text.text(msg))
                )
                p_bar.empty()
                p_text.empty()

            sync_res = st.session_state.get("sync_res")
            if sync_res:
                st.write(f"Online: **{sync_res['total_online']}** • Hiện tại: **{sync_res['total_current']}**")
                if sync_res["has_new"]:
                    st.success(f"Phát hiện {len(sync_res['new_books'])} sách mới.")
                    if st.button("Cập nhật CSDL", type="primary", key="btn_update_db"):
                        sync_manager.update_catalog_and_report(sync_res["all_online_books"])
                        st.session_state["sync_res"] = None
                        st.success("Đã cập nhật!")
                else:
                    st.info("Dữ liệu đã đồng bộ hoàn toàn.")

# ==========================================
# 8. FOOTER
# ==========================================
ICON_SVG = {
    "facebook": '<svg viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>',
    "youtube": '<svg viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>',
    "telegram": '<svg viewBox="0 0 24 24"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>',
    "tiktok": '<svg viewBox="0 0 448 512"><path d="M448 209.91a210.06 210.06 0 0 1-122.77-39.25V349.38A162.55 162.55 0 1 1 185 188.31V278.2a74.62 74.62 0 1 0 52.23 71.18V0l88 0a121.18 121.18 0 0 0 1.86 22.17h0A122.18 122.18 0 0 0 381 102.39a121.43 121.43 0 0 0 67 20.14Z"/></svg>',
    "link": '<svg viewBox="0 0 24 24"><path d="M10.6 13.4a1 1 0 0 1 0-1.4l3-3a3 3 0 1 1 4.2 4.2l-2 2a1 1 0 1 1-1.4-1.4l2-2a1 1 0 0 0-1.4-1.4l-3 3a1 1 0 0 1-1.4 0zm2.8-2.8a1 1 0 0 1 0 1.4l-3 3a3 3 0 1 1-4.2-4.2l2-2a1 1 0 0 1 1.4 1.4l-2 2a1 1 0 0 0 1.4 1.4l3-3a1 1 0 0 1 1.4 0z"/></svg>',
}


def social_icon(s):
    key = f"{s.get('id', '')} {s.get('name', '')}".lower()
    if "zalo" in key:
        inner = "Zalo"
    elif "facebook" in key or "fb" in key:
        inner = ICON_SVG["facebook"]
    elif "youtube" in key:
        inner = ICON_SVG["youtube"]
    elif "telegram" in key:
        inner = ICON_SVG["telegram"]
    elif "tiktok" in key:
        inner = ICON_SVG["tiktok"]
    else:
        inner = ICON_SVG["link"]
    label = s.get("title") or s.get("name") or "Liên kết"
    return (f'<a class="vb-icon" href="{h(s["url"])}" target="_blank" rel="noopener noreferrer" '
            f'title="{h(label)}" aria-label="{h(label)}" style="background:{h(s["color"])};">{inner}</a>')


icons = "".join(social_icon(s) for s in CFG["socials"])
eco = " · ".join(
    f'<a href="{h(a["url"])}" target="_blank" rel="noopener noreferrer" title="{h(a["description"])}">{h(a["name"])}</a>'
    for a in CFG["ecosystem"] if a.get("url", "#") != "#"
)

render_html(f"""
<div class="vb-footer">
    <div class="vb-footer-inner">
        <div class="vb-row1">
            <div class="vb-icons">{icons}</div>
            {f'<div class="vb-eco">Hệ sinh thái: {eco}</div>' if eco else ''}
        </div>
        <div class="vb-copy">
            {h(CFG['copyright'])} • <a href="mailto:{h(CFG['support_email'])}">{h(CFG['support_email'])}</a>
        </div>
    </div>
</div>
""")
