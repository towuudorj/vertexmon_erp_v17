# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import api, fields, models
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
    target_move = fields.Selection([('posted', 'Posted'), ('all', 'All'), ('picked', 'Picked'),
                                    ('invoiced', 'Орлогын данс (санхүүгийн бичилт)')],
                                   string='States', default='posted', required=True)
    is_license = fields.Boolean(string='License', default=False)
    partner_id = fields.Many2one('res.partner', string='Customer')
    account_ids = fields.Many2many('account.account', string='Орлогын данс',
                                   default=lambda self: self._default_account_ids(),
                                   help='Орлого үр дүнгийн тайлангийн "Борлуулалтын орлого (цэвэр)" мөрийн дансууд.')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.account_ids = self._default_account_ids(self.company_id)

    def _default_account_ids(self, company=None):
        account_obj = self.env['account.account']
        company = company or self.env.company
        # Орлого үр дүнгийн тайлантай ижил ангиллын дансууд (l10n_mn_account_report суусан үед)
        if 'income_id' in account_obj._fields:
            accounts = account_obj.search([('company_id', '=', company.id),
                                           ('income_id.name', 'ilike', 'Борлуулалтын орлого')])
            if accounts:
                return accounts
        return account_obj.search([('company_id', '=', company.id), ('code', '=like', '51%'),
                                   ('account_type', 'in', ('income', 'income_other'))])

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
            'account_ids': self.account_ids.ids,
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

    def _get_move_sale_line(self, move):
        return move.sale_line_id or move.origin_returned_move_id.sale_line_id

    def _get_period_pickings(self, line, start_date, end_date):
        return line.order_id.picking_ids.filtered(
            lambda picking: picking.state == 'done'
            and picking.scheduled_date
            and start_date <= picking.scheduled_date.date() <= end_date
        )

    def _get_picking_order_lines(self, picking):
        return picking.move_ids.mapped('sale_line_id') | picking.move_ids.mapped('origin_returned_move_id.sale_line_id')

    def _get_picked_moves(self, line, start_date, end_date):
        return self._get_period_pickings(line, start_date, end_date).mapped('move_ids').filtered(
            lambda move: move.state == 'done' and self._get_move_sale_line(move) == line
        )

    def _get_picked_delivered_qty(self, line, start_date, end_date):
        delivered_qty = 0.0
        for move in self._get_picked_moves(line, start_date, end_date):
            move_qty = move.quantity if 'quantity' in move._fields else move.quantity_done
            move_uom = move.product_uom or line.product_uom
            sign = -1.0 if move.picking_id.return_id else 1.0
            delivered_qty += sign * move_uom._compute_quantity(move_qty, line.product_uom)
        return delivered_qty

    def _get_line_delivered_qty_by_picking(self, picking, line):
        delivered_qty = 0.0
        moves = picking.move_ids.filtered(
            lambda move: move.state == 'done' and self._get_move_sale_line(move) == line
        )
        for move in moves:
            move_qty = move.quantity if 'quantity' in move._fields else move.quantity_done
            move_uom = move.product_uom or line.product_uom
            delivered_qty += move_uom._compute_quantity(move_qty, line.product_uom)
        return delivered_qty

    def _get_picking_amount_total_by_line(self, picking, sign=1.0, currency=None):
        order_lines = self._get_picking_order_lines(picking)
        currency = currency or picking.sale_id.currency_id or picking.sale_id.company_id.currency_id
        line_data = []
        tax_base_lines = []
        for line in order_lines:
            delivered_qty = self._get_line_delivered_qty_by_picking(picking, line)
            if not delivered_qty:
                continue

            tax_base_line = line._convert_to_tax_base_line_dict()
            tax_base_line['quantity'] = sign * delivered_qty
            tax_base_lines.append(tax_base_line)
            line_subtotal = line.price_unit * (1 - (line.discount or 0.0) / 100.0) * sign * delivered_qty
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
        currency = line.order_id.currency_id or line.order_id.company_id.currency_id
        for picking in self._get_period_pickings(line, start_date, end_date):
            sign = -1.0 if picking.return_id else 1.0
            amount_total += self._get_picking_amount_total_by_line(picking, sign=sign, currency=currency).get(line, 0.0)
        return amount_total

    def _get_income_account_ids(self, data):
        """Орлого үр дүнгийн тайлантай яг ижил дансны жагсаалт (дэд дансуудыг оруулна)."""
        account_ids = data.get('account_ids') or []
        if account_ids and 'profit.excel.report' in self.env:
            return self.env['profit.excel.report'].action_account_ids(account_ids)
        return account_ids

    def _get_income_move_lines(self, data):
        """Орлого үр дүнгийн тайлантай ижил шүүлт: батлагдсан, нээлт/хаалтын бус журнал, санхүүгийн огноо."""
        journal_ids = self.env['account.journal'].search([
            ('company_id', '=', data['company_id']), ('type', 'not in', ('opening', 'closing'))]).ids
        domain = [
            ('journal_id', 'in', journal_ids),
            ('account_id', 'in', self._get_income_account_ids(data)),
            # parent_state нь хадгалагдсан хуулбар тул хоцорч болно; Орлого үр дүнгийн тайлан шиг нэхэмжлэлээс шалгана
            ('move_id.state', '=', 'posted'),
            ('date', '>=', data['start_date']),
            ('date', '<=', data['end_date']),
        ]
        if data['sales_user_id']:
            domain.append(('move_id.invoice_user_id', '=', data['sales_user_id']))
        if data['partner_id']:
            domain.append(('partner_id', '=', data['partner_id']))
        return self.env['account.move.line'].search(domain, order='date desc, move_id, id')

    def _get_income_category(self, aml):
        """Орлогын мөрийн эх үүсвэр — Орлого үр дүнгийн тайлантай зөрүүг задлахад хэрэглэнэ."""
        move = aml.move_id
        sale_lines = aml.sale_line_ids
        if move.move_type == 'entry':
            return u'Гар бичилт (нэхэмжлэлгүй)'
        if move.move_type == 'out_refund':
            return u'Буцаалт / кредит нэхэмжлэл'
        # Төслийн нэхэмжлэл ихэвчлэн урьдчилгаа/хувиар нэхэмжлэгддэг тул түрүүлж шалгана
        has_project = 'project_id' in sale_lines._fields and any(sale_lines.mapped('project_id'))
        if (aml.account_id.code or '').startswith('5103') or has_project:
            return u'Төслийн орлого'
        if not sale_lines:
            return u'Захиалгагүй нэхэмжлэл'
        if any(sale_lines.mapped('is_downpayment')):
            return u'Урьдчилгаа нэхэмжлэл'
        if any(sale_lines.order_id.mapped('is_license')):
            return u'Лиценз борлуулалт'
        return u'Хүргэгдсэн бараа'

    def _write_income_lines(self, workbook, sheet, rowx, data, data_left, data_center, data_right,
                            title, data_bold_left):
        """Орлогын дансны мөр бүрээр: дүн = кредит - дебит (НӨАТ-гүй, компанийн валютаар)."""
        sheet.write("R%s" % (rowx - 1), u'Ангилал', title)
        sheet.write("S%s" % (rowx - 1), u'Данс', title)
        sheet.set_column(17, 18, 30)
        summary = {}
        account_summary = {}
        num = 1
        for aml in self._get_income_move_lines(data):
            category = self._get_income_category(aml)
            summary[category] = summary.get(category, 0.0) - aml.balance
            account_name = '%s %s' % (aml.account_id.code, aml.account_id.name)
            account_summary[account_name] = account_summary.get(account_name, 0.0) - aml.balance
            sale_line = aml.sale_line_ids[:1]
            order = sale_line.order_id
            move = aml.move_id
            amount = -aml.balance
            # Буцаалтын нэхэмжлэл тоо, өртгийг хасах тэмдэгтэй болгоно
            sign = -1.0 if amount < 0 else 1.0
            qty = sign * abs(aml.quantity)
            unit_cost = sale_line.purchase_price if sale_line else aml.product_id.standard_price
            total_cost = unit_cost * qty
            sheet.write("A%s" % rowx, num, data_center)
            sheet.write("B%s" % rowx, "%s" % aml.date, data_left)
            sheet.write("C%s" % rowx, ', '.join(aml.sale_line_ids.order_id.mapped('name')) or move.name, data_left)
            sheet.write("D%s" % rowx, "%s" % (aml.partner_id.code or ''), data_left)
            sheet.write("E%s" % rowx, "%s" % (aml.partner_id.name or ''), data_left)
            sheet.write("F%s" % rowx, "%s" % ((order.user_id or move.invoice_user_id).name or ''), data_left)
            sheet.write("G%s" % rowx, "%s" % (aml.product_id.default_code or ''), data_left)
            sheet.write("H%s" % rowx, "%s" % (aml.product_id.brand_id.name or ''), data_left)
            sheet.write("I%s" % rowx, aml.product_id.name or aml.name or aml.account_id.name, data_left)
            sheet.write("J%s" % rowx, aml.product_uom_id.name or '', data_left)
            sheet.write("K%s" % rowx, sale_line.product_uom_qty if sale_line else qty, data_right)
            sheet.write("L%s" % rowx, qty, data_right)
            sheet.write("M%s" % rowx, unit_cost, data_right)
            sheet.write("N%s" % rowx, total_cost, data_right)
            sheet.write("O%s" % rowx, amount - total_cost, data_right)
            sheet.write("P%s" % rowx, aml.price_unit, data_right)
            sheet.write("Q%s" % rowx, amount, data_right)
            sheet.write("R%s" % rowx, category, data_left)
            sheet.write("S%s" % rowx, '%s %s' % (aml.account_id.code, aml.account_id.name), data_left)
            num += 1
            rowx += 1

        self._write_income_summary_sheet(workbook, summary, account_summary,
                                         title, data_left, data_right, data_bold_left)
        return rowx

    def _write_income_summary_sheet(self, workbook, summary, account_summary,
                                    title, data_left, data_right, data_bold_left):
        """Ангилал болон данс тус бүрийн нийлбэр тусдаа хуудсанд — Орлого үр дүнгийн тайлантай тулгахад."""
        summary_sheet = workbook.add_worksheet(u'Ангилал')
        summary_sheet.set_column(0, 0, 40)
        summary_sheet.set_column(1, 1, 25)
        summary_sheet.write('A1', u'Ангилал', title)
        summary_sheet.write('B1', u'Орлого (НӨАТ-гүй)', title)
        srow = 2
        for category, amount in sorted(summary.items(), key=lambda x: -abs(x[1])):
            summary_sheet.write('A%s' % srow, category, data_left)
            summary_sheet.write('B%s' % srow, amount, data_right)
            srow += 1
        summary_sheet.write('A%s' % srow, u'Нийт (Борлуулалтын орлого (цэвэр))', data_bold_left)
        summary_sheet.write_formula('B%s' % srow, '=SUM(B2:B%s)' % (srow - 1), data_bold_left)

        # Данс тус бүрээр — Орлого үр дүнгийн тайлантай тулгахад
        srow += 2
        first_row = srow + 1
        summary_sheet.write('A%s' % srow, u'Данс', title)
        summary_sheet.write('B%s' % srow, u'Орлого (НӨАТ-гүй)', title)
        srow += 1
        for account_name, amount in sorted(account_summary.items()):
            summary_sheet.write('A%s' % srow, account_name, data_left)
            summary_sheet.write('B%s' % srow, amount, data_right)
            srow += 1
        summary_sheet.write('A%s' % srow, u'Нийт', data_bold_left)
        summary_sheet.write_formula('B%s' % srow, '=SUM(B%s:B%s)' % (first_row, srow - 1), data_bold_left)

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

        is_income = data['target_move'] == 'invoiced'
        sheet.write("A%s" % rowx, u'Мөр', title)
        sheet.write('B%s' % rowx, u'Санхүүгийн огноо' if is_income else u'Батлагдсан огноо', title)
        sheet.write("C%s" % rowx, u'Захиалга / Нэхэмжлэх №' if is_income else u'Захиалгын №', title)
        sheet.write("D%s" % rowx, u'Харилцагчийн №', title)
        sheet.write("E%s" % rowx, u'Харилцагч', title)
        sheet.write("F%s" % rowx, u'Хэрэглэгч', title)
        sheet.write("G%s" % rowx, u'Барааны №', title)
        sheet.write("H%s" % rowx, u'Барааны бүлэг', title)
        sheet.write("I%s" % rowx, u'Барааны нэр', title)
        sheet.write("J%s" % rowx, u'Нэгж', title)
        sheet.write("K%s" % rowx, u'Захиалгын тоо', title)
        sheet.write("L%s" % rowx, u'Нэхэмжилсэн тоо' if is_income else u'Хүргэсэн тоо', title)
        sheet.write("M%s" % rowx, u'Нэгжийн өртөг', title)
        sheet.write("N%s" % rowx, u'Нийт өртөг', title)
        sheet.write("O%s" % rowx, u'Ашиг', title)
        sheet.write("P%s" % rowx, u'Нэгжийн үнэ', title)
        sheet.write("Q%s" % rowx, u'Борлуулалтын орлого (НӨАТ-гүй)' if is_income else u'Нийт үнэ', title)
        rowx += 1

        if is_income:
            rowx = self._write_income_lines(workbook, sheet, rowx, data, data_left, data_center, data_right,
                                            title, data_bold_left)
            return self._write_footer(workbook, output, sheet, rowx, response, get_file,
                                      data_bold_left, data_bold_center)

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
        return self._write_footer(workbook, output, sheet, rowx, response, get_file,
                                  data_bold_left, data_bold_center)

    def _write_footer(self, workbook, output, sheet, rowx, response, get_file, data_bold_left, data_bold_center):
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
