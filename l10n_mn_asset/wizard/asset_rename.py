# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError

RENAME_FIELDS = [('name', 'Хөрөнгийн нэр'), ('code', 'Хөрөнгийн код')]


class AccountAssetRename(models.TransientModel):
    """Хөрөнгийн нэр/кодыг хуучин → шинэ утгаар солиж, chatter-т бүртгэнэ."""
    _name = 'account.asset.rename'
    _description = 'Хөрөнгийн нэр, код өөрчлөх'

    asset_id = fields.Many2one('account.asset.asset', string='Хөрөнгө', required=True, readonly=True)
    field_name = fields.Selection(RENAME_FIELDS, string='Талбар', required=True, readonly=True)
    old_value = fields.Char(string='Хуучин утга', compute='_compute_old_value')
    new_value = fields.Char(string='Шинэ утга')
    reason = fields.Text(string='Шалтгаан')

    @api.depends('asset_id', 'field_name')
    def _compute_old_value(self):
        for wizard in self:
            wizard.old_value = wizard.asset_id[wizard.field_name] if wizard.asset_id and wizard.field_name else False

    def action_apply(self):
        self.ensure_one()
        new_value = (self.new_value or '').strip()
        label = dict(RENAME_FIELDS)[self.field_name]
        if self.field_name == 'name' and not new_value:
            raise UserError(_('Шинэ нэрийг оруулна уу.'))
        if self.field_name == 'code' and len(new_value) > 32:
            raise UserError(_('Хөрөнгийн код 32 тэмдэгтээс ихгүй байна.'))
        if new_value == (self.old_value or ''):
            raise UserError(_('Шинэ утга хуучинтай ижил байна.'))
        old_value = self.old_value or ''
        # Давхар лог үүсгэхгүйн тулд tracking-ийг унтрааж, шалтгаантай нэг мессеж бичнэ
        self.asset_id.with_context(mail_notrack=True).write({self.field_name: new_value or False})
        body = Markup('<b>%s</b>: %s → %s') % (label, old_value or '-', new_value or '-')
        if self.reason:
            body += Markup('<br/>%s: %s') % (_('Шалтгаан'), self.reason)
        self.asset_id.message_post(body=body)
        return {'type': 'ir.actions.act_window_close'}
