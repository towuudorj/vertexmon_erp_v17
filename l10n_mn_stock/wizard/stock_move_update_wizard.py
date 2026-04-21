from odoo import _, api, fields, models
from markupsafe import Markup


class StockMoveUpdate(models.TransientModel):
    _name = 'stock.move.update'
    _description = 'Stock Move Update'

    @api.model
    def default_get(self, fields_list):
        res = super(StockMoveUpdate, self).default_get(fields_list)
        context = self.env.context
        move_id = context.get('active_id')
        if 'move_id' in fields_list:
            res['move_id'] = [(4, move_id)]
        return res

    move_id = fields.Many2many('stock.move', 'move_update_main_line', 'move_update_wizard_id', 'move_id')
    new_line_ids = fields.Many2many('stock.move', 'move_update_new_line', 'move_update_wizard_id', 'new_move_id')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def update(self):
        for obj in self:
            picking_id = obj.move_id.picking_id
            obj.move_id.sudo().write({'quantity': 0})
            message_body = f'<ul><li>{obj.move_id.product_id.name}:{obj.move_id.quantity}</li><li>→</li>'
            for new_line in obj.new_line_ids:
                for line in picking_id.move_ids_without_package:
                    if line.product_id == new_line.product_id:
                        line.sudo().write({'quantity': line.quantity + new_line.quantity})
                        message_body += f'<li>{obj.move_id.product_id.name}:{line.quantity + new_line.quantity}</li>'

                if new_line.product_id not in picking_id.move_ids_without_package.mapped('product_id'):
                    new_line.write({
                        'picking_id': picking_id.id,
                    })
                    message_body += f'<li>{new_line.product_id.name}:{new_line.quantity}</li>'
            message_body += '</ul>'
            picking_id.message_post(author_id=self.env.user.partner_id.id,
                                    body=Markup(message_body))
            purchase_id = self.env['purchase.order'].search([
                ('partner_id', '=', picking_id.partner_id.id),
                ('name', '=', picking_id.origin),
                ('picking_type_id', '=', picking_id.picking_type_id.id)
            ], limit=1)
            if purchase_id:
                if purchase_id.requisition_id and purchase_id.requisition_id.crm_lead_id:
                    lead_id = purchase_id.requisition_id.crm_lead_id
                    sale_orders = lead_id.order_ids.filtered_domain(lead_id._get_lead_sale_order_domain())
                    if sale_orders and len(sale_orders) == 1:
                        sale_picking_ids = sale_orders.picking_ids
                        lines = sale_picking_ids.mapped('move_ids_without_package').filtered(lambda l: l.product_id.id == obj.move_id.product_id.id)
                        if lines:
                            lines.sudo().write({'quantity': 0})
                            message_body = f'<ul><li>{lines[len(lines) - 1].product_id.name}:{lines[len(lines) - 1].quantity}</li><li>→</li>'
                            for new_line in obj.new_line_ids:
                                same_product_lines = sale_picking_ids.mapped('move_ids_without_package').filtered(lambda l: l.product_id.id == new_line.product_id.id)
                                if same_product_lines:
                                    same_product_lines[len(same_product_lines)-1].sudo().write({'quantity': same_product_lines[len(same_product_lines)-1].quantity + new_line.quantity})
                                    message_body += f'<li>{lines[len(lines)-1].product_id.name}:{new_line.quantity}</li>'
                                else:
                                    self.env['stock.move'].sudo().create({
                                        'picking_id': lines[len(lines)-1].picking_id.id,
                                        'location_id': lines[len(lines)-1].location_id.id,
                                        'product_id': new_line.product_id.id,
                                        'location_dest_id': lines[len(lines)-1].location_dest_id.id,
                                        'description_picking': lines[len(lines)-1].description_picking,
                                        'date': lines[len(lines)-1].date,
                                        'name': lines[len(lines)-1].name,
                                        'quantity': new_line.quantity,
                                        'sale_prices': lines[len(lines)-1].sale_prices,
                                    })
                                    message_body += f'<li>{new_line.product_id.name}:{new_line.quantity}</li>'
                            message_body += '</ul>'
                            lines[len(lines)-1].picking_id.message_post(
                                author_id=self.env.user.partner_id.id,
                                body=Markup(message_body))
        return {'type': 'ir.actions.act_window_close'}

    def cancel(self):
        for obj in self:
            if obj.new_line_ids:
                obj.new_line_ids.sudo().unlink()
        return {'type': 'ir.actions.act_window_close'}
