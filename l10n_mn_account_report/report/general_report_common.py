# -*- coding: utf-8 -*-

import io
import json
from collections import OrderedDict

import xlsxwriter
from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils, float_is_zero


class GeneralReportMixin(models.AbstractModel):
    """Ерөнхий дэвтэр / Ерөнхий журнал тайлангуудын нийтлэг логик.

    Тайлан бүр өөрийн огнооны талбарын нэрийг `_date_fields` -д заана.
    Харьцсан данс тооцох журам: сонгосон данс тухайн гүйлгээнд цэвэр
    дебитлэгдсэн бол цэвэр кредитлэгдсэн эсрэг мөрүүдэд, цэвэр
    кредитлэгдсэн бол цэвэр дебитлэгдсэн эсрэг мөрүүдэд дүнг
    пропорциональ хуваарилна.
    """
    _name = 'general.report.mixin'
    _inherit = ['xls.report.base']
    _description = 'General book/journal report mixin'

    _date_fields = ('date_from', 'date_to')
    _report_title = ''

    # ------------------------------------------------------------------
    # Wizard
    # ------------------------------------------------------------------
    def _get_dates(self):
        return self[self._date_fields[0]], self[self._date_fields[1]]

    def get_report_data(self):
        data = super().get_report_data()
        date_from, date_to = self._get_dates()
        data.update({
            'company_id': self.company_id.id,
            'start_date': str(date_from),
            'end_date': str(date_to),
        })
        return data

    def action_print_xls_report(self):
        self.ensure_one()
        date_from, date_to = self._get_dates()
        if date_from > date_to:
            raise UserError(_('Эхлэх огноо дуусах огнооноос хойш байна.'))
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': self._name,
                     'output_format': 'xlsx',
                     'options': json.dumps(data, default=date_utils.json_default),
                     'report_name': self._report_title},
        }

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def _get_states(self):
        return ('posted',) if self.target_move == 'posted' else ('posted', 'draft')

    def _get_accounts(self):
        return self.account_ids.filtered(
            lambda a: a.company_id == self.company_id).sorted('code')

    def _get_opening_balance(self, account):
        """Эхний үлдэгдэл: баланс данс бол бүх түүх, орлого/зардлын данс бол
        санхүүгийн жилийн эхнээс эхлэх огноо хүртэлх дүн."""
        date_from, _date_to = self._get_dates()
        query = """
            SELECT COALESCE(SUM(aml.debit - aml.credit), 0)
              FROM account_move_line aml
              JOIN account_move am ON am.id = aml.move_id
             WHERE aml.account_id = %s
               AND aml.company_id = %s
               AND am.state IN %s
               AND aml.date < %s
        """
        params = [account.id, self.company_id.id, self._get_states(), date_from]
        if not account.include_initial_balance:
            fy_start = self.company_id.compute_fiscalyear_dates(date_from)['date_from']
            if fy_start and fy_start <= date_from:
                query += " AND aml.date >= %s"
                params.append(fy_start)
        self.env.cr.execute(query, params)
        return self.env.cr.fetchone()[0] or 0.0

    def _get_allocated_lines(self, account):
        """Сонгосон дансны тухайн хугацааны гүйлгээ бүрийг харьцсан данс
        тус бүрээр задалсан жагсаалт буцаана.

        Мөр бүр: dict(date, move_name, ref, label, partner, account,
                      debit, credit)  — debit/credit нь СОНГОСОН дансны тал.
        """
        date_from, date_to = self._get_dates()
        precision = self.company_id.currency_id.decimal_places
        MoveLine = self.env['account.move.line']
        lines = MoveLine.search([
            ('account_id', '=', account.id),
            ('company_id', '=', self.company_id.id),
            ('parent_state', 'in', self._get_states()),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ], order='date, move_name, id')
        result = []
        for move in lines.move_id.sorted(lambda m: (m.date, m.name or '', m.id)):
            own = move.line_ids.filtered(lambda l: l.account_id == account)
            others = move.line_ids - own
            net = sum(own.mapped('debit')) - sum(own.mapped('credit'))
            if float_is_zero(net, precision_digits=precision):
                continue
            label = ', '.join(n for n in own.mapped('name') if n) or move.ref or ''
            partner = own.partner_id[:1] or move.partner_id
            # Эсрэг талын мөрүүд (данс тус бүрээр нэгтгэнэ)
            buckets = OrderedDict()
            for ol in others:
                o_net = ol.debit - ol.credit
                if (net > 0 and o_net < 0) or (net < 0 and o_net > 0):
                    key = ol.account_id
                    b = buckets.setdefault(key, {'amount': 0.0, 'partner': ol.partner_id})
                    b['amount'] += abs(o_net)
            total_w = sum(b['amount'] for b in buckets.values())
            amount = abs(net)
            if not buckets or float_is_zero(total_w, precision_digits=precision):
                # Эсрэг тал олдохгүй (зөвхөн нэг данстай гүйлгээ г.м.)
                buckets = OrderedDict({account.browse(): {'amount': 1.0, 'partner': partner}})
                total_w = 1.0
            remaining = amount
            items = list(buckets.items())
            for idx, (counter_acc, b) in enumerate(items):
                if idx == len(items) - 1:
                    share = remaining
                else:
                    share = round(amount * b['amount'] / total_w, precision)
                    remaining -= share
                result.append({
                    'date': move.date,
                    'move_name': move.name or '',
                    'label': label,
                    'partner': (partner or b['partner']).display_name or '',
                    'account': counter_acc,
                    'debit': share if net > 0 else 0.0,
                    'credit': share if net < 0 else 0.0,
                })
        return result

    # ------------------------------------------------------------------
    # XLSX helpers
    # ------------------------------------------------------------------
    def _get_formats(self, workbook):
        base = {'font_size': 10, 'valign': 'vcenter'}
        border = dict(base, border=1)
        num = '#,##0.00;(#,##0.00)'
        return {
            'title': workbook.add_format(dict(base, bold=True, font_size=14, align='center')),
            'bold': workbook.add_format(dict(base, bold=True)),
            'bold_right': workbook.add_format(dict(base, bold=True, align='right')),
            'text': workbook.add_format(dict(base)),
            'head': workbook.add_format(dict(border, bold=True, align='center', text_wrap=True,
                                             bg_color='#DCE6F1')),
            'cell': workbook.add_format(dict(border, text_wrap=True)),
            'cell_center': workbook.add_format(dict(border, align='center')),
            'num': workbook.add_format(dict(border, num_format=num)),
            'num_bold': workbook.add_format(dict(border, bold=True, num_format=num)),
            'cell_bold': workbook.add_format(dict(border, bold=True)),
            'acc_head': workbook.add_format(dict(border, bold=True, bg_color='#F2F2F2')),
            'acc_num': workbook.add_format(dict(border, bold=True, bg_color='#F2F2F2', num_format=num)),
        }

    @staticmethod
    def _acc_name(account):
        return '%s %s' % (account.code, account.name) if account else ''

    def get_xlsx_report(self, data, response, get_file=False):
        record = self.browse(data.get('res_id')).exists() if data.get('res_id') else self
        if not record:
            raise UserError(_('Тайлангийн мэдээлэл олдсонгүй. Дахин оролдоно уу.'))
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        record._write_report(workbook, record._get_formats(workbook))
        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()

    def _write_report(self, workbook, fmt):
        raise NotImplementedError

    def _write_book_report(self, workbook, fmt):
        """Данс бүрээр харьцсан дансны нэгтгэл."""
        date_from, date_to = self._get_dates()
        sheet = workbook.add_worksheet(self._report_title)
        sheet.set_column(0, 0, 6)
        sheet.set_column(1, 1, 45)
        sheet.set_column(2, 4, 18)

        sheet.merge_range(0, 0, 0, 4, self._report_title.upper(), fmt['title'])
        sheet.write(2, 0, 'Байгууллагын нэр: %s' % self.company_id.name, fmt['bold'])
        sheet.write(2, 4, '%s - %s' % (date_from, date_to), fmt['bold_right'])
        row = 4

        for account in self._get_accounts():
            balance = self._get_opening_balance(account)
            sheet.merge_range(row, 0, row, 1, 'Данс: %s' % self._acc_name(account), fmt['acc_head'])
            sheet.merge_range(row, 2, row, 3, 'Эхний үлдэгдэл', fmt['acc_head'])
            sheet.write(row, 4, balance, fmt['acc_num'])
            row += 1

            sheet.merge_range(row, 0, row + 1, 0, 'Д/д', fmt['head'])
            sheet.merge_range(row, 1, row + 1, 1, 'Харьцсан данс', fmt['head'])
            sheet.merge_range(row, 2, row, 3, 'Гүйлгээ', fmt['head'])
            sheet.write(row + 1, 2, 'Дебит', fmt['head'])
            sheet.write(row + 1, 3, 'Кредит', fmt['head'])
            sheet.merge_range(row, 4, row + 1, 4, 'Үлдэгдэл', fmt['head'])
            row += 2

            grouped = OrderedDict()
            for item in self._get_allocated_lines(account):
                g = grouped.setdefault(item['account'], {'debit': 0.0, 'credit': 0.0})
                g['debit'] += item['debit']
                g['credit'] += item['credit']

            total_debit = total_credit = 0.0
            for number, (counter_acc, vals) in enumerate(
                    sorted(grouped.items(), key=lambda kv: kv[0].code or ''), start=1):
                balance += vals['debit'] - vals['credit']
                total_debit += vals['debit']
                total_credit += vals['credit']
                sheet.write(row, 0, number, fmt['cell_center'])
                sheet.write(row, 1, self._acc_name(counter_acc) or '-', fmt['cell'])
                sheet.write(row, 2, vals['debit'], fmt['num'])
                sheet.write(row, 3, vals['credit'], fmt['num'])
                sheet.write(row, 4, balance, fmt['num'])
                row += 1

            sheet.merge_range(row, 0, row, 1, 'НИЙТ', fmt['cell_bold'])
            sheet.write(row, 2, total_debit, fmt['num_bold'])
            sheet.write(row, 3, total_credit, fmt['num_bold'])
            sheet.write(row, 4, '', fmt['cell_bold'])
            row += 1
            sheet.merge_range(row, 0, row, 3, 'Эцсийн үлдэгдэл', fmt['cell_bold'])
            sheet.write(row, 4, balance, fmt['num_bold'])
            row += 3

        self._write_signatures(sheet, row, fmt, ['Зөвшөөрсөн', 'Хөтөлсөн ня-бо'])

    def _write_journal_report(self, workbook, fmt, with_balance=False):
        """Данс бүрээр гүйлгээний дэлгэрэнгүй (харьцсан дансаар задалсан)."""
        date_from, date_to = self._get_dates()
        sheet = workbook.add_worksheet(self._report_title)
        last = 8 if with_balance else 7
        widths = [6, 11, 16, 40, 28, 36, 16, 16, 16]
        for col, width in enumerate(widths[:last + 1]):
            sheet.set_column(col, col, width)

        sheet.write(0, last, 'Сангийн сайдын 2018 оны', fmt['bold_right'])
        sheet.write(1, last, 'өдрийн 100 дугаар тушаалын хавсралт', fmt['bold_right'])
        sheet.merge_range(3, 0, 3, last, 'ЕРӨНХИЙ ЖУРНАЛ', fmt['title'])
        sheet.write(5, 0, 'Байгууллагын нэр: %s' % self.company_id.name, fmt['bold'])
        sheet.write(5, last, '%s - %s' % (date_from, date_to), fmt['bold_right'])

        row = 7
        sheet.merge_range(row, 0, row + 1, 0, 'Д/д', fmt['head'])
        sheet.merge_range(row, 1, row, 2, 'Баримтын', fmt['head'])
        sheet.write(row + 1, 1, 'Он сар', fmt['head'])
        sheet.write(row + 1, 2, 'Дугаар', fmt['head'])
        sheet.merge_range(row, 3, row + 1, 3, 'Гүйлгээний утга', fmt['head'])
        sheet.merge_range(row, 4, row + 1, 4, 'Харилцагч', fmt['head'])
        sheet.merge_range(row, 5, row + 1, 5, 'Харьцсан данс (код, нэр)', fmt['head'])
        sheet.merge_range(row, 6, row, last, 'Дүн', fmt['head'])
        sheet.write(row + 1, 6, 'Дебит', fmt['head'])
        sheet.write(row + 1, 7, 'Кредит', fmt['head'])
        if with_balance:
            sheet.write(row + 1, 8, 'Үлдэгдэл', fmt['head'])
        row += 2
        date_fmt = workbook.add_format({'font_size': 10, 'border': 1, 'align': 'center',
                                        'num_format': 'yyyy-mm-dd'})

        for account in self._get_accounts():
            balance = self._get_opening_balance(account)
            sheet.merge_range(row, 0, row, 5, 'Данс: %s — Эхний үлдэгдэл' % self._acc_name(account),
                              fmt['acc_head'])
            if with_balance:
                sheet.merge_range(row, 6, row, 7, '', fmt['acc_head'])
                sheet.write(row, 8, balance, fmt['acc_num'])
            else:
                sheet.merge_range(row, 6, row, 7, balance, fmt['acc_num'])
            row += 1

            total_debit = total_credit = 0.0
            for number, item in enumerate(self._get_allocated_lines(account), start=1):
                balance += item['debit'] - item['credit']
                total_debit += item['debit']
                total_credit += item['credit']
                sheet.write(row, 0, number, fmt['cell_center'])
                sheet.write_datetime(row, 1, fields.Datetime.to_datetime(item['date']), date_fmt)
                sheet.write(row, 2, item['move_name'], fmt['cell'])
                sheet.write(row, 3, item['label'], fmt['cell'])
                sheet.write(row, 4, item['partner'], fmt['cell'])
                sheet.write(row, 5, self._acc_name(item['account']) or '-', fmt['cell'])
                sheet.write(row, 6, item['debit'], fmt['num'])
                sheet.write(row, 7, item['credit'], fmt['num'])
                if with_balance:
                    sheet.write(row, 8, balance, fmt['num'])
                row += 1

            sheet.merge_range(row, 0, row, 5, 'НИЙТ', fmt['cell_bold'])
            sheet.write(row, 6, total_debit, fmt['num_bold'])
            sheet.write(row, 7, total_credit, fmt['num_bold'])
            if with_balance:
                sheet.write(row, 8, '', fmt['cell_bold'])
            row += 1
            sheet.merge_range(row, 0, row, 5, 'Эцсийн үлдэгдэл', fmt['cell_bold'])
            if with_balance:
                sheet.merge_range(row, 6, row, 7, '', fmt['cell_bold'])
                sheet.write(row, 8, balance, fmt['num_bold'])
            else:
                sheet.merge_range(row, 6, row, 7, balance, fmt['num_bold'])
            row += 2

        self._write_signatures(sheet, row + 1, fmt, ['Хөтөлсөн нягтлан бодогч',
                                                     'Хянасан ерөнхий (ахлах) нягтлан бодогч'])

    def _write_signatures(self, sheet, row, fmt, labels):
        for label in labels:
            sheet.write(row, 1, label + ': ............................ /                    /', fmt['text'])
            row += 2
        return row
