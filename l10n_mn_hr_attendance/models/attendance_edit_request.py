from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import *
from dateutil import parser
import pytz
import logging
from .hr_attendance_inherit import graph_list_items

_logger = logging.getLogger(__name__)


def sp_utc(value):
    """A SharePoint date as naive UTC (how Odoo stores datetimes)"""
    return parser.isoparse(value).astimezone(pytz.UTC).replace(tzinfo=None) if value else False


class AttendanceEditRequest(models.Model):
    _name = 'attendance.edit.request'
    _description = "Attendance Edit Request"

    # the SharePoint item (AttendanceEditRequest list) already applied
    share_point_id = fields.Integer(string='Sharepoint id')

    def _cron_get_attendance_request(self):
        """Approved attendance edit requests (VMC Connect / the Power App, approved by the manager and then HR in
        Teams) → the hr.attendance they are about. The attendance is then locked (manual_lock): the HikCentral /
        Timely sync leaves it alone, and it is sent to SharePoint right away (worked hours, late minutes), so VMC Connect
        shows the corrected day without waiting for the daily «Ирц шинэчилэх»."""
        session = self.env['hr.attendance']._graph_session()
        if not session:
            return
        headers, site_id, microsoft_value_obj, token = session
        list_id = get_list_id(microsoft_value_obj, site_id, token, 'att_edit_req_list_name', 'att_edit_req_list_id')
        done = set(self.sudo().search([]).mapped('share_point_id'))
        attendance_obj = self.env['hr.attendance'].sudo()
        corrected = attendance_obj
        for item in graph_list_items(headers, site_id, list_id, "fields/state eq 'Батлагдсан'"):
            data = item.get('fields', {})
            sp_id = int(data.get('id') or item.get('id') or 0)
            if not sp_id or sp_id in done or data.get('state') != 'Батлагдсан':
                continue
            try:
                with self.env.cr.savepoint():
                    attendance = attendance_obj.browse(int(data.get('attendance_odoo_id') or 0)).exists()
                    check_in = sp_utc(data.get('check_in'))
                    check_out = sp_utc(data.get('check_out'))
                    if attendance and check_in:
                        attendance.write({
                            'check_in': check_in,
                            # no check-out asked for: the day keeps one time, as the sync writes it
                            'check_out': check_out if check_out and check_out > check_in else check_in,
                            'manual_lock': True,
                        })
                        corrected |= attendance
                    else:
                        _logger.warning("Ирц засах хүсэлт %s: ирц (%s) эсвэл ирсэн цаг олдсонгүй", sp_id, data.get('attendance_odoo_id'))
                    self.sudo().create({'share_point_id': sp_id})
                self.env.cr.commit()
            except Exception:
                _logger.exception("Ирц засах хүсэлт %s-ийг оруулж чадсангүй (дараа дахин оролдоно)", sp_id)
        if corrected:
            try:
                att_list_id = get_list_id(microsoft_value_obj, site_id, token, 'attendance_list_name', 'attendance_list_id')
                corrected.push_to_sharepoint(headers, site_id, att_list_id)
            except Exception:
                # the daily «Ирц шинэчилэх» sends them anyway (they were written lately)
                _logger.exception("Засагдсан ирцийг SharePoint руу илгээж чадсангүй: %s", corrected.ids)
