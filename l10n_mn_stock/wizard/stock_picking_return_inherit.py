# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero, float_round


class ReturnPicking(models.TransientModel):
    _name = 'stock.return.picking'
    _description = 'Return Picking'
    
    
    
    def _create_returns(self):
            for return_move in self.product_return_moves.mapped('move_id'):
                return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()
    
            # create new picking for returned products
            new_picking = self.picking_id.copy(self._prepare_picking_default_values())
            picking_type_id = new_picking.picking_type_id.id
            new_picking.message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': new_picking, 'origin': self.picking_id},
                subtype_xmlid='mail.mt_note',
            )
            returned_lines = 0
            for return_line in self.product_return_moves:
                if return_line.product_id.qty_available == 0.0 and self.picking_id.picking_type_id.code == 'incoming':
                    raise UserError(_("Борлуулалт хийгдсэн тул буцаалт хийх боломжгүйг анхаарна уу."))
                if not return_line.move_id:
                    raise UserError(_("You have manually created product lines, please delete them to proceed."))
                if not float_is_zero(return_line.quantity, precision_rounding=return_line.uom_id.rounding):
                    returned_lines += 1
                    vals = self._prepare_move_default_values(return_line, new_picking)
                    r = return_line.move_id.copy(vals)
                    vals = {}
    
                    # +--------------------------------------------------------------------------------------------------------+
                    # |       picking_pick     <--Move Orig--    picking_pack     --Move Dest-->   picking_ship
                    # |              | returned_move_ids              ↑                                  | returned_move_ids
                    # |              ↓                                | return_line.move_id              ↓
                    # |       return pick(Add as dest)          return toLink                    return ship(Add as orig)
                    # +--------------------------------------------------------------------------------------------------------+
                    move_orig_to_link = return_line.move_id.move_dest_ids.mapped('returned_move_ids')
                    # link to original move
                    move_orig_to_link |= return_line.move_id
                    # link to siblings of original move, if any
                    move_orig_to_link |= return_line.move_id\
                        .mapped('move_dest_ids').filtered(lambda m: m.state not in ('cancel'))\
                        .mapped('move_orig_ids').filtered(lambda m: m.state not in ('cancel'))
                    move_dest_to_link = return_line.move_id.move_orig_ids.mapped('returned_move_ids')
                    # link to children of originally returned moves, if any. Note that the use of
                    # 'return_line.move_id.move_orig_ids.returned_move_ids.move_orig_ids.move_dest_ids'
                    # instead of 'return_line.move_id.move_orig_ids.move_dest_ids' prevents linking a
                    # return directly to the destination moves of its parents. However, the return of
                    # the return will be linked to the destination moves.
                    move_dest_to_link |= return_line.move_id.move_orig_ids.mapped('returned_move_ids')\
                        .mapped('move_orig_ids').filtered(lambda m: m.state not in ('cancel'))\
                        .mapped('move_dest_ids').filtered(lambda m: m.state not in ('cancel'))
                    vals['move_orig_ids'] = [(4, m.id) for m in move_orig_to_link]
                    vals['move_dest_ids'] = [(4, m.id) for m in move_dest_to_link]
                    r.write(vals)
            if not returned_lines:
                raise UserError(_("Please specify at least one non-zero quantity."))
    
            new_picking.action_confirm()
            new_picking.action_assign()
            return new_picking.id, picking_type_id