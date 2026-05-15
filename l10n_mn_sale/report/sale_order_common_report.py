# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from datetime import datetime

class SaleOrderCommonReport(models.TransientModel):
    """
        Борлуулалтын тайлан хураангуй
    """
    _name = "sale.order.common.report"
    _inherit = 'xls.report.base'
    _description = "Sale order common report"
    
    company_id=fields.Many2one('res.company', string='Company', required=True, 
                               default=lambda self: self.env.user.company_id)
    date_from=fields.Date('Date Start',default=fields.Date.context_today)
    date_to=fields.Date("Date Stop",default=fields.Date.context_today)
    sales_user_id = fields.Many2one('res.users', string='Salesperson')
    target_move = fields.Selection([('posted', 'Posted'), ('all', 'All'), ('picked', 'Picked')],
                                    required=True, string='States', default='posted')
    is_license = fields.Boolean(string='License', default=False)

    def get_report_data(self):
        data = super(SaleOrderCommonReport, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': str(self.date_from),
            'end_date': str(self.date_to),
            'target_move': self.target_move,
            'sales_user_id': self.sales_user_id.id,
            'is_license': self.is_license,
        })
        return data
    

    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'sale.order.common.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Sale order common report'}
        }

    def get_xlsx_report(self, data, response, get_file=False):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 12
                                    })

        title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'bold': True,
                                    'font_size': 12,
                                    'bg_color': '#FBCEB1',
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
        datetime_format = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'text_wrap': True,
                                    'font_size': 12,
                                    'num_format': 'yyyy-mm-dd hh:mm'
        })
        data_bold_center = workbook.add_format({
                                    'align': 'center',
                                    'bold': True,
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00'
                                })
        data_center = workbook.add_format({
            'align': 'center',
            'border': 1,
            'font_size': 12,
        })
        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.set_column(0, 0, 5)
        sheet.set_column(1, 9, 18)

        is_picked = data['target_move'] == 'picked'

        rowx = 3
        colly = 0
        sheet.write(rowx, colly, u'Мөр', title)
        colly += 1
        sheet.write(rowx, colly, u'Батлагдсан огноо', title)
        colly += 1
        sheet.write(rowx, colly, u'Захиалгын №', title)
        colly += 1
        if is_picked:
            sheet.write(rowx, colly, u'Хүргэлтийн №', title)
            colly += 1
        sheet.write(rowx, colly, u'Харилцагчийн №', title)
        colly += 1
        sheet.write(rowx, colly, u'Харилцагч', title)
        colly += 1
        sheet.write(rowx, colly, u'Хэрэглэгч', title)
        colly += 1
        sheet.write(rowx, colly, u'Нийт үнэ', title)
        colly += 1
        sheet.write(rowx, colly, u'НӨАТ', title)
        colly += 1
        sheet.write(rowx, colly, u'Нийт үнэ (НӨАТ-тай)', title)

        rowx += 2

        sheet.merge_range(0, 0, 0, colly, u'Борлуулалтын тайлан хураангуй', title)
        sheet.merge_range(1, 0, 1, 2, u'%s'%(data['company_name']), head)
        sheet.merge_range(1, colly-1, 1, colly, u'Огноо: %s - %s'%(data['start_date'],data['end_date']), head)

        start_date = datetime.strptime(data['start_date'], "%Y-%m-%d").date()
        end_date = datetime.strptime(data['end_date'], "%Y-%m-%d").date()
        sale_order_obj = self.env['sale.order']
        domain = [
            ('company_id', '=', data['company_id']),
            ('is_license','=', data['is_license'])
        ]

        if not is_picked:
            domain.append(('date_order', '>=', data['start_date']))
            domain.append(('date_order', '<=', data['end_date']))

        if data['sales_user_id']:
            domain.append(('user_id', '=', data['sales_user_id']))

        if data['target_move'] in ['posted', 'picked']:
            domain.append(('state', '=', 'sale'))

        sale_order_id = sale_order_obj.search(domain, order='date_order asc, name asc')

        picking_total_value_dict = []
        if is_picked:
            picking_ids = sale_order_id.mapped('picking_ids').filtered(lambda p: start_date <= p.scheduled_date.date() <= end_date and p.state=='done' and not p.return_id)
            for picking in picking_ids:
                picking_total_value_dict.append({
                    'sale_order_id': picking.sale_id,
                    'picking_id': picking,
                    'order_line_ids': picking.move_ids.sale_line_id
                })
            # picking_ids = picking_ids.ids if picking_ids else []
            # temp_sale_order = sale_order_obj
            # if picking_ids:
            #     for sale_line in sale_order_id:
            #         for picking_id in sale_line.picking_ids:
            #             if picking_id.id in picking_ids:
            #                 temp_sale_order |= sale_line
            #                 break
            #     sale_order_id = temp_sale_order
            # else:
            #     sale_order_id = []

        total_amount_untaxed = 0.0
        total_amount_tax = 0.0
        total_amount_total = 0.0
        num = 1
        if is_picked:
            amount_untaxed = 0
            amount_tax = 0
            amount_total = 0
            sorted_data = []
            if picking_total_value_dict:
                picking_total_value_dict = sorted(picking_total_value_dict, key=lambda x: x['picking_id'].date_done)
            for line in picking_total_value_dict:
                order_lines = line['order_line_ids']
                # filtered(lambda x: not x.display_type and not x.is_downpayment)
                amount_value = self.env['account.tax']._prepare_tax_totals(
                    [x._convert_to_tax_base_line_dict() for x in order_lines],
                    line['sale_order_id'].currency_id or line['sale_order_id'].company_id.currency_id
                )
                amount_untaxed = amount_value['amount_untaxed']
                amount_tax = amount_value['amount_total'] - amount_value['amount_untaxed']
                amount_total =  amount_value['amount_total']
                if amount_untaxed == 0 and amount_total == 0:
                    continue
                # convert_date = fields.Date.from_string(line['sale_order_id'].date_order)
                sheet.write("A%s" % rowx, num, data_center)
                sheet.write("B%s" % rowx, line['picking_id'].date_done, datetime_format)
                sheet.write("C%s" % rowx, line['sale_order_id'].name, data_left)
                sheet.write("D%s" % rowx, line['picking_id'].name, data_left)
                sheet.write("E%s" % rowx, line['sale_order_id'].partner_id.code, data_left)
                sheet.write("F%s" % rowx, line['sale_order_id'].partner_id.name, data_left)
                sheet.write("G%s" % rowx, line['sale_order_id'].user_id.name, data_left)
                sheet.write("H%s" % rowx, amount_untaxed, data_right)
                sheet.write("I%s" % rowx, amount_tax, data_right)
                sheet.write("J%s" % rowx, amount_total, data_right)

                total_amount_untaxed += amount_untaxed
                total_amount_tax += amount_tax
                total_amount_total += amount_total

                num +=1
                rowx +=1
        else:
            for line in sale_order_id:
                convert_date = fields.Date.from_string(line.date_order)
                sheet.write("A%s"%rowx, num, data_center)
                sheet.write("B%s"%rowx, "%s"%convert_date, data_left)
                sheet.write("C%s"%rowx, line.name, data_left)
                sheet.write("D%s"%rowx, line.partner_id.code, data_left)
                sheet.write("E%s"%rowx, line.partner_id.name, data_left)
                sheet.write("F%s"%rowx, line.user_id.name, data_left)
                sheet.write("G%s"%rowx, line.amount_untaxed if not is_picked else amount_untaxed, data_right)
                sheet.write("H%s"%rowx, line.amount_tax if not is_picked else amount_tax, data_right)
                sheet.write("I%s"%rowx, line.amount_total if not is_picked else amount_total, data_right)

                total_amount_untaxed +=line.amount_untaxed
                total_amount_tax +=line.amount_tax
                total_amount_total +=line.amount_total

                num +=1
                rowx +=1
        rowx -= 1
        sheet.merge_range(rowx, 0, rowx, colly-3, u'Нийт дүн:', data_bold_center)
        sheet.write(rowx, colly-2, total_amount_untaxed, data_bold_center)
        sheet.write(rowx, colly-1, total_amount_tax, data_bold_center)
        sheet.write(rowx, colly, total_amount_total, data_bold_center)


        rowx += 1
        sheet.write("C%s"%(rowx + 3), u"Хянасан ажилтан: ..................................................../                                            /",)
        sheet.write("C%s"%(rowx + 4), u"Тайлан гаргасан: ..................................................../                                            /",)


        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return





        



