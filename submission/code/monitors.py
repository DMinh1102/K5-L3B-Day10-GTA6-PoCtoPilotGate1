"""★ FILE ĐỘI SỬA (2/3): chỉ số theo dõi (monitor). Thêm ÍT NHẤT MỘT chỉ số bắt được sự cố của bàn.

Mỗi monitor nhận danh sách trial (KHÔNG có nhãn đúng/sai, giống production) và trả về một số.
Một trial = {"ticket_id", "seed", "day", "status", "amount_vnd", "ticket", "events", "ledger", "faults", "outbound",
             "arrive_min", "warehouse", "cost_vnd", "review_kind", "queue_wait_min", "queue_stuck"}
  "day"            một ngày vận hành giả lập: các ticket cùng "day" và cùng "seed" chạy nối nhau trên cùng một sổ cái
  "arrive_min"     phút ticket tới trong ca (0..480)          "warehouse"   kho của đơn
  "cost_vnd"       tiền LLM + nền tảng đã tốn cho ticket      "review_kind" None / "escalated" (trợ lý chuyển người) /
  "queue_wait_min" số phút chờ người duyệt (None nếu không vào hàng chờ)     "recheck" (nhân viên tự kiểm lại)
Chỉ số có thể là kỹ thuật (tỉ lệ model đè số trong ticket lên DB), vận hành (số ca cần người trong giờ đông nhất),
hay kinh doanh (tỉ lệ ticket trợ lý đọc xong vẫn phải chuyển người).

lab10.grade kiểm: monitor chạy không lỗi, và giá trị trên gói sự cố khác giá trị trên bộ nền,
tức là monitor "sáng đèn" khi sự cố xảy ra.
"""


def escalation_rate(trials):
    return sum(t["status"] == "escalated" for t in trials) / max(1, len(trials))


def fail_open_rate(trials):
    """Tỉ lệ ticket mà LLM gặp lỗi (RateLimitError 429) và rơi vào fallback fail_open."""
    return round(sum(any(e.get("type") == "llm_fallback" and e.get("mode") == "fail_open" for e in t.get("events", []))
                     for t in trials) / max(1, len(trials)), 4)


def peak_hour_queue_rate(trials):
    """Tỉ lệ ca cần người xử lý (escalated hoặc recheck) dồn vào khung giờ cao điểm sau 20h (arrive_min >= 240)."""
    peak_trials = [t for t in trials if t.get("arrive_min", 0) >= 240]
    if not peak_trials:
        return 0.0
    return round(sum(bool(t.get("review_kind")) for t in peak_trials) / len(peak_trials), 4)


MONITORS = {
    "escalation_rate": escalation_rate,     # có sẵn; KHÔNG tính là metric mới của đội
    "fail_open_rate": fail_open_rate,
    "peak_hour_queue_rate": peak_hour_queue_rate,
}
STARTER_MONITORS = ("escalation_rate",)
