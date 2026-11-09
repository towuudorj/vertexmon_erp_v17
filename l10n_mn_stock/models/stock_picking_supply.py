# -*- coding: utf-8 -*-
import logging
from collections import defaultdict

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class StockPickingSupply(models.Model):
    _inherit = 'stock.picking'

    is_supply_writeoff = fields.Boolean(
        string='Хангамж хаах эсэх', compute='_compute_supply_flags')
    is_supply_transfer = fields.Boolean(
        string='Хангамж шилжүүлэх эсэх', compute='_compute_supply_flags')
    supply_from_partner_id = fields.Many2one(
        'res.partner', string='Өгөх ажилтан', copy=False,
        domain=[('is_company', '=', False)],
        help='Хангамж шилжүүлэх баримт дээр хангамжаа өгч буй ажилтан. '
             'Хүлээн авах ажилтныг "Хүргэлтийн хаяг" талбарт сонгоно.')

    @api.depends('picking_type_id', 'location_dest_id')
    def _compute_supply_flags(self):
        for picking in self:
            dest = picking.location_dest_id or picking.picking_type_id.default_location_dest_id
            picking.is_supply_writeoff = bool(dest.supply_writeoff_location)
            picking.is_supply_transfer = bool(dest.supply_transfer_location)

    @api.model
    def _get_supply_balances(self, partner_ids=None, expire_date=None):
        """Ажилтан тус бүрийн хаагдаагүй хангамжийн үлдэгдэл.

        Олгосон (+): хангамжийн байрлалаас гарсан, эсвэл шилжүүлгээр хүлээн авсан.
        Хаагдсан (-): хангамжийн байрлал руу буцсан, актлагдсан, эсвэл шилжүүлгээр өгсөн.
        expired: ашиглах хугацаа (product.template.validity_period, сар) нь
                 expire_date гэхэд дууссан үлдэгдэл. Хаалтыг хамгийн эртний
                 олголтоос (FIFO) хасна. validity_period хоосон/0 бол дуусахгүй.

        :return: [{'partner_id', 'product_id', 'balance', 'expired'}]
        """
        self.env['stock.move.line'].flush_model()
        self.env['stock.move'].flush_model()
        self.env['stock.picking'].flush_model()
        expire_date = expire_date or fields.Date.context_today(self)
        partner_where = ''
        params = {'expire_date': expire_date}
        if partner_ids:
            partner_where = 'AND l.partner_id IN %(partner_ids)s'
            params['partner_ids'] = tuple(partner_ids)
        self.env.cr.execute(f"""
            WITH lines AS (
                SELECT COALESCE(mv.partner_id, sm.partner_id, sp.partner_id) AS partner_id,
                       mv.product_id,
                       COALESCE(sp.issue_date, mv.date::date) AS issue_date,
                       CASE WHEN COALESCE(sl.supply_location, FALSE)
                                 OR COALESCE(dest.supply_transfer_location, FALSE)
                            THEN mv.quantity ELSE 0 END AS issued,
                       CASE WHEN NOT COALESCE(sl.supply_location, FALSE)
                                 AND (COALESCE(dest.supply_location, FALSE)
                                      OR COALESCE(dest.supply_writeoff_location, FALSE))
                            THEN mv.quantity ELSE 0 END AS closed
                FROM stock_move_line mv
                JOIN stock_move sm ON sm.id = mv.move_id
                LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
                JOIN stock_location sl ON sl.id = mv.location_id
                JOIN stock_location dest ON dest.id = mv.location_dest_id
                WHERE mv.state = 'done'
                  AND (sl.supply_location OR dest.supply_location
                       OR dest.supply_writeoff_location OR dest.supply_transfer_location)

                UNION ALL

                -- Шилжүүлгээр өгсөн ажилтны талаас хасна
                SELECT sp.supply_from_partner_id, mv.product_id, mv.date::date, 0, mv.quantity
                FROM stock_move_line mv
                JOIN stock_move sm ON sm.id = mv.move_id
                JOIN stock_picking sp ON sp.id = sm.picking_id
                JOIN stock_location dest ON dest.id = mv.location_dest_id
                WHERE mv.state = 'done'
                  AND dest.supply_transfer_location
                  AND sp.supply_from_partner_id IS NOT NULL
            )
            SELECT l.partner_id,
                   l.product_id,
                   SUM(l.issued) - SUM(l.closed) AS balance,
                   GREATEST(0,
                       SUM(CASE WHEN COALESCE(pt.validity_period, 0) > 0
                                 AND (l.issue_date + pt.validity_period * INTERVAL '1 month')::date <= %(expire_date)s
                                THEN l.issued ELSE 0 END)
                       - SUM(l.closed)) AS expired
            FROM lines l
            JOIN res_partner rp ON rp.id = l.partner_id
            JOIN product_product pp ON pp.id = l.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE rp.is_company = FALSE
              {partner_where}
            GROUP BY l.partner_id, l.product_id
            HAVING SUM(l.issued) - SUM(l.closed) > 0
            ORDER BY l.partner_id, l.product_id
        """, params)
        return self.env.cr.dictfetchall()

    @api.model
    def _prepare_supply_writeoff_move(self, product, qty, location, location_dest, partner):
        return {
            'name': product.display_name,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': qty,
            'location_id': location.id,
            'location_dest_id': location_dest.id,
            'partner_id': partner.id,
        }

    @api.model
    def _create_expired_supply_writeoffs(self, expire_date=None, partner_ids=None):
        """Ашиглах хугацаа нь дууссан хангамжаар ажилтан тус бүрт ноорог "Хангамж хаах" баримт үүсгэнэ.
        Батлагдаагүй хаах баримттай ажилтныг алгасна (давхардуулахгүй).

        :return: (үүссэн баримтууд, хугацаа дууссан хангамж олдсон эсэх)
        """
        expire_date = expire_date or fields.Date.context_today(self)
        picking_type = self.env.ref('l10n_mn_stock.picking_type_supply_writeoff')
        location = picking_type.default_location_src_id
        location_dest = picking_type.default_location_dest_id

        by_partner = defaultdict(list)
        for row in self._get_supply_balances(partner_ids=partner_ids, expire_date=expire_date):
            if row['expired'] > 0:
                by_partner[row['partner_id']].append(row)
        if not by_partner:
            return self.browse(), False

        open_partners = set(self.search([
            ('picking_type_id', '=', picking_type.id),
            ('state', 'not in', ('done', 'cancel')),
            ('partner_id', 'in', list(by_partner)),
        ]).mapped('partner_id').ids)

        pickings = self.browse()
        for partner_id, partner_rows in by_partner.items():
            if partner_id in open_partners:
                continue
            partner = self.env['res.partner'].browse(partner_id)
            moves = [Command.create(self._prepare_supply_writeoff_move(
                self.env['product.product'].browse(r['product_id']), r['expired'],
                location, location_dest, partner)) for r in partner_rows]
            pickings |= self.create({
                'picking_type_id': picking_type.id,
                'partner_id': partner_id,
                'location_id': location.id,
                'location_dest_id': location_dest.id,
                'origin': _('Хугацаа дууссан хангамж (%s)') % expire_date,
                'move_ids': moves,
            })
        return pickings, True

    @api.model
    def _cron_create_expired_supply_writeoffs(self):
        """Сар бүр: хугацаа дууссан хангамжаар ноорог хаах баримт үүсгэнэ."""
        pickings, _found = self._create_expired_supply_writeoffs()
        if pickings:
            _logger.info(
                'Хугацаа дууссан хангамж: %s ноорог хаах баримт үүсгэв: %s',
                len(pickings), ', '.join(pickings.mapped('name')))
        return pickings

    def _fill_supply_lines(self, source_partner, line_partner):
        """source_partner-ийн үлдэгдлээр мөрүүдийг бөглөнө (onchange-д)."""
        balances = self._get_supply_balances(partner_ids=[source_partner.id])
        commands = [Command.clear()]
        for row in balances:
            product = self.env['product.product'].browse(row['product_id'])
            commands.append(Command.create(self._prepare_supply_writeoff_move(
                product, row['balance'], self.location_id, self.location_dest_id, line_partner)))
        self.move_ids_without_package = commands
        if not balances:
            return {'warning': {
                'title': _('Хангамжийн үлдэгдэл алга'),
                'message': _('%s дээр хангамжийн үлдэгдэл олдсонгүй.') % source_partner.display_name,
            }}

    @api.onchange('partner_id')
    def _onchange_partner_supply_writeoff(self):
        """Хангамж хаах баримт дээр ажилтан сонгоход түүний үлдэгдлээр мөрүүдийг бөглөнө."""
        if not self.is_supply_writeoff or not self.partner_id or self.state not in (False, 'draft'):
            return
        return self._fill_supply_lines(self.partner_id, self.partner_id)

    @api.onchange('supply_from_partner_id')
    def _onchange_supply_from_partner(self):
        """Хангамж шилжүүлэх баримт дээр өгөх ажилтан сонгоход түүний үлдэгдлээр мөрүүдийг бөглөнө.
        Олгосон огноо шинээр (өнөөдрөөр) эхэлнэ, хэрэглэгч өөрчилж болно."""
        if not self.is_supply_transfer or not self.supply_from_partner_id or self.state not in (False, 'draft'):
            return
        if not self.issue_date:
            self.issue_date = fields.Date.context_today(self)
        return self._fill_supply_lines(self.supply_from_partner_id, self.partner_id or self.supply_from_partner_id)

    @api.onchange('partner_id')
    def _onchange_partner_supply_transfer(self):
        """Хүлээн авах ажилтныг мөрүүд дээр тусгана."""
        if self.is_supply_transfer and self.partner_id:
            for move in self.move_ids_without_package:
                move.partner_id = self.partner_id

    def _check_supply_pickings(self):
        """Хаах/шилжүүлэх тоо нь ажилтны үлдэгдлээс хэтрэхгүй эсэхийг шалгана."""
        for picking in self.filtered(lambda p: p.is_supply_writeoff or p.is_supply_transfer):
            if picking.is_supply_transfer:
                if not picking.supply_from_partner_id or not picking.partner_id:
                    raise UserError(_('%s: "Өгөх ажилтан" болон "Хүргэлтийн хаяг" (хүлээн авах ажилтан) '
                                      'хоёуланг сонгоно уу.') % picking.name)
                if picking.supply_from_partner_id == picking.partner_id:
                    raise UserError(_('%s: Өгөх болон хүлээн авах ажилтан ижил байна.') % picking.name)
                source = picking.supply_from_partner_id
            else:
                if not picking.partner_id:
                    raise UserError(_('%s: Ажилтныг "Хүргэлтийн хаяг" талбарт сонгоно уу.') % picking.name)
                source = picking.partner_id

            balance = {r['product_id']: r['balance']
                       for r in self._get_supply_balances(partner_ids=[source.id])}
            requested = defaultdict(float)
            for move in picking.move_ids.filtered(lambda m: m.state != 'cancel'):
                qty = move.quantity or move.product_uom_qty
                requested[move.product_id] += move.product_uom._compute_quantity(qty, move.product_id.uom_id)
            for product, qty in requested.items():
                available = balance.get(product.id, 0.0)
                if float_compare(qty, available, precision_rounding=product.uom_id.rounding) > 0:
                    raise UserError(_('%(picking)s: %(partner)s дээр "%(product)s" барааны үлдэгдэл %(available)s, '
                                      'харин %(qty)s ширхэгийг хаах/шилжүүлэхээр оруулсан байна.') % {
                        'picking': picking.name, 'partner': source.display_name,
                        'product': product.display_name, 'available': available, 'qty': qty})
            if picking.is_supply_transfer:
                picking.move_ids.write({'partner_id': picking.partner_id.id})
                if not picking.issue_date:
                    picking.issue_date = fields.Date.context_today(self)

    def button_validate(self):
        self._check_supply_pickings()
        return super().button_validate()
