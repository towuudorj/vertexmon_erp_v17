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

API_PATH = "/artemis/api/attendance/v1/report"

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
            begin_date = today
            if today.month != 1:
                month = today.month-1
                year = today.year
            else:
                month = 12
                year = today.year-1
            begin_date = begin_date.replace(year=year, month=month)

        # Timely-гаас ирц татах функц
        self.get_timely_data(begin_date, today)

        for attendance_id in employees_with_attendance_id:
            page_num = 1
            response_json = False
            att_id_list = attendance_id.attendance_id.replace(" ", "")
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
                                        hr_attendance_id.sudo().write({
                                            'check_in': check_in
                                        })

                                    if check_out and hr_attendance_id.check_out < datetime.strptime(check_out, "%Y-%m-%d %H:%M:%S"):
                                        hr_attendance_id.sudo().write({
                                            'check_out': check_out
                                        })


    def get_timely_data(self, start_date, end_date):
        employees = self.env['hr.employee'].search([('timely_id', '!=', 0)])
        if not employees:
            return None
        token_url = 'https://api.timely.mn/v3/login'
        ir_config = self.env['ir.config_parameter'].sudo()
        name = ir_config.get_param('timely_user_name', default='')
        password = ir_config.get_param('timely_password', default='')
        company_vat = ir_config.get_param('timely_company_vat', default='')
        leave_obj = self.env['hr.leave'].sudo()
        token = False
        if name != ' ' and password != ' ':
            data = {
                "name": name,
                "password": password,
            }
            headers = {
                'Content-Type': 'application/json',
            }
            response = requests.request("POST", token_url, headers=headers, json=data)
            response_json = response.json()
            token = response_json['data']

        if token:
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
                        employee_id = employees.filtered(lambda emp: str(emp.timely_id) == line['workerId'])
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
                                    if check_in and hr_attendance_id.check_in > check_in:
                                        hr_attendance_id.sudo().write({
                                            'check_in': check_in
                                        })

                                    if check_out and hr_attendance_id.check_out < check_out:
                                        hr_attendance_id.sudo().write({
                                            'check_out': check_in
                                        })
                            # if value['requests']:
                            #     for requests in value['requests']:
                            #         leave_vals = {
                            #             'holiday_status_id': payroll_leave_type_id.id if requests['code'] == 'app_leave_normal' else unpayroll_leave_type_id.id,
                            #             'request_unit_hours': True,
                            #             'employee_id': employee.id if employee else False,
                            #             'sharepoint_id': data['id'],
                            #         }
                            #         leave_vals.update({'request_date_from': str(start_date.date()),
                            #                            'request_date_to': str(end_date.date()),
                            #                            'request_hour_from': hour_min_to_selection[
                            #                                str(start_date.hour) + ':' + str(start_date.minute)],
                            #                            'request_hour_to': hour_min_to_selection[
                            #                                str(end_date.hour) + ':' + str(end_date.minute)]
                            #                            })
                            #
                            #         leave_obj.create(leave_vals)
        return None