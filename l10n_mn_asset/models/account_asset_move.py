# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountAssetMove(models.Model):
    _name = 'account.asset.move'
    _description = 'Asset move'

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    name = fields.Char(string='Asset move', required=True, readonly=True, copy=False, default='/')
    date = fields.Date(string='Date', required=True,
                       default=fields.Date.context_today)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    asset_id = fields.Many2one('account.asset.asset', string='Asset', required=True)
    asset_in_location_id = fields.Many2one('asset.location', string='Asset in location', required=True)
    asset_out_location_id = fields.Many2one('asset.location', string='Asset out location', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=1)
    owner_id = fields.Many2one('res.partner', string='Owner', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, 
                              default=lambda self: self.env.user)
    note = fields.Text(string='Note')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel')
    ], string='State', default='draft', tracking=True)


    def action_asset_move_confirm(self):
        self.write({'state': 'confirm'})

    def action_asset_move_cancel(self):
        self.write({'state': 'cancel'})
