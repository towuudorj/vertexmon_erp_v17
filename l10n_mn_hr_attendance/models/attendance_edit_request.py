from odoo import api, fields, models, _
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import *
from pytz import timezone
from dateutil import parser


class AttendanceEditRequest(models.Model):
    _name = 'attendance.edit.request'
    _description = "Attendance Edit Request"

    share_point_id = fields.Integer(string='Sharepoint id')

    def _cron_get_attendance_request(self):
        req_obj = self.sudo()
        attendance_obj = self.env['hr.attendance'].sudo()
        microsoft_value_obj = self.env['microsoft.api.value'].sudo().search([], limit=1)
        token = get_token(microsoft_value_obj)
        if token['token_type'] and token['access_token']:
            token = token['token_type'] + ' ' + token['access_token']
        else:
            raise ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(token))

        site_id = get_site_id(microsoft_value_obj, token)

        list_id = get_list_id(microsoft_value_obj, site_id, token, 'att_edit_req_list_name', 'att_edit_req_list_id')

        leaves = req_obj.sudo().search([])
        sharepoint_ids = leaves.mapped('share_point_id')

        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?$expand=fields"

        headers = {
            "Authorization": token,
        }
        response = requests.get(url, headers=headers, json={})
        response_json = response.json()
        response_json = response_json.get('value', [])
        for leave in response_json:
            try:
                data = leave.get('fields', {})
                if data['state'] == 'Батлагдсан' and data['id'] and int(data['id']) not in sharepoint_ids:
                    attendance_id = attendance_obj.search([('id', '=', int(data['attendance_odoo_id']))], limit=1)
                    if attendance_id:
                        check_in = parser.isoparse(data['check_in'])
                        check_out = parser.isoparse(data['check_out'])
                        check_in = check_in.strftime("%Y-%m-%d %H:%M:%S")
                        check_out = check_out.strftime("%Y-%m-%d %H:%M:%S")
                        attendance_id.write({'check_in': check_in, 'check_out': check_out})
                        req_obj.create({'share_point_id': int(data['id'])})
            except Exception:
                continue