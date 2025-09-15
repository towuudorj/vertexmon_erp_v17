# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class ProductMarginReport(models.TransientModel):
    """
        Барааны материалын дэлгэрэнгүй тайлан
    """
    _name = "product.margin.report"
    _description = "Stock margin Report - Mongolia"

    date_from = fields.Date(string="Эхлэх огноо", required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string="Дуусах огноо", required=True, default=lambda self: fields.Date.today())
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouse')
    categ_ids = fields.Many2many('product.category', string='Category')
    location_ids = fields.Many2many('stock.location', string='Location')
    product_ids = fields.Many2many('product.product', string='Product')
    group_by = fields.Selection([('category', 'Category'),
                                 ('product', 'Product')],
                                string='Group by', default='category', required=True)
    
    
    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'location_ids':self.location_ids.ids,
            'warehouse_ids': self.warehouse_ids.ids,
            'categ_ids':self.categ_ids.ids,
            'product_ids': self.product_ids.ids,
            'group_by': self.group_by,

        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'product.margin.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'product_margin_report'}
        }
    
    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        head = workbook.add_format({
                                    'align': 'right', 
                                    'font_size': 12
                                    })
        head_title = workbook.add_format({
                                    'align': 'center', 
                                    'font_size': 16,
                                    'bold': True
                                    })
        txt_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'bold': True
                                })
        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        data_left_bold = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'bold': True,
                                    })
        
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        data_center_bold = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'bold': True,
                                    })
        
        
        
