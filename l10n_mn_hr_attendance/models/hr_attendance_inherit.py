# -*- coding: utf-8 -*-
# Attendance from HikCentral and Timely into hr.attendance, and from there to the SharePoint "Attendance" list
# (VMC Connect and the Power App read it there).
#
# What changed from the earlier version:
#  * every source goes through one merge (_merge_punch): earliest check-in, latest check-out of the day, written
#    with the ORM — so worked_hours is recomputed and write_date moves, and the change reaches SharePoint
#    (the raw SQL UPDATEs did neither);
#  * a day corrected through an approved edit request (manual_lock) is never overwritten by a sync;
#  * HikCentral: every code of an employee with several codes is read (the second one was skipped), two
#    attendances on one day no longer stop the run, the time range is +08:00, requests time out;
#  * Timely: empty credentials are caught, the leave's start minute is the start's, unknown request codes are
#    skipped and logged instead of failing;
#  * SharePoint: a push that timed out is matched by odoo_id next time instead of being added twice.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import time
import hmac
import hashlib
import base64
import requests
import urllib3
from dateutil import parser
import pytz
from datetime import datetime, timedelta, time as dt_time
from dateutil.relativedelta import relativedelta
from odoo.addons.l10n_mn_hr_attendance.models.hr_leave import hour_min_to_selection
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import *
import logging
from zoneinfo import ZoneInfo

API_PATH = "/artemis/api/attendance/v1/report"
UB = ZoneInfo('Asia/Ulaanbaatar')
HTTP_TIMEOUT = 30
HIK_PAGE_SIZE = 100
# HikCentral answers on a self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# SharePoint item id of a push whose answer never came (the item may exist): look it up by odoo_id next time
SP_PENDING = '?'
_logger = logging.getLogger(__name__)


def sign(app_secret, string_to_sign):
    h = hmac.new(app_secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256)
    return base64.b64encode(h.digest()).decode('utf-8')


def get_params(self, method=None, accept=None, content_type=None, APP_KEY=None, APP_SECRET=None, BASE_URL=None):
    config = self.env['ir.config_parameter'].sudo()
    return (
        method or 'POST',
        accept or "*/*",
        content_type or "application/json",
        APP_KEY or config.get_param('Attendance_APP_KEY'),
        APP_SECRET or config.get_param('Attendance_APP_SECRET'),
        BASE_URL or config.get_param('Attendance_BASE_URL'),
    )


def build_headers(method, accept, content_type, APP_KEY, APP_SECRET, PATH):
    timestamp = str(int(time.time() * 1000))
    string_to_sign = (
        f"{method}\n"
        f"{accept}\n"
        f"{content_type}\n"
        f"x-ca-key:{APP_KEY}\n"
        f"x-ca-timestamp:{timestamp}\n"
        f"{PATH}"
    )
    return {
        "Accept": accept,
        "Content-Type": content_type,
        "X-Ca-Key": APP_KEY,
        "X-Ca-Timestamp": timestamp,
        "X-Ca-Signature": sign(APP_SECRET, string_to_sign),
        "X-Ca-Signature-Headers": "x-ca-key,x-ca-timestamp",
    }


def graph_list_items(headers, site_id, list_id, filter_=None, timeout=HTTP_TIMEOUT):
    """Every item of a SharePoint list through Microsoft Graph, all pages (Graph answers 200 at a time)"""
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items"
    params = {'$expand': 'fields', '$top': 200}
    if filter_:
        params['$filter'] = filter_
    # the lists' columns aren't indexed; Graph filters on them only with this header
    headers = {**headers, 'Prefer': 'HonorNonIndexedQueriesWarningMayFailRandomly'}
    items = []
    while url:
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        items += data.get('value') or []
        url, params = data.get('@odata.nextLink'), None
    return items


def ub_today():
    return datetime.now(UB).date()


