# -*- coding: utf-8 -*-

#################################################################################
# Author      : Zero For Information Systems (<www.erpzero.com>)
# Copyright(c): 2016-Zero For Information Systems
# All Rights Reserved.
#zerosystems #erp #odoo
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################


from odoo import api, fields, models, tools, _

   
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    date_done = fields.Datetime('Date of Transfer',compute="_compute_date_done",store=True,readonly=False, copy=False, help="Date at which the transfer has been processed or cancelled.")

    @api.depends('scheduled_date')
    def _compute_date_done(self):
        for picking in self:
            if picking.scheduled_date:
                picking.date_done = picking.scheduled_date

    @api.onchange('scheduled_date')
    def _onchange_scheduled_date(self):
        for picking in self:
            if picking.scheduled_date:
                picking.date_done = picking.scheduled_date

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for pick in self:
            if pick.date_done:
                for moves in self.move_ids:
                    moves.update({'date': pick.date_done})
        return res

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        vals = super()._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        if self.picking_id.date_done:
            vals.update({'date': self.picking_id.date_done.date()})
        return vals


    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in self:
            move_line = move.move_line_ids
            if move.picking_id.date_done and move_line:
                for line in move_line:
                    line.update({'date': move.picking_id.date_done })
        return res

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'
    _order = 'date_done, id'

    date_done = fields.Datetime('Date of Transfer', readonly=False,copy=False,related='stock_move_id.date', help="Date at which the transfer has been processed or cancelled.")

    def init(self):
        tools.create_index(
            self._cr, 'stock_valuation_layer_index',
            self._table, ['product_id', 'remaining_qty', 'stock_move_id', 'company_id', 'create_date','date_done']
        )
