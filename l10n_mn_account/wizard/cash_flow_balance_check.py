# -*- coding: utf-8 -*-
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Мөнгөн гүйлгээний тайланд (statement.cashflow.report) орох бүлгүүд
INCOME_GROUPS = ('activities_income', 'investing_income', 'financing_income')
EXPENSE_GROUPS = ('activities_expense', 'investing_expense', 'financing_expense')
REPORT_GROUPS = INCOME_GROUPS + EXPENSE_GROUPS + ('exchange_rate_difference',)
# Тайлан нийт цэвэр гүйлгээнд тухайн бүлгийг нэмэх (+1) эсвэл хасах (-1)
REPORT_SIGN = {'activities_income': 1, 'investing_income': 1, 'financing_income': 1, 'exchange_rate_difference': 1,
               'activities_expense': -1, 'investing_expense': -1, 'financing_expense': -1}


def report_value(group, debit, credit):
    """Мөнгөн гүйлгээний тайлан (statement.cashflow.report) нэг төрлийн «тайлант хугацаа» баганад харуулдаг
    дүн, яг тэр тайлангийн тооцоогоор (debit, credit: тухайн төрлийн мөрүүдийн нийлбэр)."""
    if group in ('activities_income', 'exchange_rate_difference'):
        return debit - credit
    if group == 'activities_expense':
        return abs(credit - debit)
    if group == 'investing_income':
        # тайлан кредит мөрийг ч хасах биш нэмдэг: -(дт + кт) → abs
        return debit + credit
    # investing_expense, financing_income, financing_expense
    return abs(debit - credit)