def day_bounds_utc(day):
    """An Ulaanbaatar day as naive UTC datetimes (how Odoo stores them)"""
    start = datetime.combine(day, dt_time.min) - timedelta(hours=8)
    return start, start + timedelta(days=1) - timedelta(seconds=1)


def timely_time(value):
    """Timely sends Ulaanbaatar time marked as Z"""
    if not value:
        return False
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ") - timedelta(hours=8)


def hik_time(value):
    if not value:
        return False
    return parser.isoparse(value).astimezone(pytz.UTC).replace(tzinfo=None)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    loss_time = fields.Float(string='Loss time', compute='_compute_loss_time')
    share_point_id = fields.Char(string='Sharepoint id')
    manual_lock = fields.Boolean(
        string='Гараар засагдсан',
        help="Батлагдсан засах хүсэлтээр өөрчлөгдсөн. HikCentral/Timely-гийн татан авалт энэ ирцийг дахин өөрчлөхгүй.",
        copy=False,
    )
    check_in_location = fields.Char('Орсон байршил')
    check_out_location = fields.Char('Гарсан байршил')

    def create_check_in(self, employee_id, lat, long):
        """Create a check-in record with the given latitude and longitude."""
        self.create({
            'check_in': fields.Datetime.now(),
            'employee_id': employee_id,
            'in_mode': 'manual',
        })

    def create_check_out(self, lat, long):
        """Create a check-out record with the given latitude and longitude."""
        self.write({'check_out': fields.Datetime.now()})

    def _compute_loss_time(self):
        for rec in self:
            rec.loss_time = 0.0

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        return

    def _compute_color(self):
        for attendance in self:
            if attendance.check_out:
                attendance.color = 1 if attendance.worked_hours > 16 else 0
            elif attendance.check_in:
                attendance.color = 1 if attendance.check_in < (datetime.today() - timedelta(days=1)) else 10
            else:
                attendance.color = 1

    # ---- One merge for every source ----

    def _merge_punch(self, employee, day, check_in, check_out, check_in_location=False, check_out_location=False):
        """A day's punches from any source: keeps the earliest check-in and the latest check-out.
        check_in / check_out are naive UTC datetimes or False. Days locked by an approved correction stay as they are."""
        if not check_in and not check_out:
            return
        check_in = check_in or check_out
        check_out = check_out or check_in
        start, end = day_bounds_utc(day)
        attendances = self.sudo().search(
            [('employee_id', '=', employee.id), ('check_in', '>=', start), ('check_in', '<=', end)], order='check_in')
        if not attendances:
            self.sudo().create({'employee_id': employee.id, 'check_in': check_in, 'check_out': check_out,
                                'check_in_location': check_in_location, 'check_out_location': check_out_location})
            return
        # the day's first attendance carries the day (more than one only when entered by hand)
        attendance = attendances[0]
        if attendance.manual_lock:
            return
        vals = {}
        if check_in < attendance.check_in:
            vals['check_in'] = check_in
        if not attendance.check_out or check_out > attendance.check_out:
            vals['check_out'] = check_out
        if check_in_location and not attendance.check_in_location:
            vals['check_in_location'] = check_out_location
        if check_out_location and not attendance.check_out_location:
            vals['check_out_location'] = check_out_location
        if vals:
            attendance.write(vals)

    def get_attendance_data(self, id=False, last_days=False):
        """Pulls attendance from every source for the last `last_days` days (default: a month).
        A source that fails is logged and the others still run."""
        today = ub_today()
        begin_date = today - timedelta(days=last_days) if last_days else today - relativedelta(months=1)
        for name, pull in (
            ('Timely', lambda: self.get_timely_data(begin_date, today)),
            ('Tapa Timely', lambda: self.get_tapa_timely_data(begin_date, today)),
            ('HikCentral', lambda: self._get_hikcentral_data(begin_date, today, id)),
        ):
            try:
                pull()
                self.env.cr.commit()
            except Exception:
                self.env.cr.rollback()
                _logger.exception("Ирц татахад алдаа гарлаа: %s", name)

    # ---- HikCentral ----

    def _get_hikcentral_data(self, begin_date, end_date, employee_id=False):
        method, accept, content_type, APP_KEY, APP_SECRET, BASE_URL = get_params(self)
        if not (APP_KEY and APP_SECRET and BASE_URL):
            _logger.warning("HikCentral тохиргоо (Attendance_APP_KEY/SECRET/BASE_URL) дутуу байна")
            return
        url = BASE_URL + API_PATH
        domain = [('id', '=', employee_id)] if employee_id else [('attendance_id', '!=', False), ('attendance_id', '!=', '')]
        for employee in self.env['hr.employee'].sudo().search(domain):
            codes = [c.strip() for c in (employee.attendance_id or '').split(',') if c.strip()]
            for code in codes:
                try:
                    for line in self._hik_records(url, code, begin_date, end_date, method, accept, content_type, APP_KEY, APP_SECRET):
                        if line['personInfo']['personCode'] != code:
                            continue
                        base_info = line.get('attendanceBaseInfo') or {}
                        self._merge_punch(
                            employee,
                            fields.Date.from_string(line['date']),
                            hik_time(base_info.get('beginTime')),
                            hik_time(base_info.get('endTime')),
                        )
                except Exception:
                    _logger.exception("HikCentral: %s (%s) ажилтны ирц татахад алдаа", employee.name, code)

    def _hik_records(self, url, code, begin_date, end_date, method, accept, content_type, APP_KEY, APP_SECRET):
        """Every report row of one person code, page by page"""
        page = 1
        while page <= 50:
            body = {
                "attendanceReportRequest": {
                    "pageNo": page,
                    "pageSize": HIK_PAGE_SIZE,
                    "queryInfo": {
                        "personCode": code,
                        # HikCentral refuses "+08:00" ("beginTime parameter error"); this is the form it takes
                        "beginTime": f"{begin_date}T00:00:00 05:00",
                        "endTime": f"{end_date}T23:59:59 08:00",
                        "sortInfo": {"sortField": 1, "sortType": 1},
                    },
                }
            }
            headers = build_headers(method, accept, content_type, APP_KEY, APP_SECRET, API_PATH)
            response = requests.post(url, json=body, headers=headers, verify=False, timeout=HTTP_TIMEOUT)
            result = response.json()
            if str(result.get('code')) != '0':
                # a refused request is an error, not an empty answer
                _logger.error("HikCentral %s кодын ирцийг буцаасангүй: %s %s", code, result.get('code'), result.get('msg'))
                return
            records = (result.get('data') or {}).get('record') or []
            yield from records
            if len(records) < HIK_PAGE_SIZE:
                return
            page += 1

    # ---- Timely ----

    def _api_leave_types(self):
        """Leave types for requests coming from Timely (and VMC Connect), by request code"""
        types = self.env['hr.leave.type'].sudo()

        def find(sub_type):
            return types.search([('use_in_api', '=', True), ('sub_type', '=', sub_type)], limit=1)

        return {
            'app_leave_normal': find('payroll'),
            # Timely's paid leave
            'salary_leave': find('payroll'),
            'payroll': find('payroll'),
            'unpayroll': find('unpayroll'),
            'overtime_regular_request': find('over_time'),
            'sick': find('sick'),
        }

    def _timely_requests(self, employee, requests_list, leave_types):
        """Timely's leave/overtime requests of a day → hr.leave (each once)"""
        leave_obj = self.env['hr.leave'].sudo()
        for request in requests_list or []:
            if leave_obj.search([('timely_id', '=', int(request['id']))], limit=1):
                continue
            leave_type = leave_types.get(request.get('code'))
            if not leave_type:
                _logger.warning("Timely: танихгүй хүсэлтийн код %s (id %s) — алгаслаа", request.get('code'), request.get('id'))
                continue
            req_in = fields.Datetime.to_datetime(datetime.strptime(request['reqIn'], "%Y-%m-%dT%H:%M:%S.%fZ"))
            req_out = fields.Datetime.to_datetime(datetime.strptime(request['reqOut'], "%Y-%m-%dT%H:%M:%S.%fZ"))
            vals = {
                'request_date_from': req_in.date(),
                'request_date_to': req_out.date(),
                'request_hour_from': hour_min_to_selection[f"{req_in.hour}:{'30' if req_in.minute >= 30 else '0'}"],
                'request_hour_to': hour_min_to_selection[f"{req_out.hour}:{'30' if req_out.minute >= 30 else '0'}"],
                'request_unit_hours': True,
                'employee_id': employee.id,
                'timely_id': request['id'],
                'holiday_status_id': leave_type.id,
            }
            if vals['request_hour_to'] == '0':
                vals.update({'request_hour_from': str(float(vals['request_hour_from']) - 0.5), 'request_hour_to': '23.5'})
            leave_obj.create(vals)

    def get_timely_data(self, start_date, end_date):
        config = self.env['ir.config_parameter'].sudo()
        name = (config.get_param('timely_user_name', default='') or '').strip()
        password = (config.get_param('timely_password', default='') or '').strip()
        company_vat = config.get_param('timely_company_vat', default='')
        if not (name and password):
            return None
        response = requests.post('https://api.timely.mn/v3/login', json={"name": name, "password": password}, timeout=HTTP_TIMEOUT)
        token = response.json().get('data')
        if not token:
            _logger.warning("Timely: нэвтэрч чадсангүй")
            return None
        employees = self.update_employee_timely_id(token, self.env['hr.employee'].search([('timely_id', '!=', 0)]), company_vat)
        if not employees:
            return None
        leave_types = self._api_leave_types()
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        page = 1
        while page <= 200:
            data = {'company_register': company_vat, 'dateFrom': str(start_date), 'dateTo': str(end_date), 'page': page, 'limit': 100}
            page += 1
            response_json = requests.post('https://api.timely.mn/v3/expanded-attd', headers=headers, json=data, timeout=HTTP_TIMEOUT).json()
            if not response_json.get('data') or not response_json.get('success'):
                break
            for line in response_json['data']:
                employee = employees.filtered(lambda emp: emp.timely_id == line['workerId'])[:1]
                if not employee:
                    continue
                for key, value in list(line['attd'].items()):
                    try:
                        check_in_location = False
                        check_out_location = False
                        if value.get('clockInSource'):
                            check_in_location = value.get('clockInSource').get('name', False)
                        if value.get('clockOutSource'):
                            check_out_location = value.get('clockOutSource').get('name', False)
                        self._merge_punch(employee, fields.Date.from_string(key), timely_time(value.get('clockIn')), timely_time(value.get('clockOut')),
                                          check_in_location=check_in_location, check_out_location=check_out_location)
                        self._timely_requests(employee, value.get('requests'), leave_types)
                    except Exception:
                        _logger.exception("Timely: %s %s өдрийн ирц", employee.name, key)
        return None

    def get_tapa_timely_data(self, start_date, end_date):
        config = self.env['ir.config_parameter'].sudo()
        key = (config.get_param('tapa_timely_key', default='') or '').strip()
        company_vat = config.get_param('tapa_timely_company_vat', default='')
        if not key:
            return None
        response_json = requests.post('https://api.timely.mn/openapi/auth/token', json={"apiKey": key}, timeout=HTTP_TIMEOUT).json()
        token = (response_json.get('result') or {}).get('accessToken')
        if not token:
            _logger.warning("Tapa Timely: нэвтэрч чадсангүй")
            return None
        employees = self.update_tapa_employee_timely_id(
            token, self.env['hr.employee'].search([('timely_id', '!=', 0), ('company_id', '=', 5)]), company_vat)
        if not employees:
            return None
        leave_types = self._api_leave_types()
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        for employee in employees:
            params = {'dateFrom': str(start_date), 'dateTo': str(end_date), 'workerId': employee.timely_id}
            response_json = requests.get('https://api.timely.mn/openapi/employees/attendance', headers=headers, params=params, timeout=HTTP_TIMEOUT).json()
            if not response_json.get('success') or 'result' not in response_json:
                continue
            for line in response_json['result'].get('attendance') or []:
                try:
                    self._merge_punch(employee, fields.Date.from_string(line['date']), timely_time(line.get('clockIn')), timely_time(line.get('clockOut')))
                    self._timely_requests(employee, line.get('requests'), leave_types)
                except Exception:
                    _logger.exception("Tapa Timely: %s %s өдрийн ирц", employee.name, line.get('date'))
        return None

    # ---- To SharePoint ----

    def _graph_session(self):
        """(headers, site_id) for Microsoft Graph, or None when it isn't set up"""
        microsoft_value_obj = self.env['microsoft.api.value'].sudo().search([], limit=1)
        if not microsoft_value_obj:
            _logger.warning("Microsoft API Value тохиргоо олдсонгүй")
            return None
        token = get_token(microsoft_value_obj)
        if not (token and token.get('token_type') and token.get('access_token')):
            raise ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s' % str(token))
        token = token['token_type'] + ' ' + token['access_token']
        site_id = get_site_id(microsoft_value_obj, token)
        return {"Authorization": token, "Content-Type": "application/json"}, site_id, microsoft_value_obj, token

    def _cron_update_attendance(self, last_days=10):
        session = self._graph_session()
        if not session:
            return
        headers, site_id, microsoft_value_obj, token = session
        list_id = get_list_id(microsoft_value_obj, site_id, token, 'attendance_list_name', 'attendance_list_id')
        date_range = fields.Datetime.now() - relativedelta(days=last_days if isinstance(last_days, int) and last_days > 0 else 10)

        # 1. not in SharePoint yet (or the answer to the last push never came)
        new = self.sudo().search(['|', '|', ('share_point_id', '=', ''), ('share_point_id', '=', False), ('share_point_id', '=', SP_PENDING),
                                  ('check_in', '>=', date_range)])
        new.push_to_sharepoint(headers, site_id, list_id)
        # 2. changed lately (synced punches, approved corrections)
        changed = self.sudo().search([('write_date', '>=', date_range), ('id', 'not in', new.ids)])
        changed.push_to_sharepoint(headers, site_id, list_id)

    def _sp_find_by_odoo_id(self, headers, site_id, list_id, timeout):
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items"
        response = requests.get(url, headers={**headers, 'Prefer': 'HonorNonIndexedQueriesWarningMayFailRandomly'},
                                params={'$filter': f'fields/odoo_id eq {self.id}', '$select': 'id', '$top': 1}, timeout=timeout)
        values = (response.json().get('value') or []) if response.status_code == 200 else []
        return values[0]['id'] if values else False

    def push_to_sharepoint(self, headers, site_id, list_id, timeout=10):
        company_id = self.env.company.id or self.env['res.company'].sudo().search([], limit=1, order='id asc').id
        hour_record_model = self.env['hr.hour.record']
        for att in self:
            try:
                employee = att.employee_id
                if not employee or not att.check_in:
                    continue
                if att.share_point_id == SP_PENDING:
                    att.share_point_id = att._sp_find_by_odoo_id(headers, site_id, list_id, timeout) or False
                is_new = not att.share_point_id
                base = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items"
                url = base if is_new else f"{base}/{att.share_point_id}/fields"

                check_in = att.check_in.strftime('%Y-%m-%dT%H:%M:%SZ')
                check_out = att.check_out.strftime('%Y-%m-%dT%H:%M:%SZ') if att.check_out else check_in
                hours = int(att.worked_hours)
                minutes = int(round((att.worked_hours - hours) * 60))
                local_date = (att.check_in + timedelta(hours=8)).date()
                los_time = 0.0
                try:
                    hr_hour_record = hour_record_model.new({
                        'start_date': datetime.combine(local_date, dt_time(0, 1)) - timedelta(hours=8),
                        'end_date': datetime.combine(local_date, dt_time(23, 59)) - timedelta(hours=8),
                        'company_id': company_id,
                    })
                    line_vals = hr_hour_record.hour_record(employee_id=att.employee_id)
                    los_time = line_vals.get('miss_time', 0.0) if line_vals else 0.0
                except Exception as ex_hr:
                    _logger.warning("Ажилтан %s-ийн хоцролтын цаг бодоход алдаа гарлаа: %s", employee.name, ex_hr)

                body = {
                    "Title": employee.last_name or '',
                    "first_name": employee.name or '',
                    "odoo_id": att.id,
                    "check_in": check_in,
                    "check_out": check_out,
                    "worked_hours": f"{hours:02d}:{minutes:02d}",
                    "loss_time": str(round(los_time, 2)),
                    "emp_id": employee.id,
                    "check_in_location": att.check_in_location,
                    "check_out_location": att.check_out_location,
                }
                send = (lambda: requests.post(url, headers=headers, json={"fields": body}, timeout=timeout)) if is_new else \
                    (lambda: requests.patch(url, headers=headers, json=body, timeout=timeout))
                try:
                    response = send()
                except requests.exceptions.Timeout:
                    if is_new:
                        # it may have been added: find it by odoo_id next time instead of adding it again
                        att.share_point_id = SP_PENDING
                        self.env.cr.commit()
                    _logger.error("SharePoint руу ирц ID %s илгээхэд timeout гарлаа (%sс)", att.id, timeout)
                    continue
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    _logger.warning("Microsoft Graph 429: ирц ID %s, %s секунд хүлээнэ", att.id, retry_after)
                    time.sleep(retry_after)
                    response = send()
                if response.status_code in (200, 201):
                    if is_new and response.json().get('id'):
                        att.share_point_id = response.json()['id']
                    self.env.cr.commit()
                else:
                    _logger.warning("SharePoint руу ирц ID %s илгээхэд алдаа: %s %s", att.id, response.status_code, response.text[:200])
            except Exception as e:
                self.env.cr.rollback()
                _logger.error("push_to_sharepoint: ирц ID %s: %s", att.id, e)
                continue

    # ---- Timely ids ----

    def _match_timely_workers(self, workers, employees, id_key):
        known = employees.mapped('timely_id')
        for line in workers or []:
            try:
                if line[id_key] in known:
                    continue
                domain = []
                if line.get('register'):
                    domain += [('ssnid', '=', line['register'])]
                if line.get('phone'):
                    domain = (['|'] + domain if domain else domain) + [('work_phone', '=', line['phone'])]
                emp = self.env['hr.employee'].search(domain, limit=1) if domain else False
                if emp:
                    emp.sudo().write({'timely_id': line[id_key]})
                    employees |= emp
            except Exception:
                continue
        return employees

    def update_employee_timely_id(self, token, employees, comp_reg):
        response_json = requests.get('https://api.timely.mn/v3/employees', headers={'Authorization': f'Bearer {token}'},
                                     params={'company_register': comp_reg}, timeout=HTTP_TIMEOUT).json()
        if response_json.get('success'):
            employees = self._match_timely_workers(response_json.get('data'), employees, 'id')
        return employees

    def update_tapa_employee_timely_id(self, token, employees, comp_reg):
        response_json = requests.get('https://api.timely.mn/openapi/employees', headers={'Authorization': f'Bearer {token}'},
                                     params={'company_register': comp_reg}, timeout=HTTP_TIMEOUT).json()
        if response_json.get('success'):
            employees = self._match_timely_workers(response_json.get('result'), employees, 'workerId')
        return employees
