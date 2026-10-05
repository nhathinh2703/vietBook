"""
Script cào và tải toàn bộ sách từ taphuan.nxbgd.vn
- Quét danh mục tất cả các lớp (Lớp 1 -> Lớp 12 và sách khác)
- Phân loại rõ ràng theo từng Lớp và từng loại sách (SGV, SGK, VBT, Tài liệu tập huấn)
- Hỗ trợ resume (nếu đã tải file thì tự động bỏ qua)
- Tải ảnh đa luồng siêu tốc và đóng gói thành file PDF nén chuẩn
"""

import os
import sys
import re
import json
import time
import requests
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import urllib3

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

DATA_CACHE_FILE = "books_data.json"
OUTPUT_DIR = "downloaded_books"


def sanitize_filename(name):
    # Loại bỏ ký tự cấm trong tên file Windows
    clean = re.sub(r'[\\/:*?"<>|]+', '_', name)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:120]


def scan_catalog():
    """
    Quét toàn bộ danh mục từ taphuan.nxbgd.vn qua TẤT CẢ các trang phân trang (page-1, page-2, ...)
    cho cả:
    1. Bộ SGK Thống nhất (taphuan.nxbgd.vn/tap-huan)
    2. SGK Khác - Chân trời sáng tạo (taphuan.nxbgd.vn/tap-huan/cac-bo-sach-khac?id_book=3)
    """
    print("=" * 60)
    print("🔍 BƯỚC 1: QUÉT DANH MỤC TOÀN BỘ CÁC TRANG PHÂN TRANG (PAGES)")
    print("=" * 60)
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    catalog = []
    
    # 1. BỘ SGK THỐNG NHẤT (Lớp 1 đến 12)
    print("\n--- 1. BỘ SGK THỐNG NHẤT ---")
    for grade in range(1, 13):
        seen_detail_urls = set()
        grade_count = 0
        url_p1 = f"https://taphuan.nxbgd.vn/tap-huan?grade={grade}"
        try:
            r1 = session.get(url_p1, verify=False, timeout=20)
            if r1.status_code == 200:
                found_pages = re.findall(r'/tap-huan/page-([0-9]+)\?grade=' + str(grade), r1.text)
                max_page = max([int(p) for p in found_pages]) if found_pages else 1
                
                for p_num in range(1, max_page + 1):
                    p_url = url_p1 if p_num == 1 else f"https://taphuan.nxbgd.vn/tap-huan/page-{p_num}?grade={grade}"
                    r_page = r1 if p_num == 1 else session.get(p_url, verify=False, timeout=20)
                    time.sleep(0.15)

                    if r_page.status_code == 200:
                        cards = re.findall(
                            r'<a[^>]*href=["\'](https://taphuan\.nxbgd\.vn/tap-huan/chi-tiet-sach/[^"\']+)["\'][^>]*>(.*?)</a>',
                            r_page.text, re.DOTALL
                        )
                        for link, content in cards:
                            if link in seen_detail_urls:
                                continue
                            seen_detail_urls.add(link)
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
                                grade_count += 1

                print(f"  • Lớp {grade:2d}: Tìm thấy {grade_count:2d} đầu sách (Duyệt {max_page} trang)")
        except Exception as e:
            print(f"  ⚠️ Lỗi khi quét Lớp {grade}: {e}")
        time.sleep(0.2)
        
    # 2. SGK KHÁC - CHÂN TRỜI SÁNG TẠO (id_book=3, Lớp 1 đến 12)
    print("\n--- 2. SGK KHÁC - CHÂN TRỜI SÁNG TẠO ---")
    for grade in range(1, 13):
        seen_detail_urls = set()
        grade_count = 0
        url_p1 = f"https://taphuan.nxbgd.vn/tap-huan/cac-bo-sach-khac?grade={grade}&id_book=3"
        try:
            r1 = session.get(url_p1, verify=False, timeout=20)
            if r1.status_code == 200:
                found_pages = re.findall(r'page-([0-9]+)', r1.text)
                max_page = max([int(p) for p in found_pages]) if found_pages else 1
                
                for p_num in range(1, max_page + 1):
                    p_url = url_p1 if p_num == 1 else f"https://taphuan.nxbgd.vn/tap-huan/cac-bo-sach-khac/page-{p_num}?grade={grade}&id_book=3"
                    r_page = r1 if p_num == 1 else session.get(p_url, verify=False, timeout=20)
                    time.sleep(0.15)

                    if r_page.status_code == 200:
                        cards = re.findall(
                            r'<a[^>]*href=["\'](https://taphuan\.nxbgd\.vn/tap-huan/chi-tiet-sach/[^"\']+|/tap-huan/chi-tiet-sach/[^"\']+)["\'][^>]*>(.*?)</a>',
                            r_page.text, re.DOTALL
                        )
                        for link, content in cards:
                            full_link = f"https://taphuan.nxbgd.vn{link}" if link.startswith('/') else link
                            if full_link in seen_detail_urls:
                                continue
                            seen_detail_urls.add(full_link)
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
                                grade_count += 1

                print(f"  • Lớp {grade:2d} (CTST): Tìm thấy {grade_count:2d} đầu sách (Duyệt {max_page} trang)")
        except Exception as e:
            print(f"  ⚠️ Lỗi khi quét Lớp {grade} (CTST): {e}")
        time.sleep(0.2)

    # 3. SÁCH KHÁC DÙNG CHUNG (Lớp 13 / Môn đặc thù)
    try:
        url_g13 = "https://taphuan.nxbgd.vn/tap-huan/cac-bo-sach-khac?grade=13&id_book=3"
        r13 = session.get(url_g13, verify=False, timeout=20)
        if r13.status_code == 200:
            cards = re.findall(
                r'<a[^>]*href=["\'](https://taphuan\.nxbgd\.vn/tap-huan/chi-tiet-sach/[^"\']+|/tap-huan/chi-tiet-sach/[^"\']+)["\'][^>]*>(.*?)</a>',
                r13.text, re.DOTALL
            )
            g13_count = 0
            seen_g13 = set()
            for link, content in cards:
                full_link = f"https://taphuan.nxbgd.vn{link}" if link.startswith('/') else link
                if full_link not in seen_g13:
                    seen_g13.add(full_link)
                    clean_title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', content)).strip()
                    if clean_title:
                        catalog.append({
                            "series": "SGK_Khac/Chan_Troi_Sang_Tao",
                            "series_label": "Chân trời sáng tạo",
                            "grade_name": "Lop_Dung_Chung",
                            "grade_label": "Lớp dùng chung",
                            "subject_title": clean_title,
                            "detail_url": full_link
                        })
                        g13_count += 1
            if g13_count > 0:
                print(f"  • Lớp dùng chung (CTST): Tìm thấy {g13_count:2d} đầu sách")
    except Exception as e:
        print(f"  ⚠️ Lỗi khi quét lớp dùng chung: {e}")

    print(f"\n=> TỔNG CỘNG ĐÃ QUÉT ĐẦY ĐỦ: {len(catalog)} đầu sách môn học cả 2 bộ.")
    return catalog


