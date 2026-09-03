# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import time
import hmac
import hashlib
import base64
import requests
import urllib3
from dateutil import parser
import pytz
from datetime import date, datetime, timedelta, time as dt_time
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo.addons.l10n_mn_hr_attendance.models.hr_leave import hour_min_to_selection
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import *
import logging
from zoneinfo import ZoneInfo

API_PATH = "/artemis/api/attendance/v1/report"
_logger = logging.getLogger(__name__)


def sign(app_secret, string_to_sign):
    h = hmac.new(app_secret.encode('utf-8'),
                 string_to_sign.encode('utf-8'),
                 digestmod=hashlib.sha256)
    signature = base64.b64encode(h.digest()).decode('utf-8')
    return signature

def get_params(self, method=None, accept=None, content_type=None, APP_KEY=None, APP_SECRET=None, BASE_URL=None):
    if not method:
        method = 'POST'
    if not accept:
        accept = "*/*"
    if not content_type:
        content_type = "application/json"
    if not APP_KEY:
        APP_KEY = self.env['ir.config_parameter'].sudo().get_param('Attendance_APP_KEY')
    if not APP_SECRET:
        APP_SECRET = self.env['ir.config_parameter'].sudo().get_param('Attendance_APP_SECRET')
    if not BASE_URL:
        BASE_URL = self.env['ir.config_parameter'].sudo().get_param('Attendance_BASE_URL')
    return method, accept, content_type, APP_KEY, APP_SECRET, BASE_URL


