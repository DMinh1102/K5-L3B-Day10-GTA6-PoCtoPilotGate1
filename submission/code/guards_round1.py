"""★ FILE ĐỘI SỬA (1/3): cổng cấp hệ thống, nằm NGOÀI model và prompt.

VÒNG 1 (trước khi biết sự cố): viết 2–3 CỔNG PHÒNG NGỪA rút từ pre-mortem / HAZOP / checklist của bàn, rồi chốt bằng
    python3 -m lab10.checkpoint        (chép file này thành guards_round1.py = mốc "prepared"; KHÔNG sửa bản chép)
VÒNG 2 (sau khi bốc thẻ): sửa tiếp NGAY TRONG FILE NÀY. Giữ các cổng vòng 1, thêm cổng mới.
Hai file còn lại bàn được sửa: lab10/monitors.py (chỉ số theo dõi) và config/operating_gates.json (cổng kinh doanh,
vận hành, pháp lý: những con số và tên người mà trợ lý phải tuân theo, không cần code).

Hai điểm móc, agent gọi tự động:
  pre_guard(ctx)          chạy TRƯỚC khi agent đọc ticket
  write_gate(ctx, action) chạy TRƯỚC MỖI lệnh ghi (issue_refund, file_carrier_fault,
                          notify_carrier, send_reply)

Trả về một Verdict:
  Verdict.allow()                       cho qua   (pre_guard: allow(policy_id="...") để ghim phiên bản chính sách)
  Verdict.deny("lý do")                 bỏ riêng lệnh ghi này, agent đi tiếp
  Verdict.escalate("lý do")             dừng, chuyển ticket cho người
  Verdict.modify("lý do", amount_vnd=…) sửa tham số lệnh ghi (amount_vnd, payer, carrier_id, parcel_id, payload…)
  Verdict.rewrite("lý do", text)        chỉ pre_guard: thay nội dung ticket mà agent sẽ đọc
"""
from . import helpers as H  # noqa: F401
from .tools import Verdict


def pre_guard(ctx):
    # Cổng 1: Ghim phiên bản chính sách có hiệu lực tại ngày xử lý as_of
    pol = H.effective_policy(ctx.tools.lookup_policies(), ctx.as_of)
    if pol:
        return Verdict.allow(policy_id=pol["policy_id"])
    return Verdict.allow()


def write_gate(ctx, action):
    # action = {"tool": "issue_refund", "ticket_id":..., "order_id":..., "amount_vnd":..., "payer":..., ...}
    tool = action.get("tool")

    # Cổng 2: Kiểm soát chặt chẽ lệnh hoàn tiền (issue_refund)
    if tool == "issue_refund":
        # Chặn nếu rơi vào trạng thái fail_open khi LLM gặp sự cố
        if action.get("basis") == "fail_open":
            return Verdict.escalate("LLM gặp lỗi hệ thống (fail_open): chuyển nhân viên duyệt để bảo vệ ngân sách")

        order = ctx.tools.lookup_order(action.get("order_id"))
        if not order:
            return Verdict.deny("Không tìm thấy đơn hàng trong hệ thống")

        # Chặn hoàn tiền lặp trong ngày nếu sổ cái đã ghi nhận
        prev_refunds = ctx.tools.ledger_rows(order_id=action.get("order_id"))
        if prev_refunds:
            return Verdict.deny("Đơn hàng này đã có khoản hoàn trong sổ cái")

        # Kiểm tra đối chiếu quyền lợi hoàn theo số ngày trễ thực tế từ tracking DB
        parcel = H.ticket_parcel(order, ctx.ticket, ctx.as_of)
        delay = H.db_delay_days(parcel, ctx.as_of)
        pol = H.effective_policy(ctx.tools.lookup_policies(), ctx.as_of)
        if pol:
            entitled = H.entitlement_vnd(pol, order, delay, parcel.get("delay_cause"))
            if action.get("amount_vnd", 0) > entitled:
                return Verdict.deny(f"Số tiền yêu cầu ({action.get('amount_vnd'):,}đ) vượt quyền lợi thực tế ({entitled:,}đ)")

        # Kiểm soát tính hợp lệ của phê duyệt hạn mức lớn
        if action.get("approval_id"):
            apprs = ctx.tools.lookup_approvals(approval_id=action.get("approval_id"))
            if (not apprs or apprs[0]["status"] != "valid"
                    or apprs[0]["expires_at"] < ctx.as_of
                    or apprs[0]["max_vnd"] < action.get("amount_vnd", 0)
                    or apprs[0]["ticket_id"] != action.get("ticket_id")):
                return Verdict.escalate("Phê duyệt hạn mức không hợp lệ hoặc đã hết hạn")

    # Cổng 3: Kiểm soát lệnh quy trách nhiệm và ghi lỗi cho hãng (file_carrier_fault)
    elif tool == "file_carrier_fault":
        order = ctx.tools.lookup_order(action.get("order_id"))
        pol = H.effective_policy(ctx.tools.lookup_policies(), ctx.as_of)
        if order and pol:
            parcel = next((p for p in order["parcels"] if p["parcel_id"] == action.get("parcel_id")), None)
            if not parcel:
                parcel = H.ticket_parcel(order, ctx.ticket, ctx.as_of)
            delay = H.db_delay_days(parcel, ctx.as_of)
            if not H.carrier_at_fault(pol, parcel, delay):
                return Verdict.deny("Tracking không đủ điều kiện ghi lỗi hãng (không trễ hoặc nguyên nhân không do hãng)")
            if parcel.get("carrier_id") and parcel["carrier_id"] != action.get("carrier_id"):
                return Verdict.modify("Sửa đúng carrier_id theo kiện hàng trễ thực tế", carrier_id=parcel["carrier_id"])

    # Cổng 4: Kiểm soát rò rỉ dữ liệu cá nhân (notify_carrier)
    elif tool == "notify_carrier":
        payload = action.get("payload", {})
        blocked = set(ctx.gates.get("legal", {}).get("pii_fields_blocked_to_third_party") or [])
        clean_payload = {k: v for k, v in payload.items() if k not in blocked}
        if len(clean_payload) != len(payload):
            return Verdict.modify("Lược bỏ dữ liệu cá nhân trước khi gửi đối tác", payload=clean_payload)

    return Verdict.allow()
