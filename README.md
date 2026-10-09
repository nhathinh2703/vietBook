# vietBook 📖 - Trình tải sách giáo khoa gốc & Kho Google Drive

Ứng dụng web và công cụ dòng lệnh thuộc hệ sinh thái **vietApps** phục vụ giáo viên, học sinh và phụ huynh:
1. **Trình tải sách chuyên nghiệp:** Chỉ cần sao chép link từ [taphuan.nxbgd.vn](https://taphuan.nxbgd.vn) để tải trọn bộ file PDF chất lượng gốc.
2. **Kho sách Google Drive trọn bộ (52 GB):** Đã hoàn tất tải ngày 05/10/2026, giúp Thầy Cô chỉ với một nút bấm hay một chạm là có thể tải về máy ngay lập tức.
3. **Mở khóa nhẹ nhàng:** Kết nối qua Zalo, Facebook Page, Facebook Group, YouTube, TikTok hoặc bấm **"Chỉ lấy link"** để hiển thị link tải ngay tức thì kèm hiệu ứng chúc mừng.
4. **Công cụ tự động kiểm tra sách mới từ NXBGD:** Tự động so sánh dữ liệu trực tiếp, cập nhật `books_data.json` và `DANH_MUC_SACH.md`.

---

## 📊 Thống kê kho dữ liệu
- **Tổng số đầu sách trong cơ sở dữ liệu:** 1.718 cuốn
- **Sách Giáo Viên (SGV):** 801 cuốn
- **Sách Giáo Khoa (SGK):** 601 cuốn
- **Sách / Vở Bài Tập (SBT):** 286 cuốn
- **Đã tải về & đóng gói PDF:** ~1.497 file (51.95 GB) lưu trữ tại `D:\DuLieu\SachDienTu`

---

## 🚀 Khởi chạy ứng dụng Web

### Cách 1: Chạy bằng file `run.bat`
Click đúp chuột vào file **`run.bat`** để khởi động ứng dụng ngay lập tức.

### Cách 2: Chạy bằng dòng lệnh
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Bật công cụ quản trị
Mặc định, khu vực đồng bộ dành cho quản trị viên sẽ không xuất hiện nếu chưa cấu hình mật khẩu. Trong PowerShell (bao gồm Terminal tích hợp của VS Code), đặt mật khẩu trước khi chạy ứng dụng:

```powershell
$env:VIETBOOK_ADMIN_PASSWORD = "mat-khau-quan-tri-cua-ban"
.\run.bat
```

Khu vực quản trị sẽ nằm trong mục thu gọn ở cuối trang và chỉ hiện chức năng đồng bộ sau khi nhập đúng mật khẩu. Biến `$env:` chỉ có hiệu lực trong cửa sổ Terminal hiện tại; nếu mở Terminal mới, cần đặt lại trước khi chạy. Không chia sẻ mật khẩu hoặc lưu mật khẩu thật vào mã nguồn.

---

## 🔄 Kiểm tra và cập nhật sách mới từ NXBGD
Để kiểm tra xem Nhà xuất bản Giáo dục có vừa bổ sung cuốn sách mới nào hay không và tự động cập nhật `books_data.json` + `DANH_MUC_SACH.md`:

```bash
# Chạy công cụ kiểm tra và so sánh diff tự động
python sync_manager.py
```
*(Bạn cũng có thể bấm trực tiếp nút **Kiểm tra sách mới từ taphuan.nxbgd.vn** ngay trên giao diện web)*.
