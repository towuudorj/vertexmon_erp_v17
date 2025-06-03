# -*- coding: utf-8 -*-

from odoo import fields, models, api

class PartnerTypeRegister(models.Model):
    _name = 'partner.type.register'
    _description = 'Partner type register'

    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    name = fields.Char(string='Partner type', required=True)
    type = fields.Selection([('sale','Sale'),
                             ('purchase','Purchase')],string='Type', required=True)
    payable_account_id = fields.Many2one('account.account', string='Payable account', 
                                         required=True, domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]")
    receivable_account_id = fields.Many2one('account.account', string='Receivable account', 
                                            required=True, domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False)]")
    cash_move_id = fields.Many2one('account.cash.move.type', string='Cash move type')
    partner_group = fields.Selection([('001','001 Sales'),
                                       ('002','002 Employee'),
                                       ('003','003 Bank'),
                                       ('004','004 State'),
                                       ('005','005 Freight'),
                                       ('006','006 Supplier foreign'),
                                       ('007','007 Supplier local'),
                                       ('008','008 Marketing'),
                                       ('008','009 Relation'),
                                       ('010','010 Self'),
                                       ('011','011 Contract partner')], string='Partner group', default='001', required=True)
     
    