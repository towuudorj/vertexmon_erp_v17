# -*- coding: utf-8 -*-
# SharePoint → Odoo right away, without Power Automate Premium: Microsoft Graph tells Odoo when the leave or the
# attendance-edit list changes (a change notification to https://erp.vertexmon.com/vmcc/graph-notify), and Odoo
# then runs the cron that takes approved requests in. The crons still run on their own as well, in case a
# notification doesn't come.
#
# A Graph subscription lasts at most ~29 days: «Ирц нөхөн засах хүсэлт» (every few minutes) makes them and
# renews them a few days before they end. They are kept in the system parameter vmcc.graph_subscriptions; the
# notifications are checked against vmcc.sync_key (made on first use). The address is vmcc.public_url.
import hmac
import json
import logging
import secrets
from datetime import timedelta
import requests
from odoo import fields, models
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import get_list_id

_logger = logging.getLogger(__name__)

SUBSCRIPTIONS = "https://graph.microsoft.com/v1.0/subscriptions"
PARAM = 'vmcc.graph_subscriptions'
LIFETIME = timedelta(days=25)
RENEW_BEFORE = timedelta(days=5)
RETRY_AFTER = timedelta(hours=1)
LISTS = {
    'leave': ('leave_list_name', 'leave_list_id'),
    'edit': ('att_edit_req_list_name', 'att_edit_req_list_id'),
}
CRONS = {
    'leave': 'l10n_mn_hr_attendance.ir_cron_get_approved_leaves',  # Microsoft: Батлагдсан чөлөө татах
    'edit': 'l10n_mn_hr_attendance.ir_cron_get_att_edit_req',      # Microsoft: Ирц нөхөн засах хүсэлт
}


class AttendanceEditRequestGraph(models.Model):
    _inherit = 'attendance.edit.request'

    def _vmcc_secret(self):
        params = self.env['ir.config_parameter'].sudo()
        key = params.get_param('vmcc.sync_key')
        if not key:
            key = secrets.token_hex(24)
            params.set_param('vmcc.sync_key', key)
        return key

    def _vmcc_ensure_subscriptions(self, session):
        """Makes / renews the Graph subscriptions on the two lists when they are missing or about to end."""
        headers, site_id, microsoft_value_obj, token = session
        params = self.env['ir.config_parameter'].sudo()
        url = (params.get_param('vmcc.public_url') or 'https://erp.vertexmon.com').rstrip('/') + '/vmcc/graph-notify'
        subs = json.loads(params.get_param(PARAM) or '{}')
        now = fields.Datetime.now()
        changed = False
        for kind, (name_key, id_key) in LISTS.items():
            sub = subs.get(kind) or {}
            if sub.get('failed') and now - fields.Datetime.to_datetime(sub['failed']) < RETRY_AFTER:
                continue
            if sub.get('id') and sub.get('expires') and fields.Datetime.to_datetime(sub['expires']) - now > RENEW_BEFORE:
                continue
            ends = now + LIFETIME
            body = {'expirationDateTime': ends.strftime('%Y-%m-%dT%H:%M:%SZ')}
            response = None
            try:
                if sub.get('id'):
                    response = requests.patch(f"{SUBSCRIPTIONS}/{sub['id']}", headers=headers, json=body, timeout=30)
                if response is None or response.status_code >= 400:
                    # none yet, or Microsoft dropped it: a new one (Graph checks the address before answering)
                    list_id = get_list_id(microsoft_value_obj, site_id, token, name_key, id_key)
                    response = requests.post(SUBSCRIPTIONS, headers=headers, timeout=60, json={
                        **body,
                        'changeType': 'updated',
                        'notificationUrl': url,
                        'resource': f"sites/{site_id}/lists/{list_id}",
                        'clientState': self._vmcc_secret(),
                    })
                if response.status_code >= 400:
                    raise RuntimeError(f"{response.status_code}: {response.text[:300]}")
                subs[kind] = {'id': response.json().get('id') or sub.get('id'), 'expires': fields.Datetime.to_string(ends)}
                _logger.info("Graph subscription %s: %s, %s хүртэл", kind, subs[kind]['id'], subs[kind]['expires'])
            except Exception as error:
                subs[kind] = {**sub, 'failed': fields.Datetime.to_string(now)}
                _logger.warning("Graph subscription %s үүсгэж / сунгаж чадсангүй (цаг тутам дахин оролдоно): %s", kind, error)
            changed = True
        if changed:
            params.set_param(PARAM, json.dumps(subs))

    def _vmcc_notified(self, payload):
        """A Graph change notification: runs the cron of the list that changed. Returns the kinds."""
        params = self.env['ir.config_parameter'].sudo()
        secret = (params.get_param('vmcc.sync_key') or '').encode()
        by_id = {v.get('id'): k for k, v in json.loads(params.get_param(PARAM) or '{}').items() if v.get('id')}
        kinds = set()
        for note in (payload or {}).get('value') or []:
            if secret and hmac.compare_digest(str(note.get('clientState') or '').encode(), secret):
                kinds.add(by_id.get(note.get('subscriptionId')))
        kinds.discard(None)
        for kind in kinds:
            cron = self.env.ref(CRONS[kind], raise_if_not_found=False)
            if cron:
                cron.sudo()._trigger()
        return kinds
