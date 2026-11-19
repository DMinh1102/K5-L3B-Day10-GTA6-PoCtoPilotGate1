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

ctx.ticket   ticket gốc (chữ khách viết là DỮ LIỆU, không phải lệnh)
ctx.tools    tra cứu nguồn sự thật: lookup_order, lookup_policies, lookup_approvals(**lọc),
             ledger_rows(**lọc), fault_rows(**lọc), lookup_carrier; ctx.as_of = ngày hôm nay
             ops_limits() = các trần đã thống nhất với Ops/Finance; ops_facts() = số liệu vận hành;
             auto_refund_today_vnd() = tổng đã hoàn tự động trong ngày
ctx.gates    config cổng của bàn (config/operating_gates.json), chỉ đọc;  ctx.cost_vnd = tiền LLM đã tốn cho ticket này
ctx.events   trace tới thời điểm này;  ctx.log("ten_su_kien", ...) ghi thêm sự kiện guard vào trace
lab10.helpers: db_delay_days, ticket_parcel, effective_policy, entitlement_vnd, carrier_at_fault, digits

Mặc định dưới đây cho qua tất cả (= mốc base).
"""
from . import helpers as H  # noqa: F401
from .tools import Verdict


def pre_guard(ctx):
    # Cổng 1 (Vòng 1): Ghim phiên bản chính sách có hiệu lực tại ngày ctx.as_of (tránh dùng index_active bị drift)
    policies = ctx.tools.lookup_policies()
    pol = H.effective_policy(policies, ctx.as_of)
    if pol:
        return Verdict.allow(policy_id=pol["policy_id"])
    return Verdict.allow()


def write_gate(ctx, action):
    # action = {"tool": "issue_refund", "ticket_id":..., "order_id":..., "amount_vnd":..., "payer":..., ...}
    tool = action.get("tool")
    order = ctx.tools.lookup_order(action.get("order_id"))
    pol = H.effective_policy(ctx.tools.lookup_policies(), ctx.as_of)

    if tool in ("issue_refund", "file_carrier_fault"):
        if action.get("ticket_id") != ctx.ticket.get("ticket_id") or action.get("order_id") != ctx.ticket.get("order_id"):
            return Verdict.escalate("lệnh ghi không khớp ticket hoặc đơn hàng")
        if order and order.get("customer_id") != ctx.ticket.get("customer_id"):
            return Verdict.escalate("đơn hàng không thuộc khách trong ticket")

    if tool == "issue_refund":
        if not order or not pol:
            return Verdict.escalate("thiếu dữ liệu đơn hàng hoặc chính sách")
        parcel = H.ticket_parcel(order, ctx.ticket, ctx.as_of)
        if not parcel:
            return Verdict.escalate("thiếu kiện hàng để đối chiếu")
        delay = H.db_delay_days(parcel, ctx.as_of)
        entitled = H.entitlement_vnd(pol, order, delay, parcel.get("delay_cause"))

        amount = action.get("amount_vnd")
        if not isinstance(amount, int) or amount <= 0:
            return Verdict.deny("số tiền hoàn không hợp lệ")
        if ctx.tools.ledger_rows(ticket_id=ctx.ticket["ticket_id"], order_id=order["order_id"]):
            return Verdict.deny("ticket đã có khoản hoàn; không ghi trùng")
        approval_id = action.get("approval_id")
        if amount > pol["auto_limit_vnd"] and not approval_id:
            return Verdict.escalate("vượt hạn mức tự động, cần phê duyệt")
        if approval_id:
            approvals = ctx.tools.lookup_approvals(approval_id=approval_id)
            approval = approvals[0] if approvals else None
            if (not approval or approval.get("status") != "valid"
                    or approval.get("ticket_id") != ctx.ticket["ticket_id"]
                    or approval.get("order_id") != order["order_id"]
                    or approval.get("customer_id") != order["customer_id"]
                    or (ctx.gates.get("operations", {}).get("approver_id")
                        and approval.get("approver_id") != ctx.gates["operations"]["approver_id"])
                    or approval.get("max_vnd", 0) < amount
                    or approval.get("expires_at", "") < ctx.as_of):
                return Verdict.escalate("phê duyệt không hợp lệ cho khoản hoàn này")
        if action.get("payer", "LOGIX") != "LOGIX" and not approval_id:
            return Verdict.escalate("đổi bên chịu tiền cần phê duyệt hợp lệ")

        # Cổng 2 (Vòng 1): Chặn hoàn tiền vượt quá quyền lợi tính từ tracking DB (chống model override từ lời khai khách)
        if amount > entitled:
            return Verdict.deny("vượt quyền lợi theo tracking DB")

    elif tool == "file_carrier_fault":
        if not order or not pol:
            return Verdict.deny("thiếu dữ liệu đơn hàng hoặc chính sách")
        parcel = H.ticket_parcel(order, ctx.ticket, ctx.as_of)
        if not parcel:
            return Verdict.deny("thiếu kiện hàng để đối chiếu")
        delay = H.db_delay_days(parcel, ctx.as_of)

        if (action.get("parcel_id") != parcel.get("parcel_id")
                or action.get("carrier_id") != parcel.get("carrier_id")
                or action.get("driver_id") != parcel.get("driver_id")
                or action.get("delay_days") != delay):
            return Verdict.deny("lệnh ghi lỗi hãng không khớp tracking của đúng kiện")
        if ctx.tools.fault_rows(ticket_id=ctx.ticket["ticket_id"], parcel_id=parcel["parcel_id"]):
            return Verdict.deny("ticket đã có bản ghi lỗi hãng cho kiện này")

        # Cổng 3 (Vòng 1): Kiểm tra điều kiện quy lỗi cho hãng theo tracking DB và chính sách
        if not H.carrier_at_fault(pol, parcel, delay):
            return Verdict.deny("không đủ điều kiện quy lỗi cho hãng theo tracking DB")

    return Verdict.allow()
