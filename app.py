import streamlit as st
import json
import os
import re
import io
import hmac
import urllib3
import xml.etree.ElementTree as ET
import downloader
import sync_manager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Quản trị ─────────────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("VIETBOOK_ADMIN_PASSWORD", "")

def render_html(html_str):
    cleaned = "\n".join(line.strip() for line in html_str.strip().splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)

# ==========================================
# 1. ĐỌC CẤU HÌNH TỪ CONFIG.XML
# ==========================================
@st.cache_data
def load_config(xml_path="config.xml"):
    config = {
        "master_name": "vietApps",
        "app_name": "vietBook",
        "badge": "Miễn phí",
        "tagline": "Hệ sinh thái ứng dụng miễn phí phục vụ cộng đồng",
        "app_title": "Trình tải sách giáo khoa gốc & Kho Google Drive",
        "hero_title": "Trình tải sách giáo khoa bản gốc",
        "app_desc": "Hỗ trợ dán link tải sách bản gốc chất lượng cao từ taphuan.nxbgd.vn và chia sẻ trọn bộ sách giáo viên, sách giáo khoa, sách bài tập trên Google Drive.",
        "copyright": "© 2026 vietApps • vietBook",
        "support_email": "vietapps.official@gmail.com",
        "connect_message": "Kết nối cộng đồng vietApps",
        "drive_link": "https://drive.google.com/drive/folders/1iXlCFyOBZdM5AfOojn4h3WCVP-mAXdSp?usp=sharing",
        "drive_date": "05/10/2026",
        "storage_dir": r"D:\DuLieu\SachDienTu" if os.path.exists(r"D:\DuLieu\SachDienTu") else (r"D:\SachDienTu" if os.path.exists(r"D:\SachDienTu") else "downloaded_books"),
        "ecosystem": [],
        "socials": []
    }
    if not os.path.exists(xml_path):
        return config

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        brand = root.find("brand")
        if brand is not None:
            config["master_name"] = brand.findtext("masterName", config["master_name"])
            config["app_name"] = brand.findtext("appName", config["app_name"])
            config["badge"] = brand.findtext("badge", config["badge"])
            config["tagline"] = brand.findtext("tagline", config["tagline"])
            config["app_title"] = brand.findtext("appTitle", config["app_title"])
            config["hero_title"] = brand.findtext("heroTitle", config["hero_title"])
            config["app_desc"] = brand.findtext("appDescription", config["app_desc"])
            config["copyright"] = brand.findtext("copyright", config["copyright"])
            config["support_email"] = brand.findtext("supportEmail", config["support_email"])
            msg = brand.findtext("connectMessage", config.get("connect_message", "Kết nối cộng đồng vietApps"))
            config["connect_message"] = msg
            config["connectMessage"] = msg
            config["drive_link"] = (brand.findtext("driveLink", config["drive_link"]) or "").strip()
            config["drive_date"] = (brand.findtext("driveDate", config["drive_date"]) or "").strip()
            config["storage_dir"] = brand.findtext("booksStorageDir", config["storage_dir"]) or config["storage_dir"]

        eco = root.find("ecosystem")
        if eco is not None:
            for item in eco.findall("app"):
                config["ecosystem"].append({
                    "id": item.get("id", ""),
                    "name": item.findtext("name", ""),
                    "badge": item.findtext("badge", ""),
                    "badge_color": item.findtext("badgeColor", "#2563eb"),
                    "tagline": item.findtext("tagline", ""),
                    "description": item.findtext("description", ""),
                    "url": item.findtext("url", "#"),
                    "icon": item.findtext("icon", "📦")
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
                        "color": s.findtext("color", "#2563eb")
                    })

        # Đọc cấu hình 12 khối lớp Google Drive
        dl_node = root.find("driveLinks")
        grade_items_map = {}
        if dl_node is not None:
            all_g = dl_node.find("allGrades")
            if all_g is not None:
                config["all_grades_title"] = all_g.get("title", "Trọn bộ sách giáo khoa điện tử (52 GB)")
                config["all_grades_url"] = (all_g.get("url") or config["drive_link"]).strip()
                config["all_grades_date"] = all_g.get("date", config["drive_date"]).strip()

            for item in dl_node.findall(".//item"):
                g_num = item.get("grade", "").strip()
                if g_num:
                    grade_items_map[g_num] = {
                        "grade": g_num,
                        "name": item.get("name", f"Lớp {g_num}"),
                        "url": (item.get("url") or "").strip()
                    }

        config["grade_items"] = []
        for i in range(1, 13):
            str_i = str(i)
            if str_i in grade_items_map:
                config["grade_items"].append(grade_items_map[str_i])
            else:
                config["grade_items"].append({
                    "grade": str_i,
                    "name": f"Lớp {i}",
                    "url": ""
                })

    except Exception as e:
        print(f"Lỗi đọc config.xml: {e}")

    return config

