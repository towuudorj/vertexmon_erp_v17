# -*- coding: utf-8 -*-
from odoo import models, fields, api, SUPERUSER_ID

class EquityConfigureReport(models.Model):
    _name = 'equity.configure.report'
    _description = 'Mongolian report account'
    
    
    company_id = fields.Many2one('res.company', string='Company')
    # Statement of stockholder's equity properties - Өмчийн өөрчлөлтийн тайлангийн талбарууд
    # Дүрмийн сан
    property_statutory_fund_account = fields.Many2one('account.account', string="Statutory Fund Account", required=True)
    # Халаасны хувьцаа 
    property_treasury_stock_account = fields.Many2one('account.account', string="Treasury Stock Account", required=True)
    # Нэмж төлөгдсөн капитал 
    property_additional_capital_account = fields.Many2one('account.account', string="Additional Paid-in Capital Account", required=True)
    # Дахин үнэлгээний нэмэгдэл
    property_revaluation_addition_account = fields.Many2one('account.account', string="Revaluation Addition Account", required=True)
    # Гадаад валютын хөрвүүлэлтийн нөөц 
    property_foreign_currency_conversion_account = fields.Many2one('account.account', string="Foreign Currency Conversion Inventory Account", required=True)
    # Эздийн өмчийн бусад хэсэг 
    property_stockholders_equity_remainder_account =  fields.Many2one('account.account', string="Stockholders Equity Remainder Account", required=True)
    # Өмнөх үеийн хуримтлагдсан ашиг 
    property_previous_retained_earnings_account = fields.Many2one('account.account', string="Previously Retained Earnings Account", required=True)
    # Тайлант үеийн хуримтлагдсан ашиг 
    property_period_retained_earnings_account = fields.Many2one('account.account', string="Period Retained Earnings Account", required=True)
    # Ногдол ашгийн зардал 
    property_dividend_expense_account = fields.Many2one('account.account', string="Dividend Expense Account", required=True)
    # Залруулгын журнал 
    property_adjustment_journal = fields.Many2one('account.journal', string="Adjustment Journal", required=True)
    # Өмчид гарсан өөрчлөлтийн журнал 
    property_equity_changes_journal = fields.Many2one('account.journal', string="Equity Changes Journal", required=True)