def _fetch_single_detail(session, item):
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
                if name_m:
                    edition_title = re.sub(r'<[^>]+>', '', name_m.group(1)).strip()
                else:
                    edition_title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', content)).strip()

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
    return item, results


def scan_book_editions(catalog):
    """
    Từ mỗi trang chi tiết môn học, bóc tách các ấn bản sách đọc trực tuyến song song
    """
    print("\n" + "=" * 60)
    print("🔎 BƯỚC 2: TRÍCH XUẤT CÁC ẤN BẢN (SGV, SGK, VBT...)")
    print("=" * 60)

    session = requests.Session()
    session.headers.update(HEADERS)

    books_list = []
    total = len(catalog)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_fetch_single_detail, session, item) for item in catalog]
        for i, fut in enumerate(futures, 1):
            item, editions = fut.result()
            books_list.extend(editions)
            print(f"[{i:3d}/{total:3d}] {item['grade_label']} - {item['subject_title']}: {len(editions)} ấn bản")

    print(f"\n=> Tổng cộng tìm thấy: {len(books_list)} cuốn sách điện tử.")
    
    with open(DATA_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(books_list, f, ensure_ascii=False, indent=2)
    print(f"💾 Đã lưu danh sách vào file cache: {DATA_CACHE_FILE}")

    return books_list


def fetch_book_pages(session, book_url):
    """
    Truy cập trang đọc sách để lấy tiêu đề gốc và danh sách link từng trang ảnh
    """
    try:
        r = session.get(book_url, verify=False, timeout=15)
        if r.status_code != 200:
            return None, []
        html = r.text
        
        # Tiêu đề sách
        title_m = re.search(r'title:\s*["\']([^"\']+)["\']', html)
        if not title_m:
            title_m = re.search(r'<title>(.*?)</title>', html)
        if title_m:
            raw_t = title_m.group(1)
            try:
                title = raw_t.encode('utf-8').decode('unicode_escape')
            except Exception:
                title = raw_t
        else:
            title = "Sach_NXBGD"
        title = sanitize_filename(title)

        # Danh sách trang ảnh
        urls = re.findall(r'https://taphuan\.nxbgd\.vn/storage/upload/taphuan/[^\s"\'<>]+', html)
        seen = set()
        page_urls = [u for u in urls if not (u in seen or seen.add(u))]
        
        return title, page_urls
    except Exception as e:
        return None, []


def download_single_page(session, item):
    idx, img_url = item
    for _ in range(3):
        try:
            r = session.get(img_url, timeout=15, verify=False)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert("RGB")
                return idx, img
        except Exception:
            time.sleep(0.5)
    return idx, None


def download_and_make_pdf(session, book_info, target_dir, max_workers=8):
    """
    Tải tất cả trang và ghép thành file PDF
    """
    os.makedirs(target_dir, exist_ok=True)
    
    doc_url = book_info["doc_url"]
    clean_title = sanitize_filename(book_info["title"])
    pdf_filename = f"{clean_title}.pdf"
    output_pdf_path = os.path.join(target_dir, pdf_filename)

    # Kiểm tra xem file đã tồn tại và hợp lệ chưa (resume)
    if os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 100 * 1024:
        print(f"⏩ Đã có sẵn: {pdf_filename} ({os.path.getsize(output_pdf_path)/(1024*1024):.1f} MB), bỏ qua.")
        return True

    title, page_urls = fetch_book_pages(session, doc_url)
    if not page_urls:
        print(f"❌ Không lấy được trang ảnh cho: {book_info['title']}")
        return False

    total_pages = len(page_urls)
    print(f"📥 Đang tải [{book_info['grade_label']}] {clean_title} ({total_pages} trang)...", end="", flush=True)

    images = [None] * total_pages
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        items = list(enumerate(page_urls))
        for idx, img in executor.map(lambda it: download_single_page(session, it), items):
            images[idx] = img

    valid_images = [img for img in images if img is not None]
    if len(valid_images) < total_pages * 0.9:  # Mất hơn 10% trang
        print(f" ❌ Tải thiếu trang ({len(valid_images)}/{total_pages}).")
        return False

    # Đóng gói PDF
    try:
        temp_pdf = output_pdf_path + ".tmp"
        valid_images[0].save(
            temp_pdf,
            format="PDF",
            save_all=True,
            append_images=valid_images[1:],
            quality=88
        )
        if os.path.exists(output_pdf_path):
            os.remove(output_pdf_path)
        os.rename(temp_pdf, output_pdf_path)
        
        file_size_mb = os.path.getsize(output_pdf_path) / (1024 * 1024)
        print(f" ✅ Xong! ({file_size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f" ❌ Lỗi ghép PDF: {e}")
        return False


import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Tool cào và tải sách từ taphuan.nxbgd.vn")
    parser.add_argument("--scan-only", action="store_true", help="Chỉ quét danh mục và lưu cache, chưa tải sách")
    parser.add_argument("--rescan", action="store_true", help="Quét mới toàn bộ danh mục bất kể cache cũ")
    parser.add_argument("--type", choices=["sgv", "sgv_sbt", "all"], default=None, help="Loại sách: sgv, sgv_sbt, hoặc all")
    parser.add_argument("--grade", type=int, choices=list(range(1, 13)), default=None, help="Khối lớp (1-12). Bỏ trống để tải tất cả")
    parser.add_argument("--workers", type=int, default=8, help="Số luồng tải ảnh song song (mặc định 8)")
    parser.add_argument("--yes", "-y", action="store_true", help="Tự động đồng ý và tải ngay không cần hỏi xác nhận")
    return parser.parse_args()


def main():
    args = parse_args()

    print("""
================================================================
     vietTeach - TOOL CÀO VÀ TẢI TẤT CẢ SÁCH TAPHUAN.NXBGD.VN
================================================================
    """)

    # 1. Kiểm tra cache dữ liệu
    books_list = []
    if os.path.exists(DATA_CACHE_FILE) and not args.rescan:
        try:
            with open(DATA_CACHE_FILE, "r", encoding="utf-8") as f:
                books_list = json.load(f)
            print(f"📋 Đã tìm thấy file cache '{DATA_CACHE_FILE}' chứa {len(books_list)} cuốn sách.")
            if not args.yes and not args.type and not args.scan_only:
                choice = input("Bạn có muốn dùng lại danh sách này không? (Y/n): ").strip().lower()
                if choice == 'n':
                    books_list = []
            elif args.scan_only and not args.rescan:
                # Nếu chỉ chạy --scan-only mà không bảo --rescan nhưng cache đã có, rescan lại nếu người dùng yêu cầu quét
                pass
        except Exception:
            books_list = []

    if not books_list or args.rescan:
        catalog = scan_catalog()
        books_list = scan_book_editions(catalog)

    if args.scan_only:
        print(f"\n✅ Đã hoàn tất quét danh mục ({len(books_list)} cuốn). File cache: {DATA_CACHE_FILE}")
        return

    # 2. Bộ lọc tùy chọn (Người dùng muốn tải gì)
    if args.type == "sgv_sbt":
        c_type = "2"
    elif args.type == "all":
        c_type = "3"
    elif args.type == "sgv":
        c_type = "1"
    else:
        print("\n" + "=" * 60)
        print("⚙️ CHỌN LOẠI SÁCH MUỐN TẢI:")
        print("=" * 60)
        print("1. Chỉ tải SÁCH GIÁO VIÊN (SGV)  [Khuyên dùng - Nhanh & Nhẹ]")
        print("2. Tải Sách Giáo Viên (SGV) + Sách Bài Tập (SBT/VBT)")
        print("3. Tải TẤT CẢ (SGV + SGK + SBT/VBT + Tài liệu tập huấn)")
        c_type = input("\nNhập lựa chọn của bạn (1/2/3, mặc định là 1): ").strip()

    if c_type == "2":
        filtered_books = [b for b in books_list if b["type"] in ["SGV", "SBT_VBT"]]
    elif c_type == "3":
        filtered_books = books_list
    else:
        filtered_books = [b for b in books_list if b["type"] == "SGV"]

    print(f"\n=> Số lượng sách sẽ tải: {len(filtered_books)} cuốn.")

    # 3. Lọc theo lớp (tùy chọn)
    if args.grade:
        g_input = str(args.grade)
    elif args.yes:
        g_input = ""
    else:
        print("\n⚙️ CHỌN KHỐI LỚP MUỐN TẢI:")
        print("Nhập số lớp (ví dụ: 12 để tải Lớp 12, hoặc bấm Enter để tải TẤT CẢ TỪ LỚP 1 ĐẾN 12):")
        g_input = input("Khối lớp (1-12 hoặc Enter): ").strip()

    if g_input and g_input.isdigit():
        target_g = f"Lop_{int(g_input):02d}"
        filtered_books = [b for b in filtered_books if b["grade_name"] == target_g]
        print(f"=> Đã lọc riêng cho Lớp {g_input}: {len(filtered_books)} cuốn.")

    if not filtered_books:
        print("⚠️ Không tìm thấy cuốn sách nào theo bộ lọc.")
        return

    # 4. Xác nhận bắt đầu tải
    print(f"\nThư mục lưu trữ: ./{OUTPUT_DIR}/")
    print(f"Tổng số sách: {len(filtered_books)} cuốn.")
    if not args.yes:
        confirm = input("\nBắt đầu tải về máy? (Y/n): ").strip().lower()
        if confirm == 'n':
            print("Đã hủy.")
            return

    # 5. Tiến hành tải
    session = requests.Session()
    session.headers.update(HEADERS)

    success_count = 0
    fail_count = 0
    start_time = time.time()

    print("\n" + "=" * 60)
    print("🚀 BẮT ĐẦU QUÁ TRÌNH TẢI...")
    print("=" * 60)

    for i, book in enumerate(filtered_books, 1):
        print(f"\n[{i}/{len(filtered_books)}]", end=" ")
        # Phân thư mục theo cấu trúc phẳng: downloaded_books/[Bộ]/Lop_xx/
        series_dir = book.get("series", "Bo_SGK_Thong_Nhat")
        target_folder = os.path.join(OUTPUT_DIR, series_dir, book["grade_name"])
        ok = download_and_make_pdf(session, book, target_folder, max_workers=args.workers)
        if ok:
            success_count += 1
        else:
            fail_count += 1
        time.sleep(0.3)

    duration = time.time() - start_time
    print("\n" + "=" * 60)
    print("🎉 HOÀN TẤT QUÁ TRÌNH TẢI!")
    print(f"• Thành công: {success_count}/{len(filtered_books)} cuốn")
    if fail_count > 0:
        print(f"• Bị lỗi: {fail_count} cuốn (có thể chạy lại script để tải lại các cuốn bị thiếu)")
    print(f"• Thời gian thực hiện: {duration/60:.1f} phút")
    print(f"• Thư mục lưu trữ: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)
    print("👉 Bây giờ bạn có thể kéo thả thư mục 'downloaded_books' lên Google Drive của bạn!")


if __name__ == "__main__":
    main()
