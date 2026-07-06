# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from datetime import datetime


class SaleOrderNewReport(models.TransientModel):
    """
        Борлуулалтын тайлан
    """
    _name = "sale.order.new.report"
    _inherit = 'xls.report.base'
    _description = "Sale order report"

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    date_from = fields.Date('Date Start', default=fields.Date.context_today)
    date_to = fields.Date("Date Stop", default=fields.Date.context_today)
    sales_user_id = fields.Many2one('res.users', string='Salesperson')
    target_move = fields.Selection([('posted', 'Posted'), ('all', 'All'), ('picked', 'Picked')],
                                   string='States', default='posted', required=True)
    is_license = fields.Boolean(string='License', default=False)
    partner_id = fields.Many2one('res.partner', string='Customer')

    def get_report_data(self):
        data = super(SaleOrderNewReport, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': str(self.date_from),
            'end_date': str(self.date_to),
            'target_move': self.target_move,
            'sales_user_id': self.sales_user_id.id,
            'is_license': self.is_license,
            'partner_id': self.partner_id.id,
        })
        return data

    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'sale.order.new.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Sale order report'}
        }

    def _get_picked_moves(self, line, start_date, end_date):
        return line.move_ids.filtered(
            lambda move: move.state == 'done'
            and move.picking_id
            and move.picking_id.state == 'done'
            and not move.picking_id.return_id
            and move.picking_id.scheduled_date
            and start_date <= move.picking_id.scheduled_date.date() <= end_date
        )

    def _get_picked_delivered_qty(self, line, start_date, end_date):
        delivered_qty = 0.0
        for move in self._get_picked_moves(line, start_date, end_date):
            move_qty = move.quantity if 'quantity' in move._fields else move.quantity_done
            move_uom = move.product_uom or line.product_uom
            delivered_qty += move_uom._compute_quantity(move_qty, line.product_uom)
        return delivered_qty

    def _get_line_delivered_qty_by_picking(self, picking, line):
        delivered_qty = 0.0
        moves = picking.move_ids.filtered(
            lambda move: move.state == 'done' and move.sale_line_id == line
        )
        for move in moves:
            move_qty = move.quantity if 'quantity' in move._fields else move.quantity_done
            move_uom = move.product_uom or line.product_uom
            delivered_qty += move_uom._compute_quantity(move_qty, line.product_uom)
        return delivered_qty

    def _get_picking_amount_total_by_line(self, picking):
        order_lines = picking.move_ids.sale_line_id
        currency = picking.sale_id.currency_id or picking.sale_id.company_id.currency_id
        line_data = []
        tax_base_lines = []
        for line in order_lines:
            delivered_qty = self._get_line_delivered_qty_by_picking(picking, line)
            if not delivered_qty:
                continue

            tax_base_line = line._convert_to_tax_base_line_dict()
            tax_base_line['quantity'] = delivered_qty
            tax_base_lines.append(tax_base_line)
            line_subtotal = line.price_unit * (1 - (line.discount or 0.0) / 100.0) * delivered_qty
            line_data.append((line, line_subtotal))

        if not tax_base_lines:
            return {}

        amount_value = self.env['account.tax']._prepare_tax_totals(tax_base_lines, currency)
        subtotal_sum = sum(line_subtotal for line, line_subtotal in line_data)
        if not subtotal_sum:
            return {line: 0.0 for line, line_subtotal in line_data}

        remaining_amount = amount_value['amount_total']
        amount_by_line = {}
        for line, line_subtotal in line_data[:-1]:
            line_amount = currency.round(amount_value['amount_total'] * line_subtotal / subtotal_sum)
            amount_by_line[line] = amount_by_line.get(line, 0.0) + line_amount
            remaining_amount -= line_amount

        last_line = line_data[-1][0]
        amount_by_line[last_line] = amount_by_line.get(last_line, 0.0) + remaining_amount
        return amount_by_line

    def _get_delivered_amount_total(self, line, start_date, end_date):
        amount_total = 0.0
        for picking in self._get_picked_moves(line, start_date, end_date).mapped('picking_id'):
            amount_total += self._get_picking_amount_total_by_line(picking).get(line, 0.0)
        return amount_total

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

        data_center = workbook.add_format({
            'align': 'center',
            'border': 1,
            'font_size': 12,
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

        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.set_column(0, 7, 15)
        sheet.set_column(8, 8, 40)
        sheet.set_column(9, 17, 15)

        rowx = 1
        sheet.merge_range("A%s:Q%s" % (rowx, rowx), u'Борлуулалтын тайлан дэлгэрэнгүй', title)
        rowx += 1
        sheet.merge_range("A%s:D%s" % (rowx, rowx), u'%s' % (data['company_name']), head)
        sheet.merge_range("O%s:Q%s" % (rowx, rowx), u'Огноо: %s - %s' % (data['start_date'], data['end_date']), head)
        rowx += 2

        sheet.write("A%s" % rowx, u'Мөр', title)
        sheet.write('B%s' % rowx, u'Батлагдсан огноо', title)
        sheet.write("C%s" % rowx, u'Захиалгын №', title)
        sheet.write("D%s" % rowx, u'Харилцагчийн №', title)
        sheet.write("E%s" % rowx, u'Харилцагч', title)
        sheet.write("F%s" % rowx, u'Хэрэглэгч', title)
        sheet.write("G%s" % rowx, u'Барааны №', title)
        sheet.write("H%s" % rowx, u'Барааны бүлэг', title)
        sheet.write("I%s" % rowx, u'Барааны нэр', title)
        sheet.write("J%s" % rowx, u'Нэгж', title)
        sheet.write("K%s" % rowx, u'Захиалгын тоо', title)
        sheet.write("L%s" % rowx, u'Хүргэсэн тоо', title)
        sheet.write("M%s" % rowx, u'Нэгжийн өртөг', title)
        sheet.write("N%s" % rowx, u'Нийт өртөг', title)
        sheet.write("O%s" % rowx, u'Ашиг', title)
        sheet.write("P%s" % rowx, u'Нэгжийн үнэ', title)
        sheet.write("Q%s" % rowx, u'Нийт үнэ', title)
        rowx += 1

        start_date = datetime.strptime(data['start_date'], "%Y-%m-%d").date()
        end_date = datetime.strptime(data['end_date'], "%Y-%m-%d").date()
        sale_order_line_obj = self.env['sale.order.line']
        domain = [
            ('order_id.company_id', '=', data['company_id']),
            ('product_uom_qty', '>', 0),
            ('is_downpayment', '=', False),
            ('order_id.is_license', '=', data['is_license'])
        ]
        if data['target_move'] != 'picked':
            domain.append(('order_id.date_order', '>=', data['start_date']))
            domain.append(('order_id.date_order', '<=', data['end_date']))

        if data['target_move'] == 'posted':
            domain.append(('order_id.state', 'in', ['sale']))
        elif data['target_move'] == 'all':
            domain.append(('order_id.state', 'not in', ['cancel']))
        else:
            domain = [
                ('order_id.state', '=', 'sale'),
                ('is_downpayment', '=', False),
                ('order_id.company_id', '=', data['company_id']),
                ('order_id.is_license', '=', data['is_license'])
            ]
        if data['sales_user_id'] != False:
            domain.append(('order_id.user_id', '=', data['sales_user_id']))
        if data['partner_id'] != False:
            domain.append(('order_id.partner_id', '=', data['partner_id']))
        sale_order_line_id = sale_order_line_obj.search(domain, order='order_date desc')
        if data['target_move'] == 'picked':
            sale_order_line_id = sale_order_line_id.filtered(
                lambda line: self._get_picked_delivered_qty(line, start_date, end_date) > 0
            )
        num = 1

        for line in sale_order_line_id:
            if data['target_move'] == 'picked':
                delivered_qty = self._get_picked_delivered_qty(line, start_date, end_date)
                price_total = self._get_delivered_amount_total(line, start_date, end_date)
                margin = price_total - (line.purchase_price * delivered_qty)
                total_purchase_price = line.purchase_price * delivered_qty
            else:
                delivered_qty = line.product_uom_qty
                price_total = line.price_total
                margin = line.price_total - (line.purchase_price * line.product_uom_qty)
                total_purchase_price = line.purchase_price * line.product_uom_qty
            convert_date = fields.Date.from_string(line.order_id.date_order)
            sheet.write("A%s" % rowx, num, data_center)
            sheet.write("B%s" % rowx, "%s" % convert_date, data_left)
            sheet.write("C%s" % rowx, line.order_id.name, data_left)
            sheet.write("D%s" % rowx, "%s" % line.order_id.partner_id.code, data_left)
            sheet.write("E%s" % rowx, "%s" % line.order_id.partner_id.name, data_left)
            sheet.write("F%s" % rowx, "%s" % line.order_id.user_id.name, data_left)
            sheet.write("G%s" % rowx, "%s" % line.product_id.default_code, data_left)
            sheet.write("H%s" % rowx, "%s" % line.product_id.brand_id.name, data_left)
            sheet.write("I%s" % rowx, line.product_id.name, data_left)
            sheet.write("J%s" % rowx, line.product_uom.name, data_left)
            sheet.write("K%s" % rowx, line.product_uom_qty, data_right)
            sheet.write("L%s" % rowx, delivered_qty, data_right)
            sheet.write("M%s" % rowx, line.purchase_price, data_right)
            sheet.write("N%s" % rowx, total_purchase_price, data_right)
            sheet.write("O%s" % rowx, margin, data_right)
            sheet.write("P%s" % rowx, line.price_unit, data_right)
            sheet.write("Q%s" % rowx, price_total, data_right)
            num += 1
            rowx += 1
        sheet.merge_range('A%s:J%s' % (rowx, rowx), u'Нийт дүн:', data_bold_left)
        sheet.write('K%s' % rowx, '=SUM(K2:K%s)' % (rowx - 1), data_bold_center)
        sheet.write('L%s' % rowx, '=SUM(L2:L%s)' % (rowx - 1), data_bold_center)
        sheet.write('M%s' % rowx, '=SUM(M2:M%s)' % (rowx - 1), data_bold_center)
        sheet.write('N%s' % rowx, '=SUM(N2:N%s)' % (rowx - 1), data_bold_center)
        sheet.write('O%s' % rowx, '=SUM(O2:O%s)' % (rowx - 1), data_bold_center)
        sheet.write('P%s' % rowx, '=SUM(P2:P%s)' % (rowx - 1), data_bold_center)
        sheet.write('Q%s' % rowx, '=SUM(Q2:Q%s)' % (rowx - 1), data_bold_center)

        rowx += 1
        sheet.write("C%s" % (rowx + 3),
                    u"Хянасан ажилтан: ..................................................../                                            /", )
        sheet.write("C%s" % (rowx + 4),
                    u"Тайлан гаргасан: ..................................................../                                            /", )

        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return None
