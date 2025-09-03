# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class PurchaseOrderCommonReport(models.TransientModel):
    """
        Худалдан авалтын тайлан хураангуй
    """
    _name = "purchase.summary.report"
    _description = "Purchase summary report"
    
    company_id=fields.Many2one('res.company', string='Company', required=True, 
                               default=lambda self: self.env.user.company_id)
    date_from=fields.Date('Date Start',default=fields.Date.context_today)
    date_to=fields.Date("Date Stop",default=fields.Date.context_today)
    purchase_user_id = fields.Many2one('res.users', string='Purchase manager')
    target_move = fields.Selection([('posted', 'Posted'), ('all', 'All')],
                                      string='States', default='posted')

    
    

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'target_move': self.target_move,
            'purchase_user_id': self.purchase_user_id.id,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'purchase.summary.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Purchase order common report'}
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
                                    'bg_color': '#ead1c0',
                                    'color': 'black'
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
        sheet.merge_range("A%s:H%s"%(rowx,rowx), u'Худалдан авалтын тайлан хураангуй', title)
        sheet.merge_range("A%s:C%s"%(rowx+1,rowx+1), u'%s'%(data['company_name']), title)
        sheet.merge_range("F%s:H%s"%(rowx+1,rowx+1), u'Огноо: %s - %s'%(data['start_date'],data['end_date']), title)
        rowx += 3
        sheet.write("A%s"%rowx, u'Батлагдсан огноо', title)
        sheet.write('B%s'%rowx, u'Захиалгын №', title)
        sheet.write("C%s"%rowx, u'Харилцагчийн №', title)
        sheet.write("D%s"%rowx, u'Харилцагч', title)
        sheet.write("E%s"%rowx, u'Нийт үнэ', title)
        sheet.write("F%s"%rowx, u'НӨАТ', title)
        sheet.write("G%s"%rowx, u'Нийт үнэ НӨАТ', title)
        sheet.write("H%s"%rowx, u'Хэрэглэгч', title)
        rowx += 1


        purchase_order_obj = self.env['purchase.order']
        if data['purchase_user_id']:
            if data['target_move'] == 'posted':
                purchase_order_id = purchase_order_obj.search([
                    ('company_id', '=', data['company_id']),
                    ('date_order', '>=', data['start_date']),
                    ('date_order', '<=', data['end_date']),
                    ('state', 'in', ['purchase']),
                    ('user_id', '=', data['purchase_user_id']),
                    ('receipt_status', '!=', 'pending')
                ],order='date_order asc')
            else:
                purchase_order_id = purchase_order_obj.search([
                    ('company_id', '=', data['company_id']),
                    ('date_order', '>=', data['start_date']),
                    ('date_order', '<=', data['end_date']),
                    ('state', 'not in', ['cancel']),
                    ('user_id', '=', data['purchase_user_id']),
                    ('receipt_status', '!=', 'pending')
                ],order='date_order asc')
        else:
            if data['target_move'] == 'posted':
                purchase_order_id = purchase_order_obj.search([
                    ('company_id', '=', data['company_id']),
                    ('date_order', '>=', data['start_date']),
                    ('date_order', '<=', data['end_date']),
                    ('state', 'in', ['purchase']),
                    ('receipt_status', '!=', 'pending')
                ],order='date_order asc')
            else:
                purchase_order_id = purchase_order_obj.search([
                    ('company_id', '=', data['company_id']),
                    ('date_order', '>=', data['start_date']),
                    ('date_order', '<=', data['end_date']),
                    ('state', 'not in', ['cancel']),
                    ('receipt_status', '!=', 'pending')
                ],order='date_order asc')
        num = 1

        total_amount_untaxed = 0.0
        total_amount_tax = 0.0
        total_amount_total = 0.0
        for line in purchase_order_id:
            convert_date = fields.Date.from_string(line.date_order)
            sheet.write("A%s"%rowx, "%s"%convert_date, data_right)
            sheet.write("B%s"%rowx, line.name, data_left)
            sheet.write("C%s"%rowx, "%s"%line.partner_id.code, data_left)
            sheet.write("D%s"%rowx, "%s"%line.partner_id.name, data_left)
            sheet.write("E%s"%rowx, line.amount_untaxed, data_right)
            sheet.write("F%s"%rowx, line.amount_tax, data_right)
            sheet.write("G%s"%rowx, line.amount_total, data_right)
            sheet.write("H%s"%rowx, "%s"%line.user_id.name, data_right)
            total_amount_untaxed +=line.amount_untaxed
            total_amount_tax +=line.amount_tax
            total_amount_total +=line.amount_total
            num +=1
            rowx +=1
        sheet.merge_range("A%s:D%s"%(rowx,rowx), u'Нийт дүн:', data_bold_left)
        sheet.write("E%s"%rowx, total_amount_untaxed, data_bold_center)
        sheet.write("F%s"%rowx, total_amount_tax, data_bold_center)
        sheet.write("G%s"%rowx, total_amount_total, data_bold_center)
        sheet.write("H%s"%rowx, '', data_bold_center)


        rowx += 1
        sheet.write("C%s"%(rowx + 3), u"Хянасан ажилтан: ..................................................../                                            /",)
        sheet.write("C%s"%(rowx + 4), u"Тайлан гаргасан: ..................................................../                                            /",)


        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


