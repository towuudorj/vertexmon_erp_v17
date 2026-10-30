# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAssetGlReconcile(models.TransientModel):
    """
        Үндсэн хөрөнгийн бүртгэлийг ГБ-тэй тулгах
        Ангиллын өртөг, элэгдлийн данс бүрийн ГБ-ийн үлдэгдлийг бүртгэлийн дүнтэй тэнцүүлэх
        ноорог бичилт үүсгэнэ. ГБ-ийн нээлт дансаар нийт дүнгээр орсон тохиолдолд ч ажиллана.
    """
    _name = 'account.asset.gl.reconcile'
    _description = 'Asset register to general ledger reconciliation'

    def _default_journal(self):
        return self.env['account.asset.category'].search(
            [('company_id', '=', self.env.company.id), ('journal_id', '!=', False)], limit=1).journal_id

    def _default_offset_account(self):
        # Өмнөх үеийн хуримтлагдсан ашиг алдагдал
        return self.env['account.account'].search(
            [('company_id', '=', self.env.company.id), ('code', '=', '46020001')], limit=1)

    company_id = fields.Many2one('res.company', string='Компани', required=True,
                                 default=lambda self: self.env.company)
    date = fields.Date(string='Огноо', required=True, default=fields.Date.context_today)
    category_ids = fields.Many2many('account.asset.category', string='Хөрөнгийн ангилал',
                                    domain="[('company_id', '=', company_id)]",
                                    help='Хоосон бол компанийн бүх ангилал')
    journal_id = fields.Many2one('account.journal', string='Журнал', required=True, default=_default_journal,
                                 domain="[('type', '=', 'general'), ('company_id', '=', company_id)]")
    offset_account_id = fields.Many2one('account.account', string='Харьцах данс', required=True,
                                        default=_default_offset_account,
                                        domain="[('company_id', '=', company_id), ('deprecated', '=', False)]")
    ignore_unmapped = fields.Boolean(string='Холбогдоогүй дансыг үл тооцох')
    line_ids = fields.One2many('account.asset.gl.reconcile.line', 'wizard_id', string='Тулгалт')
    warning = fields.Text(string='Анхааруулга', readonly=True)

    def _get_categories(self):
        categories = self.category_ids._origin or self.env['account.asset.category'].search(
            [('company_id', '=', self.company_id.id)])
        for category in categories:
            if not category.account_asset_id or not category.account_depreciation_id:
                raise UserError(_("'%s' ангилалд хөрөнгийн эсвэл элэгдлийн данс тохируулагдаагүй байна.")
                                % category.name)
            if category.account_asset_id == category.account_depreciation_id:
                raise UserError(_("'%s' ангиллын хөрөнгийн данс ба элэгдлийн данс ижил (%s) байна. "
                                  "Элэгдлийн дансыг засаад дахин тооцоолно уу.")
                                % (category.name, category.account_asset_id.code))
        return categories

    def _get_register_balances(self, categories):
        """Бүртгэлээр данс тус бүрийн үлдэгдэл, ГБ-ийн тэмдгээр (өртөг +, элэгдэл -)."""
        balances = defaultdict(float)
        assets = self.env['account.asset.asset'].search([
            ('company_id', '=', self.company_id.id),
            ('category_id', 'in', categories.ids),
            ('state', '!=', 'draft'),
            ('date', '<=', self.date),
        ])
        for asset in assets:
            # Бүрэн элэгдэж хаагдсан хөрөнгө данснаас хасагдаагүй тул ГБ-д үлдэнэ
            disposal_date = asset._mn_disposal_date()
            if disposal_date and disposal_date <= self.date:
                continue
            depreciation = sum(asset.depreciation_line_ids.filtered(
                lambda x: x.move_check and not x.is_sale_line and not x.is_scrap_line
                and x.depreciation_date <= self.date).mapped('amount'))
            balances[asset.category_id.account_asset_id] += asset.value
            balances[asset.category_id.account_depreciation_id] -= depreciation
        return balances

    def _get_gl_balances(self, domain):
        groups = self.env['account.move.line']._read_group(
            domain + [('company_id', '=', self.company_id.id),
                      ('parent_state', '=', 'posted'),
                      ('date', '<=', self.date)],
            ['account_id'], ['balance:sum'])
        return {account: balance for account, balance in groups}

    def _get_unmapped_balances(self):
        all_categories = self.env['account.asset.category'].search([('company_id', '=', self.company_id.id)])
        mapped_accounts = all_categories.mapped('account_asset_id') | all_categories.mapped('account_depreciation_id')
        unmapped = self._get_gl_balances([('account_id.account_type', '=', 'asset_fixed'),
                                          ('account_id', 'not in', mapped_accounts.ids)])
        currency = self.company_id.currency_id
        return {account: balance for account, balance in unmapped.items() if not currency.is_zero(balance)}

    def _get_warning(self):
        unmapped = self._get_unmapped_balances()
        if not unmapped:
            return False
        rows = ['%s %s: %s' % (account.code, account.name, '{:,.2f}'.format(balance))
                for account, balance in sorted(unmapped.items(), key=lambda x: x[0].code)]
        return _("Дараах үндсэн хөрөнгийн данс аль ч ангилалд холбогдоогүй ч үлдэгдэлтэй тул тулгалтад орохгүй. "
                 "Ангиллын дансыг засах эсвэл дахин ангилах бичилт хийнэ үү. "
                 "Санаатай орхих бол 'Холбогдоогүй дансыг үл тооцох'-ыг сонгоно уу:\n%s") % '\n'.join(rows)

    def action_compute(self):
        self.ensure_one()
        categories = self._get_categories()
        cost_accounts = categories.mapped('account_asset_id')
        accounts = cost_accounts | categories.mapped('account_depreciation_id')
        account_category = {}
        for category in categories:
            account_category.setdefault(category.account_asset_id, category)
            account_category.setdefault(category.account_depreciation_id, category)
        register = self._get_register_balances(categories)
        gl = self._get_gl_balances([('account_id', 'in', accounts.ids)])
        currency = self.company_id.currency_id
        self.line_ids = [(5, 0, 0)] + [(0, 0, {
            'account_id': account.id,
            'category_id': account_category[account].id,
            'account_kind': 'cost' if account in cost_accounts else 'depreciation',
            'register_balance': currency.round(register.get(account, 0.0)),
            'gl_balance': currency.round(gl.get(account, 0.0)),
        }) for account in accounts.sorted('code')]
        self.warning = self._get_warning()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('ҮХ-ийн бүртгэлийг ГБ-тэй тулгах'),
        }

    def action_create_move(self):
        self.ensure_one()
        # Хаагдсан онд (жишээ нь 2024, 2025) бичилт оруулахгүй
        lock_date = self.company_id._get_user_fiscal_lock_date()
        if lock_date and self.date <= lock_date:
            raise UserError(_('%s хүртэлх хугацаа хаагдсан тул залруулах бичилтийг түүнээс хойших огноогоор үүсгэнэ үү.')
                            % lock_date)
        # Холбогдоогүй дансны үлдэгдэл тулгалтын дараа ч ГБ-д давхар үлдэнэ
        if not self.ignore_unmapped and self._get_unmapped_balances():
            raise UserError(self._get_warning())
        self.action_compute()
        currency = self.company_id.currency_id
        label = _('ҮХ-ийн бүртгэлтэй тулгасан залруулга')
        move_lines = []
        total = 0.0
        for line in self.line_ids:
            amount = currency.round(line.difference)
            if currency.is_zero(amount):
                continue
            total += amount
            move_lines.append((0, 0, {
                'name': label,
                'account_id': line.account_id.id,
                'debit': amount if amount > 0 else 0.0,
                'credit': -amount if amount < 0 else 0.0,
            }))
        if not move_lines:
            raise UserError(_('Бүртгэл ба ГБ таарч байна, залруулах зүйл алга.'))
        total = currency.round(total)
        if not currency.is_zero(total):
            move_lines.append((0, 0, {
                'name': label,
                'account_id': self.offset_account_id.id,
                'debit': -total if total < 0 else 0.0,
                'credit': total if total > 0 else 0.0,
            }))
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': _('ҮХ-ийн бүртгэл ба ГБ-ийн тулгалт (%s)') % self.date,
            'line_ids': move_lines,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }


class AccountAssetGlReconcileLine(models.TransientModel):
    _name = 'account.asset.gl.reconcile.line'
    _description = 'Asset register to general ledger reconciliation line'

    wizard_id = fields.Many2one('account.asset.gl.reconcile', required=True, ondelete='cascade')
    category_id = fields.Many2one('account.asset.category', string='Ангилал')
    account_id = fields.Many2one('account.account', string='Данс', required=True)
    account_kind = fields.Selection([('cost', 'Өртөг'), ('depreciation', 'Хуримтлагдсан элэгдэл')], string='Төрөл')
    currency_id = fields.Many2one(related='wizard_id.company_id.currency_id')
    register_balance = fields.Monetary(string='Бүртгэлээр')
    gl_balance = fields.Monetary(string='ГБ-ээр')
    difference = fields.Monetary(string='Залруулах дүн', compute='_compute_difference')

    @api.depends('register_balance', 'gl_balance')
    def _compute_difference(self):
        for line in self:
            line.difference = line.register_balance - line.gl_balance
