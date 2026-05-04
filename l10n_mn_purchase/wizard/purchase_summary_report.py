# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from datetime import datetime

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
    target_move = fields.Selection([('posted', 'Posted'), ('all', 'All'), ('delivered', 'Delivered')],
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

        sheet.set_column(0, 17, 18)
        sheet.set_column(3, 3, 25)
        sheet.set_column(6, 6, 20)
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

        start_date = datetime.strptime(data['start_date'], "%Y-%m-%d").date()
        end_date = datetime.strptime(data['end_date'], "%Y-%m-%d").date()

        is_picked = data['target_move'] == 'delivered'
        purchase_order_obj = self.env['purchase.order']

        domain = [
                    ('company_id', '=', data['company_id']),
                    ('state', 'in', ['purchase']),
                    ('receipt_status', '!=', 'pending')
                ]
        if not is_picked:
            domain.append(('date_approve', '>=', data['start_date']))
            domain.append(('date_approve', '<=', data['end_date']))

        if data['purchase_user_id']:
            domain.append(('user_id', '=', data['purchase_user_id']))
        if data['target_move'] in ['posted', 'delivered']:
            domain.append(('state', 'in', ['purchase']))
        else:
            domain.append(('state', 'not in', ['cancel']))

        purchase_order_id = purchase_order_obj.search(domain, order='date_approve asc')
        picking_total_value_dict = []
        if is_picked:
            temp_purchase_order = purchase_order_obj
            for purchase in purchase_order_id:
                for picking_id in purchase.picking_ids:
                    if start_date <= picking_id.date_done.date() <= end_date and picking_id.state == 'done' and not picking_id.return_id:
                        temp_purchase_order |= purchase
                        picking_purchase_line_id = purchase.order_line.filtered(lambda l: any(move.picking_id == picking_id for move in l.move_ids))
                        total_without_noat = 0
                        total_noat = 0
                        total_with_noat = 0
                        for line in picking_purchase_line_id:
                            price_unit = line.price_unit
                            if line.discount:
                                price_unit -= price_unit / 100 * line.discount
                            if line.taxes_id:
                                res = line.taxes_id.compute_all(
                                    price_unit,
                                    currency=purchase.currency_id,
                                    quantity=sum(line.move_ids.filtered(lambda m: m.picking_id == picking_id).mapped('quantity')),
                                    product=line.product_id,
                                    partner=purchase.partner_id,
                                )
                                total_without_noat += res['total_excluded']
                                total_with_noat += res['total_included']
                                total_noat += res['total_included'] - res['total_excluded']
                            else:
                                total = price_unit * sum(line.move_ids.filtered(lambda m: m.picking_id == picking_id).mapped('quantity'))
                                total_without_noat += total
                                total_with_noat += total
                                total_noat += 0

                        picking_total_value_dict.append({
                            'total_without_noat' : total_without_noat,
                            'total_noat': total_noat,
                            'total_with_noat': total_with_noat,
                            'date_done': picking_id.date_done.date(),
                            'order_id': purchase
                        })

            purchase_order_id = temp_purchase_order

        num = 1
        
        total_amount_untaxed = 0.0
        total_amount_tax = 0.0
        total_amount_total = 0.0
        if is_picked:
            sorted_data = []
            if picking_total_value_dict:
                sorted_data = sorted(picking_total_value_dict, key=lambda x: x["date_done"])
            for item in sorted_data:
                sheet.write("A%s" % rowx, "%s" % item['date_done'], data_right)
                sheet.write("B%s" % rowx, item['order_id'].name, data_left)
                sheet.write("C%s" % rowx, "%s" % item['order_id'].partner_id.code, data_left)
                sheet.write("D%s" % rowx, "%s" % item['order_id'].partner_id.name, data_left)
                sheet.write("E%s" % rowx, item['total_without_noat'], data_right)
                sheet.write("F%s" % rowx, item['total_noat'], data_right)
                sheet.write("G%s" % rowx, item['total_with_noat'], data_right)
                sheet.write("H%s" % rowx, "%s" % item['order_id'].user_id.name, data_right)
                total_amount_untaxed += item['total_without_noat']
                total_amount_tax += item['total_noat']
                total_amount_total += item['total_with_noat']
                num += 1
                rowx += 1
        else:
            for line in purchase_order_id:
                convert_date = fields.Date.from_string(line.date_approve)
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


