# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class PurchaseProductIncomeReport(models.TransientModel):
    """
        Барааны материалын орлого тайлан
    """
    _name = "purchase.product.income.report"
    _description = "Purchase product income"

    company_id = fields.Many2one('res.company', string=u'Компани',readonly=True,
                                default=lambda self: self.env.user.company_id)
    category_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')
    start_date = fields.Date(string='Start date')
    end_date = fields.Date('End date')
    type = fields.Selection([('purchase','Purchase income'),
                             ('internal','Internal income'),
                             ('return','Return income')
                             ('all', 'All')],string='Type', defualt='purchase')


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'categ_id':self.category_id.id,
            'product_id': self.product_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'purchase.product.income.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'purchase_product_income_report',}
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
        
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' % (data['company_name']), data_left)
        
        sheet.merge_range('A2:G2', u'Барааны орлогын тайлан', head_title)
        

        rowx = 4
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 10, 20)

        sheet.write('A%s'%(rowx), u'Д/д', txt_center)
        sheet.write('B%s'%(rowx), u'Барааны нэр', txt_center)
        sheet.write('C%s'%(rowx), u'Барааны код', txt_center)
        sheet.write('D%s'%(rowx), u'Дотоод код', txt_center)
        sheet.write('E%s'%(rowx), u'Барааны хэмжих нэгж', txt_center)
        sheet.write('F%s'%(rowx), u'Баримтын дугаар', txt_center)
        sheet.write('G%s'%(rowx), u'Худалдан авалтын дугаар', txt_center)
        sheet.write('H%s'%(rowx), u'Орлогын тоо', txt_center)        



        