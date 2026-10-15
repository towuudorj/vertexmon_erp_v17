# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError

CLOSED_LEAD_STATUSES = ('done', 'cancel', 'break')
CLOSED_TASK_STATES = ('1_done', '1_canceled')


def _raise_or_notify(product_name, errors):
    if errors:
        raise UserError(_(
            '"%s" барааг архивлах боломжгүй байна:\n\n- %s'
        ) % (product_name, '\n- '.join(errors)))
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': _('Шалгалт амжилттай'),
            'message': _('"%s" барааг архивлахад саад болох зүйл алга.') % product_name,
            'type': 'success',
            'sticky': False,
        },
    }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def write(self, vals):
        if vals.get('active') is False:
            for product in self:
                _raise_or_notify(product.display_name, product._get_archive_blockers())
        return super().write(vals)

    def action_check_before_archive(self):
        self.ensure_one()
        return _raise_or_notify(self.display_name, self._get_archive_blockers())

    def _get_archive_blockers(self):
        self.ensure_one()
        errors = []

        if self.qty_available:
            errors.append(_('Агуулахад %s үлдэгдэлтэй байна') % self.qty_available)

        def _with_qty(records, doc_field, qty_field, doc_name='name'):
            """'Doc1 (тоо: 9.0), Doc2 (тоо: 3.0)' - same document lines are summed."""
            totals = {}
            for rec in records:
                doc = rec[doc_field]
                totals[doc] = totals.get(doc, 0.0) + rec[qty_field]
            return ', '.join(_('%s (тоо: %s)') % (doc[doc_name], qty) for doc, qty in totals.items())

        sale_lines = self.env['sale.order.line'].sudo().search([
            ('product_id', '=', self.id),
            ('order_id.state', 'in', ('draft', 'sent')),
        ])
        if sale_lines:
            errors.append(_('Ноорог төлөвтэй Борлуулалтын захиалга [%s] ашиглаж байна')
                           % _with_qty(sale_lines, 'order_id', 'product_uom_qty'))

        purchase_lines = self.env['purchase.order.line'].sudo().search([
            ('product_id', '=', self.id),
            ('order_id.state', 'in', ('draft', 'sent', 'to approve')),
        ])
        if purchase_lines:
            errors.append(_('Ноорог төлөвтэй Худалдан авалтын захиалга [%s] ашиглаж байна')
                           % _with_qty(purchase_lines, 'order_id', 'product_qty'))

        draft_moves = self.env['stock.move'].sudo().search([
            ('product_id', '=', self.id),
            ('state', '=', 'draft'),
            ('picking_id', '!=', False),
        ])
        if draft_moves:
            errors.append(_('Ноорог төлөвтэй Агуулахын шилжилт [%s] ашиглаж байна')
                           % _with_qty(draft_moves, 'picking_id', 'product_uom_qty'))

        lead_lines = self.env['crm.lead.line'].sudo().search([
            ('product_id', '=', self.id),
            ('state', '=', 'draft'),
            ('lead_id.active', '=', True),
            ('lead_id.new_status', 'not in', CLOSED_LEAD_STATUSES),
        ])
        if lead_lines:
            errors.append(_('Идэвхтэй CRM боломж [%s] ашиглаж байна')
                           % _with_qty(lead_lines, 'lead_id', 'qty'))

        project_lines = self.env['project.products.line'].sudo().search([
            ('product_id', '=', self.id),
            ('project_id.state', '!=', 'done'),
        ])
        if project_lines:
            errors.append(_('Дуусаагүй Төсөл [%s] ашиглаж байна')
                           % _with_qty(project_lines, 'project_id', 'product_qty'))

        task_lines = self.env['task.products.line'].sudo().search([
            ('product_id', '=', self.id),
            ('task_id.state', 'not in', CLOSED_TASK_STATES),
        ])
        if task_lines:
            errors.append(_('Дуусаагүй Төслийн ажил [%s] ашиглаж байна')
                           % _with_qty(task_lines, 'task_id', 'product_qty'))

        return errors


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_variant_archive_blockers(self):
        errors = []
        for variant in self.product_variant_ids:
            errors += variant._get_archive_blockers()
        return errors

    def write(self, vals):
        if vals.get('active') is False:
            for template in self:
                _raise_or_notify(template.display_name, template._get_variant_archive_blockers())
        return super().write(vals)

    def action_check_before_archive(self):
        self.ensure_one()
        return _raise_or_notify(self.display_name, self._get_variant_archive_blockers())
