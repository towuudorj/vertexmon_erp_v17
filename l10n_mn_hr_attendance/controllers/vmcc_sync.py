# -*- coding: utf-8 -*-
# VMC Connect: Microsoft Graph calls this when the SharePoint leave / attendance-edit list changes, so Odoo takes
# approved requests in at once (see models/vmcc_graph_subscription.py).
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class VmccSync(http.Controller):

    @http.route('/vmcc/graph-notify', type='http', auth='public', methods=['POST'], csrf=False)
    def vmcc_graph_notify(self, validationToken=None, **kwargs):
        if validationToken:
            # Graph checking the address when the subscription is made: give the token back as it came
            return request.make_response(validationToken, headers=[('Content-Type', 'text/plain')])
        try:
            payload = json.loads(request.httprequest.data or b'{}')
        except ValueError:
            payload = {}
        kinds = request.env['attendance.edit.request'].sudo()._vmcc_notified(payload)
        if kinds:
            _logger.info("VMC Connect: SharePoint өөрчлөгдлөө (%s), татах cron-ыг эхлүүллээ", ', '.join(sorted(kinds)))
        return request.make_response('', status=202)
