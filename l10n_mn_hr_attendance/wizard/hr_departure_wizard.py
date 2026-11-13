from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.addons.l10n_mn_hr_attendance.models.hr_attendance_inherit import get_params, build_headers
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def _update_hikcentral_person_validity(record, attendance_id, begin_time, end_time):
    method, accept, content_type, APP_KEY, APP_SECRET, BASE_URL = get_params(record)
    if not BASE_URL:
        raise ValidationError(u'HikCentral холболтын тохиргоо (BASE_URL) тохируулагдаагүй байна.')

    codes = [c.strip() for c in str(attendance_id).split(',') if c.strip()]
    user_id = record.env.user.employee_id.attendance_id or 9

    for code in codes:
        API_PATH = "/artemis/api/resource/v1/person/personCode/personInfo"
        headers = build_headers(method, accept, content_type, APP_KEY, APP_SECRET, API_PATH)
        headers['userId'] = "%s" % user_id
        url = BASE_URL + API_PATH
        body = {
            "personCode": code,
            "appendInfo": [6],
        }

        data = requests.post(url, json=body, headers=headers, verify=False, timeout=15)
        if data.status_code != 200:
            raise ValidationError(u'HikCentral холболтын алдаа (HTTP %s): %s' % (data.status_code, data.text[:200]))

        response_json = data.json()
        if not response_json.get('data') or not response_json['data'].get('personId'):
            msg = response_json.get('msg', 'Ажилтан HikCentral дээр олдсонгүй (personCode=%s)' % code)
            raise ValidationError(u'HikCentral алдаа: %s' % msg)
        hik_id = response_json['data']['personId']

        API_PATH = "/artemis/api/resource/v1/person/single/update"
        headers = build_headers(method, accept, content_type, APP_KEY, APP_SECRET, API_PATH)
        headers['userId'] = "%s" % user_id
        url = BASE_URL + API_PATH
        body = {
            "personId": hik_id,
            "beginTime": begin_time,
            "endTime": end_time
        }
        update_res = requests.post(url, json=body, headers=headers, verify=False, timeout=15)
        if update_res.status_code != 200:
            raise ValidationError(u'HikCentral шинэчлэхэд алдаа гарлаа (HTTP %s): %s' % (update_res.status_code, update_res.text[:200]))

        try:
            update_json = update_res.json()
            if update_json.get('code') is not None and str(update_json.get('code')) != '0':
                msg = update_json.get('msg', 'Шинэчлэхэд алдаа гарлаа')
                raise ValidationError(u'HikCentral алдаа: %s' % msg)
        except (ValueError, TypeError):
            pass


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def action_register_departure(self):
        try:
            res = super(HrDepartureWizard, self).action_register_departure()
            if self.employee_id.attendance_id:
                date_val = fields.datetime.now() - timedelta(days=1)
                begin_time = str(date_val.date()) + "T00:00:00+08:00"
                end_time = str(date_val.date()) + "T23:59:59+08:00"
                _update_hikcentral_person_validity(self, self.employee_id.attendance_id, begin_time, end_time)
            return res
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(u'Холбогдож чадсангүй\nАлдаа:%s' % e)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _hikcentral_restore_access(self):
        now = fields.datetime.now()
        end_date = now + relativedelta(years=10)
        begin_time = str(now.date()) + "T00:00:00+08:00"
        end_time = str(end_date.date()) + "T23:59:59+08:00"
        for emp in self:
            if emp.attendance_id:
                try:
                    _update_hikcentral_person_validity(emp, emp.attendance_id, begin_time, end_time)
                except ValidationError:
                    raise
                except Exception as e:
                    raise ValidationError(u'Холбогдож чадсангүй\nАлдаа:%s' % e)

    def write(self, vals):
        unarchiving_employees = self.env['hr.employee']
        if vals.get('active') and not self.env.context.get('hikcentral_restored'):
            unarchiving_employees = self.filtered(lambda emp: not emp.active and emp.attendance_id)
        res = super(HrEmployee, self).write(vals)
        if unarchiving_employees:
            unarchiving_employees.with_context(hikcentral_restored=True)._hikcentral_restore_access()
        return res
