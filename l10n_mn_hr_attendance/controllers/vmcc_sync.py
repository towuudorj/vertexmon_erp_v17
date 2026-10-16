# -*- coding: utf-8 -*-
# VMC Connect: the Power Automate flows call this right after HR approves, so Odoo takes the request in at once
# instead of at the next run of the cron (which stays, for when this call doesn't come through).
#
#   POST https://erp.vertexmon.com/vmcc/sync   header  X-VMCC-Key: <system parameter vmcc.sync_key>
#   body {"kind": "leave"} or {"kind": "edit"}
import hmac
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

CRONS = {
    'leave': 'l10n_mn_hr_attendance.ir_cron_get_approved_leaves',  # Microsoft: Батлагдсан чөлөө татах
    'edit': 'l10n_mn_hr_attendance.ir_cron_get_att_edit_req',      # Microsoft: Ирц нөхөн засах хүсэлт
}


class VmccSync(http.Controller):

    @http.route('/vmcc/sync', type='http', auth='public', methods=['POST'], csrf=False)
    def vmcc_sync(self, **kwargs):
        def answer(status, **body):
            return request.make_json_response(body, status=status)

        key = request.env['ir.config_parameter'].sudo().get_param('vmcc.sync_key') or ''
        given = request.httprequest.headers.get('X-VMCC-Key') or ''
        if not key or not hmac.compare_digest(key.encode(), given.encode()):
            return answer(403, error='forbidden')
        try:
            kind = (json.loads(request.httprequest.data or b'{}') or {}).get('kind')
        except ValueError:
            kind = None
        cron = request.env.ref(CRONS[kind], raise_if_not_found=False) if kind in CRONS else None
        if not cron:
            return answer(400, error='kind: leave or edit')
        # run by the cron worker in a moment (not in this request): the flow gets its answer at once
        cron.sudo()._trigger()
        _logger.info("VMC Connect: %s татах cron-ыг эхлүүллээ", kind)
        return answer(202, ok=True, kind=kind)
