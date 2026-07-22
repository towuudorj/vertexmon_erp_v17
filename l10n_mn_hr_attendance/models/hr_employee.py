from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import requests
import json
import logging
from odoo.addons.l10n_mn_hr_attendance.models.hr_attendance_inherit import build_headers, get_params
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import *
from datetime import date, datetime, time, timedelta

_logger = logging.getLogger(__name__)

class Employee(models.Model):
    _inherit = 'hr.employee'

    is_sync_microsoft = fields.Boolean(default=False)
    powerpoint_id = fields.Integer("Powerpoint ID")

    def sync_user_ti_hik_central(self):
        self.ensure_one()
        add_person_wizard = self.env['hik.central.add.person'].create({
            'employee_id': self.id,
        })

        API_PATH = "/artemis/api/resource/v1/org/advance/orgList"
        method, accept, content_type, APP_KEY, APP_SECRET, BASE_URL = get_params(self)
        headers = build_headers(method, accept, content_type, APP_KEY, APP_SECRET, API_PATH)

        url = BASE_URL + API_PATH

        body = {
            "pageNo": 1,
            "pageSize": 100
        }

        response = requests.post(url, json=body, headers=headers, verify=False)
        response_json = response.json()
        if response_json.get('code', False) and response_json['code'] == '0':
            data_list = response_json['data']['list']
            hik_central_org_ob = self.env['hik.central.org']
            parent_id_list = []
            data_dict = {}
            for data in data_list:
                parent_id_list.append(data['parentOrgIndexCode'])
                data_dict[data['orgIndexCode']] = data
            for data in data_list:
                if data['orgIndexCode'] not in parent_id_list:
                    org_name = data['orgName']
                    parent = data['parentOrgIndexCode']
                    while parent != '0':
                        org_name = data_dict[parent]['orgName'] + '->' + org_name
                        parent = data_dict[parent]['parentOrgIndexCode']
                    hik_central_org_ob.create({
                        'name': org_name,
                        'org_code': data['orgIndexCode'],
                        'add_person_wiz_id': add_person_wizard.id,
                    })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hik.central.add.person',
            'view_mode': 'form',
            'res_id': add_person_wizard.id,
            'target': 'new',
        }

    def push_hr_info_to_microsoft(self):
        department_ids = self.env['hr.department'].sudo().search([('is_sync_microsoft', '=', False)])
        job_ids = self.env['hr.job'].sudo().search([('is_sync_microsoft', '=', False)])
        employee_ids = self.env['hr.employee'].sudo().search([('is_sync_microsoft', '=', False)])
        microsoft_value_obj = self.env['microsoft.api.value'].search([], limit=1)
        token = get_token(microsoft_value_obj)
        if token['token_type'] and token['access_token']:
            token = token['token_type'] + ' ' + token['access_token']
        else:
            raise ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(token))
        site_id = get_site_id(microsoft_value_obj, token)

        department_list_id = get_list_id(microsoft_value_obj, site_id, token, 'department_list_name', 'department_list_id')
        for department in department_ids:
            if not department.is_sync_microsoft:
                url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{department_list_id}/items"

                headers = {
                    "Authorization": token,
                    "Content-Type": "application/json"
                }

                body = {
                    "fields": {
                        "department_id": department.id,  # last_name
                        "Title": department.name,  # last_name
                    }
                }
                try:
                    response = requests.post(url, headers=headers, json=body)
                    response_json = response.json()
                    if response_json.get('id', False):
                        department.is_sync_microsoft = True
                except Exception as e:
                    _logger.error(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(e))
        self.env.cr.commit()
        job_list_id = get_list_id(microsoft_value_obj, site_id, token, 'job_list_name', 'job_list_id')
        for job in job_ids:
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{job_list_id}/items"

            headers = {
                "Authorization": token,
                "Content-Type": "application/json"
            }

            body = {
                "fields": {
                    "job_id": job.id,
                    "Title": job.name,
                }
            }
            try:
                response = requests.post(url, headers=headers, json=body)
                response_json = response.json()
                if response_json.get('id', False):
                    job.is_sync_microsoft = True
            except Exception as e:
                _logger.error(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(e))
        self.env.cr.commit()
        employee_ids.push_to_microsoft(token=token)


    def push_to_microsoft(self, token=False):
        microsoft_value_obj = self.env['microsoft.api.value'].search([], limit=1)
        if not microsoft_value_obj:
            raise ValidationError('Шаарлагатай параметрүүд бөглөгдөөгүй байна')
        if not token:
            token = get_token(microsoft_value_obj)
            if token['token_type'] and token['access_token']:
                token = token['token_type'] + ' ' + token['access_token']
            else:
                raise ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(token))

        site_id = get_site_id(microsoft_value_obj, token)

        list_id = get_list_id(microsoft_value_obj, site_id, token, 'employee_list_name', 'employee_list_id')
        for employee in self:
            slices = employee.name.split(".")
            name = employee.name
            max = 0
            for slice in slices:
                if len(slice) > max:
                    max = len(slice)
                    name = slice

            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items"
            headers = {
                "Authorization": token,
                "Content-Type": "application/json"
            }

            body = {
                "fields": {
                    "odoo_id": employee.id, #last_name
                    "Title": employee.last_name or '', #last_name
                    "firstName": name or '',
                    "register": employee.ssnid or '', #ssnid
                    "companyName": employee.company_id.id or 0, #company_id
                    "emailAddress": employee.work_email or '', #work_email
                    "department_id": employee.department_id.id if employee.department_id else 0,
                    "job_id": employee.job_id.id if employee.job_id else 0,
                    "parent_id": employee.parent_id.id if employee.parent_id else 0,
                    "birthday": str(employee.birthday) if employee.birthday else ""
                }
            }
            try:
                response = requests.post(url, headers=headers, json=body)
                response_json = response.json()
                if response_json.get('id', False):
                    employee.sudo().write({'is_sync_microsoft': True,
                                           'powerpoint_id': int(response_json.get('id'))})
                    employee.is_sync_microsoft = True
                    self.env.cr.commit()
            except Exception as e:
                self.env.cr.rollback()
                _logger.error(u'Ажилтаны мэдээлэл Sharepoint руу илгээхэд алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(e))

    def update_hik_central_photo(self):
        try:
            method, accept, content_type, APP_KEY, APP_SECRET, BASE_URL = get_params(self)
            API_PATH = "/artemis/api/resource/v1/person/face/update"
            headers = build_headers(method, accept, content_type, APP_KEY, APP_SECRET, API_PATH)
            image_base64 = self.image_1920.decode('utf-8')
            url = BASE_URL + API_PATH
            body = {
                "personCode": "%s" % self.attendance_id,
                "faceData": image_base64,
            }
            requests.post(url, json=body, headers=headers, verify=False)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': u'Ажилтны зургийг амжилттай шинэчиллээ',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise ValidationError(u'Холбогдож чадсангүй\nАлдаа:%s'%e)

    def push_late_time_to_microsoft(self, token=False):
        self.ensure_one()
        microsoft_value_obj = self.env['microsoft.api.value'].search([], limit=1)

        if not token:
            if not microsoft_value_obj:
                return None
            token = get_token(microsoft_value_obj)
            if token['token_type'] and token['access_token']:
                token = token['token_type'] + ' ' + token['access_token']
            else:
                return None
        try:
            today = fields.Date.context_today(self)
            current_salary_month = self.env['salary.month.range'].search([('year', '=', today.year), ('month', '=', today.month)], limit=1)
            if current_salary_month:
                start_date = current_salary_month.date_from
                end_date = current_salary_month.date_to
            else:
                start_date = date(today.year, today.month, 1)
                end_date = fields.Date.end_of(today, "month")
            hr_hour_record = self.env['hr.hour.record'].new({
                'start_date': datetime.combine(start_date, time(0, 1)) - timedelta(hours=8),
                'end_date': datetime.combine(end_date, time(23, 59)) - timedelta(hours=8),
                'company_id': self.env['res.company'].search([], limit=1, order='id asc').id
            })
            line_vals = hr_hour_record.hour_record(employee_id=self)

            site_id = get_site_id(microsoft_value_obj, token)

            list_id = get_list_id(microsoft_value_obj, site_id, token, 'employee_list_name', 'employee_list_id')

            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items/{self.powerpoint_id}/fields"

            headers = {
                "Authorization": token,
                "Content-Type": "application/json"
            }
            data = {
                "late_hour": round(line_vals['miss_time'], 2) if line_vals.get('miss_time', False) else 0
            }

            requests.patch(url, headers=headers, json=data)
        except Exception as e:
            _logger.error('ERROR:%s' % e)
            return None
        return None

    def _cron_push_late_time(self):
        employees = self.env['hr.employee'].search([('powerpoint_id', '!=', False)])
        microsoft_value_obj = self.env['microsoft.api.value'].search([], limit=1)
        if not microsoft_value_obj:
            return None
        token = get_token(microsoft_value_obj)
        if token['token_type'] and token['access_token']:
            token = token['token_type'] + ' ' + token['access_token']
        else:
            return None
        for emp in employees:
            emp.push_late_time_to_microsoft(token=token)
        return None


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    is_sync_microsoft = fields.Boolean(related='employee_id.is_sync_microsoft', compute_sudo=True)
    powerpoint_id = fields.Integer(related='employee_id.powerpoint_id')


class HrJob(models.Model):
    _inherit = 'hr.job'

    is_sync_microsoft = fields.Boolean(default=False)


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    is_sync_microsoft = fields.Boolean(default=False)


    # Sync хийсэн бүх ажилтаны регисгерийг авна
    # url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?$expand=fields"
    # headers = {
    #     "Authorization": token,
    #     "Content-Type": "application/json"
    # }
    #
    # response = requests.get(url, headers=headers, json={})
    # response_json = response.json()
    # for val in response_json['value']:
    #     if val['fields'] and 'register' in val['fields']:
    #         pushed_employee_registers.append(val['fields']['register'])



    #Listiin бүх талбаруудын утгыг авна
    # url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/columns"
    # headers = {
    #     "Authorization": token,
    #     "Content-Type": "application/json"
    # }
    # response = requests.get(url, headers=headers)
    #
    # print(response.json(), '\n\n\n')