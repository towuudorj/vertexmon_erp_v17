from odoo import fields, models, api
from odoo.addons.vertexmon_tools.controllers.microsoft_controllers import *


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def write(self, vals):
        res = super().write(vals)
        current_company = self.env.company
        if any(field in vals for field in ['sequence', 'acc_number', 'iban', 'partner_id']) and self.partner_id.id == current_company.partner_id.id:
            self.microsoft_push_bank_ids()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        current_company = self.env.company
        company_acc_ids = self.env['res.partner.bank']
        for rec in records:
            if rec.partner_id.id == current_company.partner_id.id:
                company_acc_ids |= rec
        if company_acc_ids:
            company_acc_ids.microsoft_push_bank_ids()
        return records

    def unlink(self):
        current_company = self.env.company
        update_company_acc = any(obj.partner_id.id == current_company.partner_id.id for obj in self)
        if update_company_acc:
            self.env['res.partner.bank'].microsoft_push_bank_ids()
        super(ResPartnerBank, self).unlink()

    def microsoft_push_bank_ids(self):
        microsoft_value_obj = self.env['microsoft.api.value'].sudo().search([], limit=1)
        token = get_token(microsoft_value_obj)
        if token['token_type'] and token['access_token']:
            token = token['token_type'] + ' ' + token['access_token']
        else:
            raise ValidationError(u'Алдаа гарлаа. Алдааны мэдээлэл:\n %s', str(token))

        site_id = get_site_id(microsoft_value_obj, token)

        list_id = get_list_id(microsoft_value_obj, site_id, token, 'company_account_list_name', 'company_account_list_id')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?$select=id"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, json={})
        response.raise_for_status()
        response_json = response.json()
        for item in response_json["value"]:
            requests.delete(
                f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items/{item['id']}",
                headers=headers,
            )

        for acc_id in self.env.company.bank_ids:
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items"
            body = {
                "fields":{
                    "Title": acc_id.bank_id.name or '',
                    "odoo_id": acc_id.id,
                    "sequence": acc_id.sequence or 0,
                    "acc_number": acc_id.acc_number or '',
                    "iban": acc_id.iban or '',
                }
            }
            requests.post(url, headers=headers, json=body)
