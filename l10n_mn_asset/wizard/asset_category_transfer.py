# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAssetCategoryTransfer(models.TransientModel):
    _name = 'account.asset.category.transfer'
    _description = 'Account asset category transfer'

    asset_id = fields.Many2one('account.asset.asset', string='Хөрөнгө', required=True, readonly=True,
                               default=lambda self: self.env.context.get('active_id'))
    old_category_id = fields.Many2one('account.asset.category', related='asset_id.category_id', string='Одоогийн ангилал')
    category_id = fields.Many2one('account.asset.category', string='Шинэ ангилал', required=True,
                                  domain="[('type', '=', 'purchase'), ('id', '!=', old_category_id)]")
    transfer_date = fields.Date(string='Шилжүүлэх огноо', required=True, default=fields.Date.context_today)
    depreciation_months = fields.Integer(
        string='Элэгдүүлэх сар',
        help="Үлдэгдэл өртгийг хэдэн сараар элэгдүүлж дуусгах. "
             "0 байвал шинэ ангиллын тохируулсан хугацааг ашиглана.")
    journal_id = fields.Many2one('account.journal', string='Журнал', required=True,
                                 default=lambda self: self._default_journal())

    @api.model
    def _default_journal(self):
        asset = self.env['account.asset.asset'].browse(self.env.context.get('active_id'))
        return asset.category_id.journal_id

    def action_transfer(self):
        self.ensure_one()
        asset_obj = self.env['account.asset.asset']
        line_obj = self.env['account.asset.depreciation.line']
        asset = self.asset_id
        old_category = asset.category_id
        new_category = self.category_id

        if asset.state != 'open':
            raise UserError(_("Зөвхөн 'Ашиглагдаж буй' төлөвтэй хөрөнгийн ангиллыг шилжүүлнэ."))
        if asset.salvage_value:
            raise UserError(_("Энэ хөрөнгөд Хаягдлын үнэ (Salvage value) тохируулагдсан байна. "
                              "Одоогоор зөвхөн Хаягдлын үнэгүй хөрөнгийг шилжүүлэх боломжтой."))
        if new_category == old_category:
            raise UserError(_("Шинэ ангилал одоогийн ангилалтай ижил байна."))
        if self.depreciation_months < 0:
            raise UserError(_("Элэгдүүлэх сар сөрөг байж болохгүй."))

        posted = asset.depreciation_line_ids.filtered(lambda l: l.move_check)
        if posted and max(posted.mapped('depreciation_date')) > self.transfer_date:
            raise UserError(_("Шилжүүлэх огнооноос хойших огноотой батлагдсан элэгдлийн бичилт байна."))

        residual = asset.value_residual
        if residual <= 0:
            raise UserError(_("Хөрөнгийн үлдэгдэл өртөг 0 байна."))
        gross = asset.value + asset.write_up
        accumulated = gross - residual

        move_lines = []
        if accumulated:
            move_lines.append((0, 0, {
                'name': asset.name,
                'account_id': old_category.account_depreciation_id.id,
                'debit': accumulated,
                'credit': 0.0,
            }))
        move_lines.append((0, 0, {
            'name': asset.name,
            'account_id': new_category.account_asset_id.id,
            'debit': residual,
            'credit': 0.0,
        }))
        move_lines.append((0, 0, {
            'name': asset.name,
            'account_id': old_category.account_asset_id.id,
            'debit': 0.0,
            'credit': gross,
        }))
        move = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
            'date': self.transfer_date,
            'ref': _('Ангилал шилжүүлэх: %s') % asset.name,
            'move_type': 'entry',
            'line_ids': move_lines,
        })

        # Хуучин хөрөнгийг 0 болгож хаах
        unposted = asset.depreciation_line_ids.filtered(lambda l: not l.move_check)
        sequence = len(asset.depreciation_line_ids) - len(unposted) + 1
        unposted.unlink()
        line_obj.create({
            'amount': residual,
            'asset_id': asset.id,
            'sequence': sequence,
            'move_id': move.id,
            'is_sale_line': True,
            'name': (asset.code or '') + '/' + str(sequence),
            'remaining_value': 0,
            'depreciated_value': gross,
            'depreciation_date': self.transfer_date,
        })
        asset.write({
            'method_end': self.transfer_date,
            'method_number': sequence,
            'state': 'close',
            'is_closed': True,
        })
        asset.message_post(body=_("Ангилал шилжүүлэв: %s → %s. Журнал: %s") % (
            old_category.name, new_category.name, move.name or move.id))

        # Үлдэгдэл өртгөөр шинэ хөрөнгө үүсгэх
        vals = {
            'name': asset.name,
            'code': asset.code,
            'category_id': new_category.id,
            'value': residual,
            'date': self.transfer_date,
            'first_depreciation_manual_date': self.transfer_date,
            'company_id': asset.company_id.id,
            'currency_id': asset.currency_id.id,
            'partner_id': asset.partner_id.id,
            'owner_id': asset.owner_id.id,
            'asset_location_id': asset.asset_location_id.id,
            'uom_id': asset.uom_id.id,
            'asset_qty': asset.asset_qty,
            'product_id': asset.product_id.id,
            'serial_number': asset.serial_number,
            'note': asset.note,
        }
        vals.update(asset_obj.onchange_category_id_values(new_category.id)['value'])
        if self.depreciation_months:
            vals.update({
                'method_time': 'number',
                'method_number': self.depreciation_months,
                'method_period': 1,
                'method_end': False,
                'prorata': False,
            })
        new_asset = asset_obj.create(vals)
        new_asset.message_post(body=_("'%s' хөрөнгийн ангилал шилжүүлэлтээс үүссэн (үлдэгдэл өртгөөр).") % asset.name)
        new_asset.validate()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset.asset',
            'view_mode': 'form',
            'res_id': new_asset.id,
        }
