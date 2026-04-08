# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class AccountMoveAnalysis(models.TransientModel):
    _name = 'account.move.analysis'
    _inherit = ['xls.report.base']
    _description = 'Account move analysis'
   
    
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    start_date = fields.Date(string='Start date', required=True)
    end_date = fields.Date(string='End date', required=True)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')
                                    ], string='State', required=True, default='posted')
    by_currency = fields.Boolean(u'Валютаар харах')

    def get_report_data(self):
        data = super(AccountMoveAnalysis, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'state':self.target_move,
            'by_currency':self.by_currency
        })
        return data


    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'account.move.analysis',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'account_move'}
        }
    
    
    def get_xlsx_report(self, data, response, get_file=False):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 20,
                                    'valign': 'vcenter',
                                    })

        txt_center_border = workbook.add_format({
                                    'align': 'center',
                                    'border':1,
                                    'font_size': 12
                                })
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border':1,
                                    'valign': 'vcenter',
                                    'font_size': 12
                                })
        
        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border':1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })
        
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border':1,
                                    'valign': 'vcenter',
                                    'font_size': 12
                                })

        txt_left_border = workbook.add_format({
                                    'align': 'left',
                                     'border':1,
                                    'font_size': 12
                                })
        txt_right_border = workbook.add_format({
                                    'align': 'right',
                                    'border':1,
                                    'font_size': 12,
                                    'bold': True,
                                    'num_format': '#,##0.00'
                                })
        text_center_border = workbook.add_format({
            'border': 1,
            'font_size': 12,
            'bold': True,
            'num_format': '#,##0.00',
            'valign': 'vcenter',
            'align': 'center'
        })

        txt_left_no_border = workbook.add_format({
                                    'align': 'left',
                                    'font_size': 12
                                })
        txt_right_no_border = workbook.add_format({
                                    'align': 'right',
                                    'font_size': 12
                                })
        sheet.set_column(3, 9, 20)
        sheet.set_column(2, 2, 40)
        sheet.set_column(1, 1, 10)
        sheet.freeze_panes(7, 4)
        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.write('A1', u'НХМаягт МХ-4', txt_left_no_border)
        sheet.write('J1', u'Сангийн сайдын 2018 оны 100 дугаар', txt_right_no_border)
        sheet.write('J2', u'тушаалын хавсралт',txt_right_no_border)
        sheet.merge_range('A3:J3', u'Гүйлгээ баланс тайлан', head)
        sheet.write('A4', u'Байгууллагын нэр: %s' % data['company_name'], txt_left_no_border)
        sheet.write('J4', u'Он сар өдөр: %s - %s'%(data['start_date'],data['end_date']), txt_right_no_border)

        sheet.merge_range('A6:A7', u'Д/д', txt_left_border)
        sheet.merge_range('B6:C7', u'Данс', txt_center_border)
        sheet.merge_range('D6:D7', u'Валют', txt_center_border)
        sheet.merge_range('E6:F6', u'Эхний үлдэгдэл', txt_center_border)
        sheet.write('E7', u'Дт', txt_center_border)
        sheet.write('F7', u'Кд', txt_center_border)
        sheet.merge_range('G6:H6', u'Гүйлгээ', txt_center_border)
        sheet.write('G7', u'Дт', txt_center_border)
        sheet.write('H7', u'Кд', txt_center_border)
        sheet.merge_range('I6:J6', u'Эцсийн үлдэгдэл', txt_center_border)
        sheet.write('I7', u'Дт', txt_center_border)
        sheet.write('J7', u'Кд', txt_center_border)

        if data['state'] == 'posted':
            states = ['posted']
        else:
            states = ['posted','draft']

        pre_debit_balance = 0.0
        pre_credit_balance = 0.0
        debit_balance = 0.0
        credit_balance = 0.0
        total_debit_balance = 0.0
        total_credit_balance = 0.0

        qry = f"""
        select 
                COALESCE(rc.name, 'MNT') as currency,
                aa.code||' '|| (aa.name::jsonb->>'mn_MN')::text as account_name, aa.id, 
                COALESCE(start_balance.debit, 0) as debit_start_balance,
                COALESCE(start_balance.credit, 0) as credit_start_balance,
                COALESCE(start_balance.amount_currency_credit, 0) as start_amount_currency_credit,
                COALESCE(start_balance.amount_currency_debit, 0) as start_amount_currency_debit,
                COALESCE(sum(aml.debit), 0)  as debit, COALESCE(sum(aml.credit), 0) as credit,
                COALESCE(sum(case when aml.balance > 0 then aml.amount_currency else 0 end), 0) as amount_currency_debit,
                COALESCE(sum(case when aml.balance < 0 then abs(aml.amount_currency) else 0 end), 0) as amount_currency_credit
         from 
         account_account aa
         left join (
                 select 
                 sum(aml.debit) as debit,
                 sum(aml.credit) as credit,
                 sum(case when aml.balance > 0 then aml.amount_currency else 0 end) as amount_currency_debit,
                 sum(case when aml.balance < 0 then abs(aml.amount_currency) else 0 end) as amount_currency_credit,
                 aml.account_id
             from account_account aa
             left join account_move_line aml on aml.account_id = aa.id
             where
             aml.parent_state = 'posted' and aa.company_id = {data['company_id']} and aml.date < '{data['start_date']}'
             group by aml.account_id
         ) as start_balance on start_balance.account_id = aa.id
         full join
         (
            select aml.account_id, aml.balance, aml.debit, aml.credit, aml.amount_currency, aml.date
            from account_move_line aml 
            where
             aml.date between '{data['start_date']}' and '{data['end_date']}' and aml.parent_state in ('{"', '".join(states)}')
             and aml.company_id = {data['company_id']}
         ) as aml on aa.id = aml.account_id
         left join res_currency rc on aa.currency_id = rc.id
         where aa.company_id = {data['company_id']} and aa.deprecated = False
         GROUP BY rc.name, aml.account_id, aa.code, aa.name, start_balance.debit, start_balance.credit, start_balance.amount_currency_debit, start_balance.amount_currency_credit, aa.id
         ORDER BY aa.code, aa.id;
"""
        self.env.cr.execute(qry)
        lines = self._cr.dictfetchall()

        currency_total_dict = {}
        number = 1
        rowx = 8
        account_obj = self.env['account.account']
        for line in lines:
            if line['currency'] == 'MNT' or not data['by_currency']:
                start_balance = line['debit_start_balance'] - line['credit_start_balance']
                sheet.write('A%s' % rowx, number, data_center)
                sheet.merge_range('B%s:C%s' % (rowx, rowx), line['account_name'], data_left)
                sheet.write('D%s' % rowx, 'MNT', data_left)
                
                account_id = account_obj.search([('id','=',line['id'])],limit=1)
                if account_id.account_type == 'asset_fixed' and start_balance < 0.0:
                    sheet.write('E%s' % rowx, start_balance if start_balance < 0 else 0, data_right)
                    sheet.write('F%s' % rowx, abs(start_balance) if start_balance > 0 else 0, data_right)
                    
                else:
                    sheet.write('E%s' % rowx, start_balance if start_balance > 0 else 0, data_right)
                    sheet.write('F%s' % rowx, abs(start_balance) if start_balance < 0 else 0, data_right)
                sheet.write('G%s' % rowx, line['debit'], data_right)
                sheet.write('H%s' % rowx, line['credit'], data_right)
                end_balance = line['debit_start_balance'] - line['credit_start_balance'] + line['debit'] - line['credit']
                if account_id.account_type == 'asset_fixed' and end_balance < 0.0:
                    sheet.write('I%s' % rowx, end_balance if end_balance < 0 else 0, data_right)
                    sheet.write('J%s' % rowx, abs(end_balance) if end_balance > 0 else 0, data_right)
                else:
                    sheet.write('I%s' % rowx, end_balance if end_balance > 0 else 0, data_right)
                    sheet.write('J%s' % rowx, abs(end_balance) if end_balance < 0 else 0, data_right)
                if data['by_currency']:
                    if not currency_total_dict.get('MNT', False):
                        
                        currency_total_dict['MNT'] = {
                            'pre_debit_balance':start_balance if start_balance > 0 else 0,
                            'pre_credit_balance':abs(start_balance) if start_balance < 0 else 0,
                            'debit_balance':line['debit'],
                            'credit_balance':line['credit'],
                            'total_debit_balance':end_balance if end_balance > 0 else 0,
                            'total_credit_balance':abs(end_balance) if end_balance < 0 else 0
                        }
                    else:
                        if account_id.account_type == 'asset_fixed' and start_balance < 0.0:
                            currency_total_dict['MNT']['pre_debit_balance'] += start_balance if start_balance < 0 else 0
                            currency_total_dict['MNT']['pre_credit_balance'] += abs(start_balance) if start_balance > 0 else 0
                        else:
                            currency_total_dict['MNT']['pre_debit_balance'] += start_balance if start_balance > 0 else 0
                            currency_total_dict['MNT']['pre_credit_balance'] += abs(start_balance) if start_balance < 0 else 0
                        currency_total_dict['MNT']['debit_balance'] += line['debit']
                        currency_total_dict['MNT']['credit_balance'] += line['credit']
                        if account_id.account_type == 'asset_fixed' and end_balance < 0.0:
                            currency_total_dict['MNT']['total_debit_balance'] += end_balance if end_balance < 0 else 0
                            currency_total_dict['MNT']['total_credit_balance'] += abs(end_balance) if end_balance > 0 else 0
                        else:
                            currency_total_dict['MNT']['total_debit_balance'] += end_balance if end_balance > 0 else 0
                            currency_total_dict['MNT']['total_credit_balance'] += abs(end_balance) if end_balance < 0 else 0
                if account_id.account_type == 'asset_fixed' and start_balance < 0.0:
                    pre_debit_balance += start_balance if start_balance < 0 else 0
                    pre_credit_balance += abs(start_balance) if start_balance > 0 else 0
                else:
                    pre_debit_balance += start_balance if start_balance > 0 else 0
                    pre_credit_balance += abs(start_balance) if start_balance < 0 else 0
                debit_balance += line['debit']
                credit_balance += line['credit']
                if account_id.account_type == 'asset_fixed' and end_balance < 0.0:
                    total_debit_balance += end_balance if end_balance < 0 else 0
                    total_credit_balance += abs(end_balance) if end_balance > 0 else 0
                else:
                    total_debit_balance += end_balance if end_balance > 0 else 0
                    total_credit_balance += abs(end_balance) if end_balance < 0 else 0
                number += 1
                rowx += 1
            else:
                start_balance = line['debit_start_balance'] - line['credit_start_balance']
                currency_start_balance = line['start_amount_currency_debit'] - line['start_amount_currency_credit']
                sheet.merge_range('A%s:A%s' % (rowx, rowx+1), number, data_center)
                sheet.merge_range('B%s:C%s' % (rowx, rowx+1), line['account_name'], data_left)
                sheet.write('D%s' % rowx, 'MNT', data_left)
                sheet.write('D%s' % str(rowx+1), line['currency'], data_left)
                account_id = account_obj.search([('id','=',line['id'])],limit=1)
                if account_id.account_type == 'asset_fixed' and currency_start_balance < 0.0:
                    sheet.write('E%s' % rowx, start_balance if start_balance < 0 else 0, data_right)
                    sheet.write('E%s' % str(rowx+1), currency_start_balance if currency_start_balance < 0 else 0, data_right)
                    sheet.write('F%s' % rowx, abs(start_balance) if start_balance > 0 else 0, data_right)
                    sheet.write('F%s' % str(rowx+1), abs(currency_start_balance) if currency_start_balance > 0 else 0, data_right)
                else:
                    sheet.write('E%s' % rowx, start_balance if start_balance > 0 else 0, data_right)
                    sheet.write('E%s' % str(rowx+1), currency_start_balance if currency_start_balance > 0 else 0, data_right)
                    sheet.write('F%s' % rowx, abs(start_balance) if start_balance < 0 else 0, data_right)
                    sheet.write('F%s' % str(rowx+1), abs(currency_start_balance) if currency_start_balance < 0 else 0, data_right)
                
                sheet.write('G%s' % rowx, line['debit'], data_right)
                sheet.write('G%s' % str(rowx+1), line['amount_currency_debit'], data_right)
                sheet.write('H%s' % rowx, line['credit'], data_right)
                sheet.write('H%s' % str(rowx+1), line['amount_currency_credit'], data_right)

                end_balance = line['debit_start_balance'] - line['credit_start_balance'] + line['debit'] - line['credit']
                end_balance_currency = line['start_amount_currency_debit'] - line['start_amount_currency_credit'] + line['amount_currency_debit'] - line['amount_currency_credit']
                if account_id.account_type == 'asset_fixed' and end_balance_currency < 0.0:
                    sheet.write('I%s' % rowx, end_balance if end_balance < 0 else 0, data_right)
                    sheet.write('I%s' % str(rowx + 1), end_balance_currency if end_balance_currency < 0 else 0, data_right)
                    sheet.write('J%s' % rowx, abs(end_balance) if end_balance > 0 else 0, data_right)
                    sheet.write('J%s' % str(rowx + 1), abs(end_balance_currency) if end_balance_currency > 0 else 0, data_right)
                else:
                    sheet.write('I%s' % rowx, end_balance if end_balance > 0 else 0, data_right)
                    sheet.write('I%s' % str(rowx+1), end_balance_currency if end_balance_currency > 0 else 0, data_right)
                    sheet.write('J%s' % rowx, abs(end_balance) if end_balance < 0 else 0, data_right)
                    sheet.write('J%s' % str(rowx+1), abs(end_balance_currency) if end_balance_currency < 0 else 0, data_right)
                if line['currency'] not in currency_total_dict.keys():
                    currency_total_dict[line['currency']] = {
                        'pre_debit_balance': currency_start_balance if currency_start_balance > 0 else 0,
                        'pre_credit_balance':abs(currency_start_balance) if currency_start_balance < 0 else 0,
                        'debit_balance':line['amount_currency_debit'],
                        'credit_balance':line['amount_currency_credit'],
                        'total_debit_balance':end_balance_currency if end_balance_currency > 0 else 0,
                        'total_credit_balance':abs(end_balance_currency) if end_balance_currency < 0 else 0
                    }
                else:
                    if account_id.account_type == 'asset_fixed' and currency_start_balance < 0.0:
                        currency_total_dict[line['currency']]['pre_debit_balance'] += currency_start_balance if currency_start_balance < 0 else 0
                        currency_total_dict[line['currency']]['pre_credit_balance'] += abs(currency_start_balance) if currency_start_balance > 0 else 0
                    else:
                        currency_total_dict[line['currency']]['pre_debit_balance'] += currency_start_balance if currency_start_balance > 0 else 0
                        currency_total_dict[line['currency']]['pre_credit_balance'] += abs(currency_start_balance) if currency_start_balance < 0 else 0
                    currency_total_dict[line['currency']]['debit_balance'] += line['amount_currency_debit']
                    currency_total_dict[line['currency']]['credit_balance'] += line['amount_currency_credit']
                    if account_id.account_type == 'asset_fixed' and end_balance_currency < 0.0:
                        currency_total_dict[line['currency']]['total_debit_balance'] += end_balance_currency if end_balance_currency < 0 else 0
                        currency_total_dict[line['currency']]['total_credit_balance'] += abs(end_balance_currency) if end_balance_currency > 0 else 0
                    else:
                        currency_total_dict[line['currency']]['total_debit_balance'] += end_balance_currency if end_balance_currency > 0 else 0
                        currency_total_dict[line['currency']]['total_credit_balance'] += abs(end_balance_currency) if end_balance_currency < 0 else 0
                if account_id.account_type == 'asset_fixed' and start_balance < 0.0:
                    pre_debit_balance += start_balance if start_balance < 0 else 0
                    pre_credit_balance += abs(start_balance) if start_balance > 0 else 0
                else:
                    pre_debit_balance += start_balance if start_balance > 0 else 0
                    pre_credit_balance += abs(start_balance) if start_balance < 0 else 0
                debit_balance += line['debit']
                credit_balance += line['credit']
                if account_id.account_type == 'asset_fixed' and end_balance < 0.0:
                    total_debit_balance += end_balance if end_balance < 0 else 0
                    total_credit_balance += abs(end_balance) if end_balance > 0 else 0
                else:
                    total_debit_balance += end_balance if end_balance > 0 else 0
                    total_credit_balance += abs(end_balance) if end_balance < 0 else 0
                number += 1
                rowx += 2

        if currency_total_dict and data['by_currency']:
            sheet.merge_range('A%s:C%s' % (rowx, rowx+len(currency_total_dict.keys())-1), u'Валютын нийт дүн', text_center_border)
            for key, value in currency_total_dict.items():
                sheet.write('D%s' % rowx, key, text_center_border)
                sheet.write('E%s' % rowx, currency_total_dict[key]['pre_debit_balance'], txt_right_border)
                sheet.write('F%s' % rowx, currency_total_dict[key]['pre_credit_balance'], txt_right_border)
                sheet.write('G%s' % rowx, currency_total_dict[key]['debit_balance'], txt_right_border)
                sheet.write('H%s' % rowx, currency_total_dict[key]['credit_balance'], txt_right_border)
                sheet.write('I%s' % rowx, currency_total_dict[key]['total_debit_balance'], txt_right_border)
                sheet.write('J%s' % rowx, currency_total_dict[key]['total_credit_balance'], txt_right_border)
                rowx += 1

        sheet.merge_range('A%s:C%s' % (rowx, rowx), u'Нийт дүн', text_center_border)
        sheet.write('D%s' % rowx, 'MNT', text_center_border)
        sheet.write('E%s' % rowx, pre_debit_balance, txt_right_border)
        sheet.write('F%s' % rowx, pre_credit_balance, txt_right_border)
        sheet.write('G%s' % rowx, debit_balance, txt_right_border)
        sheet.write('H%s' % rowx, credit_balance, txt_right_border)
        sheet.write('I%s' % rowx, total_debit_balance, txt_right_border)
        sheet.write('J%s' % rowx, total_credit_balance, txt_right_border)

        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return
