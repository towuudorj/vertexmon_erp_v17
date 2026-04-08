from odoo import api, fields, models
import requests
import json
from odoo.exceptions import ValidationError
from odoo.addons.l10n_mn_hr_attendance.models.hr_attendance_inherit import build_headers, get_params


class HikCentralAddPerson(models.TransientModel):
    _name = 'hik.central.add.person'
    _description = 'hik.central.add.person'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    hik_central_org_id = fields.Many2one('hik.central.org', string="Organization", domain="[('add_person_wiz_id', '=', id)]")
    employee_has_picture = fields.Boolean(string="Has Picture", compute='_compute_employee_has_picture')
    add_picture = fields.Boolean(string="Add Picture", default=False)


    def add_person_to_hik_central(self):
        self.ensure_one()
        method, accept, content_type, APP_KEY, APP_SECRET, BASE_URL = get_params(self)
        API_PATH = "/artemis/api/resource/v1/person/personList"
        url = BASE_URL + API_PATH
        page_num = 1
        response_json = False
        person_code_max = 0
        while not response_json or 'code' in response_json and response_json['code'] == 0:
            body = {
                "pageNo": page_num,
                "pageSize": 100
            }
            headers = build_headers(method, accept, content_type, APP_KEY, APP_SECRET, API_PATH)
            response = requests.post(url, json=body, headers=headers, verify=False)
            response_json = response.json()

            if response_json.get('data', False) and 'list' in response_json['data']:
                data_list = response_json['data']['list']
                for data in data_list:
                    try:
                        person_code = int(data['personCode'])
                    except Exception:
                        continue
                    if person_code_max < person_code:
                        person_code_max = person_code
            page_num += 1
        if person_code_max:
            API_PATH = "/artemis/api/resource/v1/person/single/add"
            url = BASE_URL + API_PATH
            headers = build_headers(method, accept, content_type, APP_KEY, APP_SECRET, API_PATH)
            body = {
                "personCode": "%s" % str(person_code_max+1),
                "personGivenName": self.employee_id.name,
                "personFamilyName": self.employee_id.last_name,
                "gender": 1 if self.employee_id.gender == 'male' else 2,
                "orgIndexCode": self.hik_central_org_id.org_code,
                "phoneNo": self.employee_id.work_phone,
                "email": self.employee_id.work_email
            }
            response = requests.post(url, json=body, headers=headers, verify=False)
            response_json = response.json()
            if response_json.get('code', False) and response_json['code'] == '0':
                if self.add_picture:
                    image_base64 = self.employee_id.image_1920
                    if image_base64:
                        image_base64 = image_base64.decode('utf-8')
                    API_PATH = "/artemis/api/resource/v1/person/face/update"
                    url = BASE_URL + API_PATH
                    headers = build_headers(method, accept, content_type, APP_KEY, APP_SECRET, API_PATH)
                    body = {
                        "personCode": "%s" % str(person_code_max + 1),
                        "faceData": image_base64,
                    }
                    requests.post(url, json=body, headers=headers, verify=False)
                self.employee_id.sudo().write({"attendance_id": str(person_code_max+1)})
            return {
                'type': 'ir.actions.act_window_close'
            }
        else:
            raise ValidationError(u"Hik Central-тай холбогдож чадсангүй")

    def _compute_employee_has_picture(self):
        for obj in self:
            if obj.employee_id and obj.employee_id.image_1920:
                obj.employee_has_picture = True
            else:
                obj.employee_has_picture = False

class HikCentralOrg(models.TransientModel):
    _name = 'hik.central.org'
    _description = 'hik.central.org'

    name = fields.Char('Organization Name')
    org_code = fields.Char()
    add_person_wiz_id = fields.Many2one('hik.central.add.person')

