# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class SaleOrderCommonReport(models.TransientModel):
    """
        Борлуулалтын тайлан хураангуй
    """
    _name = "sale.order.common.report"
    _description = "Sale order common report"
    
    company_id=fields.Many2one('res.company', string='Company', required=True, 
                               default=lambda self: self.env.user.company_id)
    date_from=fields.Date('Date Start',default=fields.Date.context_today)
    date_to=fields.Date("Date Stop",default=fields.Date.context_today)
    sales_user_id = fields.Many2one('res.users', string='Salesperson')
    target_move = fields.Selection([('posted', 'Posted'), ('all', 'All')],
                                      string='States', default='posted')
    
    

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'target_move': self.target_move,
            'sales_user_id': self.sales_user_id.id,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'sale.order.common.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Sale order common report'}
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 16
                                    })
        txt = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12
                                })

        title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'bold': True,
                                    'font_size': 12,
                                    'bg_color': '#B22222',
                                    'color': 'white'
                                })

        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'text_wrap': True,
                                    'font_size': 12,
                                    'num_format': '#,##0.00'
                                })
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00'
                                })


        data_bold_left = workbook.add_format({
                                    'align': 'left',
                                    'bold': True,
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00'
                                })
        
        data_bold_center = workbook.add_format({
                                    'align': 'center',
                                    'bold': True,
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00'
                                })

        sheet.set_column(0, 5, 15)
        sheet.set_column(6, 6, 40)
        sheet.set_column(7, 17, 15)

        rowx = 1
        sheet.write('A%s'%rowx, u'Захиалгын №', title)
        sheet.write("B%s"%rowx, u'Харилцагчийн №', title)
        sheet.write("C%s"%rowx, u'Харилцагч', title)
        sheet.write("D%s"%rowx, u'Нийт үнэ', title)
        sheet.write("E%s"%rowx, u'НӨАТ', title)
        sheet.write("F%s"%rowx, u'Нийт үнэ НӨАТ', title)
        sheet.write("G%s"%rowx, u'Батлагдсан огноо', title)
        sheet.write("H%s"%rowx, u'Хэрэглэгч', title)
        rowx += 1


        sale_order_obj = self.env['sale.order']
        if data['sales_user_id']:
            if data['target_move'] == 'posted':
                sale_order_id = sale_order_obj.search([
                    ('company_id', '=', data['company_id']),
                    ('date_order', '>=', data['start_date']),
                    ('date_order', '<=', data['end_date']),
                    ('state', 'in', ['sale']),
                    ('user_id', '=', data['sales_user_id']),
                ])
            else:
                sale_order_id = sale_order_obj.search([
                    ('company_id', '=', data['company_id']),
                    ('date_order', '>=', data['start_date']),
                    ('date_order', '<=', data['end_date']),
                    ('state', 'not in', ['cancel']),
                    ('user_id', '=', data['sales_user_id'])
                ])
        else:
            if data['target_move'] == 'posted':
                sale_order_id = sale_order_obj.search([
                    ('company_id', '=', data['company_id']),
                    ('date_order', '>=', data['start_date']),
                    ('date_order', '<=', data['end_date']),
                    ('state', 'in', ['sale'])
                ])
            else:
                sale_order_id = sale_order_obj.search([
                    ('company_id', '=', data['company_id']),
                    ('date_order', '>=', data['start_date']),
                    ('date_order', '<=', data['end_date']),
                    ('state', 'not in', ['cancel'])
                ])
        num = 1

        for line in sale_order_id:
            sheet.write("A%s"%rowx, line.name, data_left)
            sheet.write("B%s"%rowx, "%s"%line.partner_id.code, data_left)
            sheet.write("C%s"%rowx, "%s"%line.partner_id.name, data_left)
            sheet.write("D%s"%rowx, line.amount_untaxed, data_right)
            sheet.write("E%s"%rowx, line.amount_tax, data_right)
            sheet.write("F%s"%rowx, line.amount_total, data_right)
            sheet.write("G%s"%rowx, "%s"%line.date_order, data_right)
            sheet.write("H%s"%rowx, "%s"%line.user_id.name, data_right)

            num +=1
            rowx +=1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()





        



