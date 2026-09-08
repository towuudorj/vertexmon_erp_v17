# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountBankStatementLineBatchUpdate(models.TransientModel):
    _name = "account.bank.statement.line.batch.update"
    _description = "Bank Statement Line Batch Update Wizard"

    @api.model
    def _default_line_ids(self):
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            return [(6, 0, active_ids)]
        return False

    line_ids = fields.Many2many(
        'account.bank.statement.line',
        'st_line_batch_update_rel',
        'wizard_id',
        'line_id',
        string='Bank Statement Lines',
        default=_default_line_ids,
    )
    line_count = fields.Integer(
        compute='_compute_line_count',
        string='Selected Lines Count',
    )

    update_partner = fields.Boolean(
        string='Update Partner',
        default=False,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
    )

    update_cash_move_type = fields.Boolean(
        string='Update Cash Move Type',
        default=False,
    )
    cash_move_type_id = fields.Many2one(
        'account.cash.move.type',
        string='Cash Move Type',
    )

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.update_partner = True

    @api.onchange('cash_move_type_id')
    def _onchange_cash_move_type_id(self):
        if self.cash_move_type_id:
            self.update_cash_move_type = True

    def action_update(self):
        self.ensure_one()
        if not self.update_partner and not self.update_cash_move_type:
            raise UserError(_("Please select at least one field to update! (Partner or Cash Move Type)"))

        lines = self.line_ids
        if not lines:
            raise UserError(_("No lines selected to update!"))

        if self.update_cash_move_type and not self.cash_move_type_id:
            raise UserError(_("Please select a Cash Move Type!"))

        for line in lines:
            vals = {}
            if self.update_partner:
                partner_val = self.partner_id.id if self.partner_id else False
                vals['partner_id'] = partner_val
            if self.update_cash_move_type:
                vals['cash_move_type_id'] = self.cash_move_type_id.id

            # skip_account_move_synchronization avoids deleting reconciled lines in _synchronize_to_moves
            line.with_context(skip_account_move_synchronization=True).write(vals)

            liquidity_lines, suspense_lines, _other_lines = line._seek_for_lines()

            # Update partner across move and related move lines
            if self.update_partner:
                partner_val = self.partner_id.id if self.partner_id else False
                if line.move_id and line.move_id.partner_id.id != partner_val:
                    line.move_id.write({'partner_id': partner_val})
                if liquidity_lines:
                    liquidity_lines.write({'partner_id': partner_val})
                if suspense_lines:
                    suspense_lines.write({'partner_id': partner_val})
                unrec_lines = line.move_id.line_ids.filtered(
                    lambda l: not l.reconciled and l.id not in liquidity_lines.ids and l.id not in suspense_lines.ids
                )
                if unrec_lines:
                    unrec_lines.write({'partner_id': partner_val})

            # Update cash move type on liquidity move lines
            if self.update_cash_move_type:
                cm_val = self.cash_move_type_id.id
                if liquidity_lines:
                    liquidity_lines.write({'cash_move_type_id': cm_val})

        return {'type': 'ir.actions.act_window_close'}