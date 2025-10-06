# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class ProductQRequireReport(models.TransientModel):
    """
        Барааны материалын шаардах тайлан
    """
    _name = "product.require.report"
    _description = "Stock product quantity page"

    company_id = fields.Many2one('res.company', string=u'Компани',readonly=True,
                                default=lambda self: self.env.user.company_id)
    category_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'categ_id':self.category_id.id,
            'product_id': self.product_id.id,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'product.quantity.page',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'product_quantity_page_report',}
        }