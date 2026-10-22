# -*- coding: utf-8 -*-
import io
import json
import calendar
from datetime import date

import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import date_utils


class IncomePlanReport(models.TransientModel):
    """
        Орлого үр дүнгийн тайлангийн төлөвлөгөөний гүйцэтгэл
    """
    _name = "income.plan.report"
    _inherit = ['xls.report.base']
    _description = "Income report plan execution"

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    period_type = fields.Selection([('year', 'Year'), ('quarter', 'Quarter'), ('month', 'Month')],
                                   string='Period', required=True, default='year')
    year = fields.Integer(string='Year', required=True,
                          default=lambda self: fields.Date.today().year)
    quarter = fields.Selection([('1', 'Q1'), ('2', 'Q2'), ('3', 'Q3'), ('4', 'Q4')],
                               string='Quarter', default='1')
    month = fields.Selection([(str(m), calendar.month_name[m]) for m in range(1, 13)],
                             string='Month', default='1')
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')],
                                   string='State', required=True, default='posted')

    def _get_months(self):
        """Return (first month, last month) of the selected period."""
        self.ensure_one()
        if self.period_type == 'year':
            return 1, 12
        if self.period_type == 'quarter':
            q = int(self.quarter)
            return (q - 1) * 3 + 1, q * 3
        return int(self.month), int(self.month)

    def get_report_data(self):
        data = super().get_report_data()
        month_from, month_to = self._get_months()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'year': self.year,
            'month_from': month_from,
            'month_to': month_to,
            'start_date': str(date(self.year, month_from, 1)),
            'end_date': str(date(self.year, month_to, calendar.monthrange(self.year, month_to)[1])),
            'target_move': self.target_move,
        })
        return data

    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'income.plan.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data, default=date_utils.json_default),
                     'report_name': 'Income plan execution report'}
        }

    @api.model
    def _get_actual(self, income_type, data):
        """Actual amount of one income report type for the period, signed the same way as the
        profit excel report (income: credit - debit, expense: debit - credit)."""
        accounts = self.env['account.account'].search([('income_id', '=', income_type.id)])
        account_ids = self.env['profit.excel.report'].action_account_ids(accounts.ids) if accounts else []
        if not account_ids:
            return 0.0
        states = ['posted'] if data['target_move'] == 'posted' else ['posted', 'draft']
        journals = self.env['account.journal'].search([
            ('company_id', '=', data['company_id']), ('type', 'not in', ('opening', 'closing'))])
        lines = self.env['account.move.line'].search([
            ('move_id.journal_id', 'in', journals.ids),
            ('account_id', 'in', account_ids),
            ('move_id.state', 'in', states),
            ('date', '>=', data['start_date']),
            ('date', '<=', data['end_date'])])
        credit_minus_debit = sum(lines.mapped('credit')) - sum(lines.mapped('debit'))
        seq_type = int(income_type.seq_type or 0)
        if seq_type == 1:
            amount = abs(credit_minus_debit)
        elif seq_type == 2:
            amount = credit_minus_debit
        else:
            amount = -credit_minus_debit
        return -amount if income_type.is_value_negative else amount

    def get_xlsx_report(self, data, response, get_file=False):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        header = workbook.add_format({'align': 'center', 'bold': True, 'font_size': 16})
        header_txt = workbook.add_format({'align': 'center', 'font_size': 12, 'text_wrap': True})
        header_title = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1,
                                            'bold': True, 'font_size': 12, 'text_wrap': True})
        text = workbook.add_format({'align': 'left', 'border': 1, 'font_size': 12})
        number = workbook.add_format({'align': 'right', 'border': 1, 'font_size': 12,
                                      'num_format': '#,##0.00; (#,##0.00)'})
        percent = workbook.add_format({'align': 'right', 'border': 1, 'font_size': 12,
                                       'num_format': '0.00"%"'})
        bold_text = workbook.add_format({'align': 'left', 'border': 1, 'bold': True, 'font_size': 12})
        bold_number = workbook.add_format({'align': 'right', 'border': 1, 'bold': True, 'font_size': 12,
                                           'num_format': '#,##0.00; (#,##0.00)'})
        bold_percent = workbook.add_format({'align': 'right', 'border': 1, 'bold': True, 'font_size': 12,
                                            'num_format': '0.00"%"'})

        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0)
        sheet.set_column(0, 0, 6)
        sheet.set_column(1, 1, 60)
        sheet.set_column(2, 5, 22)

        self = self.env[self._name]
        sheet.merge_range("A1:F1", u'ОРЛОГО ҮР ДҮНГИЙН ТАЙЛАНГИЙН ТӨЛӨВЛӨГӨӨНИЙ ГҮЙЦЭТГЭЛ', header)
        sheet.merge_range("A2:F2", data['company_name'], header_txt)
        sheet.merge_range("A3:F3", u'%s - %s' % (data['start_date'], data['end_date']), header_txt)

        row = 4
        for col, title in enumerate([u'№', u'Үзүүлэлт', u'Төлөвлөгөө', u'Гүйцэтгэл',
                                     u'Гүйцэтгэлийн %', u'Зөрүү']):
            sheet.write(row, col, title, header_title)
        row += 1

        plan = self.env['account.income.plan'].search([
            ('company_id', '=', data['company_id']), ('year', '=', data['year'])], limit=1)
        if not plan:
            raise UserError(_('There is no plan for the year %s.') % data['year'])
        plan_lines = {line.income_type_id.id: line for line in plan.line_ids}

        income_types = self.env['account.income.type'].search(
            [('company_id', '=', data['company_id'])], order='seq_type, sequence, id')
        total_plan = total_actual = 0.0
        number_no = 1
        for income_type in income_types:
            plan_line = plan_lines.get(income_type.id)
            planned = plan_line.get_planned(data['month_from'], data['month_to']) if plan_line else 0.0
            actual = self._get_actual(income_type, data)
            if not planned and not actual:
                continue
            sheet.write(row, 0, number_no, text)
            sheet.write(row, 1, income_type.name, text)
            sheet.write(row, 2, planned, number)
            sheet.write(row, 3, actual, number)
            if planned:
                sheet.write(row, 4, actual / planned * 100.0, percent)
            else:
                sheet.write(row, 4, '', percent)
            sheet.write(row, 5, actual - planned, number)
            row += 1
            number_no += 1

            # Net result: income lines (type income) are added, expense lines subtracted
            sign = 1 if income_type.type == 'income' else -1
            if income_type.type in ('income', 'expense'):
                total_plan += sign * planned
                total_actual += sign * actual

        sheet.write(row, 0, '', bold_text)
        sheet.write(row, 1, u'Орлого, зардлын зөрүү (цэвэр дүн)', bold_text)
        sheet.write(row, 2, total_plan, bold_number)
        sheet.write(row, 3, total_actual, bold_number)
        if total_plan:
            sheet.write(row, 4, total_actual / total_plan * 100.0, bold_percent)
        else:
            sheet.write(row, 4, '', bold_percent)
        sheet.write(row, 5, total_actual - total_plan, bold_number)

        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return
