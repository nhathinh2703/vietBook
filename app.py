import streamlit as st
import json
import os
import re
import urllib3
import xml.etree.ElementTree as ET

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Hàm render HTML an toàn, loại bỏ thụt lề thừa để tránh Markdown parse sai
def render_html(html_str):
    cleaned = "\n".join(line.strip() for line in html_str.strip().splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)


# ==========================================
# 1. ĐỌC CẤU HÌNH ĐỘNG TỪ CONFIG.XML
# ==========================================
def load_config(xml_path="config.xml"):
    config = {
        "master_name": "vietApps",
        "app_name": "vietBook",
        "badge": "FREE",
        "tagline": "Hệ sinh thái ứng dụng miễn phí phục vụ cộng đồng",
        "app_title": "Thư viện tra cứu & Tải sách giáo khoa điện tử",
        "hero_title": "Kho sách điện tử & Sách giáo viên toàn diện",
        "app_desc": "Hệ thống tra cứu tức thì và tải trọn bộ sách giáo viên, sách giáo khoa, sách bài tập chất lượng gốc.",
        "copyright": "© 2026 vietApps • vietBook – Thư viện sách điện tử",
        "support_email": "vietapps.official@gmail.com",
        "connect_message": "Kết nối với chúng tôi để xem hướng dẫn, cập nhật sách mới và sử dụng các tiện ích miễn phí",
        "drive_link": "",
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
            config["connect_message"] = brand.findtext("connectMessage", config["connect_message"])
            config["drive_link"] = brand.findtext("driveLink", "") or ""

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
                        "url": s.findtext("url", "#"),
                        "color": s.findtext("color", "#2563eb")
                    })

    except Exception as e:
        print(f"Lỗi đọc config.xml: {e}")

    return config

CFG = load_config()

