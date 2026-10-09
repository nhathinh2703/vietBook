"""
Module xử lý bóc tách và tải sách từ taphuan.nxbgd.vn
- Phân tích URL (hỗ trợ cả link đọc sách và link chi tiết môn học)
- Bóc tách danh sách trang ảnh gốc chất lượng cao
- Tải đa luồng siêu tốc và đóng gói thành file PDF nén chuẩn
- Kiểm tra cache file offline có sẵn trên máy (D:\\DuLieu\\SachDienTu)
"""

import os
import re
import io
import time
import requests
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
}


def sanitize_filename(name):
    """Làm sạch tên file hợp lệ trên Windows/Linux"""
    clean = re.sub(r'[\\/:*?"<>|]+', '_', name)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:140]


def decode_vietnamese_text(text):
    """Giải mã chuỗi unicode escape (ví dụ: Ti\\u1ebfng Vi\\u1ec7t -> Tiếng Việt)"""
    if not text:
        return ""
    try:
        # Nếu chuỗi chứa \uXXXX
        if r'\u' in text:
            return text.encode('utf-8').decode('unicode_escape')
    except Exception:
        pass
    return text.strip()


def parse_taphuan_url(raw_input):
    """
    Phân tích chuỗi URL nhập vào:
    Trả về dict:
      {
        "valid": bool,
        "type": "doc_sach" | "chi_tiet_sach" | "invalid",
        "url": str,
        "message": str
      }
    """
    if not raw_input:
        return {"valid": False, "type": "invalid", "url": "", "message": "Vui lòng dán link từ taphuan.nxbgd.vn"}

    clean_url = raw_input.strip()
    # Loại bỏ fragment #... nếu có (ví dụ: #page=0)
    clean_url = re.sub(r'#.*$', '', clean_url).strip()
    # Thêm https nếu thiếu protocol
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    if "taphuan.nxbgd.vn" not in clean_url:
        return {
            "valid": False,
            "type": "invalid",
            "url": clean_url,
            "message": "Link không thuộc hệ thống taphuan.nxbgd.vn. Vui lòng kiểm tra lại."
        }

    if "/tap-huan/doc-sach/" in clean_url:
        return {
            "valid": True,
            "type": "doc_sach",
            "url": clean_url,
            "message": "Link đọc sách trực tuyến hợp lệ."
        }
    elif "/tap-huan/chi-tiet-sach/" in clean_url:
        return {
            "valid": True,
            "type": "chi_tiet_sach",
            "url": clean_url,
            "message": "Link chi tiết môn học hợp lệ (chứa nhiều ấn bản SGV, SGK, SBT)."
        }
    else:
        return {
            "valid": False,
            "type": "invalid",
            "url": clean_url,
            "message": "Link hợp lệ phải có dạng '.../tap-huan/doc-sach/...' hoặc '.../tap-huan/chi-tiet-sach/...'"
        }


def fetch_reader_info(doc_url, session=None):
    """
    Truy cập trang đọc sách (.../tap-huan/doc-sach/...) để bóc tách:
    - Tiêu đề sách
    - Danh sách link ảnh từng trang (độ phân giải gốc)
    - Ảnh bìa / trang xem trước
    """
    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)

    try:
        r = session.get(doc_url, verify=False, timeout=15)
        if r.status_code != 200:
            return None, f"Không thể tải trang đọc sách (Mã lỗi HTTP: {r.status_code})"

        html = r.text

        # Lấy tiêu đề sách
        title = "Sách NXB Giáo Dục"
        title_m = re.search(r'title:\s*["\']([^"\']+)["\']', html)
        if not title_m:
            title_m = re.search(r'<title>(.*?)</title>', html)
        if title_m:
            raw_title = title_m.group(1).replace(" - Tập huấn NXBGD", "").strip()
            title = decode_vietnamese_text(raw_title)

        # Lấy danh sách link ảnh các trang
        urls = re.findall(r'https://taphuan\.nxbgd\.vn/storage/upload/taphuan/[^\s"\'<>]+', html)
        seen = set()
        page_urls = [u for u in urls if not (u in seen or seen.add(u))]

        if not page_urls:
            return None, "Không tìm thấy dữ liệu trang ảnh trong cuốn sách này (có thể sách cần đăng nhập hoặc chưa mở công khai)."

        preview_url = page_urls[0] if page_urls else ""

        return {
            "title": title,
            "page_urls": page_urls,
            "total_pages": len(page_urls),
            "preview_url": preview_url,
            "doc_url": doc_url
        }, None

    except Exception as e:
        return None, f"Lỗi kết nối tới taphuan.nxbgd.vn: {str(e)}"


