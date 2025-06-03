# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
import json, requests

class AccountMove(models.Model):
    _inherit = "account.move"
    

    vat_type = fields.Selection([('B2C_RECEIPT','Бизнес эрхлэгчээс хувь хүнд борлуулсан бүтээгдэхүүн, үйлчилгээний төлбөрийн баримт'),
                             ('B2B_RECEIPT','Бизнес эрхлэгч хооронд борлуулсан бүтээгдэхүүн, үйлчилгээний төлбөрийн баримт'),
                             ('B2C_INVOICE','Бизнес эрхлэгчээс хувь хүнд борлуулсан бүтээгдэхүүн, үйлчилгээний нэхэмжлэх'),
                             ('B2B_INVOICE','Бизнес эрхлэгч хооронд борлуулсан бүтээгдэхүүн, үйлчилгээний нэхэмжлэх')],
                             string='Татварын баримтын төрөл')
    invoice_vat_id = fields.Many2one('invoice.vat.data',string='Vat')
    is_vat_data_return = fields.Boolean(string='Vat return')
    vat_qr_data = fields.Char(string='Qr data')
    amount_nhat = fields.Float(string='Amount nhat')
    

            
            
        
    
    