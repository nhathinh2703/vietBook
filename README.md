# vietBook 📖 - Kho Sách & Thư Viện Tra Cứu Sách Giáo Khoa Điện Tử

Ứng dụng web và công cụ dòng lệnh thuộc hệ sinh thái **vietApps** phục vụ giáo viên và phụ huynh tra cứu, tải sách điện tử chất lượng gốc từ Bộ GD&ĐT (Bộ SGK Thống nhất, Chân trời sáng tạo, Cánh diều).

---

## 📊 Thống kê hiện tại
- **Tổng số đầu sách trong cơ sở dữ liệu:** 1.749 cuốn
- **Sách Giáo Viên (SGV):** 808 cuốn
- **Sách Giáo Khoa (SGK):** 620 cuốn
- **Sách / Vở Bài Tập (SBT):** 291 cuốn
- **Đã tải về & đóng gói PDF:** ~1.559 file (53.76 GB)

---

## 🚀 Khởi chạy ứng dụng Web tra cứu
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 🛠️ Sử dụng Tool dòng lệnh (Crawler)
```bash
# Quét lại toàn bộ danh mục cập nhật mới
python crawler_nxbgd.py --scan-only --rescan

# Tải sách giáo viên lớp 12
python crawler_nxbgd.py --type sgv --grade 12 -y

# Tạo cây thư mục DANH_MUC_SACH.md
python generate_tree_report.py
```
