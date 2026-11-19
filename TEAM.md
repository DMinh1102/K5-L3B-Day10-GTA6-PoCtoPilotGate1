# Team

## Thông tin nhóm

- Tên nhóm : `GTA6`
- Lớp: `L3B`
- Repo của bàn: `K5-L3B-Day10-GTA6-PoCtoPilotGate1`
- Thẻ sự cố đã bốc (S1–S8): `S4`

## Thành viên

Họ tên đầy đủ và MSSV của **mọi** thành viên; bàn 3 người thì để trống dòng 4. Vai: Kỹ sư cổng · Sản phẩm và kinh doanh · Vận hành và pháp lý (README mục 3, phút 0–15).

| STT | Họ và tên | MSSV | Vai | Trưởng nhóm |
| --: | --------- | ---- | --- | :---------: |
|   1 | Đặng Đức Minh          | 2A202603886 | Kỹ sư cổng                                      |      X      |
|   2 | Phạm Quốc Huy          | 2A202603897 | Vận hành và kinh doanh & Sản phẩm và pháp lý    |             |
|   

Ghi `members` trong `submission/submission.json` theo dạng `"HoVaTen-MSSV"`, khớp bảng trên.

## Cá nhân

Mỗi thành viên tự viết một mục bên dưới (chép mẫu, đổi tiêu đề thành họ tên không dấu và MSSV, ví dụ `## NguyenVanAn-20241234`).

## DangDucMinh-2A202603886

### Phần việc phụ trách

- Vai trong bàn: Kỹ sư cổng (Trưởng nhóm).
- Phụ trách chính: Phiếu A (A0–A8), Phiếu B (B0–B4, B8), Phiếu C (C4–C9, C12).
- Kỹ thuật & Code: Thiết kế và cài đặt hệ thống cổng phòng vệ `lab10/guards.py` (`pre_guard` và `write_gate`), chốt checkpoint vòng 1 (`guards_round1.py`, `round1.lock`), xây dựng 2 metric giám sát mới trong `lab10/monitors.py` (`fail_open_rate` và `peak_hour_queue_rate`).

### Đóng góp cụ thể

- Ký và chốt `config/acceptance_criteria.json` (hash `35e1fdf0e2b7`).
- Triển khai cổng tất định `write_gate`: chặn hoàn tiền sai dựa trên quyền lợi thực tế từ cơ sở dữ liệu tracking (`entitlement_vnd`), chặn ghi phạt oan hãng vận chuyển khi nguyên nhân không thuộc trách nhiệm của hãng (`MERCHANT_HANDOVER`), chặn rò rỉ dữ liệu cá nhân (`customer_note`, `recipient_contact`).
- Khắc phục sự cố thẻ S4: ngăn chặn triệt để hành vi tự động hoàn tiền và phạt hãng bừa bãi khi LLM gặp mã lỗi 429 quá tải kích hoạt fallback `fail_open`.
- Cài đặt 2 hàm metric `fail_open_rate` và `peak_hour_queue_rate` vào `MONITORS`, giúp hệ thống tự động phát hiện lỗi 429 và hiện tượng dồn ứ hàng chờ sau 20h.

### Bằng chứng

- Commit: `4a7cb32` (Sign acceptance criteria), `0c28aac` (LAB 10: chốt cổng vòng 1, quyết định v1).
- Mã lần chạy:
  + Bộ nền prepared: `R-base-prepared-20261119-202028-11b61f` (100% pass_rate, 0đ hoàn sai, 0 lỗi oan, 0 lộ PII).
  + S4 after: `R-S4-after-20261119-204422-63347e` (100% pass_rate, 0 ca ùn, hoàn tự động 292.000đ <= 300.000đ).
  + Grade tự kiểm tra: `R-S4-grade-20261119-204421-63347e` (PASS-VISIBLE).

### Hỗ trợ AI

- Codex hỗ trợ rà soát `lab10/guards.py`, bổ sung kiểm tra phê duyệt, hoàn trùng và đối tượng ghi lỗi hãng; chạy lại test công khai và grade S4. Cần tự kiểm tra và giải thích các thay đổi này khi demo.

### Exit ticket