CFG = load_config()

# ==========================================
# 2. CẤU HÌNH TRANG & CSS
# ==========================================
st.set_page_config(
    page_title=f"{CFG['app_name']} – {CFG['app_title']}",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

render_html("""
<style>
    /* ── ẨN THANH CÔNG CỤ MẶC ĐỊNH STREAMLIT ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ── TYPOGRAPHY & ĐỘ RỘNG TRANG HIỆN ĐẠI (1200px) ── */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        color: #1e293b;
        background-color: #f8fafc;
    }

    .block-container {
        max-width: 1200px !important;
        padding-top: 1.2rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }

    /* ── HEADER THANH ĐIỀU HƯỚNG ── */
    .vb-topbar {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .vb-brand-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .vb-brand-avatar {
        width: 44px;
        height: 44px;
        background: linear-gradient(135deg, #0d9488, #0f766e);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        color: #ffffff;
        box-shadow: 0 2px 4px rgba(13, 148, 136, 0.25);
    }
    .vb-brand-name {
        font-size: 20px;
        font-weight: 800;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .vb-badge-pill {
        font-size: 11px;
        font-weight: 700;
        padding: 3px 8px;
        background: #ecfdf5;
        color: #047857;
        border: 1px solid #a7f3d0;
        border-radius: 999px;
    }
    .vb-brand-desc {
        font-size: 13px;
        color: #64748b;
        margin-top: 2px;
    }

    /* ── TABS HIỆN ĐẠI & RÕ RÀNG ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #e2e8f0;
        padding: 6px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        border-radius: 8px;
        padding: 0 24px;
        font-size: 15px;
        font-weight: 600;
        color: #475569;
        transition: all 0.2s;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0f766e !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }

    /* ── CĂN ĐỀU KHỐI NHẬP LIỆU & NÚT BẤM (FIX LỆCH HÀNG) ── */
    .search-row-container {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    div[data-testid="stHorizontalBlock"] {
        align-items: flex-end !important;
    }
    .stTextInput > div > div {
        height: 48px !important;
        border-radius: 10px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        display: flex;
        align-items: center;
    }
    .stTextInput input {
        height: 48px !important;
        font-size: 15px !important;
        padding: 0 14px !important;
    }
    .stTextInput > div > div:focus-within {
        border-color: #0d9488 !important;
        box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.15) !important;
    }
    .stButton > button, .stDownloadButton > button {
        height: 48px !important;
        border-radius: 10px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
        background: #0f766e !important;
        border: 1px solid #0f766e !important;
    }
    .stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
        background: #115e59 !important;
        border-color: #115e59 !important;
        box-shadow: 0 4px 8px rgba(15, 118, 110, 0.25);
    }

    /* ── CARD THÔNG TIN SÁCH ── */
    .vb-card-result {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 24px;
        margin-top: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .vb-edition-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 12px;
    }

    /* ── FOOTER HIỆN ĐẠI (BOTTOM TỰ NHIÊN) ── */
    .vb-footer-container {
        margin-top: 40px;
        padding: 28px 24px 20px;
        background: #ffffff;
        border-top: 1px solid #e2e8f0;
        border-radius: 16px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .vb-social-wrapper {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }
    .vb-social-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border-radius: 999px;
        color: #ffffff !important;
        font-size: 13px;
        font-weight: 600;
        text-decoration: none !important;
        transition: transform 0.15s, opacity 0.15s;
    }
    .vb-social-pill:hover {
        opacity: 0.9;
        transform: translateY(-1px);
    }
    .vb-eco-wrapper {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        justify-content: center;
        font-size: 13px;
        color: #64748b;
    }
    .vb-eco-link {
        color: #0f766e !important;
        text-decoration: none;
        font-weight: 600;
    }
    .vb-eco-link:hover {
        text-decoration: underline;
    }
    .vb-copyright-text {
        font-size: 13px;
        color: #94a3b8;
        text-align: center;
    }

    /* ── RESPONSIVE MOBILE ── */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .vb-topbar {
            padding: 14px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0 14px;
            font-size: 13.5px;
            height: 42px;
        }
        .search-row-container {
            padding: 16px;
        }
    }
</style>
""")

# ==========================================
# 3. HEADER THANH ĐIỀU HƯỚNG
# ==========================================
render_html(f"""
<div class="vb-topbar">
    <div class="vb-brand-wrap">
        <div class="vb-brand-avatar">📖</div>
        <div>
            <div class="vb-brand-name">
                {CFG['app_name']}
                <span class="vb-badge-pill">{CFG['badge']}</span>
            </div>
            <div class="vb-brand-desc">{CFG['app_title']}</div>
        </div>
    </div>
    <div style="font-size: 13px; color: #64748b; font-weight: 500;">
        {CFG['tagline']}
    </div>
</div>
""")

# KHỞI TẠO STATE
if "current_url_input" not in st.session_state:
    st.session_state["current_url_input"] = ""
if "analyzed_data" not in st.session_state:
    st.session_state["analyzed_data"] = None

# ==========================================
# 4. CHIA 2 TÍNH NĂNG CHÍNH BẰNG TABS
# ==========================================
tab_download, tab_drive = st.tabs([
    "📥 Tải sách bản gốc (NXBGD)",
    "☁️ Kho sách Google Drive"
])

# ------------------------------------------
# TAB 1: TẢI SÁCH TỪ LINK
# ------------------------------------------
with tab_download:
    EXAMPLE_URL = "https://taphuan.nxbgd.vn/tap-huan/doc-sach/sgk-tin-hoc-12-dinh-huong-tin-hoc-ung-dung.4719365396#page=0"

    st.markdown("##### 🔗 Dán link đọc sách hoặc môn học từ taphuan.nxbgd.vn:")
    col_inp, col_btn = st.columns([4.2, 1.2], gap="small")

    with col_inp:
        user_url = st.text_input(
            "Nhập link taphuan.nxbgd.vn:",
            value=st.session_state["current_url_input"],
            placeholder="Ví dụ: https://taphuan.nxbgd.vn/tap-huan/doc-sach/...",
            label_visibility="collapsed"
        )

    with col_btn:
        analyze_btn = st.button("Tải sách", type="primary", use_container_width=True)

    st.caption(f"💡 Link mẫu dùng thử: [SGK Tin học 12 (Định hướng ứng dụng)]({EXAMPLE_URL})")

    # Xử lý khi nhấn Tải sách hoặc URL thay đổi
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
                    if err:
                        st.error(err)
                        st.session_state["analyzed_data"] = None
                    else:
                        st.session_state["analyzed_data"] = {"type": "doc_sach", "data": info}
                elif parsed["type"] == "chi_tiet_sach":
                    info, err = downloader.fetch_detail_editions(parsed["url"])
                    if err:
                        st.error(err)
                        st.session_state["analyzed_data"] = None
                    else:
                        st.session_state["analyzed_data"] = {"type": "chi_tiet_sach", "data": info}

    # HIỂN THỊ KẾT QUẢ TỐI GIẢN & NHANH
    if st.session_state.get("analyzed_data"):
        res = st.session_state["analyzed_data"]

        # 1. TRƯỜNG HỢP: SÁCH ĐƠN LẺ (doc_sach)
        if res["type"] == "doc_sach":
            book = res["data"]
            title = book["title"]
            page_urls = book["page_urls"]
            total_pages = book["total_pages"]

            offline_path, offline_sz = downloader.find_offline_pdf(title, CFG.get("storage_dir"))

            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:16px 20px; margin: 16px 0;">
                <div style="font-size:16px; font-weight:700; color:#0f172a;">📖 {title}</div>
                <div style="font-size:13px; color:#64748b; margin-top:4px;">Tổng số: <strong>{total_pages} trang</strong> • Bản gốc NXB Giáo Dục</div>
            </div>
            """, unsafe_allow_html=True)

            if offline_path and os.path.exists(offline_path):
                try:
                    with open(offline_path, "rb") as f:
                        file_data = f.read()
                    st.download_button(
                        label=f"💾 Tải ngay PDF có sẵn ({offline_sz:.1f} MB)",
                        data=file_data,
                        file_name=os.path.basename(offline_path),
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Lỗi đọc file: {e}")
            else:
                if st.button(f"📥 Bắt đầu tải PDF ({total_pages} trang)", type="primary", use_container_width=True):
                    p_bar = st.progress(0)
                    p_label = st.empty()

                    def progress_cb(current, total, msg):
                        pct = int((current / total) * 100) if total else 0
                        p_bar.progress(pct)
                        p_label.text(f"{msg} ({current}/{total})")

                    target_save = None
                    if CFG.get("storage_dir") and os.path.exists(CFG.get("storage_dir")):
                        target_save = os.path.join(CFG.get("storage_dir"), downloader.sanitize_filename(title) + ".pdf")

                    with st.spinner("Đang tải các trang ảnh gốc..."):
                        pdf_bytes, sz_mb, dl_err = downloader.download_pages_and_build_pdf(
                            page_urls=page_urls, title=title, progress_callback=progress_cb, save_path=target_save, max_workers=8
                        )

                    if dl_err:
                        st.error(dl_err)
                    else:
                        p_bar.progress(100)
                        p_label.text(f"✅ Hoàn tất ({sz_mb:.1f} MB)")
                        st.download_button(
                            label=f"💾 Lưu file PDF về máy ({sz_mb:.1f} MB)",
                            data=pdf_bytes,
                            file_name=f"{downloader.sanitize_filename(title)}.pdf",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True
                        )

        # 2. TRƯỜNG HỢP: MÔN HỌC NHIỀU ẤN BẢN (chi_tiet_sach)
        elif res["type"] == "chi_tiet_sach":
            detail = res["data"]
            st.markdown(f"##### 📚 {detail['main_title']} ({len(detail['editions'])} ấn bản)")
            st.caption("Chọn ấn bản bạn muốn tải:")

            for i, ed in enumerate(detail["editions"]):
                off_path, off_sz = downloader.find_offline_pdf(ed["title"], CFG.get("storage_dir"))
                status_txt = f" • Có sẵn ({off_sz:.1f} MB)" if off_path else ""

                col_name, col_action = st.columns([4.2, 1.2], gap="small")
                with col_name:
                    st.markdown(f"""
                    <div style="padding:10px 14px; background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; display:flex; align-items:center; gap:10px; min-height:48px;">
                        <span style="background:{ed['badge_color']}; color:#fff; font-size:11px; font-weight:700; padding:2px 8px; border-radius:6px; white-space:nowrap;">{ed['type_label']}</span>
                        <span style="font-weight:600; font-size:14px; color:#1e293b;">{ed['title']}</span>
                        <span style="font-size:12px; color:#059669; font-weight:600; white-space:nowrap;">{status_txt}</span>
                    </div>
                    """, unsafe_allow_html=True)
                with col_action:
                    if st.button("Chọn tải", key=f"sel_ed_{i}", use_container_width=True):
                        st.session_state["current_url_input"] = ed["doc_url"]
                        st.session_state["last_analyzed_url"] = ""
                        st.rerun()


# ------------------------------------------
# TAB 2: KHO SÁCH GOOGLE DRIVE
# ------------------------------------------
with tab_drive:
    drive_date = CFG.get("drive_date", "")
    main_drive_url = CFG.get("drive_link", "#")

    render_html(f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:20px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
            <div>
                <span style="font-size:11px; font-weight:700; color:#0f766e; letter-spacing:0.08em; text-transform:uppercase;">KHO GOOGLE DRIVE TRỰC TUYẾN</span>
                <h3 style="margin:4px 0 6px; color:#0f172a; font-size:20px;">Bộ sách Thống nhất (Bộ GD&amp;ĐT)</h3>
                <div style="font-size:13.5px; color:#64748b;">
                    Tải nhanh sách giáo khoa, sách giáo viên và vở bài tập theo từng khối lớp từ Lớp 1 đến Lớp 12.
                </div>
            </div>
            <div style="background:#f0fdf4; border:1px solid #bbf7d0; padding:8px 16px; border-radius:10px; text-align:center;">
                <div style="font-size:16px; font-weight:800; color:#15803d;">Lớp 1 – 12</div>
                <div style="font-size:11px; color:#166534;">Cập nhật {drive_date}</div>
            </div>
        </div>
    </div>
    """)

    # 12 KHỐI LỚP (LỚP 1 - LỚP 12)
    grade_items = CFG.get("grade_items", [])
    if not grade_items:
        grade_items = [{"grade": str(i), "name": f"Lớp {i}", "url": ""} for i in range(1, 13)]

    g_cols = st.columns(4, gap="small")
    for idx, item in enumerate(grade_items):
        with g_cols[idx % 4]:
            g_name = item.get("name", f"Lớp {idx+1}")
            g_url = item.get("url", "").strip()
            dest_url = g_url if g_url else main_drive_url

            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:12px 14px; margin-bottom:8px; display:flex; align-items:center; justify-content:space-between;">
                <div>
                    <div style="font-weight:700; font-size:14px; color:#0f172a;">📘 {g_name}</div>
                    <div style="font-size:11px; color:#64748b;">SGK, SGV &amp; VBT</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.link_button(f"Tải {g_name} ↗", dest_url, use_container_width=True)

    # KHU VỰC THAM GIA CỘNG ĐỒNG ĐỂ NHẬN LINK FULL
    zalo_url = next((s["url"] for s in CFG.get("socials", []) if "zalo" in s.get("id", "").lower() or "zalo" in s.get("name", "").lower()), "https://zalo.me/g/lapbvhp0mku5bvgle0a1")
    fb_url = next((s["url"] for s in CFG.get("socials", []) if "group" in s.get("id", "").lower() or "facebook_group" in s.get("id", "").lower()), "https://www.facebook.com/groups/1143352114790841")

    render_html(f"""
    <div style="background:linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%); border:1px solid #ccfbf1; border-radius:14px; padding:22px; margin-top:24px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <span style="font-size:22px;">🔒</span>
            <div style="font-size:17px; font-weight:800; color:#0f766e;">
                Kho sách Trọn bộ Toàn diện (52 GB • 1.700+ đầu sách)
            </div>
        </div>
        <div style="font-size:13.5px; color:#475569; line-height:1.6; margin-bottom:16px;">
            Bao gồm đầy đủ tất cả các bộ sách (Cánh Diều, Kết Nối Tri Thức, Chân Trời Sáng Tạo,...), tài liệu tập huấn và chuyên đề 12 khối lớp.<br>
            👉 <strong>Để nhận liên kết mở Full Kho sách:</strong> Thầy cô và các bạn vui lòng tham gia nhóm Zalo hoặc Cộng đồng Facebook vietApps để lấy link ghim miễn phí.
        </div>
    </div>
    """)

    col_btn1, col_btn2 = st.columns(2, gap="small")
    with col_btn1:
        st.link_button("💬 Tham gia Nhóm Zalo nhận Link Full ↗", zalo_url, type="primary", use_container_width=True)
    with col_btn2:
        st.link_button("👥 Tham gia Nhóm Facebook nhận Link Full ↗", fb_url, use_container_width=True)

    with st.expander("🔑 Đã là thành viên nhóm? Bấm vào đây để lấy Link Full Kho Google Drive", expanded=False):
        st.success("Cảm ơn bạn đã tham gia cộng đồng chia sẻ tri thức vietApps!")
        st.link_button("☁️ Mở Kho Sách Google Drive Trọn Bộ (52 GB) ↗", main_drive_url, type="primary", use_container_width=True)
        st.code(main_drive_url, language=None)


