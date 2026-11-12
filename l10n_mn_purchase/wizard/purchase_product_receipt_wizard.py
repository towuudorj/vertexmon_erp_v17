# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class PurchaseProductReceiptWizard(models.TransientModel):
    """ Олон худалдан авалтын захиалгын хүлээгдэж буй орлогыг бараагаар нь
    нэгтгэж (шүүлт/бүлэглэлттэй жагсаалтаар) харуулаад, сонгосон бараануудыг
    хүлээн авах баримт бүрээс тусад нь салгаж хүлээн авна. """
    _name = 'purchase.product.receipt.wizard'
    _description = 'Худалдан авалтыг бараагаар хүлээн авах'

    order_ids = fields.Many2many('purchase.order', string='Худалдан авалтын захиалгууд')
    line_ids = fields.One2many('purchase.product.receipt.wizard.line', 'wizard_id', string='Бараа')
    selected_line_ids = fields.Many2many('purchase.product.receipt.wizard.line', compute='_compute_totals',
                                         string='Хүлээн авах бараа')
    date_receive = fields.Datetime('Хүлээн авах огноо', default=fields.Datetime.now)
    currency_id = fields.Many2one('res.currency', string='Валют', compute='_compute_totals')
    multi_currency = fields.Boolean('Олон валют', compute='_compute_totals')
    selected_count = fields.Integer('Сонгосон бараа', compute='_compute_totals')
    selected_qty = fields.Float('Хүлээн авах нийт тоо', compute='_compute_totals', digits='Product Unit of Measure')
    selected_amount = fields.Monetary('Хүлээн авах нийт дүн', compute='_compute_totals')

    @api.depends('line_ids.selected', 'line_ids.qty_to_receive', 'line_ids.amount_to_receive')
    def _compute_totals(self):
        for wiz in self:
            selected = wiz.line_ids.filtered('selected')
            currencies = selected.currency_id
            wiz.selected_line_ids = selected
            wiz.selected_count = len(selected)
            wiz.selected_qty = sum(selected.mapped('qty_to_receive'))
            wiz.multi_currency = len(currencies) > 1
            wiz.currency_id = currencies[:1]
            # Олон валют холилдсон бол нийлбэр дүн утгагүй тул тооцохгүй
            wiz.selected_amount = 0.0 if len(currencies) > 1 else sum(selected.mapped('amount_to_receive'))

    # ------------------------------------------------------------------
    # Нээх: мөрүүдийг сервер дээр урьдчилан үүсгэж, шүүлттэй жагсаалтаар нээнэ
    # ------------------------------------------------------------------
    @api.model
    def action_open(self, records):
        if records._name == 'purchase.order':
            orders = records
        elif records._name == 'purchase.order.line':
            orders = records.order_id
        else:
            orders = self.env['purchase.order']
        if not orders:
            raise UserError(_('Худалдан авалтын захиалга сонгоно уу.'))
        not_confirmed = orders.filtered(lambda o: o.state not in ('purchase', 'done'))
        if not_confirmed:
            raise UserError(_('Дараах захиалгууд батлагдаагүй байна: %s') % ', '.join(not_confirmed.mapped('name')))
        if len(orders.company_id) > 1:
            raise UserError(_('Өөр өөр компанийн захиалгыг хамт сонгох боломжгүй.'))

        wizard = self.create({
            'order_ids': [(6, 0, orders.ids)],
            'line_ids': [(0, 0, vals) for vals in self._prepare_line_vals(orders)],
        })
        return wizard._action_open_lines()

    def _action_open_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Бараагаар хүлээн авах: %s') % ', '.join(self.order_ids.mapped('name')),
            'res_model': 'purchase.product.receipt.wizard.line',
            'view_mode': 'tree',
            'views': [(self.env.ref('l10n_mn_purchase.purchase_product_receipt_line_tree').id, 'list')],
            'search_view_id': [self.env.ref('l10n_mn_purchase.purchase_product_receipt_line_search').id],
            'domain': [('wizard_id', '=', self.id)],
            'context': {'search_default_pending': 1, 'create': False, 'delete': False,
                        'receipt_wizard_id': self.id},
            'limit': 500,
            'target': 'current',
        }

    def action_open_receive_dialog(self):
        """ Жагсаалтад сонгосон (Сонгох талбар) мөрүүдээр хүлээн авах огноо сонгох цонхыг нээнэ """
        self.ensure_one()
        self._get_lines_to_process()
        self.date_receive = fields.Datetime.now()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Хүлээн авах'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('l10n_mn_purchase.purchase_product_receipt_wizard_form').id, 'form')],
            'target': 'new',
            'context': {'dialog_size': 'extra-large'},
        }

    @api.model
    def _pending_moves(self, po_lines):
        """ Хүлээн авах боломжтой (батлагдаагүй, эхэлж хүлээн аваагүй) орлогын хөдөлгөөнүүд """
        return po_lines.move_ids.filtered(
            lambda m: m.state not in ('draft', 'done', 'cancel')
            and m.picking_id
            and m.picking_id.state not in ('done', 'cancel')
            and m.picking_code == 'incoming'
            and not m.picked
            and not m.move_line_ids.filtered('picked')
        )

    @api.model
    def _prepare_line_vals(self, orders):
        # Захиалга + бараа тус бүрээр мөр (өөр захиалгуудын барааг нийлүүлэхгүй).
        # Дүн нь захиалгын валютаар (хөрвүүлэхгүй).
        by_product = defaultdict(lambda: self.env['purchase.order.line'])
        for line in orders.order_line:
            if line.display_type or not line.product_id or line.product_id.type not in ('product', 'consu'):
                continue
            by_product[(line.order_id, line.product_id)] |= line

        vals_list = []
        for (order, product), po_lines in by_product.items():
            uom = product.uom_id
            ordered = sum(l.product_uom._compute_quantity(l.product_qty, uom) for l in po_lines)
            received = sum(l.product_uom._compute_quantity(l.qty_received, uom) for l in po_lines)
            moves = self._pending_moves(po_lines)
            pending = sum(moves.mapped('product_qty'))
            # Хүлээгдэж буй дүн — захиалгын валютаар
            pending_amount = 0.0
            for line in po_lines:
                line_moves = moves.filtered(lambda m: m.purchase_line_id == line)
                if not line_moves or float_is_zero(line.product_qty, precision_rounding=line.product_uom.rounding):
                    continue
                line_qty = sum(line_moves.mapped('product_qty'))
                qty_in_line_uom = uom._compute_quantity(line_qty, line.product_uom)
                pending_amount += line.price_subtotal / line.product_qty * qty_in_line_uom
            vals_list.append({
                'product_id': product.id,
                'uom_id': uom.id,
                'currency_id': order.currency_id.id,
                'order_id': order.id,
                'partner_id': order.partner_id.id,
                'ordered_qty': ordered,
                'received_qty': received,
                'pending_qty': pending,
                'qty_to_receive': pending,
                'pending_amount': pending_amount,
            })
        Order = self.env['purchase.order']
        Product = self.env['product.product']
        vals_list.sort(key=lambda v: (not v['pending_qty'], Order.browse(v['order_id']).name or '',
                                      Product.browse(v['product_id']).display_name or ''))
        return vals_list

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_create_receipts(self):
        """ Зөвхөн салгана: сонгосон бараануудаар шинэ хүлээн авах баримт (Бэлэн төлөвтэй) үүсгэнэ """
        self.ensure_one()
        new_pickings = self._split_into_pickings()
        self._refresh_lines()
        return self._action_view_pickings(new_pickings)

    def action_receive(self):
        """ Салгаад шууд хүлээн авна (батална). Үлдсэн бараа эх баримтдаа Бэлэн төлөвтэй үлдэнэ. """
        self.ensure_one()
        if not self.date_receive:
            raise UserError(_('Хүлээн авах огноог оруулна уу.'))
        if self.date_receive > fields.Datetime.now():
            raise UserError(_('Хүлээн авах огноо ирээдүйд байж болохгүй.'))
        date_receive = self.date_receive
        new_pickings = self._split_into_pickings()
        # zero_stock_effective_date: date_done нь scheduled_date-ээс тооцогдож, бичилтийн огноо болно
        new_pickings.write({'scheduled_date': date_receive})
        for picking in new_pickings:
            for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                if float_compare(move.quantity, move.product_uom_qty, precision_rounding=move.product_uom.rounding) != 0:
                    move.quantity = move.product_uom_qty
                move.picked = True
        for picking in new_pickings:
            picking.date_done = date_receive
            res = picking.with_context(force_period_date=date_receive.date()).button_validate()
            # Цуврал/багцын дугаар гэх мэт нэмэлт мэдээлэл шаардсан цонх гарвал хэрэглэгчид харуулна
            if isinstance(res, dict) and res.get('type') == 'ir.actions.act_window' and res.get('target') == 'new':
                return res
        self._apply_receive_date(new_pickings.filtered(lambda p: p.state == 'done'), date_receive)
        self._refresh_lines()
        return self._action_view_pickings(new_pickings)

    def _refresh_lines(self):
        """ Жагсаалт руу буцаж ороход тоо хэмжээ шинэчлэгдсэн байхаар мөрүүдийг дахин тооцно """
        new_vals = {(v['order_id'], v['product_id']): v for v in self._prepare_line_vals(self.order_ids)}
        for line in self.line_ids:
            vals = new_vals.get((line.order_id.id, line.product_id.id))
            if vals:
                line.write({k: vals[k] for k in ('ordered_qty', 'received_qty', 'pending_qty',
                                                 'qty_to_receive', 'pending_amount')} | {'selected': False})

    @api.model
    def _apply_receive_date(self, pickings, date):
        """ Батлагдсан баримт, хөдөлгөөн, хөдөлгөөний мөрүүдийн огноог сонгосон огноогоор тавина """
        if not pickings:
            return
        pickings.write({'date_done': date})
        pickings.move_ids.filtered(lambda m: m.state == 'done').write({'date': date})
        pickings.move_ids.move_line_ids.write({'date': date})

    def _get_lines_to_process(self):
        lines = self.line_ids.filtered(lambda l: l.selected and float_compare(
            l.qty_to_receive, 0.0, precision_rounding=l.uom_id.rounding) > 0)
        if not lines:
            raise UserError(_('Хүлээн авах бараа сонгож, тоо хэмжээг оруулна уу.'))
        return lines

    def _split_into_pickings(self):
        """ Сонгосон бараануудын хүлээгдэж буй хөдөлгөөнийг эх баримтаас нь салгаж
        шинэ баримт(ууд)-д шилжүүлнэ. Шинэ баримтуудыг буцаана. """
        lines = self._get_lines_to_process()

        # key -> нэг шинэ баримтад орох stock.move-ууд
        groups = defaultdict(lambda: self.env['stock.move'])
        old_pickings = self.env['stock.picking']
        for line in lines:
            product = line.product_id
            rounding = line.uom_id.rounding
            po_lines = line.order_id.order_line.filtered(lambda l: l.product_id == product)
            moves = self._pending_moves(po_lines).sorted(
                lambda m: (m.date or fields.Datetime.now(), m.id))
            pending = sum(moves.mapped('product_qty'))
            if float_compare(line.qty_to_receive, pending, precision_rounding=rounding) > 0:
                raise UserError(_('%(product)s: хүлээн авах тоо (%(qty)s) нь хүлээгдэж буй тооноос (%(pending)s) их байна. '
                                  'Жагсаалтыг хаагаад дахин нээнэ үү.') % {
                    'product': product.display_name, 'qty': line.qty_to_receive, 'pending': pending})

            remaining = line.qty_to_receive
            for move in moves:
                if float_compare(remaining, 0.0, precision_rounding=rounding) <= 0:
                    break
                old_pickings |= move.picking_id
                move._do_unreserve()
                take = min(remaining, move.product_qty)
                rest = move.product_qty - take
                if float_compare(rest, 0.0, precision_rounding=rounding) > 0:
                    # Үлдэгдлийг эх баримтад шинэ хөдөлгөөн болгон үлдээж,
                    # анхны хөдөлгөөнийг (take тоотой) шинэ баримт руу шилжүүлнэ.
                    new_vals = move._split(rest)
                    if new_vals:
                        self.env['stock.move'].create(new_vals)._action_confirm(merge=False)
                remaining -= take
                # Эх хүлээн авах баримт бүрээс тусдаа шинэ баримт
                groups[move.picking_id] |= move

        new_pickings = self.env['stock.picking']
        for source, moves in groups.items():
            other_moves = source.move_ids.filtered(lambda m: m.state != 'cancel') - moves
            if not other_moves:
                # Эх баримтын бүх бараа сонгогдсон бол шинэ баримт үүсгэлгүй эх баримтыг нь ашиглана
                new_pickings |= source
                continue
            picking = self.env['stock.picking'].create({
                'picking_type_id': source.picking_type_id.id,
                'location_id': source.location_id.id,
                'location_dest_id': source.location_dest_id.id,
                'partner_id': source.partner_id.id,
                'origin': source.origin,
                'scheduled_date': self.date_receive or min(moves.mapped('date')),
                'company_id': source.company_id.id,
                'user_id': self.env.user.id,
                'move_type': source.move_type,
            })
            sources = moves.picking_id
            moves.write({'picking_id': picking.id})
            if len(sources) == 1:
                self._copy_signature_users(sources, picking)
            picking.message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': picking, 'origin': sources},
                subtype_xmlid='mail.mt_note',
            )
            new_pickings |= picking

        new_pickings.filtered(lambda p: p.state not in ('done', 'cancel')).action_assign()

        # Бүх хөдөлгөөнөө алдсан эх баримтуудыг устгаж, үлдсэнийг дахин нөөцлөнө (Бэлэн төлөв)
        old_pickings = old_pickings - new_pickings
        empty = old_pickings.filtered(lambda p: not p.move_ids)
        (old_pickings - empty).filtered(lambda p: p.state not in ('done', 'cancel')).action_assign()
        if empty:
            empty.unlink()
        return new_pickings

    @api.model
    def _copy_signature_users(self, source, picking):
        """ l10n_mn_stock суусан бол эх баримтын гарын үсгийн хүмүүсийг шинэ баримтад хуулна """
        if 'signature_user_ids' not in picking._fields or not source.signature_user_ids:
            return
        picking.signature_user_ids.sudo().unlink()
        for sig in source.signature_user_ids:
            sig.sudo().copy({'picking_id': picking.id})

    def _action_view_pickings(self, pickings):
        action = self.env['ir.actions.actions']._for_xml_id('stock.action_picking_tree_all')
        if len(pickings) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        else:
            action['domain'] = [('id', 'in', pickings.ids)]
        action['context'] = {'create': False}
        return action


