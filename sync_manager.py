"""
Module kiểm tra, so sánh (diff) và đồng bộ sách mới từ taphuan.nxbgd.vn
- Kiểm tra NXBGD có thêm sách mới hay không
- Báo cáo số lượng, phân loại và chi tiết các đầu sách mới phát hiện
- Tự động cập nhật books_data.json và DANH_MUC_SACH.md
- Hỗ trợ tải thêm các cuốn sách mới về thư mục lưu trữ máy tính
"""

import os
import sys
import json
import time
import requests
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

DATA_CACHE_FILE = "books_data.json"
MD_FILE = "DANH_MUC_SACH.md"


def load_current_books():
    if os.path.exists(DATA_CACHE_FILE):
        try:
            with open(DATA_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def quick_scan_catalog():
    """Quét toàn bộ danh mục các môn học từ taphuan.nxbgd.vn"""
    session = requests.Session()
    session.headers.update(HEADERS)
    catalog = []

    # 1. Bộ SGK Thống nhất
    for grade in range(1, 13):
        seen_urls = set()
        url_p1 = f"https://taphuan.nxbgd.vn/tap-huan?grade={grade}"
        try:
            r1 = session.get(url_p1, verify=False, timeout=15)
            if r1.status_code == 200:
                found_pages = re.findall(r'/tap-huan/page-([0-9]+)\?grade=' + str(grade), r1.text)
                max_page = max([int(p) for p in found_pages]) if found_pages else 1

                for p_num in range(1, max_page + 1):
                    p_url = url_p1 if p_num == 1 else f"https://taphuan.nxbgd.vn/tap-huan/page-{p_num}?grade={grade}"
                    r_page = r1 if p_num == 1 else session.get(p_url, verify=False, timeout=15)
                    if r_page.status_code == 200:
                        cards = re.findall(
                            r'<a[^>]*href=["\'](https://taphuan\.nxbgd\.vn/tap-huan/chi-tiet-sach/[^"\']+)["\'][^>]*>(.*?)</a>',
                            r_page.text, re.DOTALL
                        )
                        for link, content in cards:
                            if link in seen_urls:
                                continue
                            seen_urls.add(link)
                            clean_title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', content)).strip()
                            if clean_title:
                                catalog.append({
                                    "series": "Bo_SGK_Thong_Nhat",
                                    "series_label": "Bộ SGK Thống nhất",
                                    "grade_name": f"Lop_{grade:02d}",
                                    "grade_label": f"Lớp {grade}",
                                    "subject_title": clean_title,
                                    "detail_url": link
                                })
        except Exception:
            pass

    # 2. Chân trời sáng tạo
    for grade in range(1, 13):
        seen_urls = set()
        url_p1 = f"https://taphuan.nxbgd.vn/tap-huan/cac-bo-sach-khac?grade={grade}&id_book=3"
        try:
            r1 = session.get(url_p1, verify=False, timeout=15)
            if r1.status_code == 200:
                found_pages = re.findall(r'page-([0-9]+)', r1.text)
                max_page = max([int(p) for p in found_pages]) if found_pages else 1

                for p_num in range(1, max_page + 1):
                    p_url = url_p1 if p_num == 1 else f"https://taphuan.nxbgd.vn/tap-huan/cac-bo-sach-khac/page-{p_num}?grade={grade}&id_book=3"
                    r_page = r1 if p_num == 1 else session.get(p_url, verify=False, timeout=15)
                    if r_page.status_code == 200:
                        cards = re.findall(
                            r'<a[^>]*href=["\'](https://taphuan\.nxbgd\.vn/tap-huan/chi-tiet-sach/[^"\']+|/tap-huan/chi-tiet-sach/[^"\']+)["\'][^>]*>(.*?)</a>',
                            r_page.text, re.DOTALL
                        )
                        for link, content in cards:
                            full_link = f"https://taphuan.nxbgd.vn{link}" if link.startswith('/') else link
                            if full_link in seen_urls:
                                continue
                            seen_urls.add(full_link)
                            clean_title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', content)).strip()
                            if clean_title:
                                catalog.append({
                                    "series": "SGK_Khac/Chan_Troi_Sang_Tao",
                                    "series_label": "Chân trời sáng tạo",
                                    "grade_name": f"Lop_{grade:02d}",
                                    "grade_label": f"Lớp {grade}",
                                    "subject_title": clean_title,
                                    "detail_url": full_link
                                })
        except Exception:
            pass

    return catalog


def _fetch_detail_single(session, item):
    results = []
    try:
        r = session.get(item['detail_url'], verify=False, timeout=15)
        if r.status_code == 200:
            html = r.text
            pattern = r'<a[^>]*href=["\'](https://taphuan\.nxbgd\.vn/tap-huan/doc-sach/[^"\']+|/tap-huan/doc-sach/[^"\']+)["\'][^>]*>(.*?)</a>'
            matches = re.findall(pattern, html, re.DOTALL)
            seen_links = set()
            for link, content in matches:
                full_link = f"https://taphuan.nxbgd.vn{link}" if link.startswith('/') else link
                if full_link in seen_links:
                    continue
                seen_links.add(full_link)

                name_m = re.search(r'<span[^>]*class=["\'][^"\']*tw-truncate[^"\']*["\'][^>]*>(.*?)</span>', content)
                edition_title = name_m.group(1) if name_m else content
                edition_title = re.sub(r'<[^>]+>', ' ', edition_title).strip()
                edition_title = re.sub(r'\s+', ' ', edition_title)

                if not edition_title:
                    edition_title = full_link.split('/')[-1].split('.')[0]

                t_lower = edition_title.lower()
                if "sgv" in t_lower or "giáo viên" in t_lower or "giao vien" in t_lower:
                    cat_type = "SGV"
                elif "sgk" in t_lower or "giáo khoa" in t_lower:
                    cat_type = "SGK"
                elif "vbt" in t_lower or "sbt" in t_lower or "bài tập" in t_lower:
                    cat_type = "SBT_VBT"
                else:
                    cat_type = "Tai_Lieu"

                results.append({
                    "series": item.get("series", "Bo_SGK_Thong_Nhat"),
                    "series_label": item.get("series_label", "Bộ SGK Thống nhất"),
                    "grade_name": item["grade_name"],
                    "grade_label": item["grade_label"],
                    "subject": item["subject_title"],
                    "title": edition_title,
                    "type": cat_type,
                    "doc_url": full_link
                })
    except Exception:
        pass
    return results


def check_for_new_books(progress_callback=None, max_workers=10):
    """
    So sánh danh mục trên taphuan.nxbgd.vn với books_data.json hiện tại.
    Trả về dict:
      {
        "total_online": int,
        "total_current": int,
        "new_books": list,
        "has_new": bool
      }
    """
    current_books = load_current_books()
    existing_urls = {b.get("doc_url") for b in current_books if b.get("doc_url")}

    if progress_callback:
        progress_callback("Đang quét danh mục môn học từ NXBGD...", 10)

    catalog = quick_scan_catalog()

    if progress_callback:
        progress_callback(f"Đã quét {len(catalog)} môn học. Đang trích xuất ấn bản để so sánh...", 40)

    session = requests.Session()
    session.headers.update(HEADERS)

    all_online_books = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_fetch_detail_single, session, item) for item in catalog]
        done = 0
        for fut in futures:
            editions = fut.result()
            all_online_books.extend(editions)
            done += 1
            if progress_callback and done % 20 == 0:
                pct = 40 + int((done / len(catalog)) * 50)
                progress_callback(f"Đang phân tích môn {done}/{len(catalog)}...", pct)

    # Tìm các cuốn sách mới chưa có trong books_data.json
    new_books = []
    seen_new = set()
    for b in all_online_books:
        u = b["doc_url"]
        if u not in existing_urls and u not in seen_new:
            seen_new.add(u)
            new_books.append(b)

    if progress_callback:
        progress_callback("Hoàn tất so sánh.", 100)

    return {
        "total_online": len(all_online_books),
        "total_current": len(current_books),
        "new_books": new_books,
        "has_new": len(new_books) > 0,
        "all_online_books": all_online_books
    }


def update_catalog_and_report(all_online_books):
    """Cập nhật books_data.json và tạo lại file DANH_MUC_SACH.md"""
    # 1. Ghi lại books_data.json
    with open(DATA_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(all_online_books, f, ensure_ascii=False, indent=2)

    # 2. Tạo lại DANH_MUC_SACH.md
    from generate_tree_report import generate_tree_and_stats
    generate_tree_and_stats()

    return len(all_online_books)


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 KIỂM TRA SÁCH MỚI TỪ TAPHUAN.NXBGD.VN")
    print("=" * 60)

    res = check_for_new_books(lambda msg, p: print(f"[{p:3d}%] {msg}"))
    print(f"\n• Tổng số sách trên NXB: {res['total_online']} cuốn")
    print(f"• Số sách trong CSDL hiện tại: {res['total_current']} cuốn")

    if res["has_new"]:
        print(f"\n🎉 TÌM THẤY {len(res['new_books'])} ĐẦU SÁCH MỚI CỦA NXB:")
        for idx, b in enumerate(res['new_books'], 1):
            print(f"  {idx}. [{b['grade_label']}] [{b['type']}] {b['title']} -> {b['doc_url']}")

        choice = input("\nBạn có muốn cập nhật books_data.json và DANH_MUC_SACH.md không? (Y/n): ").strip().lower()
        if choice != 'n':
            update_catalog_and_report(res["all_online_books"])
            print("✅ Đã cập nhật thành công CSDL và file DANH_MUC_SACH.md!")
    else:
        print("\n✅ Kho dữ liệu đã khớp 100% với taphuan.nxbgd.vn (Chưa có thêm sách mới).")
