# -*- coding: utf-8 -*-
# Nightly: the SharePoint lists VMC Connect and the Power App read people from (AttendanceEmployee,
# AttendanceDepartment, AttendanceJob) follow Odoo.
#
# push_hr_info_to_microsoft adds a person once and never again: later changes in Odoo (email, manager,
# department, job) didn't reach SharePoint, people pushed twice stayed twice, and archived people stayed.
# This makes SharePoint match Odoo:
#  * every active employee has exactly one row, with Odoo's current values (added when missing);
#  * rows of archived / deleted employees, and second copies, are removed;
#  * departments and jobs are added or renamed.
# `role` (set by hand in SharePoint) and `late_hour` (pushed by _cron_push_late_time) are left alone.
#
# Try it first without changing anything:  env['hr.employee']._cron_sync_employees_to_sharepoint(dry_run=True)
import logging
import time
import requests
from collections import defaultdict
from odoo import api, models
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import get_list_id
from .hr_attendance_inherit import graph_list_items

_logger = logging.getLogger(__name__)
GRAPH = "https://graph.microsoft.com/v1.0/sites/{site}/lists/{list}/items"
HTTP_TIMEOUT = 30


def _graph(method, url, headers, body=None):
    """One Graph call, waiting once if Microsoft asks to slow down"""
    for attempt in range(2):
        response = requests.request(method, url, headers=headers, json=body, timeout=HTTP_TIMEOUT)
        if response.status_code == 429 and attempt == 0:
            time.sleep(int(response.headers.get('Retry-After', 5)))
            continue
        if response.status_code >= 400:
            raise RuntimeError(f"{method} {response.status_code}: {response.text[:200]}")
        return response.json() if response.content else {}


def _same(a, b):
    """SharePoint gives numbers back as 474.0 and missing text as None"""
    def norm(v):
        if v is None or v is False:
            return ''
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        return str(v).strip()
    return norm(a) == norm(b)


def _odoo_id(fields_, key):
    try:
        return int(float(fields_.get(key) or 0))
    except (TypeError, ValueError):
        return 0


class EmployeeSharePointSync(models.Model):
    _inherit = 'hr.employee'

    def _sharepoint_first_name(self):
        """The first name as push_to_microsoft writes it: the longest part of «Нэр.О»"""
        parts = [p for p in (self.name or '').split('.') if p]
        return max(parts, key=len) if parts else (self.name or '')

    def _sharepoint_employee_fields(self):
        self.ensure_one()
        return {
            'odoo_id': self.id,
            'Title': self.last_name or '',
            'firstName': self._sharepoint_first_name(),
            'register': self.ssnid or '',
            'companyName': self.company_id.id or 0,
            'emailAddress': (self.work_email or '').strip(),
            'department_id': self.department_id.id or 0,
            'job_id': self.job_id.id or 0,
            'parent_id': self.parent_id.id or 0,
            'birthday': str(self.birthday) if self.birthday else '',
            'mobile': self.mobile_phone or self.work_phone or '',
        }

    @api.model
    def _cron_sync_employees_to_sharepoint(self, dry_run=False):
        """Makes the SharePoint people lists match Odoo. dry_run: only log what would change."""
        session = self.env['hr.attendance']._graph_session()
        if not session:
            return {}
        headers, site_id, microsoft_value_obj, token = session
        report = defaultdict(int)

        def write(method, url, body=None):
            if dry_run:
                return {}
            return _graph(method, url, headers, body)

        def sync_simple(list_key_name, list_key_id, records, id_field, values):
            """Departments / jobs: one row per record id, Title (and more) as in Odoo"""
            list_id = get_list_id(microsoft_value_obj, site_id, token, list_key_name, list_key_id)
            base = GRAPH.format(site=site_id, list=list_id)
            rows = defaultdict(list)
            for item in graph_list_items(headers, site_id, list_id):
                rows[_odoo_id(item.get('fields', {}), id_field)].append(item)
            for record in records:
                want = {id_field: record.id, **values(record)}
                found = rows.get(record.id) or []
                if not found:
                    write('POST', base, {'fields': want})
                    report[f'{id_field}: added'] += 1
                    _logger.info("SharePoint sync: add %s %s %s", id_field, record.id, want.get('Title'))
                elif any(not _same(found[0].get('fields', {}).get(k), v) for k, v in want.items()):
                    write('PATCH', f"{base}/{found[0]['id']}/fields", want)
                    report[f'{id_field}: updated'] += 1

        try:
            sync_simple('department_list_name', 'department_list_id', self.env['hr.department'].sudo().search([]), 'department_id',
                        lambda d: {'Title': d.name or '', 'fullname': d.complete_name or d.name or ''})
            sync_simple('job_list_name', 'job_list_id', self.env['hr.job'].sudo().search([]), 'job_id', lambda j: {'Title': j.name or ''})
        except Exception:
            _logger.exception("SharePoint sync: departments / jobs")

        list_id = get_list_id(microsoft_value_obj, site_id, token, 'employee_list_name', 'employee_list_id')
        base = GRAPH.format(site=site_id, list=list_id)
        rows = defaultdict(list)
        for item in graph_list_items(headers, site_id, list_id):
            rows[_odoo_id(item.get('fields', {}), 'odoo_id')].append(item)

        for employee in self.sudo().search([]):  # active ones
            try:
                want = employee._sharepoint_employee_fields()
                found = rows.pop(employee.id, [])
                # the row Odoo knows about, else the first; any other copy goes
                keep = next((r for r in found if str(r['id']) == str(employee.powerpoint_id)), found[0] if found else None)
                for extra in found:
                    if extra is not keep:
                        write('DELETE', f"{base}/{extra['id']}")
                        report['employee: duplicate removed'] += 1
                        _logger.info("SharePoint sync: remove 2nd row %s of %s %s", extra['id'], employee.id, employee.name)
                if keep is None:
                    created = write('POST', base, {'fields': want})
                    report['employee: added'] += 1
                    _logger.info("SharePoint sync: add %s %s", employee.id, employee.name)
                    if created.get('id'):
                        employee.write({'is_sync_microsoft': True, 'powerpoint_id': int(created['id'])})
                    continue
                have = keep.get('fields', {})
                changed = {k: v for k, v in want.items() if not _same(have.get(k), v)}
                if changed:
                    write('PATCH', f"{base}/{keep['id']}/fields", changed)
                    report['employee: updated'] += 1
                    _logger.info("SharePoint sync: update %s %s: %s", employee.id, employee.name, ', '.join(changed))
                if not dry_run and (not employee.is_sync_microsoft or str(employee.powerpoint_id) != str(keep['id'])):
                    employee.write({'is_sync_microsoft': True, 'powerpoint_id': int(keep['id'])})
                if not dry_run:
                    self.env.cr.commit()
            except Exception:
                self.env.cr.rollback()
                _logger.exception("SharePoint sync: employee %s %s", employee.id, employee.name)

        # rows left over: archived or deleted in Odoo
        for odoo_id, leftover in rows.items():
            for item in leftover:
                try:
                    write('DELETE', f"{base}/{item['id']}")
                    report['employee: removed (archived/deleted in Odoo)'] += 1
                    f = item.get('fields', {})
                    _logger.info("SharePoint sync: remove row %s (odoo_id %s %s %s)", item['id'], odoo_id, f.get('Title'), f.get('firstName'))
                except Exception:
                    _logger.exception("SharePoint sync: remove row %s", item.get('id'))

        _logger.info("SharePoint sync%s: %s", ' (dry run, nothing changed)' if dry_run else '', dict(report))
        return dict(report)
