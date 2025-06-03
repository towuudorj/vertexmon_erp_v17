# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountAssetCapitalization(models.TransientModel):
    _name = "account.asset.capitalization"
    _description = 'Account asset capitalization'
    
    old_amount =  fields.Float(string='Current Amount', readonly=True)
    capital_amount =  fields.Float(string='Capital Amount', required=True)
    account_id = fields.Many2one('account.account', string='Source Account', required=True)
    partner_id = fields.Many2one('res.partner', string='Associated Partner')
    note = fields.Text(string='Notes', required=True)
    date = fields.Date(string='Date', required=True)
    
    
    def button_capital_asset(self):
        ''' Хөрөнгийг капиталжуулахдаа анхны өртөгийн нэмэгдлийг хөрөнгийн дансанд бүртгэнэ.
            Мөн элэгдэх хугацааг сунгаж түүх хөтөлнө.
        '''
        context = dict(self._context or {})
        obj = self.browse(self.id)
        active_ids = context.get('active_ids', []) or []
        asset_obj = self.env['account.asset.asset']
        if obj.capital_amount <= 0 :
            raise UserError(_('The Capital Amount required !'))
        move_id = asset_obj.asset_capitalization(active_ids,self)
        move_ids = []
        for line in move_id:
            move_ids.append(line.id)
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }
