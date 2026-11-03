# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
import pytz
from datetime import datetime, time, timedelta

class PurchaseOrderCommonReport(models.TransientModel):
    """
        Худалдан авалтын тайлан хураангуй
    """
    _name = "purchase.summary.report"
    _inherit = "xls.report.base"
    _description = "Purchase summary report"
    
    company_id=fields.Many2one('res.company', string='Company', required=True, 
                               default=lambda self: self.env.user.company_id)
    date_from=fields.Date('Date Start',default=fields.Date.context_today)
    date_to=fields.Date("Date Stop",default=fields.Date.context_today)
    purchase_user_id = fields.Many2one('res.users', string='Purchase manager')
    target_move = fields.Selection([('posted', 'Posted'), ('all', 'All'), ('delivered', 'Delivered')],
                                      string='States', default='posted')
    order_by_p_order = fields.Boolean('Order By Purchase Order')

    
    

    def get_report_data(self):
        data = super(PurchaseOrderCommonReport, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': str(self.date_from),
            'end_date': str(self.date_to),
            'target_move': self.target_move,
            'purchase_user_id': self.purchase_user_id.id if self.purchase_user_id else False,
            'order_by_p_order': self.order_by_p_order,
        })
        return data

    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'purchase.summary.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Purchase order common report'}
        }

    def get_xlsx_report(self, data, response, get_file=False):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0)
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
        title_no_border = workbook.add_format({
                                    'align': 'center',
                                    'border': 0,
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
        datetime_format = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'text_wrap': True,
                                    'font_size': 12,
                                    'num_format': 'yyyy-mm-dd hh:mm'
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
        sheet.merge_range("A%s:J%s"%(rowx,rowx), u'Худалдан авалтын тайлан хураангуй', title_no_border)
        sheet.merge_range("A%s:C%s"%(rowx+1,rowx+1), u'%s'%(data['company_name']), title_no_border)
        sheet.merge_range("D%s:G%s"%(rowx+1,rowx+1), '', title_no_border)
        sheet.merge_range("H%s:J%s"%(rowx+1,rowx+1), u'Огноо: %s - %s'%(data['start_date'],data['end_date']), title_no_border)
        rowx += 3
        sheet.write("A%s"%rowx, u'Батлагдсан огноо', title)
        sheet.write('B%s'%rowx, u'Захиалгын №', title)
        sheet.write("C%s"%rowx, u'Харилцагчийн №', title)
        sheet.write("D%s"%rowx, u'Харилцагч', title)
        sheet.write("E%s"%rowx, u'Валют', title)
        sheet.write("F%s"%rowx, u'Нийт үнэ', title)
        sheet.write("G%s"%rowx, u'НӨАТ', title)
        sheet.write("H%s"%rowx, u'Нийт үнэ НӨАТ', title)
        sheet.write("I%s"%rowx, u'Нийт үнэ НӨАТ /₮/', title)
        sheet.write("J%s"%rowx, u'Хэрэглэгч', title)
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
            # date_approve нь UTC-ээр хадгалагддаг тул хэрэглэгчийн цагийн бүсээр өдрийн хил хязгаарыг тооцно
            user_tz = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
            start_dt = user_tz.localize(datetime.combine(start_date, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
            end_dt = user_tz.localize(datetime.combine(end_date + timedelta(days=1), time.min)).astimezone(pytz.utc).replace(tzinfo=None)
            domain.append(('date_approve', '>=', start_dt))
            domain.append(('date_approve', '<', end_dt))

        if data['purchase_user_id']:
            domain.append(('user_id', '=', data['purchase_user_id']))
        if data['target_move'] in ['posted', 'delivered']:
            domain.append(('state', 'in', ['purchase']))
        else:
            domain.append(('state', 'not in', ['cancel']))

        purchase_order_id = purchase_order_obj.search(domain, order='date_approve asc')
        picking_total_value_dict = []
        if is_picked:
            for purchase in purchase_order_id:
                for picking_id in purchase.picking_ids:
                    if picking_id.state == 'done' and picking_id.picking_type_code in ('incoming', 'outgoing') and start_date <= fields.Datetime.context_timestamp(self, picking_id.date_done).date() <= end_date:
                        # Орлого (буцаасныг дахин авсан орлого орно) +, нийлүүлэгч рүү буцаасан зарлага −
                        is_return = picking_id.picking_type_code == 'outgoing'
                        sign = -1 if is_return else 1
                        picking_purchase_line_id = purchase.order_line.filtered(lambda l: any(move.picking_id == picking_id for move in l.move_ids))
                        total_without_noat = 0
                        total_noat = 0
                        total_with_noat_mnt = 0
                        total_with_noat = 0
                        for line in picking_purchase_line_id:
                            currency_rate = self.env['res.currency.rate'].search([('company_id','=',purchase.company_id.id),('currency_id','=',line.currency_id.id),('name','=',fields.Datetime.context_timestamp(self, picking_id.date_done).date())])
                            curr_rate = currency_rate.inverse_company_rate if currency_rate else purchase.currency_rate
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
                                total_with_noat_mnt += res['total_included'] * curr_rate
                                total_noat += res['total_included'] - res['total_excluded']
                            else:
                                total = price_unit * sum(line.move_ids.filtered(lambda m: m.picking_id == picking_id).mapped('quantity'))
                                total_without_noat += total
                                total_with_noat += total
                                total_with_noat_mnt += total * curr_rate
                                total_noat += 0

                        picking_total_value_dict.append({
                            'currency' : purchase.currency_id.name,
                            'total_without_noat' : sign * total_without_noat,
                            'total_noat': sign * total_noat,
                            'total_with_noat': sign * total_with_noat,
                            'total_with_noat_mnt': sign * total_with_noat_mnt,
                            'is_return': is_return,
                            'date_done': picking_id.date_done,
                            'order_id': purchase
                        })

        num = 1

        total_with_noat_mnt = 0.0
        if is_picked:
            sorted_data = []
            if picking_total_value_dict:
                if data['order_by_p_order']:
                    sorted_data = sorted(picking_total_value_dict, key=lambda x: (x["order_id"].name or "", x["date_done"] or datetime.min))
                else:
                    sorted_data = sorted(picking_total_value_dict, key=lambda x: x["date_done"])
            for item in sorted_data:
                sheet.write("A%s" % rowx, fields.Datetime.context_timestamp(self, item['date_done']).replace(tzinfo=None), datetime_format)
                sheet.write("B%s" % rowx, u'%s (Буцаалт)' % item['order_id'].name if item['is_return'] else item['order_id'].name, data_left)
                sheet.write("C%s" % rowx, "%s" % item['order_id'].partner_id.code, data_left)
                sheet.write("D%s" % rowx, "%s" % item['order_id'].partner_id.name, data_left)
                sheet.write("E%s" % rowx, item['currency'], data_right)
                sheet.write("F%s" % rowx, item['total_without_noat'], data_right)
                sheet.write("G%s" % rowx, item['total_noat'], data_right)
                sheet.write("H%s" % rowx, item['total_with_noat'], data_right)
                sheet.write("I%s" % rowx, item['total_with_noat_mnt'], data_right)
                sheet.write("J%s" % rowx, "%s" % item['order_id'].user_id.name, data_right)
                total_with_noat_mnt += item['total_with_noat_mnt']
                num += 1
                rowx += 1
        else:
            for line in purchase_order_id:
                convert_date = fields.Datetime.context_timestamp(self, line.date_approve).date()
                sheet.write("A%s"%rowx, "%s"%convert_date, data_right)
                sheet.write("B%s"%rowx, line.name, data_left)
                sheet.write("C%s"%rowx, "%s"%line.partner_id.code, data_left)
                sheet.write("D%s"%rowx, "%s"%line.partner_id.name, data_left)
                sheet.write("E%s"%rowx, line.currency_id.name, data_right)
                sheet.write("F%s"%rowx, line.amount_untaxed, data_right)
                sheet.write("G%s"%rowx, line.amount_tax, data_right)
                sheet.write("H%s"%rowx, line.amount_total, data_right)
                sheet.write("I%s"%rowx, line.amount_total * line.currency_rate, data_right)
                sheet.write("J%s"%rowx, "%s"%line.user_id.name, data_right)
                total_with_noat_mnt += line.amount_total * line.currency_rate
                num +=1
                rowx +=1
        sheet.merge_range("A%s:E%s"%(rowx,rowx), u'Нийт дүн:', data_bold_center)
        sheet.write("F%s"%rowx, '', data_bold_center)
        sheet.write("G%s"%rowx, '', data_bold_center)
        sheet.write("H%s"%rowx, '', data_bold_center)
        sheet.write("I%s"%rowx, total_with_noat_mnt, data_bold_center)
        sheet.write("J%s"%rowx, '', data_bold_center)


        rowx += 1
        sheet.write("C%s"%(rowx + 3), u"Хянасан ажилтан: ..................................................../                                            /",)
        sheet.write("C%s"%(rowx + 4), u"Тайлан гаргасан: ..................................................../                                            /",)


        workbook.close()
        if get_file:
            output.seek(0)
            return output.getvalue()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


