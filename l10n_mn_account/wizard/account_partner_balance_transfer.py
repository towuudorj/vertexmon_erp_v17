# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class AccountPartnerBalanceTransfer(models.TransientModel):
    """Нэг дансны доторх харилцагчдын үлдэгдлийг нэг харилцагч (эсвэл харилцагчгүй) руу эсрэг
    бичилтээр шилжүүлж тэглэнэ. Дансны нийт үлдэгдэл өөрчлөгдөхгүй."""
    _name = 'account.partner.balance.transfer'
    _description = 'Partner balance transfer'

    company_id = fields.Many2one('res.company', string='Компани', required=True, default=lambda self: self.env.company)
    account_ids = fields.Many2many('account.account', string='Данс', required=True,
                                   domain="[('company_id', '=', company_id), "
                                          "('account_type', 'in', ('asset_receivable', 'asset_prepayments', 'liability_payable'))]")
    date = fields.Date(string='Огноо', required=True, default=fields.Date.context_today,
                       help='Энэ огноо хүртэлх (огноог оролцуулан) үлдэгдлийг шилжүүлж, бичилтийг энэ огноогоор үүсгэнэ.')
    journal_id = fields.Many2one('account.journal', string='Журнал', required=True,
                                 domain="[('type', '=', 'general'), ('company_id', '=', company_id)]")
    target_partner_id = fields.Many2one('res.partner', string='Үлдэгдэл төвлөрүүлэх харилцагч',
                                        help='Бусад харилцагчийн үлдэгдэл энэ харилцагч руу шилжинэ. '
                                             'Хоосон бол харилцагчгүй мөр рүү шилжинэ.')
    available_partner_ids = fields.Many2many('res.partner', compute='_compute_available_partner_ids')
    partner_ids = fields.Many2many('res.partner', string='Тэглэх харилцагчид',
                                   domain="[('id', 'in', available_partner_ids)]",
                                   help='Хоосон бол дансны бүх харилцагчийн (харилцагчгүй мөр орно) үлдэгдлийг шилжүүлнэ. '
                                        'Зөвхөн сонгосон дансанд огноо хүртэл үлдэгдэлтэй харилцагчид сонгогдоно.')
    include_no_partner = fields.Boolean(string='Харилцагчгүй үлдэгдлийг оруулах', default=True,
                                        help='Тэглэх харилцагчид сонгосон үед харилцагчгүй үлдэгдлийг мөн шилжүүлэх эсэх.')
    ref = fields.Char(string='Тайлбар', default='Харилцагчийн үлдэгдэл шилжүүлэг')
    auto_reconcile = fields.Boolean(string='Автоматаар тулгах', default=True,
                                    help='Тэглэсэн харилцагч бүрийн шинэ мөрийг тухайн харилцагчийн тулгагдаагүй '
                                         'хуучин мөрүүдтэй тулгана (тулгалт хийгддэг дансанд).')
    line_ids = fields.One2many('account.partner.balance.transfer.line', 'wizard_id', string='Шилжүүлэх үлдэгдэл')

    @api.depends('account_ids', 'date', 'company_id')
    def _compute_available_partner_ids(self):
        for wizard in self:
            partners = self.env['res.partner']
            if wizard.account_ids and wizard.date:
                rounding = wizard.company_id.currency_id.rounding
                partners = self.env['res.partner'].browse([
                    partner_id for (_account_id, partner_id), balance in wizard._get_balances().items()
                    if partner_id and not float_is_zero(balance, precision_rounding=rounding)
                ])
            wizard.available_partner_ids = partners

    def _get_balances(self):
        """{(account_id, partner_id or False): balance} - огноо хүртэлх батлагдсан үлдэгдэл."""
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('account_id', 'in', self.account_ids.ids),
            ('parent_state', '=', 'posted'),
            ('date', '<=', self.date),
        ]
        groups = self.env['account.move.line']._read_group(domain, ['account_id', 'partner_id'], ['balance:sum'])
        return {(account.id, partner.id or False): balance for account, partner, balance in groups}

    def action_compute(self):
        self.ensure_one()
        rounding = self.company_id.currency_id.rounding
        target_id = self.target_partner_id.id or False
        vals = []
        for (account_id, partner_id), balance in self._get_balances().items():
            if partner_id == target_id or float_is_zero(balance, precision_rounding=rounding):
                continue
            if self.partner_ids:
                selected = (partner_id in self.partner_ids.ids) or (not partner_id and self.include_no_partner)
                if not selected:
                    continue
            vals.append((0, 0, {'account_id': account_id, 'partner_id': partner_id, 'balance': balance}))
        self.line_ids = [(5, 0, 0)] + vals
        if not vals:
            raise UserError(_('Шилжүүлэх үлдэгдэл олдсонгүй.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_move(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Эхлээд "Тооцоолох" дарж шилжүүлэх үлдэгдлийг гаргана уу.'))
        currency = self.company_id.currency_id
        target_id = self.target_partner_id.id or False
        move_lines = []
        totals = {}
        for line in self.line_ids:
            if currency.is_zero(line.balance):
                continue
            # Харилцагчийн үлдэгдлийг эсрэг дүнгээр тэглэнэ
            move_lines.append((0, 0, {
                'account_id': line.account_id.id,
                'partner_id': line.partner_id.id or False,
                'name': self.ref,
                'debit': -line.balance if line.balance < 0 else 0.0,
                'credit': line.balance if line.balance > 0 else 0.0,
            }))
            totals[line.account_id] = totals.get(line.account_id, 0.0) + line.balance
        # Данс бүрийн нийлбэрийг төвлөрүүлэх харилцагч руу шилжүүлнэ
        for account, total in totals.items():
            if currency.is_zero(total):
                continue
            move_lines.append((0, 0, {
                'account_id': account.id,
                'partner_id': target_id,
                'name': self.ref,
                'debit': total if total > 0 else 0.0,
                'credit': -total if total < 0 else 0.0,
            }))
        if not move_lines:
            raise UserError(_('Шилжүүлэх үлдэгдэл олдсонгүй.'))
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': self.date,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'ref': self.ref,
            'line_ids': move_lines,
        })
        # Харилцагчгүй үлдэгдлийг тэглэх/хүлээн авах мөр харилцагчгүй байх ёстой тул шалгалтыг алгасна
        move.with_context(skip_receivable_payable_partner_check=True).action_post()
        if self.auto_reconcile:
            self._reconcile_transferred(move, target_id)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }


    def _reconcile_transferred(self, move, target_id):
        """Тэглэсэн (дансны, харилцагчийн) шинэ мөрийг огноо хүртэлх тулгагдаагүй мөрүүдтэй тулгана.
        Төвлөрүүлэх харилцагчийн мөрийг тулгахгүй: түүний үлдэгдэл тэглэгдэхгүй."""
        AML = self.env['account.move.line']
        for new_line in move.line_ids:
            partner_id = new_line.partner_id.id or False
            if partner_id == target_id or not new_line.account_id.reconcile:
                continue
            open_lines = AML.search([
                ('company_id', '=', self.company_id.id),
                ('account_id', '=', new_line.account_id.id),
                ('partner_id', '=', partner_id),
                ('parent_state', '=', 'posted'),
                ('date', '<=', self.date),
                ('reconciled', '=', False),
                ('move_id', '!=', move.id),
            ])
            if open_lines:
                (open_lines | new_line).reconcile()

class AccountPartnerBalanceTransferLine(models.TransientModel):
    _name = 'account.partner.balance.transfer.line'
    _description = 'Partner balance transfer line'

    wizard_id = fields.Many2one('account.partner.balance.transfer', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Данс', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Харилцагч', readonly=True)
    balance = fields.Float(string='Үлдэгдэл', readonly=True, digits='Account')
