from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import base64
import requests
import json
from datetime import datetime, timedelta
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
        def api_type(sub_type):
            return self.env['hr.leave.type'].search([('use_in_api', '=', True), ('sub_type', '=', sub_type)], limit=1)

        # typeSalary as VMC Connect writes it: the list's paid code, annual leave, overtime, sick and «Гадуур ажил» (work
        # outside the office, paid: the paid type, the description says what it was); anything else is the list's unpaid
        # code (the Power App's two). Annual leave is HR's own type, not an API one (its sub-type is
        # shared with «Нөхөн амралт»): the one whose Code is ANNUAL. Without an allocation for the person Odoo
        # refuses it, and it is tried again each run until HR allocates the days.
        types = {
            'salary': api_type('payroll'),
            'annual': self.env['hr.leave.type'].search([('code', '=ilike', 'ANNUAL')], limit=1),
            'overtime': api_type('over_time'),
            'sick': api_type('sick'),
            'outwork': api_type('payroll'),
        }
        unpayroll_type = api_type('unpayroll')
        tz = timezone('Asia/Ulaanbaatar')
        created = leave_obj.browse()
        # VMC Connect's side lists (VMCC_Log, VMCC_Files), looked up once a run
        edits, log, lists = self.env['attendance.edit.request'].sudo(), {}, {}

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
                    kind = data.get('typeSalary')
                    leave_type = types.get(kind, unpayroll_type)
                    if not leave_type:
                        # never as another type (overtime as unpaid leave would cut the pay): tried again once it is there
                        _logger.warning("Чөлөөний хүсэлт %s: «%s»-д тохирох чөлөөний төрөл (use_in_api) Odoo-д алга", sp_id, kind)
                        continue
                    vals = {
                        'holiday_status_id': leave_type.id,
                        'request_unit_hours': by_hour,
                        'employee_id': employee.id,
                        'sharepoint_id': sp_id,
                        'request_date_from': str(start.date()),
                        'request_date_to': str(end.date()),
                        # approved in Teams already: validated without another round in Odoo
                        'state': 'validate',
                    }
                    # overtime past midnight (23:00–05:00 the next day): Odoo keeps an hourly leave inside one day (it moves
                    # the end onto the first day, and an end before the start breaks date_check2), so it is made up to the
                    # day's last half hour and its real end is set once it is there
                    overnight = by_hour and end.date() > start.date()
                    if by_hour:
                        vals.update({'request_hour_from': hour(start),
                                     'request_hour_to': hour_min_to_selection['23:30'] if overnight else hour(end)})
                    if kind == 'outwork':
                        vals['private_name'] = f"Гадуур ажил: {data['reason']}" if data.get('reason') else 'Гадуур ажил'
                    elif data.get('reason'):
                        vals['private_name'] = data['reason']
                    # sick leave: the doctor's note handed in with it, fetched first (a failure tries it all again)
                    note = None
                    if kind == 'sick':
                        sick_note = edits._vmcc_extras(headers, site_id, f"AttendanceRequest#{sp_id}", log, quiet=False).get('sickNote') or {}
                        if sick_note.get('item'):
                            content = edits._vmcc_file(headers, site_id, sick_note['item'], lists)
                            if content is None:
                                _logger.warning("Чөлөөний хүсэлт %s: акт «%s» VMCC_Files-д алга", sp_id, sick_note.get('name'))
                            else:
                                note = (sick_note.get('name') or 'акт', content)
                    leave = leave_obj.with_context(
                        tracking_disable=True,
                        mail_activity_automation_skip=True,
                        leave_fast_create=True,
                        leave_skip_state_check=True,
                    ).create(vals)
                    # (with the context above: a validated leave may be changed)
                    if overnight:
                        leave.write({'date_to': end.astimezone(pytz.utc).replace(tzinfo=None)})
                    if kind == 'overtime':
                        leave.write(leave._vmcc_overtime_duration(start, end, by_hour))
                    if note:
                        # on the leave: its supporting documents and the chatter
                        self.env['ir.attachment'].sudo().create(
                            {'name': note[0], 'datas': base64.b64encode(note[1]), 'res_model': 'hr.leave', 'res_id': leave.id})
                    created |= leave
                self.env.cr.commit()
            except Exception:
                _logger.exception("Чөлөөний хүсэлт %s-ийг оруулж чадсангүй (дараа дахин оролдоно)", sp_id)
        if created:
            # the leave is in: the lost time SharePoint shows for those days takes it off now
            try:
                created.push_attendance_to_sharepoint()
            except Exception:
                _logger.exception("Чөлөөний өдрүүдийн ирцийг SharePoint руу дахин илгээж чадсангүй")

    def _vmcc_overtime_duration(self, start, end, by_hour):
        """Odoo counts a leave by the working schedule, and overtime is outside it (evenings, days off), where that
        comes to nothing. hr.hour.record pays number_of_hours (under a day) or number_of_days × the day's hours, so
        those are set to what was worked: the hours asked for, or a day's hours for each day off of a by-day request.
        start, end: Ulaanbaatar datetimes."""
        self.ensure_one()
        calendar = self.resource_calendar_id or self.employee_id.resource_calendar_id
        per_day = (calendar.hours_per_day if calendar else 0) or 8.0
        if by_hour:
            hours = max(0.0, (end - start).total_seconds() / 3600)
            return {'number_of_hours': round(hours, 2), 'number_of_days': round(hours / per_day, 4)}
        days = 0
        day = start.date()
        while day <= end.date():
            if calendar:
                tz = pytz.timezone(calendar.tz or 'Asia/Ulaanbaatar')
                first = tz.localize(datetime.combine(day, datetime.min.time()))
                off = not calendar.get_work_hours_count(first, first + timedelta(days=1), compute_leaves=True)
            else:
                off = day.weekday() >= 5
            days += 1 if off else 0
            day += timedelta(days=1)
        return {'number_of_hours': days * per_day, 'number_of_days': days}

    def push_attendance_to_sharepoint(self):
        """The lost time (loss_time) of a day's attendance in SharePoint is worked out when the row is pushed, and an
        approved leave takes its hours off it (hr.hour.record). The push only repeats the last days, so for a leave on
        an older day, or approved after the push, SharePoint would keep the old number: push the attendance these
        leaves cover again."""
        from .hr_attendance_inherit import day_bounds_utc
        attendance_obj = self.env['hr.attendance'].sudo()
        session = attendance_obj._graph_session()
        if not session:
            return
        headers, site_id, microsoft_value_obj, token = session
        list_id = get_list_id(microsoft_value_obj, site_id, token, 'attendance_list_name', 'attendance_list_id')
        attendances = attendance_obj
        for leave in self.sudo():
            if not leave.employee_id or not leave.request_date_from:
                continue
            first = day_bounds_utc(leave.request_date_from)[0]
            last = day_bounds_utc(leave.request_date_to or leave.request_date_from)[1]
            attendances |= attendance_obj.search(
                [('employee_id', '=', leave.employee_id.id), ('check_in', '>=', first), ('check_in', '<=', last)])
        attendances.push_to_sharepoint(headers, site_id, list_id)

    @api.model
    def refresh_attendance_in_sharepoint(self, since):
        """One-off, for leaves that came before the above: push again the attendance of every SharePoint leave from a
        date on, e.g. env['hr.leave'].refresh_attendance_in_sharepoint('2026-10-01'). Returns how many leaves it went through."""
        leaves = self.sudo().search([('sharepoint_id', '!=', False), ('state', '=', 'validate'), ('request_date_from', '>=', since)])
        leaves.push_attendance_to_sharepoint()
        return len(leaves)
