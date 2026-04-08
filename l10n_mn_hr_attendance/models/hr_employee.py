from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import requests
import json
from odoo.addons.l10n_mn_hr_attendance.models.hr_attendance_inherit import build_headers, get_params


class Employee(models.Model):
    _inherit = 'hr.employee'

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
