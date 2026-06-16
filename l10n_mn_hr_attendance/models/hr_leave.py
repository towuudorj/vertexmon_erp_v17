from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import requests
import json
from datetime import datetime
from dateutil import parser
import pytz
from pytz import timezone
from odoo.addons.l10n_mn_hr_attendance.controllers.microsoft_controllers import *

hour_min_to_selection = {
    '0:0': '0',
    '0:5': '0.5',
    '1:0': '1',
    '1:30': '1.5',
    '2:0': '2',
    '2:30': '2.5',
    '3:0': '3',
    '3:30': '3.5',
    '4:0': '4',
    '4:30': '4.5',
    '5:0': '5',
    '5:30': '5.5',
    '6:0': '6',
    '6:30': '6.5',
    '7:0': '7',
    '7:30': '7.5',
    '8:0': '8',
    '8:30': '8.5',
    '9:0': '9',
    '9:30': '9.5',
    '10:0': '10',
    '10:30': '10.5',
    '11:0': '11',
    '11:30': '11.5',
    '12:0': '12',
    '12:30': '12.5',
    '13:0': '13',
    '13:30': '13.5',
    '14:0': '14',
    '14:30': '14.5',
    '15:0': '15',
    '15:30': '15.5',
    '16:0': '16',
    '16:30': '16.5',
    '17:0': '17',
    '17:30': '17.5',
    '18:0': '18',
    '18:30': '18.5',
    '19:0': '19',
    '19:30': '19.5',
    '20:0': '20',
    '20:30': '20.5',
    '21:0': '21',
    '21:30': '21.5',
    '22:0': '22',
    '22:30': '22.5',
    '23:0': '23',
    '23:30': '23.5'
}

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    sharepoint_id = fields.Integer("Share Point ID")
    timely_id = fields.Integer("Share Point ID")

    def _get_leaves_on_public_holiday(self):
        return False


    def get_approved_leaves(self):
        leave_obj = self.env['hr.leave'].sudo()
        microsoft_value_obj = self.env['microsoft.api.value'].sudo().search([], limit=1)
        token = get_token(microsoft_value_obj)
        if token['token_type'] and token['access_token']:
            token = token['token_type'] + ' ' + token['access_token']
        else:
            raise ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(token))

        site_id = get_site_id(microsoft_value_obj, token)

        list_id = get_list_id(microsoft_value_obj, site_id, token, 'leave_list_name', 'leave_list_id')

        leaves = self.env['hr.leave'].sudo().search([('sharepoint_id', '!=', False)])
        sharepoint_ids = leaves.mapped('sharepoint_id')

        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?$expand=fields"
        # url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/columns"

        headers = {
            "Authorization": token,
        }
        response = requests.get(url, headers=headers, json={})
        response_json = response.json()
        payroll_leave_type_id = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'payroll')], limit=1)
        unpayroll_leave_type_id = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'unpayroll')], limit=1)
        response_json = response_json.get('value', [])
        for leave in response_json:
            try:
                data = leave.get('fields', {})
                if data['status'] == 'approved' and data['id'] and int(data['id']) not in sharepoint_ids:
                    employee = self.env['hr.employee'].search([('ssnid', '=', data['_x0420__x0435__x0433__x0438__x04'])], limit=1)
                    if data['typeDate'] and data['typeDate'] == 'Цагаар':
                        start_date = data['_x042d__x0445__x043b__x044d__x04']
                        end_date = data['_x0414__x0443__x0443__x0441__x04']
                    else:
                        start_date = data['beginDate']
                        end_date = data['endDate']

                    tz = timezone('Asia/Ulaanbaatar')
                    start_date = parser.isoparse(start_date).astimezone(tz)
                    end_date = parser.isoparse(end_date).astimezone(tz)

                    leave_vals =  {
                        'holiday_status_id': payroll_leave_type_id.id if data['typeSalary'] == 'salary' else unpayroll_leave_type_id.id,
                        'request_unit_hours': True if data['typeDate'] == 'Цагаар' else False,
                        'employee_id': employee.id if employee else False,
                        'sharepoint_id': data['id'],
                    }
                    if data['typeDate'] == 'Цагаар':
                        leave_vals.update({'request_date_from': str(start_date.date()), 'request_date_to': str(end_date.date()),
                                           'request_hour_from': hour_min_to_selection[str(start_date.hour) + ':' + str(start_date.minute)],
                                           'request_hour_to': hour_min_to_selection[str(end_date.hour) + ':' + str(end_date.minute)]
                                           })

                    else:
                        leave_vals.update({'request_date_from': str(start_date.date()), 'request_date_to': str(end_date.date())})
                    leave_obj.create(leave_vals)
            except Exception:
                continue