- Một điều học được: Khi LLM gặp sự cố nghẽn mạng (429 Rate Limit), cơ chế fallback `fail_open` cực kỳ nguy hiểm nếu không có cổng ghi tất định (`write_gate`) chặn cứng ở tầng thực thi. Cổng phòng vệ bên ngoài model là lớp bảo vệ sinh tử để giữ vững toàn vẹn tài chính và pháp lý.
- Một điều còn chưa chắc: Cần nghiên cứu thêm cơ chế xử lý ngoại lệ khi chính kết nối tới cơ sở dữ liệu tracking bị đứt quãng hoặc timeout trong giờ cao điểm siêu sale để tránh làm crash tiến trình guard.

## PhamQuocHuy-2A202603897

### Phần việc phụ trách

- Vai trong bàn: Vận hành và kinh doanh & Sản phẩm và pháp lý.
- Phụ trách chính: Phiếu B (B5–B7, B7.6 Giờ cao điểm), Phiếu C (C0–C3, C10–C11, C12).
- Vận hành & Cấu hình: Thiết kế chính sách vận hành và kinh doanh trong `config/operating_gates.json`, định hình cơ chế trực ca giờ cao điểm, tính toán chi phí mỗi ticket, ROI và hạn mức ngân sách hoàn tự động.

### Đóng góp cụ thể

- Điền bảng phân tích rủi ro pre-mortem (B6) và bảng kiểm 9 nhóm việc trước pilot (B5).
- Soát lỗi sự cố S4 trên trace: xác định rõ nguyên nhân do nghẽn hàng chờ khi 41 ticket dồn sau 20h và trần hoàn tự động ngày sale chưa được đồng bộ từ Finance.
- Điều chỉnh `config/operating_gates.json`:
  + Thiết lập `daily_refund_cap_vnd = 300000` theo đúng chỉ đạo của Finance cho ngày 11.11, giúp tổng hoàn tự động đạt 292.000đ <= 300.000đ.
  + Nâng `reviewers_on_shift = 2`, bật `decision_note = true` (rút ngắn thời gian duyệt còn 4 phút/ca, nâng công suất lên 12 ca/h), xóa sổ hoàn toàn 11 ca ùn tắc (`queue.stuck = 0`), đưa thời gian chờ tối đa từ 136 phút xuống 15 phút.
  + Duy trì hiệu quả kinh tế với ROI 0.37 (vượt ngưỡng tối thiểu 0.25) và chi phí mỗi ticket 7.296đ (dưới trần 8.000đ).
- Cập nhật Risk Register (C10), Checklist 9 nhóm việc và Runbook 4-5 phục vụ giám sát vận hành thực tế.

### Bằng chứng

- Phiếu B mục B5, B6, B7 (Runbook 1–3, Giờ cao điểm B7.6).
- Phiếu C mục C0, C1, C2, C10, C11, C12.
- Cấu hình vận hành trong `config/operating_gates.json`.
- Báo cáo kết quả: `runs/R-S4-grade-20261119-204421-63347e.md` xác nhận 0 ca ùn tắc, 0 dòng vượt trần kinh doanh và vận hành.

### Hỗ trợ AI
- Codex hỗ trợ đối chiếu số liệu và điều kiện dừng trong Phiếu C, `config/operating_gates.json` và gói nộp; các số liệu lịch sử ở Phiếu B được giữ nguyên và sai lệch được ghi rõ trong Phiếu C. Cần tự kiểm tra và giải thích các thay đổi này khi demo.
- Codex hỗ trợ tổng hợp thông tin từ các lần chạy evaluation, giúp đưa ra kết luận trong phiếu B.

### Exit ticket

- Một điều học được: Năng lực của con người trong chu trình AI-in-the-loop (human-in-the-loop) là một thành phần có giới hạn hữu hạn (INCAPABLE). Khi AI đẩy nhiều ca nghi vấn sang người duyệt, việc tăng cường công cụ hỗ trợ giải thích (`decision_note`) và linh hoạt mở rộng nhân sự trực ca (`reviewers_on_shift`) là yếu tố quyết định để giữ vững cam kết SLA.
- Một điều còn chưa chắc: Cần khảo sát thêm mức độ mệt mỏi và tỷ lệ duyệt sai sót của reviewer khi phải làm việc liên tục trong khung giờ đêm khuya 20h–24h của ngày sale lớn.
