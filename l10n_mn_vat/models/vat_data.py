# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json, requests


class VatData(models.Model):
    _name = "vat.data"
    _description = "Vat data"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Vat id')
    pos_id = fields.Char(string='Pos id')
    company_id = fields.Many2one('res.company',string='Company', default=lambda self: self.env.company)
    reg_date = fields.Datetime(string='Register date')
    total_amount = fields.Float(string='Total amount')
    total_vat = fields.Float(string='Total vat')
    total_city_tax = fields.Float(string='Total city tax')
    district_code = fields.Char(string='District code')
    branch_no = fields.Char(string='Branch no')
    merchant_tin = fields.Char(string='Merchant tin')
    pos_no = fields.Char(string='Pos no')
    customer_tin = fields.Char(string='Customer tin')
    customer_no = fields.Char(string='Customer no')
    type = fields.Char(string='Type')
    inactive_id = fields.Char(string='Inactive id')
    invoice_id = fields.Char(string='Invoice id')
    report_month = fields.Char(string='Report month')
    line_ids = fields.One2many('vat.data.line','vat_id',string='Items')
    is_return = fields.Boolean(string='Is return')
    
    def action_return(self):
        vat_config_obj  = self.env['vat.configure']
        vat_config_id = vat_config_obj.search([('company_id','=',self.company_id.id)],limit=1)
        url = vat_config_id.ebarimt_return_url
        header = {
                "Content-Type":"application/json",                
                }
        
        send_data = {
                    "id":self.vat_id,
                    'date':str(self.reg_date),
                }
        send_datas = json.dumps(send_data)
        try:
            return_data = requests.request("DELETE", url, headers = header, data=send_datas)
            if return_data.status_code == 200:
                json_data = return_data.json()
                self.is_return = True
            elif return_data.status_code == 500:
                self.is_return = True
            else:
                raise UserError(_(u'Тохиргоо зөв эсэхийг шалгана уу.'))
        except:
            print("a")
        
        
        


class VatDataLine(models.Model):
    _name = 'vat.data.line'
    _description = "Vat data line"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    
    company_id = fields.Many2one('res.company',string='Company', default=lambda self: self.env.company)
    vat_id = fields.Many2one('vat.data',string='Vat data')
    name = fields.Char(string='Product name')
    barcode = fields.Char(string='Barcode')
    barcode_type = fields.Char(string='Barcode type')
    classification_code = fields.Char(string='Classification code')
    tax_product_code = fields.Char(string='Tax product code')
    measure_unit = fields.Char(string='Measure unit')
    qty = fields.Char(string='Qty')
    unit_price = fields.Char(string='Unit price')
    total_bonus = fields.Float(string='Total bonus')
    total_vat = fields.Float(string='Total vat')
    total_city_tax = fields.Float(string='Total city tax')
    total_amount = fields.Float(string='Total amount')
    
    
    
    
    