# ==========================================
# 5. CÔNG CỤ QUẢN TRỊ (NẾU CÓ PASSWORD)
# ==========================================
if ADMIN_PASSWORD:
    with st.expander("⚙️ Công cụ Quản trị viên (Đồng bộ sách)", expanded=False):
        admin_is_authorized = (
            st.session_state.get("admin_password_verified") == ADMIN_PASSWORD
        )

        if not admin_is_authorized:
            st.info("Khu vực này chỉ dành cho quản trị viên.")
            pwd = st.text_input("Mật khẩu quản trị:", type="password", key="admin_pwd")
            if st.button("Xác nhận", key="btn_admin_login"):
                if hmac.compare_digest(pwd, ADMIN_PASSWORD):
                    st.session_state["admin_password_verified"] = ADMIN_PASSWORD
                    st.rerun()
                else:
                    st.error("Sai mật khẩu.")
        else:
            st.markdown("Kiểm tra và cập nhật cơ sở dữ liệu sách từ NXB Giáo dục.")
            if st.button("Bắt đầu quét dữ liệu", key="btn_check_sync"):
                p_bar = st.progress(0)
                p_text = st.empty()
                sync_res = sync_manager.check_for_new_books(lambda msg, pct: (p_bar.progress(pct), p_text.text(msg)))
                p_bar.progress(100)
                p_text.empty()

                st.write(f"Online: {sync_res['total_online']} | Hiện tại: {sync_res['total_current']}")
                if sync_res["has_new"]:
                    st.success(f"Phát hiện {len(sync_res['new_books'])} sách mới.")
                    if st.button("Cập nhật CSDL", type="primary"):
                        sync_manager.update_catalog_and_report(sync_res["all_online_books"])
                        st.success("Đã cập nhật!")
                else:
                    st.info("Dữ liệu đã đồng bộ hoàn toàn.")