def build_headers(method, accept, content_type, APP_KEY, APP_SECRET, PATH):
    timestamp = str(int(time.time() * 1000))

    # -------- Signature String --------
    string_to_sign = (
        f"{method}\n"
        f"{accept}\n"
        f"{content_type}\n"
        f"x-ca-key:{APP_KEY}\n"
        f"x-ca-timestamp:{timestamp}\n"
        f"{PATH}"
    )

    signature = sign(APP_SECRET, string_to_sign)

    headers = {
        "Accept": accept,
        "Content-Type": content_type,
        "X-Ca-Key": APP_KEY,
        "X-Ca-Timestamp": timestamp,
        "X-Ca-Signature": signature,
        "X-Ca-Signature-Headers": "x-ca-key,x-ca-timestamp"
    }

    return headers

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    loss_time = fields.Float(string='Loss time', compute='_compute_loss_time')
    share_point_id = fields.Char(string='Sharepoint id')

    def create_check_in(self, employee_id, lat, long):
        """
        Create a check-in record with the given latitude and longitude.
        """
        self.create({
            'check_in': fields.Datetime.now(),
            'employee_id': employee_id,
            'in_mode':'manual',
        })
    def create_check_out(self, lat, long):
        """
        Create a check-out record with the given latitude and longitude.
        """
        self.write({
            'check_out': fields.Datetime.now(),
        })


    def _compute_loss_time(self):
        for rec in self:
            total_time = 0.0
            rec.loss_time = total_time

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        return

    def _compute_color(self):
        for attendance in self:
            if attendance.check_out:
                attendance.color = 1 if attendance.worked_hours > 16 else 0
            else:
                if attendance.check_in:
                    attendance.color = 1 if attendance.check_in < (datetime.today() - timedelta(days=1)) else 10
                else:
                    attendance.color = 1

    def get_attendance_data(self, id=False, last_days=False):
        employees_with_attendance_id = self.env['hr.employee'].search([('attendance_id','!=','')])
        if id:
            employees_with_attendance_id = self.env['hr.employee'].search([('id', '=', id)])
        method, accept, content_type, APP_KEY, APP_SECRET, BASE_URL = get_params(self)

        url = BASE_URL + API_PATH
        today = fields.Date.today()
        if last_days:
            begin_date = today - timedelta(days=last_days)
        else:
            begin_date = today - relativedelta(months=1)

        # Timely-гаас ирц татах функц
        self.get_timely_data(begin_date, today)
        self.get_tapa_timely_data(begin_date, today)

        for attendance_id in employees_with_attendance_id:
            page_num = 1
            response_json = False
            att_id_list = attendance_id.attendance_id
            if ' ' in att_id_list:
                att_id_list = att_id_list.replace(' ', '')
            att_id_list = att_id_list.split(',')
            for att_id in att_id_list:
                while not response_json or 'record' in response_json['data']:
                    body = {
                        "attendanceReportRequest": {
                            "pageNo": page_num,
                            "pageSize": 100,
                            "queryInfo": {
                                "personCode": att_id,
                                "beginTime": f"{begin_date}T00:00:00 05:00",
                                "endTime": f"{str(today)}T23:59:59 08:00",
                                "sortInfo": {
                                    "sortField": 1,
                                    "sortType": 1
                                }
                            }
                        }
                    }
                    page_num += 1
                    headers = build_headers(method, accept, content_type, APP_KEY, APP_SECRET, API_PATH)
                    response = requests.post(url, json=body, headers=headers, verify=False)
                    response_json = response.json()
                    if 'record' in response_json['data']:
                        for line in response_json['data']['record']:
                            if line['personInfo']['personCode'] == att_id:
                                date = fields.Date.from_string(line['date'])
                                start = datetime.combine(date, dt_time.min)
                                end = datetime.combine(date, dt_time.max)
                                check_in = False
                                check_out = False
                                hr_attendance_id = self.env['hr.attendance'].search([('employee_id', '=', attendance_id.id),
                                                                                     ('check_in', '>=', start + relativedelta(hours=-8)),
                                                                                     ('check_in', '<=', end + relativedelta(hours=-8))])
                                if line['attendanceBaseInfo']['beginTime'] != "":
                                    check_in = fields.Datetime.to_string(
                                        parser.isoparse(line['attendanceBaseInfo']['beginTime']).astimezone(pytz.UTC))

                                if line['attendanceBaseInfo']['endTime'] != "":
                                    check_out = fields.Datetime.to_string(
                                        parser.isoparse(line['attendanceBaseInfo']['endTime']).astimezone(pytz.UTC))

                                if check_in or check_out:
                                    if not hr_attendance_id:
                                        self.env['hr.attendance'].create({
                                            'employee_id': attendance_id.id,
                                            'check_in': check_in if check_in else check_out,
                                            'check_out': check_out if check_out else check_in,
                                        })
                                    else:
                                        if check_in and hr_attendance_id.check_in > datetime.strptime(check_in, "%Y-%m-%d %H:%M:%S"):
                                            self.env.cr.execute("""
                                                                    UPDATE hr_attendance
                                                                    SET check_in = %s
                                                                    WHERE id = %s
                                                                """, (str(check_in), hr_attendance_id.id))

                                        if check_out and hr_attendance_id.check_out < datetime.strptime(check_out, "%Y-%m-%d %H:%M:%S"):
                                            self.env.cr.execute("""
                                                                    UPDATE hr_attendance
                                                                    SET check_out = %s
                                                                    WHERE id = %s
                                                                """, (str(check_out), hr_attendance_id.id))


    def get_timely_data(self, start_date, end_date):
        token_url = 'https://api.timely.mn/v3/login'
        ir_config = self.env['ir.config_parameter'].sudo()
        name = ir_config.get_param('timely_user_name', default='')
        password = ir_config.get_param('timely_password', default='')
        company_vat = ir_config.get_param('timely_company_vat', default='')
        leave_obj = self.env['hr.leave'].sudo()
        token = False
        payroll_leave_type_id = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'payroll')], limit=1)
        unpayroll_leave_type_id = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'unpayroll')], limit=1)
        overtime_leave_type_id = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'over_time')], limit=1)
        sick_leave_type_id = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'sick')], limit=1)
        if name != ' ' and password != ' ':
            data = {
                "name": name,
                "password": password,
            }
            headers = {
                'Content-Type': 'application/json',
            }
            response = requests.post(token_url, headers=headers, json=data)
            response_json = response.json()
            token = response_json['data']

        if token:
            employees = self.env['hr.employee'].search([('timely_id', '!=', 0)])
            employees = self.update_employee_timely_id(token, employees, company_vat)
            if not employees:
                return None
            url = 'https://api.timely.mn/v3/expanded-attd'
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }

            have_value = True
            page = 1
            while have_value:
                data = {
                    'company_register': company_vat,
                    'dateFrom': str(start_date),
                    'dateTo': str(end_date),
                    'page': page,
                    'limit': 100
                }
                page += 1
                response = requests.post(url, headers=headers, json=data)
                response_json = response.json()
                if not response_json['data']:
                    break
                if 'success' in response_json and response_json.get('success', False):
                    for line in response_json['data']:
                        try:
                            employee_id = employees.filtered(lambda emp: emp.timely_id == line['workerId'])
                            if not employee_id:
                                continue
                            for key, value in list(line['attd'].items()):
                                date = fields.Date.from_string(key)
                                start = datetime.combine(date, dt_time.min)
                                end = datetime.combine(date, dt_time.max)
                                check_in = False
                                check_out = False
                                hr_attendance_id = self.env['hr.attendance'].search([('employee_id', '=', employee_id.id),
                                                                                     ('check_in', '>=',
                                                                                      start + relativedelta(hours=-8)),
                                                                                     ('check_in', '<=',
                                                                                      end + relativedelta(hours=-8))])

                                if value['clockIn']:
                                    dt = datetime.strptime(value['clockIn'], "%Y-%m-%dT%H:%M:%S.%fZ")
                                    check_in = fields.Datetime.to_datetime(dt) - timedelta(hours=8)

                                if value['clockOut']:
                                    dt = datetime.strptime(value['clockOut'], "%Y-%m-%dT%H:%M:%S.%fZ")
                                    check_out = fields.Datetime.to_datetime(dt) - timedelta(hours=8)

                                if check_in or check_out:
                                    if not hr_attendance_id:
                                        self.env['hr.attendance'].create({
                                            'employee_id': employee_id.id,
                                            'check_in': check_in if check_in else check_out,
                                            'check_out': check_out if check_out else check_in,
                                        })
                                    else:
                                        qry = f"""
                                            UPDATE hr_attendance
                                            SET {"check_in='%s'"%check_in if check_in else ''}{', ' if check_in and check_out else ''}
                                                {"check_out='%s'"%check_out if check_out else ''}
                                            WHERE id = {hr_attendance_id.id}
                                        """
                                        self.env.cr.execute(qry)
                                if value['requests']:
                                    for request in value['requests']:
                                        if leave_obj.search([('timely_id', '=', int(request['id']))]):
                                            continue
                                        req_in = datetime.strptime(request['reqIn'], "%Y-%m-%dT%H:%M:%S.%fZ")
                                        req_in = fields.Datetime.to_datetime(req_in)
                                        req_out = datetime.strptime(request['reqOut'], "%Y-%m-%dT%H:%M:%S.%fZ")
                                        req_out = fields.Datetime.to_datetime(req_out)
                                        leave_vals = {
                                            'request_date_from': req_in.date(),
                                            'request_date_to': req_out.date(),
                                            'request_hour_from': hour_min_to_selection[str(req_in.hour) + ':' + ('30' if req_out.minute >= 30 else '0')],
                                            'request_hour_to': hour_min_to_selection[str(req_out.hour) + ':' + ('30' if req_out.minute >= 30 else '0')],
                                            'request_unit_hours': True,
                                            'employee_id': employee_id.id if employee_id else False,
                                            'timely_id': request['id']
                                        }
                                        if leave_vals['request_hour_to'] == '0':
                                            leave_vals.update({'request_hour_from': str(float(leave_vals['request_hour_from']) - 0.5),
                                                               'request_hour_to': '23.5'})
                                        if request['code'] == 'app_leave_normal':
                                            leave_vals.update({
                                                'holiday_status_id': payroll_leave_type_id.id if request['code'] == 'app_leave_normal' else unpayroll_leave_type_id.id,
                                            })

                                        elif request['code'] == 'overtime_regular_request':
                                            leave_vals.update({
                                                'holiday_status_id': overtime_leave_type_id.id
                                            })
                                        elif request['code'] == 'sick':
                                            leave_vals.update({
                                                'holiday_status_id': sick_leave_type_id.id
                                            })
                                        leave_obj.create(leave_vals)
                        except Exception as e:
                            _logger.error("error accured on get_timely_data error:%s\n", e)
                            continue
        return None

    def get_tapa_timely_data(self, start_date, end_date):
        token_url = 'https://api.timely.mn/openapi/auth/token'
        ir_config = self.env['ir.config_parameter'].sudo()
        key = ir_config.get_param('tapa_timely_key', default='')
        company_vat = ir_config.get_param('tapa_timely_company_vat', default='')
        leave_obj = self.env['hr.leave'].sudo()
        token = False
        payroll_leave_type_id = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'payroll')], limit=1)
        unpayroll_leave_type_id = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'unpayroll')], limit=1)
        overtime_leave_type_id = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'over_time')], limit=1)
        sick_leave_type_id = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'sick')], limit=1)
        if key != '':
            data = {
                "apiKey": key,
            }
            headers = {
                'Content-Type': 'application/json',
            }
            response = requests.post(token_url, headers=headers, json=data)
            response_json = response.json()
            token = False
            if 'result' in response_json and 'accessToken' in response_json['result']:
                token = response_json['result']['accessToken']

        if token:
            employees = self.env['hr.employee'].search([('timely_id', '!=', 0), ('company_id', '=', 5)])
            employees = self.update_tapa_employee_timely_id(token, employees, company_vat)
            if not employees:
                return None
            url = 'https://api.timely.mn/openapi/employees/attendance'
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }
            for employee_id in employees:
                data = {
                    'dateFrom': str(start_date),
                    'dateTo': str(end_date),
                    'workerId': employee_id.timely_id
                }
                response = requests.get(url, headers=headers, params=data)
                response_json = response.json()
                if not response_json['result']:
                    break
                if response_json.get('success', False) and 'result' in response_json:
                    for line in response_json['result']['attendance']:
                        try:
                            date = fields.Date.from_string(line['date'])
                            start = datetime.combine(date, dt_time.min)
                            end = datetime.combine(date, dt_time.max)
                            check_in = False
                            check_out = False
                            hr_attendance_id = self.env['hr.attendance'].search([('employee_id', '=', employee_id.id),
                                                                                 ('check_in', '>=',
                                                                                  start + relativedelta(hours=-8)),
                                                                                 ('check_in', '<=',
                                                                                  end + relativedelta(hours=-8))])

                            if line['clockIn']:
                                dt = datetime.strptime(line['clockIn'], "%Y-%m-%dT%H:%M:%S.%fZ")
                                check_in = fields.Datetime.to_datetime(dt) - timedelta(hours=8)

                            if line['clockOut']:
                                dt = datetime.strptime(line['clockOut'], "%Y-%m-%dT%H:%M:%S.%fZ")
                                check_out = fields.Datetime.to_datetime(dt) - timedelta(hours=8)

                            if check_in or check_out:
                                if not hr_attendance_id:
                                    self.env['hr.attendance'].create({
                                        'employee_id': employee_id.id,
                                        'check_in': check_in if check_in else check_out,
                                        'check_out': check_out if check_out else check_in,
                                    })
                                else:
                                    qry = f"""
                                        UPDATE hr_attendance
                                        SET {"check_in='%s'"%check_in if check_in else ''}{', ' if check_in and check_out else ''}
                                            {"check_out='%s'"%check_out if check_out else ''}
                                        WHERE id = {hr_attendance_id.id}
                                    """
                                    self.env.cr.execute(qry)
                            if line['requests']:
                                for request in line['requests']:
                                    if leave_obj.search([('timely_id', '=', int(request['id']))]):
                                        continue
                                    req_in = datetime.strptime(request['reqIn'], "%Y-%m-%dT%H:%M:%S.%fZ")
                                    req_in = fields.Datetime.to_datetime(req_in)
                                    req_out = datetime.strptime(request['reqOut'], "%Y-%m-%dT%H:%M:%S.%fZ")
                                    req_out = fields.Datetime.to_datetime(req_out)
                                    leave_vals = {
                                        'request_date_from': req_in.date(),
                                        'request_date_to': req_out.date(),
                                        'request_hour_from': hour_min_to_selection[str(req_in.hour) + ':' + ('30' if req_out.minute >= 30 else '0')],
                                        'request_hour_to': hour_min_to_selection[str(req_out.hour) + ':' + ('30' if req_out.minute >= 30 else '0')],
                                        'request_unit_hours': True,
                                        'employee_id': employee_id.id if employee_id else False,
                                        'timely_id': request['id']
                                    }
                                    if leave_vals['request_hour_to'] == '0':
                                        leave_vals.update({'request_hour_from': str(float(leave_vals['request_hour_from']) - 0.5),
                                                           'request_hour_to': '23.5'})
                                    if request['code'] == 'app_leave_normal':
                                        leave_vals.update({
                                            'holiday_status_id': payroll_leave_type_id.id if request['code'] == 'app_leave_normal' else unpayroll_leave_type_id.id,
                                        })

                                    elif request['code'] == 'overtime_regular_request':
                                        leave_vals.update({
                                            'holiday_status_id': overtime_leave_type_id.id
                                        })
                                    elif request['code'] == 'sick':
                                        leave_vals.update({
                                            'holiday_status_id': sick_leave_type_id.id
                                        })
                                    leave_obj.create(leave_vals)
                        except Exception as e:
                            _logger.error("error accured on get_timely_data error:%s\n", e)
                            continue
        return None

    def _cron_update_attendance(self):
        microsoft_value_obj = self.env['microsoft.api.value'].sudo().search([], limit=1)
        token = get_token(microsoft_value_obj)
        if token['token_type'] and token['access_token']:
            token = token['token_type'] + ' ' + token['access_token']
        else:
            raise ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(token))

        site_id = get_site_id(microsoft_value_obj, token)

        list_id = get_list_id(microsoft_value_obj, site_id, token, 'attendance_list_name', 'attendance_list_id')
        date_range = fields.Datetime.now()
        date_range = date_range - relativedelta(days=7)
        attendance_ids = self.env['hr.attendance'].sudo().search(['|', ('share_point_id', '=', ''), ('share_point_id', '=', False)])
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        attendance_ids.push_to_sharepoint(headers, site_id, list_id)
        changed_att_ids = self.env['hr.attendance'].sudo().search([('write_date', '>=', date_range)])
        changed_att_ids.push_to_sharepoint(headers, site_id, list_id)

    def push_to_sharepoint(self, headers, site_id, list_id):
        for att in self:
            try:
                if att.share_point_id == '' or not att.share_point_id:
                    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items"
                else:
                    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items/{att.share_point_id}/fields"
                employee = att.employee_id
                check_in = att.check_in + timedelta(hours=8)
                check_in = check_in.replace(tzinfo=ZoneInfo('Asia/Ulaanbaatar'))
                check_in = check_in.astimezone(ZoneInfo('UTC'))
                check_in = check_in.strftime('%Y-%m-%dT%H:%M:%SZ')

                check_out = att.check_out + timedelta(hours=8)
                check_out = check_out.replace(tzinfo=ZoneInfo('Asia/Ulaanbaatar'))
                check_out = check_out.astimezone(ZoneInfo('UTC'))
                check_out = check_out.strftime('%Y-%m-%dT%H:%M:%SZ')

                hours = int(att.worked_hours)
                minutes = int((att.worked_hours - hours) * 60)

                worked_hour = f"{hours:02d}:{minutes:02d}"
                hr_hour_record = self.env['hr.hour.record'].new({
                    'start_date': datetime.combine(att.check_in.date(), dt_time(0, 1)) - timedelta(hours=8),
                    'end_date': datetime.combine(att.check_out.date(), dt_time(23, 59)) - timedelta(hours=8),
                    'company_id': self.env['res.company'].search([], limit=1, order='id asc').id
                })
                line_vals = hr_hour_record.hour_record(employee_id=att.employee_id)
                los_time = line_vals['miss_time'] or 0
                body = {
                    "Title": employee.last_name or '',
                    "first_name": employee.name or '',
                    "odoo_id": att.id,
                    "check_in": str(check_in),
                    "check_out": str(check_out),
                    "worked_hours": worked_hour,
                    "loss_time": str(round(los_time, 2)),
                    "emp_id": employee.id,
                }
                if att.share_point_id == '' or not att.share_point_id:
                    body = {"fields": body}
                    response = requests.post(url, headers=headers, json=body)
                else:
                    response = requests.patch(url, headers=headers, json=body)
                response_json = response.json()
                if response_json.get('id', False):
                    att.share_point_id = response_json.get('id')
                    self.env.cr.commit()

            except Exception as e:
                self.env.cr.rollback()
                _logger.error("error accured on push_attendance_to_microsoft error:%s\n", e)
                continue

    def update_employee_timely_id(self, token, employees, comp_reg):
        url = 'https://api.timely.mn/v3/employees'
        headers = {
            'Authorization': f'Bearer {token}',
        }

        att_ids = employees.mapped('timely_id')
        response = requests.get(url, headers=headers, params={'company_register': comp_reg})
        response_json = response.json()

        if 'success' in response_json and response_json.get('success', False):
            for line in response_json['data']:
                try:
                    if line['id'] in att_ids:
                        continue
                    else:
                        domain = []
                        if line.get('register', False):
                            domain += [('ssnid', '=', line['register'])]
                        if line.get('phone', False):
                            if domain:
                                domain = ['|'] + domain
                            domain += [('work_phone', '=', line['phone'])]
                        if domain:
                            emp = self.env['hr.employee'].search(domain, limit=1)
                            if emp:
                                self.env.cr.execute("""
                                    UPDATE hr_employee
                                    SET timely_id = %s
                                    WHERE id = %s
                                """ , (line['id'], emp.id))
                                employees |= emp
                except Exception:
                    continue
        return employees

    def update_tapa_employee_timely_id(self, token, employees, comp_reg):
        url = 'https://api.timely.mn/openapi/employees'
        headers = {
            'Authorization': f'Bearer {token}',
        }

        att_ids = employees.mapped('timely_id')
        response = requests.get(url, headers=headers, params={'company_register': comp_reg})
        response_json = response.json()

        if 'success' in response_json and response_json.get('success', False):
            for line in response_json['result']:
                try:
                    if line['workerId'] in att_ids:
                        continue
                    else:
                        domain = []
                        if line.get('register', False):
                            domain += [('ssnid', '=', line['register'])]
                        if line.get('phone', False):
                            if domain:
                                domain = ['|'] + domain
                            domain += [('work_phone', '=', line['phone'])]
                        if domain:
                            emp = self.env['hr.employee'].search(domain, limit=1)
                            if emp:
                                self.env.cr.execute("""
                                    UPDATE hr_employee
                                    SET timely_id = %s
                                    WHERE id = %s
                                """ , (line['workerId'], emp.id))
                                employees |= emp
                except Exception:
                    continue
        return employees
