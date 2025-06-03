# -*- encoding: utf-8 -*-
from datetime import timedelta, datetime
import time
from odoo import api, fields, models, _

class account_asset_writeoff(models.TransientModel):
    _name = 'account.asset.writeoff'
    _description = 'Asset Writeoff'
    
    
    @api.model
    def default_get(self, fields):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values 
        @param context: A standard dictionary 
        @return: A dictionary which of fields with values. 
        """ 
        context = dict(self._context or {})
        asset_obj = self.env['account.asset.asset']
        res = super(account_asset_writeoff, self).default_get(fields)
        asset_id = self.env.context.get('active_ids')
        asset = asset_obj.browse(asset_id)
        if 'writeoff_amount' in fields:
            res.update({'writeoff_amount':asset.value_residual})
        if 'depreciation_amount' in fields:
            depreciation_amount = 0
            for depr in asset.depreciation_line_ids:
                if depr.move_id:
                    depreciation_amount += depr.amount
            res.update({'depreciation_amount':depreciation_amount})
        return res
    
    writeoff_account = fields.Many2one('account.account', string='Writeoff Account', required=True) #Тооцооноос хассан данс
    writeoff_amount = fields.Float(string='Writeoff Amount', readonly=True) #Тооцооноос хассан дүн
    depreciation_amount = fields.Float(string='Depreciation Amount', readonly=True) #Элэгдэл дүн
    writeoff_journal = fields.Many2one('account.journal',string='Writeoff Journal', required=True) #Тооцооноос хассан журнал
    name = fields.Char(string='Reason', required=True) #Нэр
    writeoff_date = fields.Date(string='Date', required=True,
                                default=lambda *a: time.strftime('%Y-%m-%d')) #Тооцооноос хассан огноо
    
           
    def writeoff(self):
        asset_obj = self.env['account.asset.asset']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        context = dict(self._context or {})
        asset_id = self.env.context.get('active_ids')
        asset = asset_obj.browse(asset_id)
        data = self
        move_lines = []
        asset_name_ref = asset.name_get()[0][1]
        asset_credit = 0
        writeoff_credit = 0
        writeoff_debit = 0
        if data.writeoff_amount > 0:
            asset_credit += data.writeoff_amount
        depr_debit = 0
        if data.depreciation_amount > 0:
            depr_debit += data.depreciation_amount
        if asset_credit > depr_debit:
            writeoff_debit = asset_credit - depr_debit
        else:
            writeoff_credit = depr_debit - asset_credit
        if asset_credit:
            move_lines.append( (0,0,{
                'name': asset_name_ref, #Нэр
                'debit': 0, #Дебит
                'credit': asset_credit, #Кредит
                'account_id': asset.category_id.account_asset_id.id, #Дансны
                'date': data.writeoff_date, #Огноо
                'ref': asset.code, #Тайлбар
                'partner_id': asset.partner_id.id, #Харилцагч
                'asset_id': asset.id, #Мөнгөн хөрөнгө
                'journal_id': data.writeoff_journal.id #Журнал
            }))
        if depr_debit:
            move_lines.append( (0,0,{
                'name': asset_name_ref, #Нэр
                'debit': depr_debit, #Дебит
                'credit': 0, #Кредит
                'account_id': asset.category_id.account_depreciation_id.id, #Дансны дугаар
                'date': data.writeoff_date, #Огноо
                'ref': asset.code, #Тайлбар
                'partner_id': asset.partner_id.id, #Харилцагч
                'journal_id': data.writeoff_journal.id #Журнал
            }))
        if writeoff_debit >0.0:
            move_lines.append( (0,0,{
                'name': asset_name_ref, #Нэр
                'debit': writeoff_debit, #Дебит
                'credit': 0, #Кредит
                'account_id': data.writeoff_account.id, #Данс
                'date': data.writeoff_date, #Огноо
                'ref': asset.code, #Тайлбар
                'partner_id': asset.partner_id.id, #Харилцагч
                'journal_id': data.writeoff_journal.id #Журнал
            }))
        if writeoff_credit >0.0:
            move_lines.append( (0,0,{
                'name': asset_name_ref, #Нэр
                'debit': 0, #Дебит
                'credit': writeoff_credit, #Кредит
                'account_id': data.writeoff_account.id, #Данс
                'date': data.writeoff_date, #Огноо
                'ref': asset.code, #Тайлбар
                'partner_id': asset.partner_id.id, #Харилцагч
                'journal_id': data.writeoff_journal.id #Журнал
            }))
        
        if move_lines:
            move_id = move_obj.create({
                'journal_id': data.writeoff_journal.id, #Журнал
                'ref': asset.code, #Тайлбар
                'date': data.writeoff_date, #Огноо
                'narration': data.name, #Түүх
                'line_ids': move_lines #Зөөх мөрүүд
            })
        
        todo_unlink_board = []
        for line in asset.depreciation_line_ids:
            if not line.move_id:
                todo_unlink_board.append(line.id)
        if todo_unlink_board !=[]:
            for todo in todo_unlink_board:
                for dpi in self.env['account.asset.depreciation.line'].browse(todo):
                    dpi.unlink()
        asset.write({'state':'close',
                     'is_closed':True,
                     })
        return {'type': 'ir.actions.act_window_close'}

