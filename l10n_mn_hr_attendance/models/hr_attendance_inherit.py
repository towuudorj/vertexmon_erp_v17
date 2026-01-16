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

API_PATH = "/artemis/api/attendance/v1/report"

def sign(app_secret, string_to_sign):
    h = hmac.new(app_secret.encode('utf-8'),
                 string_to_sign.encode('utf-8'),
                 digestmod=hashlib.sha256)
    signature = base64.b64encode(h.digest()).decode('utf-8')
    return signature


def build_headers(method, accept, content_type, APP_KEY, APP_SECRET):
    timestamp = str(int(time.time() * 1000))

    # -------- Signature String --------
    string_to_sign = (
        f"{method}\n"
        f"{accept}\n"
        f"{content_type}\n"
        f"x-ca-key:{APP_KEY}\n"
        f"x-ca-timestamp:{timestamp}\n"
        f"{API_PATH}"
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
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=False, tracking=True)
    
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

    def get_attendance_data(self):
        employees_with_attendance_id = self.env['hr.employee'].search([('attendance_id','!=',0)])
        method = "POST"
        accept = "*/*"
        content_type = "application/json"
        APP_KEY = self.env['ir.config_parameter'].sudo().get_param('Attendance_APP_KEY')
        APP_SECRET = self.env['ir.config_parameter'].sudo().get_param('Attendance_APP_SECRET')
        BASE_URL = self.env['ir.config_parameter'].sudo().get_param('Attendance_BASE_URL')

        url = BASE_URL + API_PATH
        today = fields.Date.today()
        for attendance_id in employees_with_attendance_id:
            page_num = 1
            response_json = False
            while not response_json or 'record' in response_json['data']:
                body = {
                    "attendanceReportRequest": {
                        "pageNo": page_num,
                        "pageSize": 100,
                        "queryInfo": {
                            "personCode": str(attendance_id.attendance_id),
                            "beginTime": "2024-01-01T00:00:00 08:00",
                            "endTime": f"{str(today)}T23:59:59 08:00",
                            "sortInfo": {
                                "sortField": 1,
                                "sortType": 1
                            }
                        }
                    }
                }
                page_num += 1
                headers = build_headers(method, accept, content_type, APP_KEY, APP_SECRET)
                response = requests.post(url, json=body, headers=headers, verify=False)
                response_json = response.json()
                if 'record' in response_json['data']:
                    for line in response_json['data']['record']:
                        date = fields.Date.from_string(line['date'])
                        start = datetime.combine(date, dt_time.min)
                        end = datetime.combine(date, dt_time.max)
                        hr_attendance_id = self.env['hr.attendance'].search([('employee_id', '=', attendance_id.id),
                                                                             ('check_in', '>=', start),
                                                                             ('check_in', '<=', end)])
                        if line['attendanceBaseInfo']['beginTime'] != "":
                            check_in = fields.Datetime.to_string(
                                parser.isoparse(line['attendanceBaseInfo']['beginTime']).astimezone(pytz.UTC))
                        else:
                            check_in = False
                        if line['attendanceBaseInfo']['endTime'] != "":
                            check_out = fields.Datetime.to_string(
                                parser.isoparse(line['attendanceBaseInfo']['endTime']).astimezone(pytz.UTC))
                        else:
                            check_out = False
                        if not hr_attendance_id and (check_in or check_out):
                            self.env['hr.attendance'].create({
                                'employee_id': attendance_id.id,
                                'check_in': check_in,
                                'check_out': check_out,
                            })
                        else:
                            hr_attendance_id.sudo().write({
                                'check_in': check_in,
                                'check_out': check_out,
                            })