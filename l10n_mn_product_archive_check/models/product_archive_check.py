# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


def _archive_check_result(product_name, errors):
    if errors:
        raise UserError(_(
            '"%s" барааг архивлахад анхаарах зүйлс байна:\n\n- %s'
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
                errors = product._get_archive_blockers()
                if errors:
                    raise UserError(_(
                        '"%s" барааг архивлах боломжгүй байна:\n\n- %s'
                    ) % (product.display_name, '\n- '.join(errors)))
        return super().write(vals)

    def action_check_before_archive(self):
        self.ensure_one()
        return _archive_check_result(self.display_name, self._get_archive_blockers())

    def _get_archive_blockers(self):
        self.ensure_one()
        errors = []

        if self.qty_available:
            errors.append(_('Агуулахад %s үлдэгдэлтэй байна') % self.qty_available)

        sale_orders = self.env['sale.order.line'].search([
            ('product_id', '=', self.id),
            ('order_id.state', 'in', ('draft', 'sent')),
        ]).mapped('order_id')
        if sale_orders:
            errors.append(_('Ноорог төлөвтэй Борлуулалтын захиалга (%s) ашиглаж байна')
                           % ', '.join(sale_orders.mapped('name')))

        purchase_orders = self.env['purchase.order.line'].search([
            ('product_id', '=', self.id),
            ('order_id.state', 'in', ('draft', 'sent', 'to approve')),
        ]).mapped('order_id')
        if purchase_orders:
            errors.append(_('Ноорог төлөвтэй Худалдан авалтын захиалга (%s) ашиглаж байна')
                           % ', '.join(purchase_orders.mapped('name')))

        draft_pickings = self.env['stock.move'].search([
            ('product_id', '=', self.id),
            ('state', '=', 'draft'),
        ]).mapped('picking_id')
        if draft_pickings:
            errors.append(_('Ноорог төлөвтэй Агуулахын шилжилт (%s) ашиглаж байна')
                           % ', '.join(draft_pickings.mapped('name')))

        crm_leads = self.env['crm.lead.line'].search([
            ('product_id', '=', self.id),
            ('state', '=', 'draft'),
            ('lead_id.active', '=', True),
            ('lead_id.new_status', 'not in', ('done', 'cancel')),
        ]).mapped('lead_id')
        if crm_leads:
            errors.append(_('Идэвхтэй CRM боломж (%s) ашиглаж байна')
                           % ', '.join(crm_leads.mapped('name')))

        projects = self.env['project.products.line'].search([
            ('product_id', '=', self.id),
            ('project_id.state', '!=', 'done'),
        ]).mapped('project_id')
        if projects:
            errors.append(_('Дуусаагүй Төсөл (%s) ашиглаж байна')
                           % ', '.join(projects.mapped('name')))

        tasks = self.env['task.products.line'].search([
            ('product_id', '=', self.id),
            ('task_id.state', 'not in', ('1_done', '1_canceled')),
        ]).mapped('task_id')
        if tasks:
            errors.append(_('Дуусаагүй Төслийн ажил (%s) ашиглаж байна')
                           % ', '.join(tasks.mapped('name')))

        return errors


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        if vals.get('active') is False:
            for template in self:
                errors = []
                for variant in template.product_variant_ids:
                    errors += variant._get_archive_blockers()
                if errors:
                    raise UserError(_(
                        '"%s" барааг архивлах боломжгүй байна:\n\n- %s'
                    ) % (template.display_name, '\n- '.join(errors)))
        return super().write(vals)

    def action_check_before_archive(self):
        self.ensure_one()
        errors = []
        for variant in self.product_variant_ids:
            errors += variant._get_archive_blockers()
        return _archive_check_result(self.display_name, errors)