class CashFlowBalanceCheck(models.TransientModel):
    """Мөнгөн гүйлгээний тайлан ба Гүйлгээ балансын зөрүү шалгах.

    Гүйлгээ баланс мөнгөн хөрөнгийн (asset_cash) дансны бүх мөрийг, мөнгөн гүйлгээний тайлан зөвхөн тайланд
    орох төрөлтэй мөрүүдийг тоолно. Тиймээс:
        Гүйлгээ балансын цэвэр өөрчлөлт = Тайланд орсон дүн + «Тайланд нөлөөлөхгүй» төрөлтэй + Төрөлгүй
    Зөрүүг данс бүрээр, мөр мөрөөр нь харуулна. Чиглэл зөрсөн мөрүүд (зарлагын төрөлтэй орлого гэх мэт)
    дүнд зөрүү үүсгэхгүй ч тайланд буруу ангилагдана.
    """
    _name = 'cash.flow.balance.check'
    _description = 'Мөнгөн гүйлгээ ба Гүйлгээ балансын зөрүү шалгах'

    company_id = fields.Many2one('res.company', 'Компани', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date_from = fields.Date('Эхлэх огноо', required=True,
                            default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date('Дуусах огноо', required=True,
                          default=lambda self: fields.Date.context_today(self).replace(day=1) + relativedelta(months=1, days=-1))
    target_move = fields.Selection([('posted', 'Батлагдсан бичилтүүд'), ('all', 'Бүх бичилт (ноорог орно)')],
                                   'Бичилт', required=True, default='posted')
    transfer_days = fields.Integer('Шилжүүлгийн хос хайх хоног', default=3,
                                   help='Дансны хоорондын шилжүүлгийн хоёр талын огнооны зөрүү (± хоног)')
    checked = fields.Boolean()

    # Гүйлгээ баланс (мөнгөн хөрөнгийн данснууд)
    tb_opening = fields.Monetary('Эхний үлдэгдэл', readonly=True)
    tb_debit = fields.Monetary('Дебет', readonly=True)
    tb_credit = fields.Monetary('Кредит', readonly=True)
    tb_net = fields.Monetary('Цэвэр өөрчлөлт', readonly=True)
    tb_closing = fields.Monetary('Эцсийн үлдэгдэл', readonly=True)
    # Мөнгөн гүйлгээний тайлан: тайлан дээр яг харагдах дүнгээр
    cf_operating = fields.Monetary('Үндсэн үйл ажиллагааны цэвэр гүйлгээ', readonly=True)
    cf_investing = fields.Monetary('Хөрөнгө оруулалтын цэвэр гүйлгээ', readonly=True)
    cf_financing = fields.Monetary('Санхүүгийн цэвэр гүйлгээ', readonly=True)
    cf_exchange = fields.Monetary('Валютын ханшийн зөрүү', readonly=True)
    cf_net = fields.Monetary('Бүх цэвэр мөнгөн гүйлгээ', readonly=True)
    cf_opening = fields.Monetary('Эхний үлдэгдэл (тайлан)', readonly=True)
    cf_closing = fields.Monetary('Эцсийн үлдэгдэл (тайлан)', readonly=True)
    # Зөрүүний задаргаа: difference = missing_amount + dummy_amount + report_error
    dummy_amount = fields.Monetary('«Тайланд нөлөөлөхгүй» төрөлтэй', readonly=True)
    missing_amount = fields.Monetary('Төрөл сонгоогүй', readonly=True)
    report_error = fields.Monetary('Тайлангийн тэмдэг / abs-ийн алдаа', readonly=True,
                                   help='Чиглэл зөрсөн мөрүүдийг тайлан үнэмлэхүй утгаар (abs) авах, хөрөнгө оруулалтын '
                                        'орлогын кредит мөрийг нэмэх зэргээс үүсэх зөрүү (төрөл тус бүрээр харна уу)')
    difference = fields.Monetary('Зөрүү (Гүйлгээ баланс − Мөнгөн гүйлгээний тайлан)', readonly=True)
    missing_count = fields.Integer('Төрөлгүй мөр', readonly=True)
    dummy_count = fields.Integer('«Нөлөөлөхгүй» мөр', readonly=True)
    wrong_count = fields.Integer('Чиглэл зөрсөн мөр', readonly=True)
    wrong_amount = fields.Monetary('Чиглэл зөрсөн дүн', readonly=True,
                                   help='Тайланд буруу ангилагдах дүн (үнэмлэхүй утгаар)')
    is_balanced = fields.Boolean('Тэнцсэн', readonly=True)
    mismatch_count = fields.Integer('Шилжүүлгийн нөгөө тал өөр төрөлтэй', readonly=True)
    mismatch_amount = fields.Monetary('Шилжүүлгийн нөгөө тал өөр төрөлтэй (дүн)', readonly=True)
    dummy_unmatched_count = fields.Integer('Хосгүй «нөлөөлөхгүй» мөр', readonly=True)

    account_line_ids = fields.One2many('cash.flow.balance.check.account', 'check_id', 'Данс тус бүрээр', readonly=True)
    issue_line_ids = fields.One2many('cash.flow.balance.check.issue', 'check_id', 'Асуудалтай мөрүүд', readonly=True)
    type_line_ids = fields.One2many('cash.flow.balance.check.type', 'check_id', 'Төрөл тус бүрээр', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise UserError(_('Эхлэх огноо дуусах огнооноос хойш байна.'))

    def _line_domain(self):
        self.ensure_one()
        states = ['posted'] if self.target_move == 'posted' else ['posted', 'draft']
        return [('company_id', '=', self.company_id.id), ('account_id.account_type', '=', 'asset_cash'),
                ('parent_state', 'in', states)]

    def action_check(self):
        self.ensure_one()
        Line = self.env['account.move.line']
        domain = self._line_domain()
        cur = self.currency_id

        # Эхний үлдэгдэл данс бүрээр
        opening = defaultdict(float)
        for account, balance in Line._read_group(domain + [('date', '<', self.date_from)], ['account_id'], ['balance:sum']):
            opening[account.id] = balance

        lines = Line.search(domain + [('date', '>=', self.date_from), ('date', '<=', self.date_to)], order='date, move_id, id')
        # Нэг бичилтэд хоёр ба түүнээс олон мөнгөн дансны мөр байвал дотоод шилжүүлэг (нийлбэр нь тэглэгдэнэ)
        cash_lines_per_move = defaultdict(int)
        for line in lines:
            cash_lines_per_move[line.move_id.id] += 1

        acc = defaultdict(lambda: defaultdict(float))
        per_type = defaultdict(lambda: [0.0, 0.0])  # төрөл → [дебет, кредит]
        issues = []
        dummies = []
        totals = defaultdict(float)
        for line in lines:
            amount = line.debit - line.credit
            a = acc[line.account_id.id]
            a['debit'] += line.debit
            a['credit'] += line.credit
            group = line.cash_move_type_id.group
            transfer = cash_lines_per_move[line.move_id.id] > 1
            if not line.cash_move_type_id:
                a['missing'] += amount
                totals['missing'] += amount
                totals['missing_count'] += 1
                issues.append((line, 'missing', transfer, None))
                continue
            if group not in REPORT_GROUPS:
                a['dummy'] += amount
                totals['dummy'] += amount
                totals['dummy_count'] += 1
                dummies.append(line)
                continue
            a['typed'] += amount
            per_type[line.cash_move_type_id][0] += line.debit
            per_type[line.cash_move_type_id][1] += line.credit
            if (group in INCOME_GROUPS and amount < 0) or (group in EXPENSE_GROUPS and amount > 0):
                totals['wrong_count'] += 1
                totals['wrong_amount'] += abs(amount)
                issues.append((line, 'wrong_direction', transfer, None))

        # Дансны хоорондын шилжүүлгийн хос: «Тайлан тооцохгүй» мөр бүрийн нөгөө тал (өөр мөнгөн данс, ижил дүн,
        # эсрэг чиглэл, ±transfer_days хоног). Нөгөө тал өөр сард байж болох тул хугацааны гадна талаас ч хайна.
        days = max(self.transfer_days, 0)
        window = Line.search(domain + [('date', '>=', self.date_from - relativedelta(days=days)),
                                       ('date', '<=', self.date_to + relativedelta(days=days))], order='date, id')
        by_amount = defaultdict(list)
        for cand in window:
            by_amount[cur.round(cand.balance)].append(cand)
        used = set()

        def find_pair(line, accept):
            best = None
            for cand in by_amount.get(cur.round(-line.balance), []):
                if cand.id in used or cand.id == line.id or cand.account_id == line.account_id:
                    continue
                gap = abs((cand.date - line.date).days)
                if gap > days or not accept(cand):
                    continue
                if best is None or gap < abs((best.date - line.date).days):
                    best = cand
            return best

        is_dummy = lambda l: bool(l.cash_move_type_id) and l.cash_move_type_id.group not in REPORT_GROUPS
        is_typed = lambda l: l.cash_move_type_id.group in REPORT_GROUPS
        in_period = lambda l: self.date_from <= l.date <= self.date_to
        missing_pairs = {}
        unmatched = []
        # 1. «нөлөөлөхгүй» ↔ «нөлөөлөхгүй»: зөв дотоод шилжүүлэг (нөгөө тал хугацааны гадна бол л харуулна)
        for d in dummies:
            if d.id in used:
                continue
            if cur.is_zero(d.balance):
                # 0 дүнтэй мөр зөрүүнд нөлөөлөхгүй (санамсаргүй хослохоос сэргийлнэ)
                used.add(d.id)
                continue
            pair = find_pair(d, is_dummy)
            if pair:
                used.update((d.id, pair.id))
                if not in_period(pair):
                    issues.append((d, 'dummy', True, pair))
                    totals['dummy_unmatched_count'] += 1
            else:
                unmatched.append(d)
        # 2. «нөлөөлөхгүй» ↔ тайланд орох / төрөлгүй мөр: нөгөө талын төрлийг засах ёстой
        for d in unmatched:
            pair = find_pair(d, lambda c: is_typed(c) or not c.cash_move_type_id)
            if pair and is_typed(pair):
                used.update((d.id, pair.id))
                issues.append((pair, 'transfer_mismatch', True, d))
                totals['mismatch_count'] += 1
                totals['mismatch_amount'] += abs(pair.balance)
            elif pair:
                used.update((d.id, pair.id))
                missing_pairs[pair.id] = d
                issues.append((d, 'dummy', True, pair))
                totals['dummy_unmatched_count'] += 1
            else:
                issues.append((d, 'dummy', False, None))
                totals['dummy_unmatched_count'] += 1
        # төрөлгүй мөрийн нөгөө тал «нөлөөлөхгүй» бол тэр мөрийг заана
        issues = [(l, c, t or l.id in missing_pairs, missing_pairs.get(l.id) if c == 'missing' and not p else p)
                  for l, c, t, p in issues]

        account_vals = []
        accounts = self.env['account.account'].browse(set(opening) | set(acc))
        for account in accounts.sorted('code'):
            a = acc[account.id]
            net = a['debit'] - a['credit']
            account_vals.append((0, 0, {
                'account_id': account.id,
                'opening': opening[account.id],
                'debit': a['debit'],
                'credit': a['credit'],
                'closing': opening[account.id] + net,
                'typed_amount': a['typed'],
                'dummy_amount': a['dummy'],
                'missing_amount': a['missing'],
                'difference': net - a['typed'],
            }))
        tb_debit = sum(a['debit'] for a in acc.values())
        tb_credit = sum(a['credit'] for a in acc.values())
        tb_opening = sum(opening.values())
        # Мөнгөн гүйлгээний тайлангийн дүн, яг тайлангийн тооцоогоор (төрөл бүрээр)
        section = defaultdict(float)
        type_vals = []
        for cash_type, (debit, credit) in sorted(per_type.items(), key=lambda kv: (kv[0].group, kv[0].sequence, kv[0].id)):
            group = cash_type.group
            shown = report_value(group, debit, credit)
            effect = REPORT_SIGN[group] * shown
            section[group.split('_')[0]] += effect
            type_vals.append((0, 0, {
                'cash_move_type_id': cash_type.id,
                'debit': debit,
                'credit': credit,
                'true_net': debit - credit,
                'report_value': shown,
                'report_effect': effect,
                'difference': (debit - credit) - effect,
            }))
        cf_operating = section['activities']
        cf_investing = section['investing']
        cf_financing = section['financing']
        cf_exchange = section['exchange']
        cf_net = cf_operating + cf_investing + cf_financing + cf_exchange
        difference = (tb_debit - tb_credit) - cf_net
        report_error = difference - totals['missing'] - totals['dummy']

        self.account_line_ids.unlink()
        self.issue_line_ids.unlink()
        self.type_line_ids.unlink()
        self.write({
            'checked': True,
            'tb_opening': tb_opening,
            'tb_debit': tb_debit,
            'tb_credit': tb_credit,
            'tb_net': tb_debit - tb_credit,
            'tb_closing': tb_opening + tb_debit - tb_credit,
            'cf_operating': cf_operating,
            'cf_investing': cf_investing,
            'cf_financing': cf_financing,
            'cf_exchange': cf_exchange,
            'cf_net': cf_net,
            'cf_opening': tb_opening,
            'cf_closing': tb_opening + cf_net,
            'report_error': report_error,
            'dummy_amount': totals['dummy'],
            'missing_amount': totals['missing'],
            'difference': difference,
            'missing_count': int(totals['missing_count']),
            'dummy_count': int(totals['dummy_count']),
            'wrong_count': int(totals['wrong_count']),
            'wrong_amount': totals['wrong_amount'],
            'is_balanced': cur.is_zero(difference),
            'mismatch_count': int(totals['mismatch_count']),
            'mismatch_amount': totals['mismatch_amount'],
            'dummy_unmatched_count': int(totals['dummy_unmatched_count']),
            'account_line_ids': account_vals,
            'type_line_ids': type_vals,
            'issue_line_ids': [(0, 0, {'move_line_id': line.id, 'category': cat, 'internal_transfer': transfer,
                                       'paired_line_id': pair.id if pair else False})
                               for line, cat, transfer, pair in issues],
        })
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Мөнгөн гүйлгээ ба Гүйлгээ балансын зөрүү'),
            'context': dict(self.env.context, dialog_size='extra-large'),
        }

    def _open_lines(self, category, title):
        self.ensure_one()
        move_lines = self.issue_line_ids.filtered(lambda l: l.category == category).move_line_id
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', move_lines.ids)],
            'context': {'create': False},
            'target': 'current',
        }

    def action_open_missing(self):
        return self._open_lines('missing', _('Төрөл сонгоогүй мөнгөн гүйлгээ'))

    def action_open_dummy(self):
        return self._open_lines('dummy', _('«Тайланд нөлөөлөхгүй» төрөлтэй мөнгөн гүйлгээ'))

    def action_open_wrong(self):
        return self._open_lines('wrong_direction', _('Чиглэл зөрсөн мөнгөн гүйлгээ'))

    def action_open_mismatch(self):
        return self._open_lines('transfer_mismatch', _('Шилжүүлгийн нөгөө тал өөр төрөлтэй'))


class CashFlowBalanceCheckAccount(models.TransientModel):
    _name = 'cash.flow.balance.check.account'
    _description = 'Мөнгөн гүйлгээний зөрүү: данс'
    _order = 'id'

    check_id = fields.Many2one('cash.flow.balance.check', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='check_id.currency_id')
    account_id = fields.Many2one('account.account', 'Данс', readonly=True)
    opening = fields.Monetary('Эхний үлдэгдэл', readonly=True)
    debit = fields.Monetary('Дебет', readonly=True)
    credit = fields.Monetary('Кредит', readonly=True)
    closing = fields.Monetary('Эцсийн үлдэгдэл', readonly=True)
    typed_amount = fields.Monetary('Тайланд орсон', readonly=True)
    dummy_amount = fields.Monetary('«Нөлөөлөхгүй»', readonly=True)
    missing_amount = fields.Monetary('Төрөлгүй', readonly=True)
    difference = fields.Monetary('Зөрүү', readonly=True)


class CashFlowBalanceCheckIssue(models.TransientModel):
    _name = 'cash.flow.balance.check.issue'
    _description = 'Мөнгөн гүйлгээний зөрүү: асуудалтай мөр'
    _order = 'category, date, id'

    check_id = fields.Many2one('cash.flow.balance.check', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='check_id.currency_id')
    category = fields.Selection([
        ('missing', 'Төрөл сонгоогүй'),
        ('dummy', '«Тайланд нөлөөлөхгүй» төрөл'),
        ('wrong_direction', 'Чиглэл зөрсөн'),
        ('transfer_mismatch', 'Шилжүүлгийн нөгөө тал өөр төрөлтэй'),
    ], 'Асуудал', readonly=True)
    internal_transfer = fields.Boolean('Дотоод шилжүүлэг', readonly=True,
                                       help='Нэг бичилтэд хоёр мөнгөн дансны мөр байна (дансны хооронд шилжүүлэг)')
    move_line_id = fields.Many2one('account.move.line', 'Журналын мөр', readonly=True)
    date = fields.Date(related='move_line_id.date')
    move_id = fields.Many2one(related='move_line_id.move_id')
    journal_id = fields.Many2one(related='move_line_id.journal_id')
    account_id = fields.Many2one(related='move_line_id.account_id')
    partner_id = fields.Many2one(related='move_line_id.partner_id')
    name = fields.Char(related='move_line_id.name')
    cash_move_type_id = fields.Many2one(related='move_line_id.cash_move_type_id')
    debit = fields.Monetary(related='move_line_id.debit', currency_field='currency_id')
    credit = fields.Monetary(related='move_line_id.credit', currency_field='currency_id')
    paired_line_id = fields.Many2one('account.move.line', 'Шилжүүлгийн нөгөө тал', readonly=True,
                                     help='Өөр мөнгөн данс, ижил дүн, эсрэг чиглэл, ойрын огноотой мөр')
    paired_move_id = fields.Many2one(related='paired_line_id.move_id', string='Нөгөө талын бичилт')
    paired_account_id = fields.Many2one(related='paired_line_id.account_id', string='Нөгөө талын данс')
    paired_date = fields.Date(related='paired_line_id.date', string='Нөгөө талын огноо')
    paired_type_id = fields.Many2one(related='paired_line_id.cash_move_type_id', string='Нөгөө талын төрөл')

    def action_set_paired_type(self):
        """Шилжүүлгийн энэ талд нөгөө талынх нь («Тайлан тооцохгүй») төрлийг тавьж, дахин шалгана.
        Журналын мөрийн төрөл банкны хуулгын мөрт автоматаар дамжина."""
        self.ensure_one()
        if self.category != 'transfer_mismatch' or not self.paired_line_id.cash_move_type_id:
            raise UserError(_('Зөвхөн шилжүүлгийн нөгөө тал өөр төрөлтэй мөрийг засна.'))
        self.move_line_id.cash_move_type_id = self.paired_line_id.cash_move_type_id
        check = self.check_id
        check.action_check()
        return check._reopen()


class CashFlowBalanceCheckType(models.TransientModel):
    _name = 'cash.flow.balance.check.type'
    _description = 'Мөнгөн гүйлгээний зөрүү: төрөл'
    _order = 'id'

    check_id = fields.Many2one('cash.flow.balance.check', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='check_id.currency_id')
    cash_move_type_id = fields.Many2one('account.cash.move.type', 'Мөнгөн гүйлгээний төрөл', readonly=True)
    group = fields.Selection(related='cash_move_type_id.group')
    debit = fields.Monetary('Орлого (Дт)', readonly=True)
    credit = fields.Monetary('Зарлага (Кт)', readonly=True)
    true_net = fields.Monetary('Бодит цэвэр дүн', readonly=True, help='Дебет − Кредит: Гүйлгээ балансад орох дүн')
    report_value = fields.Monetary('Тайланд харагдах', readonly=True, help='Мөнгөн гүйлгээний тайлангийн мөрөнд харагдах дүн')
    report_effect = fields.Monetary('Цэвэр гүйлгээнд нөлөө', readonly=True,
                                    help='Тайлан нийт цэвэр гүйлгээнд нэмэх (+) / хасах (−) дүн')
    difference = fields.Monetary('Зөрүү', readonly=True)
