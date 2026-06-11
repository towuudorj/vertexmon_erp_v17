from odoo import fields, http
from odoo.http import route, request
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)

class ControllerAttendance(http.Controller):

    @http.route("/get/attendance", methods=["GET"], type="json", auth="public")
    def get_attendance_data(self, **kwargs):
        data = json.loads(request.httprequest.data or b"{}")
        try:
            auth_header = request.httprequest.headers.get('Authorization')
            if not auth_header:
                return {'error': 'Missing Authorization header'}

            if not auth_header.startswith('Bearer '):
                return {'error': 'Invalid Authorization header'}

            token = auth_header.split(' ')[1]
            if token != request.env['ir.config_parameter'].sudo().get_param('attendance_secret'):
                return {}, {'error': 'Invalid token'}

            start_date = data['start_date']
            end_date = data['end_date']

            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            end_date = datetime.combine(end_date, datetime.max.time())
            attendance_ids = request.env['hr.attendance'].sudo().search([
                ('employee_id.company_id', '=', 5),
                ('check_in', '<=', end_date),
                ('check_in', '>=', start_date)
            ])
            attendance_data = []
            for attendance_id in attendance_ids:
                attendance_data.append({
                    'first_name': attendance_id.employee_id.name,
                    'last_name': attendance_id.employee_id.last_name,
                    'email': attendance_id.employee_id.work_email,
                    'register': attendance_id.employee_id.ssnid,
                    'in': str(attendance_id.check_in + timedelta(hours=8)),
                    'out': str(attendance_id.check_out + timedelta(hours=8)),
                })
            return attendance_data
        except Exception as e:
            _logger.error(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(e))
