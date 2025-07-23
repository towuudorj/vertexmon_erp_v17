# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class SaleOrderNewReport(models.TransientModel):
    """
        Борлуулалтын тайлан
    """
    _name = "sale.order.new.report"
    _description = "Sale order report"
    
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
            'data': {'model': 'sale.order.new.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Sale order report'}
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
        sheet.write("B%s"%rowx, u'Мөр', title)
        sheet.write("C%s"%rowx, u'Харилцагчийн №', title)
        sheet.write("D%s"%rowx, u'Харилцагч', title)
        sheet.write("E%s"%rowx, u'Барааны №', title)
        sheet.write("F%s"%rowx, u'Барааны бүлэг', title)
        sheet.write("G%s"%rowx, u'Барааны нэр', title)
        sheet.write("H%s"%rowx, u'Нэгжийн үнэ', title)
        sheet.write("I%s"%rowx, u'Тоо', title)
        sheet.write("J%s"%rowx, u'Нэгж', title)
        sheet.write("K%s"%rowx, u'Нийт үнэ', title)
        sheet.write("L%s"%rowx, u'Батлагдсан огноо', title)
        sheet.write("M%s"%rowx, u'Нэгжийн өртөг', title)
        sheet.write("N%s"%rowx, u'Нийт өртөг', title)
        sheet.write("O%s"%rowx, u'Ашиг', title)
        sheet.write("P%s"%rowx, u'Хэрэглэгч', title)
        rowx += 1


        sale_order_line_obj = self.env['sale.order.line']
        if data['sales_user_id']:
            if data['target_move'] == 'posted':
                sale_order_line_id = sale_order_line_obj.search([
                    ('order_id.company_id', '=', data['company_id']),
                    ('order_id.date_order', '>=', data['start_date']),
                    ('order_id.date_order', '<=', data['end_date']),
                    ('order_id.state', 'in', ['sale']),
                    ('order_id.user_id', '=', data['sales_user_id']),
                ])
            else:
                sale_order_line_id = sale_order_line_obj.search([
                    ('order_id.company_id', '=', data['company_id']),
                    ('order_id.date_order', '>=', data['start_date']),
                    ('order_id.date_order', '<=', data['end_date']),
                    ('order_id.state', 'not in', ['cancel']),
                    ('order_id.user_id', '=', data['sales_user_id'])
                ])
        else:
            if data['target_move'] == 'posted':
                sale_order_line_id = sale_order_line_obj.search([
                    ('order_id.company_id', '=', data['company_id']),
                    ('order_id.date_order', '>=', data['start_date']),
                    ('order_id.date_order', '<=', data['end_date']),
                    ('order_id.state', 'in', ['sale'])
                ])
            else:
                sale_order_line_id = sale_order_line_obj.search([
                    ('order_id.company_id', '=', data['company_id']),
                    ('order_id.date_order', '>=', data['start_date']),
                    ('order_id.date_order', '<=', data['end_date']),
                    ('order_id.state', 'not in', ['cancel'])
                ])
        num = 1

        for line in sale_order_line_id:
            margin = line.price_total - (line.purchase_price * line.product_uom_qty)
            sheet.write("A%s"%rowx, line.order_id.name, data_left)
            sheet.write("B%s"%rowx, num, data_right)
            sheet.write("C%s"%rowx, "%s"%line.order_id.partner_id.code, data_left)
            sheet.write("D%s"%rowx, "%s"%line.order_id.partner_id.name, data_left)
            sheet.write("E%s"%rowx, "%s"%line.product_id.default_code, data_left)
            sheet.write("F%s"%rowx, "%s"%line.product_id.brand_id.name, data_left)
            sheet.write("G%s"%rowx, "%s"%line.product_id.name, data_left)
            sheet.write("H%s"%rowx, line.price_unit, data_right)
            sheet.write("I%s"%rowx, line.product_uom_qty, data_right)
            sheet.write("J%s"%rowx, "%s"%line.product_uom.name, data_right)
            sheet.write("K%s"%rowx, line.price_total, data_right)
            sheet.write("L%s"%rowx, "%s"%line.order_id.date_order, data_right)
            sheet.write("M%s"%rowx, line.purchase_price, data_right)
            sheet.write("N%s"%rowx, line.purchase_price*line.product_uom_qty, data_right)
            sheet.write("O%s"%rowx, margin, data_right)
            sheet.write("P%s"%rowx, "%s"%line.order_id.user_id.name, data_right)

            num +=1
            rowx +=1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()





        





