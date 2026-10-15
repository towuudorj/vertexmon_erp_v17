# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CLOSED_LEAD_STATUSES = ('done', 'cancel', 'break')
CLOSED_TASK_STATES = ('1_done', '1_canceled')


class ProductMergeReassignWizard(models.TransientModel):
    """
        Давхардаж бүртгэгдсэн 2 барааны хооронд дуусаагүй захиалга, шилжилтийг
        нэг товчоор шинэ (зорилтот) бараа руу шилжүүлэх зориулалттай wizard.
        Одоогийн үлдэгдэл (stock.quant)-ийг өөрчлөхгүй — зөвхөн ирээдүйд
        чиглэсэн, хараахан дуусаагүй баримтуудын барааны холбоосыг л шилжүүлнэ.
        Хийсэн шилжүүлгийг бүрэн лог болгож хадгалж, хариуцсан ажилтнуудад
        имэйлээр мэдэгдэнэ.
    """
    _name = 'product.merge.reassign.wizard'
    _description = 'Барааны давхардал шилжүүлэх'

    source_product_id = fields.Many2one('product.product', string=u'Хуучин/Давхардсан бараа', required=True)
    target_product_id = fields.Many2one('product.product', string=u'Шилжүүлэх бараа', required=True)

    def _notify_responsible(self, document, users, source, target):
        partner_ids = users.mapped('partner_id').ids
        if not partner_ids:
            return
        body = _('"%s" баримт дээрх "%s" бараа "%s" болж солигдлоо (Барааны давхардал шилжүүлэх).') % (
            document.display_name, source.display_name, target.display_name)
        document.message_post(body=body, partner_ids=partner_ids)

    def action_reassign(self):
        self.ensure_one()
        source = self.source_product_id
        target = self.target_product_id

        if source == target:
            raise UserError(_('Хуучин болон Шилжүүлэх бараа адилхан байна.'))

        if source.uom_id.category_id != target.uom_id.category_id:
            raise UserError(_(
                '"%s" болон "%s" хэмжих нэгжийн ангилал (%s / %s) зөрж байна тул шилжүүлэх боломжгүй.'
            ) % (source.display_name, target.display_name, source.uom_id.name, target.uom_id.name))

        log_lines = []

        sale_lines = self.env['sale.order.line'].sudo().search([
            ('product_id', '=', source.id),
            ('order_id.state', 'in', ('draft', 'sent', 'sale')),
        ]).filtered(lambda l: l.qty_delivered < l.product_uom_qty)
        for line in sale_lines:
            log_lines.append((0, 0, {
                'category': _('Борлуулалтын захиалгын мөр'),
                'document_name': line.order_id.name,
                'res_model': 'sale.order',
                'res_id': line.order_id.id,
            }))
        sale_lines.write({'product_id': target.id})
        for order in sale_lines.mapped('order_id'):
            self._notify_responsible(order, order.user_id, source, target)

        purchase_lines = self.env['purchase.order.line'].sudo().search([
            ('product_id', '=', source.id),
            ('order_id.state', 'in', ('draft', 'sent', 'to approve', 'purchase')),
        ]).filtered(lambda l: l.qty_received < l.product_qty)
        for line in purchase_lines:
            log_lines.append((0, 0, {
                'category': _('Худалдан авалтын захиалгын мөр'),
                'document_name': line.order_id.name,
                'res_model': 'purchase.order',
                'res_id': line.order_id.id,
            }))
        purchase_lines.write({'product_id': target.id})
        for order in purchase_lines.mapped('order_id'):
            self._notify_responsible(order, order.user_id, source, target)

        pending_moves = self.env['stock.move'].sudo().search([
            ('product_id', '=', source.id),
            ('state', 'not in', ('done', 'cancel')),
        ])
        for move in pending_moves:
            log_lines.append((0, 0, {
                'category': _('Агуулахын шилжилт'),
                'document_name': move.picking_id.name or move.reference or move.name,
                'res_model': 'stock.picking' if move.picking_id else 'stock.move',
                'res_id': move.picking_id.id if move.picking_id else move.id,
            }))
        pending_moves.mapped('move_line_ids').write({'product_id': target.id})
        pending_moves.write({'product_id': target.id})
        for picking in pending_moves.mapped('picking_id'):
            self._notify_responsible(picking, picking.user_id, source, target)

        crm_lines = self.env['crm.lead.line'].sudo().search([
            ('product_id', '=', source.id),
            ('state', '=', 'draft'),
            ('lead_id.active', '=', True),
            ('lead_id.new_status', 'not in', CLOSED_LEAD_STATUSES),
        ])
        for line in crm_lines:
            log_lines.append((0, 0, {
                'category': _('CRM боломжийн мөр'),
                'document_name': line.lead_id.name,
                'res_model': 'crm.lead',
                'res_id': line.lead_id.id,
            }))
        crm_lines.write({'product_id': target.id})
        for lead in crm_lines.mapped('lead_id'):
            self._notify_responsible(lead, lead.user_id, source, target)

        project_lines = self.env['project.products.line'].sudo().search([
            ('product_id', '=', source.id),
            ('project_id.state', '!=', 'done'),
        ])
        _logger.info(
            'Product merge %s -> %s: project lines %s',
            source.display_name, target.display_name,
            [(l.id, l.project_id.name, l.project_id.state, l.product_qty, l.qty_delivered) for l in project_lines])
        # Зарлага хийгдсэн мөрийн барааг солих боломжгүй (project.products.line.write).
        # Зарлагадсан хэсгийг хуучин бараан дээр үлдээж, зарлага хийгдээгүй үлдсэн
        # тоог шинэ бараатай мөр болгон салгана. Бүрэн зарлагадсан мөрийг орхино.
        project_lines_to_move = project_lines.filtered(lambda l: l.qty_delivered <= 0)
        for line in project_lines - project_lines_to_move:
            delivered = line.qty_delivered
            remaining = line.product_qty - delivered
            if remaining <= 0:
                continue
            line.write({
                'product_qty': delivered,
                'price_total': line.price_unit * delivered,
                'cost_total': line.cost_price * delivered,
            })
            new_line = line.copy({
                'product_id': target.id,
                'product_qty': remaining,
                'price_total': line.price_unit * remaining,
                'cost_total': line.cost_price * remaining,
            })
            # create() нь өртгийг шинэ барааны стандарт өртгөөр дардаг тул хуучныг сэргээнэ
            new_line.write({'cost_price': line.cost_price, 'cost_total': line.cost_price * remaining,
                            'name': line.name})
            log_lines.append((0, 0, {
                'category': _('Төслийн барааны мөр (зарлагагүй %s тоог салгав)') % remaining,
                'document_name': line.project_id.name,
                'res_model': 'project.project',
                'res_id': line.project_id.id,
            }))
            self._notify_responsible(line.project_id, line.project_id.user_id, source, target)
        for line in project_lines_to_move:
            log_lines.append((0, 0, {
                'category': _('Төслийн барааны мөр'),
                'document_name': line.project_id.name,
                'res_model': 'project.project',
                'res_id': line.project_id.id,
            }))
        project_lines_to_move.write({'product_id': target.id})
        for project in project_lines_to_move.mapped('project_id'):
            self._notify_responsible(project, project.user_id, source, target)

        task_lines = self.env['task.products.line'].sudo().search([
            ('product_id', '=', source.id),
            ('task_id.state', 'not in', CLOSED_TASK_STATES),
        ])
        for line in task_lines:
            log_lines.append((0, 0, {
                'category': _('Төслийн ажлын барааны мөр'),
                'document_name': line.task_id.name,
                'res_model': 'project.task',
                'res_id': line.task_id.id,
            }))
        task_lines.write({'product_id': target.id})
        for task in task_lines.mapped('task_id'):
            self._notify_responsible(task, task.user_ids, source, target)

        log = self.env['product.merge.reassign.log'].create({
            'source_product_id': source.id,
            'target_product_id': target.id,
            'line_ids': log_lines,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Барааны шилжүүлэг'),
            'res_model': 'product.merge.reassign.log.line',
            'view_mode': 'tree',
            'domain': [('log_id', '=', log.id)],
            'target': 'current',
        }