# ==========================================
# 6. FOOTER ĐẦY ĐỦ KẾT NỐI & LIÊN HỆ
# ==========================================
social_pills_html = ""
for s in CFG.get("socials", []):
    url = s.get("url", "#")
    name = s.get("title") or s.get("name", "")
    color = s.get("color", "#2563eb")
    social_pills_html += f"""
    <a href="{url}" target="_blank" rel="noopener noreferrer" class="vb-social-pill" style="background-color: {color};">
        <span>🔗</span> {name}
    </a>
    """

eco_links_html = " • ".join([
    f'<a href="{app.get("url", "#")}" target="_blank" class="vb-eco-link">{app.get("name")}</a>'
    for app in CFG.get("ecosystem", []) if app.get("url", "#") != "#"
])

render_html(f"""
<div class="vb-footer-container">
    <div style="font-weight:700; font-size:14px; color:#475569;">
        {CFG.get('connectMessage') or CFG.get('connect_message', 'Kết nối cộng đồng vietApps')}
    </div>
    <div class="vb-social-wrapper">
        {social_pills_html}
    </div>
    {f'<div class="vb-eco-wrapper">Hệ sinh thái: {eco_links_html}</div>' if eco_links_html else ''}
    <div class="vb-copyright-text">
        {CFG['copyright']} • Email hỗ trợ: <a href="mailto:{CFG['support_email']}" style="color:#64748b; text-decoration:none;">{CFG['support_email']}</a>
    </div>
</div>
""")
