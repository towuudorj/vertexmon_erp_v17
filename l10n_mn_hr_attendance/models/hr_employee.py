from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import requests
import json
from odoo.addons.l10n_mn_hr_attendance.models.hr_attendance_inherit import build_headers, get_params
from odoo.addons.l10n_mn_hr_attendance.controllers.microsoft_controllers import *


class Employee(models.Model):
    _inherit = 'hr.employee'

    is_sync_microsoft = fields.Boolean(default=False)

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
        department_ids = self.env['hr.department'].sudo().search([])
        job_ids = self.env['hr.job'].sudo().search([])
        employee_ids = self.env['hr.employee'].sudo().search([])
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
                    ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(e))

        job_list_id = get_list_id(microsoft_value_obj, site_id, token, 'job_list_name', 'job_list_id')
        for job in job_ids:
            if not job.is_sync_microsoft:
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
                    ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(e))
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
            if not employee.is_sync_microsoft:
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
                        "Title": employee.last_name, #last_name
                        "firstName": name,
                        "register": employee.ssnid, #ssnid
                        "companyName": employee.company_id.id, #company_id
                        "emailAddress": employee.work_email, #work_email
                        "department_id": employee.department_id.id if employee.department_id else 0,
                        "job_id": employee.job_id.id if employee.job_id else 0,
                        "odoo_userid": employee.user_id.id if employee.user_id else 0, #user_id
                        "parent_id": employee.parent_id.id if employee.parent_id else 0,
                    }
                }
                try:
                    response = requests.post(url, headers=headers, json=body)
                    response_json = response.json()
                    if response_json.get('id', False):
                        employee.is_sync_microsoft = True
                except Exception as e:
                    ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(e))

class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    is_sync_microsoft = fields.Boolean(related='employee_id.is_sync_microsoft', compute_sudo=True)


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