# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleReport(models.Model):
    _inherit = "sale.report"
    
    brand_id = fields.Many2one('product.brand', string='Brand')
    distributor_ids = fields.Many2one('res.partner', string='Distributor')


    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['brand_id'] = "t.brand_id"
        res['distributor_ids'] = "t.distributor_ids"
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            t.brand_id,
            t.distributor_ids"""
        return res