# ==========================================
# 2. CẤU HÌNH TRANG STREAMLIT
# ==========================================
st.set_page_config(
    page_title=f"{CFG['app_name']} – {CFG['app_title']}",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS phong cách hiện đại viFix & vietApps
render_html("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container {
        max-width: 1240px !important;
        padding-top: 1rem !important;
        padding-bottom: 1.2rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }

    /* NAVBAR */
    .vb-nav-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 20px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .vb-brand-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .vb-brand-icon {
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: linear-gradient(135deg, #10b981, #059669);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 20px;
        box-shadow: 0 3px 8px rgba(16, 185, 129, 0.25);
    }
    .vb-brand-title {
        font-size: 22px;
        font-weight: 900;
        background: linear-gradient(90deg, #059669, #10b981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.4px;
    }
    .vb-brand-badge {
        font-size: 10px;
        font-weight: 800;
        padding: 2px 8px;
        border-radius: 12px;
        background: #d1fae5;
        color: #065f46;
        margin-left: 6px;
    }
    .vb-nav-tagline {
        font-size: 13px;
        color: #64748b;
        font-weight: 500;
    }

    /* THẺ THỐNG KÊ (STAT CARDS) */
    .vb-stats-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        margin-bottom: 18px;
    }
    @media (max-width: 800px) {
        .vb-stats-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    .vb-stat-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 14px 16px;
        display: flex;
        align-items: center;
        gap: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .vb-stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .vb-stat-icon-wrap {
        width: 46px;
        height: 46px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        flex-shrink: 0;
    }
    .vb-stat-num {
        font-size: 22px;
        font-weight: 900;
        color: #0f172a;
        line-height: 1.1;
    }
    .vb-stat-label {
        font-size: 12.5px;
        font-weight: 600;
        color: #64748b;
        margin-top: 3px;
    }

    /* KHUNG TÌM KIẾM & BẢNG SÁCH */
    .vb-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        margin-bottom: 16px;
    }
    .vb-card-title {
        font-size: 16px;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* BADGE LOẠI SÁCH */
    .badge-sgv {
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 6px;
    }
    .badge-sgk {
        background: #fef2f2;
        color: #b91c1c;
        border: 1px solid #fecaca;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 6px;
    }
    .badge-sbt {
        background: #fffbeb;
        color: #b45309;
        border: 1px solid #fde68a;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 6px;
    }
    .badge-other {
        background: #f1f5f9;
        color: #475569;
        border: 1px solid #cbd5e1;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 6px;
    }

    /* LINK BUTTON */
    .vb-read-btn {
        display: inline-block;
        padding: 4px 10px;
        background: #059669;
        color: #ffffff !important;
        text-decoration: none !important;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 700;
        transition: background 0.15s;
    }
    .vb-read-btn:hover {
        background: #047857;
    }

    /* HỆ SINH THÁI FOOTER */
    .vb-eco-wrapper {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 12px 16px;
        margin-top: 14px;
        margin-bottom: 12px;
    }
    .vb-eco-heading {
        font-size: 13px;
        font-weight: 800;
        color: #334155;
        margin-bottom: 10px;
    }
    .vb-eco-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
    }
    @media (max-width: 900px) {
        .vb-eco-grid {
            grid-template-columns: 1fr;
        }
    }
    .vb-app-item-card {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 10px 12px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        transition: all 0.15s ease;
    }
    .vb-app-card-current {
        border-color: #10b981;
        background: #f0fdf4;
    }
    .vb-app-item-title {
        font-size: 13.5px;
        font-weight: 800;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 4px;
    }
    .vb-app-item-badge {
        font-size: 9.5px;
        font-weight: 800;
        padding: 1px 6px;
        border-radius: 6px;
        color: #ffffff;
    }
    .vb-app-item-desc {
        font-size: 12px;
        color: #64748b;
        line-height: 1.35;
        margin-bottom: 8px;
    }
    .vb-app-item-btn {
        padding: 4px 10px;
        font-size: 11.5px;
        font-weight: 700;
        color: #059669 !important;
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        border-radius: 6px;
        text-align: center;
        text-decoration: none !important;
    }
    .vb-app-item-btn-current {
        padding: 4px 10px;
        font-size: 11.5px;
        font-weight: 700;
        color: #065f46;
        background: #d1fae5;
        border-radius: 6px;
        text-align: center;
    }

    /* BOTTOM FOOTER */
    .vb-bottom-footer {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding: 10px;
        text-align: center;
    }
    .vb-socials-group {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }
    .vb-social-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 4px 12px;
        border-radius: 16px;
        color: #ffffff !important;
        font-size: 11.5px;
        font-weight: 700;
        text-decoration: none !important;
    }
    .vb-footer-copy {
        font-size: 12px;
        color: #94a3b8;
    }
</style>
""")

# ==========================================
# 3. HEADER NAVBAR
# ==========================================
drive_btn_html = ""
if CFG.get("drive_link"):
    drive_btn_html = f"""
    <a href="{CFG['drive_link']}" target="_blank" style="padding: 6px 14px; background: #2563eb; color: #fff; font-size: 12.5px; font-weight: 700; border-radius: 8px; text-decoration: none; display: flex; align-items: center; gap: 6px;">
        <span>☁️ Tải trọn bộ Google Drive</span>
    </a>
    """

render_html(f"""
<div class="vb-nav-bar">
    <div class="vb-brand-left">
        <div class="vb-brand-icon">📖</div>
        <div>
            <div style="display:flex;align-items:center;">
                <span class="vb-brand-title">{CFG['app_name']}</span>
                <span class="vb-brand-badge">{CFG['badge']}</span>
            </div>
            <div style="font-size:12px;color:#64748b;font-weight:600;">{CFG['app_title']}</div>
        </div>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
        {drive_btn_html}
        <div class="vb-nav-tagline">{CFG['tagline']}</div>
    </div>
</div>
""")

# ==========================================
# 4. LOAD DỮ LIỆU SÁCH & THỐNG KÊ
# ==========================================
@st.cache_data
def load_books_data():
    json_path = "books_data.json"
    if not os.path.exists(json_path):
        return []
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

all_books = load_books_data()
total_books_count = len(all_books)

# Phân loại thống kê
count_sgv = sum(1 for b in all_books if b.get("type") == "SGV")
count_sgk = sum(1 for b in all_books if b.get("type") == "SGK")
count_sbt = sum(1 for b in all_books if b.get("type") == "SBT_VBT")
count_other = sum(1 for b in all_books if b.get("type") == "Tai_Lieu")

count_thong_nhat = sum(1 for b in all_books if "thống nhất" in b.get("series_label", "").lower())
count_ctst = sum(1 for b in all_books if "chân trời" in b.get("series_label", "").lower())

# Thống kê dung lượng offline nếu có
downloaded_dir = "downloaded_books"
total_downloaded_files = 0
total_downloaded_gb = 0.0
if os.path.exists(downloaded_dir):
    try:
        total_downloaded_files = sum(len(f) for r, d, f in os.walk(downloaded_dir) if any(x.endswith('.pdf') for x in f))
        bytes_sz = sum(os.path.getsize(os.path.join(r, x)) for r, d, f in os.walk(downloaded_dir) for x in f if x.endswith('.pdf'))
        total_downloaded_gb = bytes_sz / (1024 * 1024 * 1024)
    except Exception:
        pass

# ==========================================
# 5. CÁC THẺ THỐNG KÊ (STAT CARDS)
# ==========================================
render_html(f"""
<div class="vb-stats-grid">
    <div class="vb-stat-card">
        <div class="vb-stat-icon-wrap" style="background:#eff6ff;color:#2563eb;">📚</div>
        <div>
            <div class="vb-stat-num">{total_books_count:,}</div>
            <div class="vb-stat-label">Tổng số đầu sách điện tử</div>
        </div>
    </div>
    <div class="vb-stat-card">
        <div class="vb-stat-icon-wrap" style="background:#f0fdf4;color:#059669;">📘</div>
        <div>
            <div class="vb-stat-num">{count_sgv:,}</div>
            <div class="vb-stat-label">Sách Giáo Viên (SGV)</div>
        </div>
    </div>
    <div class="vb-stat-card">
        <div class="vb-stat-icon-wrap" style="background:#fef2f2;color:#dc2626;">📕</div>
        <div>
            <div class="vb-stat-num">{count_sgk:,}</div>
            <div class="vb-stat-label">Sách Giáo Khoa (SGK)</div>
        </div>
    </div>
    <div class="vb-stat-card">
        <div class="vb-stat-icon-wrap" style="background:#fffbeb;color:#d97706;">📙</div>
        <div>
            <div class="vb-stat-num">{count_sbt:,}</div>
            <div class="vb-stat-label">Sách / Vở Bài Tập (SBT)</div>
        </div>
    </div>
</div>
""")

# ==========================================
# 6. GIAO DIỆN TÌM KIẾM & BỘ LỌC ĐA NĂNG
# ==========================================
st.markdown('<div class="vb-card"><div class="vb-card-title">🔍 Bộ lọc &amp; Tra cứu sách giáo khoa / giáo viên</div>', unsafe_allow_html=True)

col_s1, col_s2, col_s3, col_s4 = st.columns([2.5, 1.5, 1.2, 1.2])

with col_s1:
    search_keyword = st.text_input("Tên môn học / Tiêu đề sách:", placeholder="Ví dụ: Toán 12, Tiếng Việt, Tin học, Ngữ văn...", label_visibility="collapsed")

with col_s2:
    series_options = ["Tất cả bộ sách", "Bộ SGK Thống nhất", "Chân trời sáng tạo"]
    selected_series = st.selectbox("Bộ sách:", series_options, label_visibility="collapsed")

with col_s3:
    grade_options = ["Tất cả lớp"] + [f"Lớp {i}" for i in range(1, 13)] + ["Lớp dùng chung"]
    selected_grade = st.selectbox("Khối lớp:", grade_options, label_visibility="collapsed")

with col_s4:
    type_options = ["Tất cả loại sách", "SGV (Giáo viên)", "SGK (Giáo khoa)", "SBT / VBT (Bài tập)", "Tài liệu tập huấn"]
    selected_type = st.selectbox("Loại sách:", type_options, label_visibility="collapsed")

st.markdown('</div>', unsafe_allow_html=True)

# Xử lý lọc dữ liệu
filtered_books = all_books

# 1. Lọc theo từ khóa
if search_keyword.strip():
    kw = search_keyword.strip().lower()
    filtered_books = [
        b for b in filtered_books
        if kw in b.get("title", "").lower() or kw in b.get("subject", "").lower()
    ]

# 2. Lọc theo bộ sách
if selected_series == "Bộ SGK Thống nhất":
    filtered_books = [b for b in filtered_books if "thống nhất" in b.get("series_label", "").lower()]
elif selected_series == "Chân trời sáng tạo":
    filtered_books = [b for b in filtered_books if "chân trời" in b.get("series_label", "").lower()]

# 3. Lọc theo khối lớp
if selected_grade != "Tất cả lớp":
    filtered_books = [b for b in filtered_books if b.get("grade_label") == selected_grade]

# 4. Lọc theo loại sách
if "SGV" in selected_type:
    filtered_books = [b for b in filtered_books if b.get("type") == "SGV"]
elif "SGK" in selected_type:
    filtered_books = [b for b in filtered_books if b.get("type") == "SGK"]
elif "SBT" in selected_type:
    filtered_books = [b for b in filtered_books if b.get("type") == "SBT_VBT"]
elif "Tài liệu" in selected_type:
    filtered_books = [b for b in filtered_books if b.get("type") == "Tai_Lieu"]

# ==========================================
# 7. HIỂN THỊ KẾT QUẢ TÌM KIẾM
# ==========================================
col_res_l, col_res_r = st.columns([3, 1])
with col_res_l:
    st.markdown(f"**Kết quả tìm kiếm:** Tìm thấy **{len(filtered_books):,}** cuốn sách phù hợp")
with col_res_r:
    if total_downloaded_files > 0:
        st.markdown(f"<div style='text-align:right;font-size:12px;color:#059669;font-weight:700;'>💾 Đã lưu offline: {total_downloaded_files} file ({total_downloaded_gb:.1f} GB)</div>", unsafe_allow_html=True)

if not filtered_books:
    st.info("💡 Không tìm thấy cuốn sách nào khớp với điều kiện tìm kiếm. Hãy thử từ khóa khác!")
else:
    # Phân trang hiển thị (mỗi trang 50 cuốn)
    items_per_page = 40
    total_pages = max(1, (len(filtered_books) + items_per_page - 1) // items_per_page)
    
    col_p1, col_p2 = st.columns([1, 4])
    with col_p1:
        current_page = st.number_input("Trang hiển thị:", min_value=1, max_value=total_pages, value=1, step=1)
    
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_books = filtered_books[start_idx:end_idx]

    # Bảng kết quả HTML sạch đẹp
    rows_html = []
    type_badge_map = {
        "SGV": '<span class="badge-sgv">📘 Giáo viên</span>',
        "SGK": '<span class="badge-sgk">📕 Giáo khoa</span>',
        "SBT_VBT": '<span class="badge-sbt">📙 Bài tập</span>',
        "Tai_Lieu": '<span class="badge-other">📑 Tập huấn</span>'
    }

    for idx, b in enumerate(page_books, start=start_idx + 1):
        btype = b.get("type", "Tai_Lieu")
        badge_html = type_badge_map.get(btype, '<span class="badge-other">Khác</span>')
        series_label = b.get("series_label", "Bộ SGK Thống nhất")
        title = b.get("title", "Chưa rõ tên")
        subject = b.get("subject", "")
        grade = b.get("grade_label", "")
        url = b.get("doc_url", "#")

        row = f"""
        <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px 8px; text-align: center; color: #94a3b8; font-size: 12px; font-weight: 700;">{idx}</td>
            <td style="padding: 10px 8px; font-weight: 700; color: #1e293b; font-size: 13px;">{grade}</td>
            <td style="padding: 10px 8px; color: #475569; font-size: 13px; font-weight: 600;">{subject}</td>
            <td style="padding: 10px 8px; font-weight: 700; color: #0f172a; font-size: 13.5px;">{title}</td>
            <td style="padding: 10px 8px; text-align: center;">{badge_html}</td>
            <td style="padding: 10px 8px; color: #64748b; font-size: 12px; font-weight: 600;">{series_label}</td>
            <td style="padding: 10px 8px; text-align: center;">
                <a href="{url}" target="_blank" class="vb-read-btn">Đọc trực tiếp ↗</a>
            </td>
        </tr>
        """
        rows_html.append(row)

    table_html = f"""
    <div style="overflow-x: auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; margin-top: 8px;">
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <thead>
                <tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-size: 12px; color: #64748b; font-weight: 800;">
                    <th style="padding: 10px 8px; text-align: center; width: 45px;">STT</th>
                    <th style="padding: 10px 8px; width: 75px;">KHỐI</th>
                    <th style="padding: 10px 8px; width: 170px;">MÔN HỌC</th>
                    <th style="padding: 10px 8px;">TÊN ẤN BẢN SÁCH</th>
                    <th style="padding: 10px 8px; text-align: center; width: 110px;">PHÂN LOẠI</th>
                    <th style="padding: 10px 8px; width: 160px;">BỘ SÁCH</th>
                    <th style="padding: 10px 8px; text-align: center; width: 120px;">THAO TÁC</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
    """
    render_html(table_html)

# ==========================================
# 8. HỆ SINH THÁI ỨNG DỤNG VIETAPPS
# ==========================================
eco_cards_html = []
for app in CFG["ecosystem"]:
    is_current = (app.get("id", "").lower() == "vietBook".lower()) or (app.get("url") == "#")
    if is_current:
        action_btn_html = """
        <div class="vb-app-item-btn-current">
            Đang sử dụng
        </div>
        """
    else:
        action_btn_html = f"""
        <a href="{app['url']}" target="_blank" class="vb-app-item-btn">
            Bắt đầu sử dụng ↗
        </a>
        """

    card_html = f"""
    <div class="vb-app-item-card {'vb-app-card-current' if is_current else ''}">
        <div>
            <div class="vb-app-item-title">
                <span>{app['icon']}</span>
                <span>{app['name']}</span>
                <span class="vb-app-item-badge" style="background-color: {app['badge_color']};">{app['badge']}</span>
                <span style="font-size:11.5px;color:#64748b;font-weight:600;">– {app['tagline']}</span>
            </div>
            <div class="vb-app-item-desc">{app['description']}</div>
        </div>
        {action_btn_html}
    </div>
    """
    eco_cards_html.append(card_html)

render_html(f"""
<div class="vb-eco-wrapper">
    <div class="vb-eco-heading">
        <span>🌐 Các ứng dụng trong hệ sinh thái {CFG['master_name']}:</span>
    </div>
    <div class="vb-eco-grid">
        {''.join(eco_cards_html)}
    </div>
</div>
""")

# ==========================================
# 9. FOOTER KẾT NỐI MẠNG XÃ HỘI
# ==========================================
social_pills = []
for s in CFG["socials"]:
    pill = f"""<a href="{s['url']}" target="_blank" class="vb-social-badge" style="background-color: {s['color']};">
        <span>{s['name']}</span>
    </a>"""
    social_pills.append(pill)

render_html(f"""
<div class="vb-bottom-footer">
    <div class="vb-socials-group">
        <span style="font-size:12px;font-weight:700;color:#64748b;">💬 {CFG['connect_message']}:</span>
        {''.join(social_pills)}
    </div>
    <div class="vb-footer-copy">
        {CFG['copyright']} • {CFG['support_email']}
    </div>
</div>
""")
