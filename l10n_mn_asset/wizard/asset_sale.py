# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAssetSale(models.TransientModel):
    _name = 'account.asset.sale'
    _description = 'Account asset sale'

    partner_id = fields.Many2one('res.partner', string='Худалдан авагч', required=True)
    sale_date = fields.Date(string='Огноо', required=True, default=fields.Date.context_today)
    sale_price = fields.Float(string='Борлуулсан үнэ (НӨАТ-гүй)', required=True)
    vat_percent = fields.Float(string='НӨАТ хувь', default=10.0)
    vat_account_id = fields.Many2one('account.account', string='НӨАТ-ын өглөгийн данс', required=True)
    receivable_account_id = fields.Many2one('account.account', string='Дансны авлага', required=True)
    journal_id = fields.Many2one('account.journal', string='Журнал', required=True)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id.property_account_receivable_id:
            self.receivable_account_id = self.partner_id.property_account_receivable_id

    def action_sell(self):
        asset_obj = self.env['account.asset.asset']
        depreciation_line_obj = self.env['account.asset.depreciation.line']
        asset = asset_obj.browse(self.env.context.get('active_id'))

        if asset.salvage_value:
            raise UserError(_(
                "Энэ хөрөнгөд Хаягдлын үнэ (Salvage value) тохируулагдсан байна. "
                "Одоогоор зөвхөн Хаягдлын үнэгүй хөрөнгийг зарах боломжтой."
            ))

        category = asset.category_id
        if not category.account_asset_gain_id or not category.account_asset_loss_id:
            raise UserError(_(
                "'%s' ангилалд Үндсэн хөрөнгө данснаас хассаны Олз/Гарзын данс тохируулагдаагүй байна."
            ) % category.name)

        unposted_depreciation_lines = asset.depreciation_line_ids.filtered(lambda dep_line: not dep_line.move_check)

        old_values = {
            'method_end': asset.method_end,
            'method_number': asset.method_number,
        }

        accumulated_depreciation = asset.value - asset.salvage_value - asset.value_residual
        vat_amount = self.sale_price * self.vat_percent / 100.0
        receivable_amount = self.sale_price + vat_amount
        gain_loss_amount = asset.value_residual - self.sale_price

        move_lines = [
            (0, 0, {
                'name': asset.name,
                'account_id': self.receivable_account_id.id,
                'partner_id': self.partner_id.id,
                'debit': receivable_amount,
                'credit': 0.0,
            }),
            (0, 0, {
                'name': asset.name,
                'account_id': category.account_depreciation_id.id,
                'debit': accumulated_depreciation,
                'credit': 0.0,
            }),
        ]

        if gain_loss_amount > 0:
            move_lines.append((0, 0, {
                'name': asset.name,
                'account_id': category.account_asset_loss_id.id,
                'debit': gain_loss_amount,
                'credit': 0.0,
            }))

        if vat_amount:
            move_lines.append((0, 0, {
                'name': asset.name,
                'account_id': self.vat_account_id.id,
                'partner_id': self.partner_id.id,
                'debit': 0.0,
                'credit': vat_amount,
            }))

        if gain_loss_amount < 0:
            move_lines.append((0, 0, {
                'name': asset.name,
                'account_id': category.account_asset_gain_id.id,
                'debit': 0.0,
                'credit': -gain_loss_amount,
            }))

        move_lines.append((0, 0, {
            'name': asset.name,
            'account_id': category.account_asset_id.id,
            'debit': 0.0,
            'credit': asset.value,
        }))

        move = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
            'date': self.sale_date,
            'ref': asset.name,
            'partner_id': self.partner_id.id,
            'move_type': 'entry',
            'line_ids': move_lines,
        })

        sequence = len(asset.depreciation_line_ids) - len(unposted_depreciation_lines) + 1
        unposted_depreciation_lines.unlink()
        depreciation_line_obj.create({
            'amount': asset.value_residual,
            'asset_id': asset.id,
            'sequence': sequence,
            'move_id': move.id,
            'is_sale_line': True,
            'name': (asset.code or '') + '/' + str(sequence),
            'remaining_value': 0,
            'depreciated_value': asset.value - asset.salvage_value,
            'depreciation_date': self.sale_date,
        })

        fresh_asset = asset_obj.browse(asset.id)
        fresh_asset.write({
            'method_end': self.sale_date,
            'method_number': sequence,
            'state': 'close',
            'is_closed': True,
        })
        tracked_fields = asset_obj.fields_get(['method_number', 'method_end'])
        changes, tracking_value_ids = fresh_asset._mail_track(tracked_fields, old_values)
        if changes:
            fresh_asset.message_post(
                subject=_('Asset sold. Accounting entry awaiting for validation.'),
                tracking_value_ids=tracking_value_ids)

        return {
            'name': _('Journal Entry'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'res_id': move.id,
        }
