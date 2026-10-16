from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import requests
import json
from datetime import datetime
from dateutil import parser
import pytz
from pytz import timezone
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import *
import logging

_logger = logging.getLogger(__name__)

hour_min_to_selection = {
    '0:0': '0',
    '0:30': '0.5',
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
    timely_id = fields.Integer("Timly ID")

    def _get_leaves_on_public_holiday(self):
        return False


    def get_approved_leaves(self):
        """Approved leave requests from SharePoint (AttendanceRequest: VMC Connect / the Power App, approved by the
        manager and then HR in Teams) → validated hr.leave, each once (sharepoint_id)."""
        from .hr_attendance_inherit import graph_list_items
        session = self.env['hr.attendance']._graph_session()
        if not session:
            return
        headers, site_id, microsoft_value_obj, token = session
        list_id = get_list_id(microsoft_value_obj, site_id, token, 'leave_list_name', 'leave_list_id')
        leave_obj = self.env['hr.leave'].sudo()
        done = set(leave_obj.search([('sharepoint_id', '!=', False)]).mapped('sharepoint_id'))
        payroll_type = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'payroll')], limit=1)
        unpayroll_type = self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', 'unpayroll')], limit=1)
        tz = timezone('Asia/Ulaanbaatar')

        def local(value):
            return parser.isoparse(value).astimezone(tz)

        def hour(dt):
            # the half hour it falls in (the selection has :00 and :30 only)
            return hour_min_to_selection[f"{dt.hour}:{'30' if dt.minute >= 30 else '0'}"]

        for item in graph_list_items(headers, site_id, list_id, "fields/status eq 'approved'"):
            data = item.get('fields', {})
            sp_id = int(data.get('id') or item.get('id') or 0)
            if not sp_id or sp_id in done or data.get('status') != 'approved':
                continue
            try:
                with self.env.cr.savepoint():
                    employee = self.env['hr.employee'].search([('ssnid', '=', data.get('_x0420__x0435__x0433__x0438__x04'))], limit=1) \
                        if data.get('_x0420__x0435__x0433__x0438__x04') else self.env['hr.employee']
                    email = (data.get('_x0411__x0430__x0442__x043b__x040') or '').strip()
                    if not employee and email:
                        employee = self.env['hr.employee'].search([('work_email', '=ilike', email)], limit=1)
                    if not employee:
                        _logger.warning("Чөлөөний хүсэлт %s: ажилтан олдсонгүй (%s)", sp_id, email)
                        continue
                    # «byHour» is what the lists keep (attTypeDate); «Цагаар» is its title
                    by_hour = data.get('typeDate') in ('byHour', 'Цагаар')
                    if by_hour:
                        start = local(data['_x042d__x0445__x043b__x044d__x04'])
                        end = local(data['_x0414__x0443__x0443__x0441__x04'])
                    else:
                        start = local(data['beginDate'])
                        end = local(data.get('endDate') or data['beginDate'])
                    vals = {
                        'holiday_status_id': (payroll_type if data.get('typeSalary') == 'salary' else unpayroll_type).id,
                        'request_unit_hours': by_hour,
                        'employee_id': employee.id,
                        'sharepoint_id': sp_id,
                        'request_date_from': str(start.date()),
                        'request_date_to': str(end.date()),
                        # approved in Teams already: validated without another round in Odoo
                        'state': 'validate',
                    }
                    if by_hour:
                        vals.update({'request_hour_from': hour(start), 'request_hour_to': hour(end)})
                    if data.get('reason'):
                        vals['private_name'] = data['reason'][:200]
                    leave_obj.with_context(
                        tracking_disable=True,
                        mail_activity_automation_skip=True,
                        leave_fast_create=True,
                        leave_skip_state_check=True,
                    ).create(vals)
                self.env.cr.commit()
            except Exception:
                _logger.exception("Чөлөөний хүсэлт %s-ийг оруулж чадсангүй (дараа дахин оролдоно)", sp_id)
