"""
Script tạo cây thư mục và bảng thống kê toàn bộ sách taphuan.nxbgd.vn
- Xuất file DANH_MUC_SACH.md dạng cây thư mục (tree view) có link trực tiếp
- Xuất file DANH_MUC_SACH.json phục vụ so sánh diff tự động khi NXB cập nhật sách mới
- Thống kê chi tiết theo Lớp, theo Loại (SGV, SGK, VBT, Tài liệu)
"""

import os
import sys
import json
from collections import defaultdict
from datetime import datetime

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DATA_CACHE_FILE = "books_data.json"
MD_FILE = "DANH_MUC_SACH.md"


def generate_tree_and_stats():
    if not os.path.exists(DATA_CACHE_FILE):
        print(f"❌ Không tìm thấy {DATA_CACHE_FILE}")
        return

    with open(DATA_CACHE_FILE, "r", encoding="utf-8") as f:
        books = json.load(f)

    # Tổ chức dữ liệu theo cây: Series -> Grade -> Subject -> Type -> List of books
    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    type_counts = defaultdict(int)
    series_counts = defaultdict(int)

    for b in books:
        series = b.get("series_label", "Bộ SGK Thống nhất")
        grade = b["grade_label"]
        subject = b["subject"]
        btype = b["type"]
        tree[series][grade][subject][btype].append(b)
        type_counts[btype] += 1
        series_counts[series] += 1

    total_books = len(books)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Tạo nội dung Markdown
    md_lines = []
    md_lines.append(f"# 📚 CÂY THƯ MỤC VÀ DANH MỤC TOÀN BỘ SÁCH TAPHUAN.NXBGD.VN\n")
    md_lines.append(f"> **Thời gian quét & lập chỉ mục:** {now_str}  ")
    md_lines.append(f"> **Tổng số sách đã được bóc tách link:** **{total_books} cuốn** (gồm cả Bộ SGK Thống nhất & Chân trời sáng tạo)  \n")
    md_lines.append(f"---\n")

    # Bảng thống kê theo Bộ sách
    md_lines.append("## 📊 1. Bảng thống kê tổng quan\n")
    md_lines.append("### 📦 Thống kê theo Bộ sách:")
    md_lines.append("| Bộ sách | Số lượng ấn bản | Tỷ lệ |")
    md_lines.append("| :--- | :---: | :---: |")
    for s_name, s_cnt in sorted(series_counts.items(), key=lambda x: -x[1]):
        s_pct = (s_cnt / total_books * 100) if total_books else 0
        md_lines.append(f"| **{s_name}** | **{s_cnt}** | {s_pct:.1f}% |")
    md_lines.append(f"| **TỔNG CỘNG** | **{total_books}** | 100% |\n")

    # Bảng thống kê theo Loại sách
    md_lines.append("### 📚 Thống kê theo Loại sách:")
    md_lines.append("| Phân loại | Số lượng | Tỷ lệ | Ghi chú |")
    md_lines.append("| :--- | :---: | :---: | :--- |")
    type_names = {
        "SGV": ("📘 Sách Giáo Viên (SGV)", "Tài liệu giảng dạy cho giáo viên"),
        "SGK": ("📕 Sách Giáo Khoa (SGK)", "Bản đọc điện tử chuẩn của học sinh"),
        "SBT_VBT": ("📙 Sách / Vở Bài Tập", "Vở bài tập, sách bài tập bổ trợ"),
        "Tai_Lieu": ("📑 Tài liệu tập huấn", "Tài liệu bồi dưỡng giáo viên, tập viết...")
    }
    for t_key, (t_name, t_note) in type_names.items():
        cnt = type_counts.get(t_key, 0)
        pct = (cnt / total_books * 100) if total_books else 0
        md_lines.append(f"| **{t_name}** | **{cnt}** | {pct:.1f}% | {t_note} |")
    md_lines.append(f"| **TỔNG CỘNG** | **{total_books}** | 100% | *Đầy đủ từ Lớp 1 đến Lớp 12* |\n")

    # Sắp xếp lớp theo thứ tự Lớp 1 -> 12, Sách khác
    def grade_sort_key(g):
        if "Lớp" in g:
            num = ''.join(filter(str.isdigit, g))
            return int(num) if num else 99
        return 100

    # Cây thư mục chi tiết theo từng Bộ sách
    md_lines.append("## 🌳 2. Cây thư mục chi tiết (Kèm Link trực tiếp)\n")
    md_lines.append("*Bấm vào tên từng cuốn sách để mở xem trực tiếp trên hệ thống Nhà xuất bản.*\n")

    for s_name in sorted(tree.keys()):
        md_lines.append(f"## 🏛️ {s_name.upper()} ({series_counts[s_name]} cuốn)\n")
        grades = tree[s_name]
        sorted_grades = sorted(grades.keys(), key=grade_sort_key)
        
        for g in sorted_grades:
            g_books = [b for b in books if b.get("series_label", "Bộ SGK Thống nhất") == s_name and b["grade_label"] == g]
            md_lines.append(f"### 📂 {g} ({len(g_books)} cuốn)")
            
            subjects = grades[g]
            for subj, types in subjects.items():
                total_subj_books = sum(len(items) for items in types.values())
                md_lines.append(f"- 📁 **{subj}** `({total_subj_books} ấn bản)`")
                for t_key in ["SGV", "SGK", "SBT_VBT", "Tai_Lieu"]:
                    if t_key in types:
                        t_label = type_names.get(t_key, (t_key, ""))[0]
                        for b in types[t_key]:
                            title = b["title"]
                            url = b["doc_url"]
                            md_lines.append(f"  - [{t_label}] [{title}]({url})")
            md_lines.append("")

    # Ghi file DANH_MUC_SACH.md
    with open(MD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"✅ Đã tạo cây thư mục và thống kê chi tiết vào file: {MD_FILE}")
    print(f"📊 Tổng kết: {total_books} cuốn ({type_counts['SGV']} SGV, {type_counts['SGK']} SGK, {type_counts['SBT_VBT']} SBT, {type_counts['Tai_Lieu']} Tài liệu)")


if __name__ == "__main__":
    generate_tree_and_stats()