def fetch_detail_editions(detail_url, session=None):
    """
    Truy cập trang chi tiết môn học (.../tap-huan/chi-tiet-sach/...) để trích xuất
    tất cả các ấn bản có trong môn này (SGV, SGK, VBT, Tài liệu tập huấn...)
    """
    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)

    try:
        r = session.get(detail_url, verify=False, timeout=15)
        if r.status_code != 200:
            return None, f"Không thể truy cập trang môn học (Mã HTTP: {r.status_code})"

        html = r.text

        # Bóc tách tên môn học chính
        main_title = "Môn học"
        m_title = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if not m_title:
            m_title = re.search(r'<title>(.*?)</title>', html)
        if m_title:
            clean_main = re.sub(r'<[^>]+>', ' ', m_title.group(1))
            main_title = decode_vietnamese_text(clean_main).replace(" - Tập huấn NXBGD", "").strip()

        pattern = r'<a[^>]*href=["\'](https://taphuan\.nxbgd\.vn/tap-huan/doc-sach/[^"\']+|/tap-huan/doc-sach/[^"\']+)["\'][^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)

        editions = []
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

            edition_title = decode_vietnamese_text(edition_title)

            t_lower = edition_title.lower()
            if "sgv" in t_lower or "giáo viên" in t_lower or "giao vien" in t_lower:
                cat_type = "SGV"
                type_label = "Sách Giáo Viên"
                badge_color = "#2563eb"
            elif "sgk" in t_lower or "giáo khoa" in t_lower:
                cat_type = "SGK"
                type_label = "Sách Giáo Khoa"
                badge_color = "#dc2626"
            elif "vbt" in t_lower or "sbt" in t_lower or "bài tập" in t_lower or "vở bài tập" in t_lower:
                cat_type = "SBT_VBT"
                type_label = "Sách / VBT"
                badge_color = "#d97706"
            else:
                cat_type = "Tai_Lieu"
                type_label = "Tài Liệu Tập Huấn"
                badge_color = "#475569"

            editions.append({
                "title": edition_title,
                "type": cat_type,
                "type_label": type_label,
                "badge_color": badge_color,
                "doc_url": full_link
            })

        if not editions:
            return None, "Không tìm thấy ấn bản sách nào trong trang môn học này."

        return {
            "main_title": main_title,
            "editions": editions,
            "detail_url": detail_url
        }, None

    except Exception as e:
        return None, f"Lỗi khi trích xuất trang môn học: {str(e)}"


def _download_one_page(session, item):
    """Hàm tải 1 ảnh trang với cơ chế thử lại"""
    idx, img_url = item
    for _ in range(3):
        try:
            r = session.get(img_url, timeout=15, verify=False)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert("RGB")
                return idx, img
        except Exception:
            time.sleep(0.4)
    return idx, None


def download_pages_and_build_pdf(page_urls, title, progress_callback=None, save_path=None, max_workers=8):
    """
    Tải danh sách trang ảnh và đóng gói PDF.
    - progress_callback(current, total, status_text)
    - Trả về: (bytes_data, file_size_mb, error)
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    total_pages = len(page_urls)
    images = [None] * total_pages

    if progress_callback:
        progress_callback(0, total_pages, f"Bắt đầu tải {total_pages} trang ảnh gốc...")

    completed_count = 0
    items = list(enumerate(page_urls))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_download_one_page, session, it): it[0] for it in items}
        for future in as_completed(futures):
            idx, img = future.result()
            images[idx] = img
            completed_count += 1
            if progress_callback:
                progress_callback(completed_count, total_pages, f"Đang tải trang {completed_count}/{total_pages}...")

    # Lọc các trang hợp lệ
    valid_images = [img for img in images if img is not None]
    if len(valid_images) < total_pages * 0.85:
        return None, 0, f"Tải thiếu nhiều trang ({len(valid_images)}/{total_pages} trang). Vui lòng thử lại."

    if progress_callback:
        progress_callback(total_pages, total_pages, "Đang đóng gói và nén file PDF chuẩn...")

    # Đóng gói PDF
    pdf_buffer = io.BytesIO()
    valid_images[0].save(
        pdf_buffer,
        format="PDF",
        save_all=True,
        append_images=valid_images[1:],
        quality=88
    )
    pdf_bytes = pdf_buffer.getvalue()
    size_mb = len(pdf_bytes) / (1024 * 1024)

    # Nếu có chỉ định đường dẫn lưu trữ trên đĩa
    if save_path:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(pdf_bytes)
        except Exception:
            pass

    return pdf_bytes, size_mb, None


def find_offline_pdf(book_title, storage_dir):
    """
    Tìm kiếm xem cuốn sách đã có file PDF sẵn trong thư mục máy tính hay chưa.
    Trả về: (full_path, size_mb) hoặc (None, 0)
    """
    if not storage_dir or not os.path.exists(storage_dir):
        return None, 0

    clean_search = sanitize_filename(book_title).lower().replace(" ", "").replace("_", "")

    try:
        for root, dirs, files in os.walk(storage_dir):
            for file in files:
                if file.lower().endswith(".pdf"):
                    clean_file = file.lower()[:-4].replace(" ", "").replace("_", "")
                    if clean_file == clean_search or clean_search in clean_file or clean_file in clean_search:
                        full_path = os.path.join(root, file)
                        size_mb = os.path.getsize(full_path) / (1024 * 1024)
                        return full_path, size_mb
    except Exception:
        pass

    return None, 0
