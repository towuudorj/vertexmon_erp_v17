# -*- coding: utf-8 -*-
# VMC Connect: deliveries not delivered by their time. Every two hours (working hours only) the delivery staff
# get one Teams card in their own chat listing them, until each is delivered, postponed or cancelled.
#
# Read from the OdooERP-PowerApps site: the Delivery list (status «Шинэ», time past), VMCC_Log (a delivery postponed
# with no new time yet is left out) and VMCC_Config (the delivery staff and the chat workflow VMC Connect uses).
# Try it without sending:  env['attendance.edit.request']._cron_delivery_reminders(dry_run=True)
import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import requests
from odoo import api, models
from .hr_attendance_inherit import graph_list_items

_logger = logging.getLogger(__name__)
UB = timezone(timedelta(hours=8))
GRAPH = "https://graph.microsoft.com/v1.0/sites/{site}/lists"
TEAMS_APP_ID = '8984c2ca-1f3f-47df-bf46-e6e3edc42b4d'
DELIVERY_NEW = 'Шинэ'
HOURS = (8, 19)  # Ulaanbaatar working hours, Monday to Saturday


def _when(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None


def _app_link(target):
    return f"https://teams.microsoft.com/l/entity/{TEAMS_APP_ID}/vmc-connect?context=" + quote(json.dumps({'subEntityId': target}))


class DeliveryReminder(models.Model):
    _inherit = 'attendance.edit.request'

    def _vmcc_list_id(self, headers, site_id, title):
        """A list's id by its title (VMC Connect's own lists are hidden, so not always found by title directly)"""
        base = GRAPH.format(site=site_id)
        response = requests.get(f"{base}/{quote(title)}", headers=headers, params={'$select': 'id'}, timeout=30)
        if response.status_code == 200:
            return response.json().get('id')
        response = requests.get(base, headers=headers, params={'$select': 'id,displayName', '$top': 500}, timeout=30)
        response.raise_for_status()
        return next((l['id'] for l in response.json().get('value', []) if l.get('displayName') == title), None)

    @api.model
    def _cron_delivery_reminders(self, dry_run=False, force=False):
        """Tells the delivery staff about late deliveries. force: also outside working hours (for trying it)."""
        now = datetime.now(timezone.utc)
        local = now.astimezone(UB)
        if not force and (local.weekday() == 6 or not HOURS[0] <= local.hour < HOURS[1]):
            return []
        session = self.env['hr.attendance']._graph_session()
        if not session:
            return []
        headers, site_id = session[0], session[1]

        config_id = self._vmcc_list_id(headers, site_id, 'VMCC_Config')
        settings = {}
        if config_id:
            for item in graph_list_items(headers, site_id, config_id, "fields/Title eq 'settings'"):
                settings = json.loads(item.get('fields', {}).get('Data') or '{}')
        staff = [e for e in settings.get('deliveryStaff') or [] if e]
        webhook = settings.get('chatWebhook') or ''

        delivery_id = self._vmcc_list_id(headers, site_id, 'Delivery')
        if not delivery_id:
            _logger.warning("Хүргэлтийн сануулга: Delivery жагсаалт олдсонгүй")
            return []
        late = []
        for item in graph_list_items(headers, site_id, delivery_id, f"fields/status eq '{DELIVERY_NEW}'"):
            f = item.get('fields', {})
            when = _when(f.get('delivery_date'))
            if f.get('status') == DELIVERY_NEW and when and when < now:
                late.append((int(item['id']), when, f))
        if late:
            # postponed with no new time yet: the old time stays in the list, the app keeps that in VMCC_Log
            log_id = self._vmcc_list_id(headers, site_id, 'VMCC_Log')
            open_ended = set()
            if log_id:
                for item in graph_list_items(headers, site_id, log_id):
                    f = item.get('fields', {})
                    if not str(f.get('Title') or '').startswith('Delivery#'):
                        continue
                    try:
                        if json.loads(f.get('Data') or '{}').get('postponedOpen'):
                            open_ended.add(int(str(f.get('Title')).split('#')[1]))
                    except (ValueError, IndexError):
                        continue
            late = [x for x in late if x[0] not in open_ended]
        late.sort(key=lambda x: x[1])

        names = {}
        for e in self.env['hr.employee'].sudo().with_context(active_test=False).search([('id', 'in', [int(x[2].get('requester_odoo_id') or 0) for x in late])]):
            names[e.id] = f"{e.last_name or ''} {e.name or ''}".strip()
        lines = [{
            'title': f"{x[1].astimezone(UB):%m/%d %H:%M}",
            'value': f"{x[2].get('Title') or ''} → {x[2].get('delivery_to') or ''} ({names.get(int(x[2].get('requester_odoo_id') or 0), '')})",
        } for x in late]
        _logger.info("Хүргэлтийн сануулга%s: %s хоцорсон хүргэлт, %s хүнд", ' (dry run)' if dry_run else '', len(late), len(staff))
        if not late or dry_run:
            return lines
        if not staff or not webhook:
            _logger.warning("Хүргэлтийн сануулга: VMC Connect-ийн тохиргоонд хүргэлтийн ажилтан эсвэл хувийн чатын workflow алга")
            return lines
        card = {
            'type': 'AdaptiveCard',
            '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json',
            'version': '1.4',
            'body': [
                {'type': 'TextBlock', 'text': '⏰ Хүргэгдээгүй хүргэлт', 'size': 'Small', 'weight': 'Bolder', 'color': 'Attention'},
                {'type': 'TextBlock', 'text': f"{len(late)} хүргэлтийн цаг өнгөрсөн байна", 'size': 'Large', 'weight': 'Bolder', 'wrap': True},
                {'type': 'FactSet', 'facts': lines[:15]},
                {'type': 'TextBlock', 'text': 'Хүргэсэн, хойшлуулсан эсвэл цуцалсан гэж VMC Connect-д тэмдэглэнэ үү.', 'wrap': True, 'isSubtle': True},
            ],
            'actions': [{'type': 'Action.OpenUrl', 'title': 'VMC Connect-д нээх', 'url': _app_link('delivery')}],
        }
        try:
            response = requests.post(webhook, json={'recipients': staff, 'card': card}, timeout=30)
            if response.status_code >= 400:
                _logger.warning("Хүргэлтийн сануулга илгээгдсэнгүй: %s %s", response.status_code, response.text[:200])
        except requests.RequestException as error:
            _logger.warning("Хүргэлтийн сануулга илгээгдсэнгүй: %s", error)
        return lines
