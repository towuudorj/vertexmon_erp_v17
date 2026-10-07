# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import api, fields, models, _


class AccountMoveMissingProductConfirm(models.TransientModel):
    _name = 'account.move.missing.product.confirm'
    _description = 'Бараагүй мөртэй нэхэмжлэл батлах баталгаажуулалт'

    move_ids = fields.Many2many('account.move', string='Нэхэмжлэл')
    message = fields.Html(compute='_compute_message', sanitize=False)

    @api.depends('move_ids')
    def _compute_message(self):
        for wizard in self:
            items = Markup()
            for move in wizard.move_ids:
                # Дугаар нь нэхэмжлэлийн мөрүүдийн жагсаалтын ### дугаартай таарна
                for index, line in enumerate(move.invoice_line_ids, start=1):
                    if line.display_type != 'product' or line.product_id:
                        continue
                    items += Markup('<li><b>%s</b>: мөр %s — %s %s — %s</li>') % (
                        move.name or _('Ноорог'), index, line.account_id.code or '', line.account_id.name or '',
                        escape(line.name or ''),
                    )
            wizard.message = Markup('<p>Дараах нэхэмжлэлийн мөрөнд бараа сонгоогүй байна:</p><ul>%s</ul>'
                                    '<p>Бараагүйгээр батлахдаа итгэлтэй байна уу?</p>') % items

    def action_confirm(self):
        moves = self.move_ids
        missing_lines = moves._get_missing_product_lines()
        # Хэрэглэгч аль хэдийн баталгаажуулсан тул дахин шалгахгүй
        result = moves.with_context(check_missing_product=False).action_post()
        # Хэн, ямар мөрийг бараагүйгээр баталсныг chatter-т үлдээнэ
        for move in moves:
            lines = missing_lines.filtered(lambda line: line.move_id == move)
            if lines:
                body = Markup('<p>Бараа сонгоогүй мөртэйгээр баталсан:</p><ul>%s</ul>') % Markup().join(
                    Markup('<li>%s %s — %s</li>') % (line.account_id.code or '', line.account_id.name or '',
                                                     escape(line.name or ''))
                    for line in lines)
                move.message_post(body=body)
        return result or {'type': 'ir.actions.act_window_close'}
