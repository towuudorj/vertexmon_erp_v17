# -*- coding: utf-8 -*-
#############################################################################
#   Төслийн дугаарлалт
#    
#############################################################################
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    task_id = fields.Many2one('project.task', string='Project Task')

    def action_cancel(self):
        if not self.env.user.has_group('stock.group_stock_manager'):
            if self.filtered('analytic_id'):
                raise UserError(_("Төсөлтэй холбоотой шилжүүлгийг зөвхөн Агуулахын админ цуцлах эрхтэй."))
        return super().action_cancel()

    def write(self, vals):
        if 'analytic_id' in vals and not self.env.user.has_group('stock.group_stock_manager'):
            locked = self.filtered(lambda p: p.analytic_id and p.state in ('confirmed', 'assigned'))
            if locked:
                raise UserError(_("Хүлээгдэж байгаа/бэлэн төлөвтэй, төсөл сонгогдсон шилжүүлгийн Analytic Account талбарыг зөвхөн Агуулахын админ өөрчлөх эрхтэй."))
        return super().write(vals)

    def _action_done(self):
        res = super()._action_done()
        for picking in self:
            purchase = picking.purchase_id
            if (picking.picking_type_id.code == 'incoming' and purchase
                    and purchase.purchase_type == 'local' and purchase.user_id.email):
                purchase_url = f'/web#id={purchase.id}&model=purchase.order&view_type=form'
                self.env['mail.mail'].create({
                    'email_to': purchase.user_id.email,
                    'subject': f'Дотоод худалдан авалт: {purchase.name} -ийн бараа хүлээн авагдлаа.',
                    'body_html': f'Таны захиалсан дотоод худалдан авалтын бараа хүлээн авагдлаа. '
                    f'<a href="{purchase_url}">{purchase.name}</a>',
                }).send()
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    project_balance = fields.Integer('Project Balance', compute='_compute_project_balance')
    product_in_project = fields.Boolean('Product In Project', compute='_compute_project_balance')


    def _compute_project_balance(self):
        for obj in self:
             if obj.picking_id.analytic_id.project_ids:
                 project = obj.picking_id.analytic_id.project_ids[0]
                 project_line = project.products_line.filtered(lambda line: line.product_id.id == obj.product_id.id)
                 if project_line:
                     obj.product_in_project = True
                     obj.project_balance = project_line[0].last_qty
                 else:
                     obj.product_in_project = False
                     obj.project_balance = 0
             else:
                 obj.product_in_project = False
                 obj.project_balance = 0

    @api.depends('picking_id', 'product_uom_qty', 'discount', 'sale_price', 'sale_prices', 'price_subtotal')
    def _compute_tax_amount(self):
        super(StockMove, self)._compute_tax_amount()
        for obj in self:
            if obj.picking_id.analytic_id.project_ids:
                project = obj.picking_id.analytic_id.project_ids[0]
                tax_id = project.tax_id
                if tax_id:
                    taxes = tax_id.with_company(obj.company_id).compute_all(
                        obj.price_subtotal or 0.0,
                        currency=obj.company_id.currency_id,
                        quantity=1.0,
                        product=obj.product_id,
                        partner=obj.picking_id.partner_id,
                        handle_price_include=False,
                    )

                    obj.tax_amount = taxes['total_included'] - taxes['total_excluded']