class PurchaseProductReceiptWizardLine(models.TransientModel):
    _name = 'purchase.product.receipt.wizard.line'
    _description = 'Худалдан авалтыг бараагаар хүлээн авах мөр'
    _order = 'id'
    _rec_name = 'product_id'

    wizard_id = fields.Many2one('purchase.product.receipt.wizard', required=True, ondelete='cascade')
    selected = fields.Boolean('Сонгосон')
    product_id = fields.Many2one('product.product', 'Бараа', required=True)
    uom_id = fields.Many2one('uom.uom', 'Х.нэгж')
    order_id = fields.Many2one('purchase.order', string='Захиалга')
    partner_id = fields.Many2one('res.partner', string='Нийлүүлэгч')
    ordered_qty = fields.Float('Захиалсан', digits='Product Unit of Measure')
    received_qty = fields.Float('Хүлээн авсан', digits='Product Unit of Measure')
    pending_qty = fields.Float('Хүлээгдэж буй', digits='Product Unit of Measure')
    qty_to_receive = fields.Float('Хүлээн авах тоо', digits='Product Unit of Measure')
    currency_id = fields.Many2one('res.currency', string='Валют')
    pending_amount = fields.Monetary('Хүлээгдэж буй дүн')
    amount_to_receive = fields.Monetary('Хүлээн авах дүн', compute='_compute_amount_to_receive', store=True)

    @api.depends('qty_to_receive', 'pending_qty', 'pending_amount')
    def _compute_amount_to_receive(self):
        for line in self:
            if line.pending_qty:
                line.amount_to_receive = line.pending_amount / line.pending_qty * line.qty_to_receive
            else:
                line.amount_to_receive = 0.0

    @api.onchange('qty_to_receive')
    def _onchange_qty_to_receive(self):
        for line in self:
            if line.qty_to_receive < 0:
                line.qty_to_receive = 0.0
            if float_compare(line.qty_to_receive, line.pending_qty, precision_rounding=line.uom_id.rounding or 0.01) > 0:
                line.qty_to_receive = line.pending_qty
                return {'warning': {
                    'title': _('Анхааруулга'),
                    'message': _('Хүлээн авах тоо хүлээгдэж буй тооноос их байж болохгүй.'),
                }}

    @api.model
    def get_receipt_summary(self, wizard_id):
        """ Шүүлтээс үл хамааран тухайн жагсаалтын бүх сонгосон мөрийн нийлбэр (JS header-т) """
        lines = self.search([('wizard_id', '=', wizard_id), ('selected', '=', True)])
        amounts = defaultdict(float)
        for line in lines:
            amounts[line.currency_id.id] += line.amount_to_receive
        return {
            'count': len(lines),
            'qty': sum(lines.mapped('qty_to_receive')),
            'amounts': [[currency_id, amount] for currency_id, amount in amounts.items()],
        }
