from odoo import api, fields, models, _
from odoo.addons.l10n_mn_hr_attendance.controllers.microsoft_controllers import *
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    powerpoint_id = fields.Integer("Powerpoint ID")

    def push_to_microsoft(self):
        microsoft_value_obj = self.env['microsoft.api.value'].search([], limit=1)
        if not microsoft_value_obj:
            raise ValidationError('Шаарлагатай параметрүүд бөглөгдөөгүй байна')
        token = get_token(microsoft_value_obj)
        if token['token_type'] and token['access_token']:
            token = token['token_type'] + ' ' + token['access_token']
        else:
            raise ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(token))

        site_id = get_site_id(microsoft_value_obj, token)

        list_id = get_list_id(microsoft_value_obj, site_id, token, 'partner_list_name', 'partner_list_id')
        for partner in self:
            if partner.powerpoint_id == 0:
                url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items"
                headers = {
                    "Authorization": token,
                    "Content-Type": "application/json"
                }

                body = {
                    "fields": {
                        "odoo_id": partner.id,  # last_name
                        "Title": partner.name or '',  # last_name
                        "register": partner.vat or ''
                    }
                }
                try:
                    response = requests.post(url, headers=headers, json=body)
                    response_json = response.json()
                    if response_json.get('id', False):
                        partner.sudo().write(
                            {'powerpoint_id': int(response_json.get('id'))}
                        )
                except Exception as e:
                    _logger.error(u'Ажилтаны мэдээлэл Sharepoint руу илгээхэд алдаа гарлаа. Алдааны мэдээлэл:\n %s',
                                  str(e))
