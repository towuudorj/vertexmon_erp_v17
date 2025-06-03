# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools


class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    tax_type = fields.Selection([('VAT_ABLE','НӨАТ тооцох бүтээгдэхүүн, үйлчилгээ'),
                                ('VAT_FREE','НӨАТ-өөс чөлөөлөгдөх бүтээгдэхүүн, үйлчилгээ'),
                                ('VAT_ZERO','НӨАТ-н 0 хувь тооцох бүтээгдэхүүн, үйлчилгээ'),
                                ('NO_VAT','Монгол улсын хилийн гадна борлуулсан бүтээгдэхүүн үйлчилгээ')],
                                string='Tax type',  default='VAT_ABLE')
    barcode_type = fields.Selection([('UNDEFINED','Баркодгүй бараа, ажил, үйлчилгээ'),
                                    ('GS1','GS1 зураасан код'),
                                    ('ISBN','ISBN зураасан код')],string='Barcode type', default='UNDEFINED')
    tax_product_code = fields.Char(string='Tax product code')
    vat_categ_id = fields.Many2one('vat.category',string='Vat category')
    is_send_tax = fields.Boolean(string=u'Is send tax product')
    
    @api.onchange('vat_categ_id')
    def _vat_categ(self):
        for vat in self:
            if vat.vat_categ_id:
                vat.tax_product_code = vat.vat_categ_id.code
    
    