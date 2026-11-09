# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class SupplyWriteoffWizard(models.TransientModel):
    _name = 'supply.writeoff.wizard'
    _description = 'Хугацаа дууссан хангамжийн ноорог хаах баримт үүсгэх'

    expire_date = fields.Date(
        string='Огноо', required=True, default=fields.Date.context_today,
        help='Энэ огноо гэхэд ашиглах хугацаа нь дууссан хангамжийг хаана.')
    partner_ids = fields.Many2many(
        'res.partner', string='Ажилтан',
        help='Хоосон бол бүх ажилтнаар шалгана.')

    def action_create_pickings(self):
        self.ensure_one()
        pickings, found = self.env['stock.picking']._create_expired_supply_writeoffs(
            expire_date=self.expire_date, partner_ids=self.partner_ids.ids or None)
        if not found:
            raise UserError(_('%s гэхэд ашиглах хугацаа нь дууссан хангамж олдсонгүй.\n'
                              'Барааны "Ашиглах хугацаа (сар)" талбар бөглөгдсөн эсэхийг шалгана уу.')
                            % self.expire_date)
        if not pickings:
            raise UserError(_('Хугацаа дууссан хангамжтай бүх ажилтан дээр батлагдаагүй '
                              '"Хангамж хаах" баримт аль хэдийн байна.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Хангамж хаах'),
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', pickings.ids)],
            'context': {'contact_display': 'partner_address'},
        }
