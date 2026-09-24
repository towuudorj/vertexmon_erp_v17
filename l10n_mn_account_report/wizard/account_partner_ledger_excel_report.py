# -*- coding: utf-8 -*#
import io
import json
import xlsxwriter
import time
from odoo import fields, models, _, api
from odoo.tools import date_utils
from lxml import etree
from dateutil.relativedelta import relativedelta

class AccountPartnerLedgerExcelReport(models.TransientModel):
    _name = 'account.partner.ledger.excel.report'
    _inherit = ['xls.report.base']
    _description = 'account partner ledger excel report'


    company_id = fields.Many2one('res.company',u'Компани',required=True, default=lambda self: self.env.company)
    account_id = fields.Many2one('account.account',u'Данс')
    target_move = fields.Selection([('posted',u'Батлагдсан гүйлгээ'),
                                    ('all',u'Бүх гүйлгээ')],u'Зорилтот гүйлгээ',required=True,default='posted')
    result_selection = fields.Selection([('customer',u'Авлагын данс'),
                                         ('supplier',u'Өглөгийн данс'),
                                         ('customer_supplier',u'Өглөг авлагийн данс')],u'Харилцагчийн',required=True,default='customer')
    partner_ids = fields.Many2many('res.partner', 'ledger_report_partner_ids', 'report_id', 'partner_id', u'Харилцагч')
    is_extra = fields.Boolean(u'Задаргаатай эсэх')
    start_date = fields.Date(u'Эхлэх огноо',default=lambda *a: time.strftime('%Y-%m-01'))
    end_date = fields.Date(u'Дуусах огноо',default=lambda *a: time.strftime('%Y-%m-%d'))
    account_journal_ids = fields.Many2many('account.journal', 'account_partner_new_ledger_excel_journal_rel', 'account_id', 'journal_id',
                                          string='Journals', domain="[('type', '!=', 'opening'), ('company_id', '=', company_id)]")
    group_option_ids = fields.Many2many('ledger.report.group.option', 'ledger_report_group_option_re', 'report_id', 'group_id', string="Group options")


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'target_move': self.target_move,
            'result_selection': self.result_selection,
            'account_id': self.account_id.id,
            'partner_ids': self.partner_ids.ids or False,
            'is_extra': self.is_extra,
            'res_id': self.id,
            'account_journal_ids': self.account_journal_ids.ids
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'account.partner.ledger.excel.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Account balance report'}
        }


    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            doc = arch
            if self.env.user.has_group('l10n_mn_account_report.group_all_partner_report'):
                domain = "[]"
            else:
                self._cr.execute(f"SELECT partner_id from sale_order so  where so.user_id = {self.env.user.id} and so.company_id = {self.env.company.id} group by partner_id;")
                partner_ids = self._cr.dictfetchall()
                p_ids = [p_id['partner_id'] for p_id in partner_ids]
                domain = "[('id','in',%s)]" % str(p_ids)
            for node in doc.xpath("//field[@name='partner_ids']"):
                    node.attrib["domain"] = domain
        return arch, view

    def get_xlsx_report(self, data, response, get_file=False):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        sheet.set_landscape()
        sheet.set_paper(9)  # A4
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.repeat_rows(0, 0)
        group1_num = {
            'align': 'right',
            'bold': True,
            'bg_color': '#ffce99',
            'font_size': 12,
            'border': 1,
            'num_format': '#,##0.00 "₮"'
        }
        group_1_num = workbook.add_format(group1_num)
        group1_str = group1_num.copy()
        group1_str['num_format'] = 'General'
        group1_str['align'] = 'left'
        group_1_str = workbook.add_format(group1_str)
        group2_num = group1_num.copy()
        group2_num['bg_color'] = '#ffdab3'
        group_2_num = workbook.add_format(group2_num)
        group2_str = group2_num.copy()
        group2_str['num_format'] = 'General'
        group2_str['align'] = 'left'
        group_2_str = workbook.add_format(group2_str)
        group3_num = group1_num.copy()
        group3_num['bg_color'] = '#ffe6cc'
        group_3_num = workbook.add_format(group3_num)
        group3_str = group3_num.copy()
        group3_str['num_format'] = 'General'
        group3_str['align'] = 'left'
        group_3_str = workbook.add_format(group3_str)


        head = workbook.add_format({
                                    'align': 'center',
                                    'bold': True,
                                    'font_size': 16
                                    })
        data_left_no_border = workbook.add_format({
                                    'align': 'left',
                                    'font_size': 12
                                    })
        txt = workbook.add_format({
                                    'align': 'center',
                                    'font_size': 12,
                                    'border': 1,
                                    'num_format': 'General'
                                })
        txt_left = workbook.add_format({
                                    'align': 'left',
                                    'font_size': 11,
                                    'border': 1,
                                    'num_format': 'General'
                                })
        num_right = workbook.add_format({
                                    'align': 'right',
                                    'font_size': 11,
                                    'border': 1,
                                    'num_format': '#,##0.00'
                                })
        format_date = workbook.add_format({
                                    'align': 'center',
                                    'font_size': 11,
                                    'border': 1,
                                    'num_format': 'yyyy-mm-dd'
                                })

        title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'bold': True,
                                    'font_size': 12
                                })
        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 40)
        sheet.set_column(2, 2, 40)
        sheet.set_column(3, 3, 10)
        sheet.set_column(4, 4, 10)
        sheet.set_column(5, 5, 40)
        sheet.set_column(6, 14, 20)
        sheet.set_column('P:P', None, None, {'hidden': 1})
        sheet.freeze_panes(5, 3)
        group_values = []
        group_formats = {
            1: {'str': group_1_str, 'num': group_1_num},
            2: {'str': group_2_str, 'num': group_2_num},
            3: {'str': group_3_str, 'num': group_3_num}
        }
        self_obj = self.browse(data['res_id'])
        move_state = ['draft', 'posted']
        if self_obj.result_selection == 'customer':
            account_type = ['asset_receivable', 'asset_prepayments']
        elif self_obj.result_selection == 'supplier':
            account_type = ['liability_payable']
        else:
            account_type = ['asset_receivable','liability_payable', 'asset_prepayments']
        if self_obj.target_move == 'posted':
            move_state = ['posted']

        where = "and aa.account_type in ('%s')" % "', '".join(type for type in account_type)
        where_aml = ""
        order_by = []
        group_by = []
        select = ""
        if self_obj.partner_ids:
            where += f" and rp.id in (%s)" % ", ".join(str(p_id) for p_id in self_obj.partner_ids.ids)

        if self_obj.group_option_ids:
            for i in range(len(self_obj.group_option_ids)):
                if self_obj.group_option_ids[i].code == 'currency':
                    order_by.append("rc.id")
                    if not self_obj.is_extra:
                        group_by.append("aml.currency_id")
                    group_values.append({'last_value': False,
                                         'sequence': 0,
                                         'check_row' : 'currency',
                                         'write_row' : 'currency',
                                         'str': group_formats[i+1]['str'],
                                         'num': group_formats[i+1]['num'],
                                         'row': False,
                                         'start_balance': 0,
                                         'debit': 0,
                                         'credit': 0,
                                         })
                if self_obj.group_option_ids[i].code == 'partner':
                    order_by.append("rp.id")
                    if not self_obj.is_extra:
                        group_by.append("aml.partner_id")
                    group_values.append({'last_value': False,
                                         'sequence': 0,
                                         'check_row': 'partner_id',
                                         'write_row': 'partner_name',
                                         'str': group_formats[i+1]['str'],
                                         'num': group_formats[i+1]['num'],
                                         'row': False,
                                         'start_balance': 0,
                                         'debit': 0,
                                         'credit': 0,
                                         })
                if self_obj.group_option_ids[i].code == 'account':
                    order_by.append("aa.id")
                    if not self_obj.is_extra:
                        group_by.append("aml.account_id")
                    group_values.append({'last_value': False,
                                         'sequence': 0,
                                         'check_row': 'account_id',
                                         'write_row': 'account_name',
                                         'str': group_formats[i+1]['str'],
                                         'num': group_formats[i+1]['num'],
                                         'row': False,
                                         'start_balance': 0,
                                         'debit': 0,
                                         'credit': 0,
                                         })
        if not self_obj.is_extra:
            select += ("sum(aml.debit)  as debit,"
                       "sum(aml.credit) as credit,"
                       "sum(aml.amount_currency) as amount_currency")
            group_by = ["aml.partner_id", "aml.account_id", "aml.currency_id"]
        else:
            select += ("aml.debit as debit,"
                       "aml.credit as credit,"
                       "aml.amount_currency as amount_currency,"
                       "aml.name as name,"
                       "aml.date as date")

        if group_by:
            group_by = '\nGROUP BY ' + ', '.join(group for group in group_by)
        else:
            group_by = ''
        if 'partner_id' not in order_by:
            order_by.append('rp.id')
        if 'account_id' not in order_by:
            order_by.append('aa.id')
        if self_obj.is_extra:
            order_by.append("aml.date ASC")
        order_by = '\nORDER BY ' + ', '.join(order for order in order_by)

        if self_obj.account_journal_ids:
            where_aml += f" and aml.journal_id in ({', '.join(str(j_id.id) for j_id in self_obj.account_journal_ids)})"

        if self_obj.account_id:
            where += f" and aa.id = {self_obj.account_id.id}"
        env_user = self.env.user
        if not env_user.has_group('l10n_mn_account_report.group_all_partner_report'):
            self._cr.execute(f"SELECT partner_id from sale_order so  where so.user_id = {env_user.id} and so.company_id = {self.env.company.id} group by partner_id;")
            partner_ids = self._cr.dictfetchall()
            partner_ids_str = ', '.join(str(p_id['partner_id']) for p_id in partner_ids)
            if partner_ids_str:
                where += f" and rp.id in ({partner_ids_str})"

        qry = f"""
     select rp.id           as partner_id,
            aa.id as account_id,
            COALESCE(rp.name, '')||COALESCE('['||rp.code||']', '') as partner_name,
            coalesce(rc.name, 'MNT') as currency,
            aa.code||' '|| (aa.name::jsonb->>'mn_MN')::text as account_name,
            COALESCE(start_balance.balance, 0) as start_balance,
            COALESCE(start_balance.currency_balance, 0) as start_currency_balance,
            COALESCE(aml.debit, 0) as debit,
            COALESCE(aml.credit, 0) as credit,
            COALESCE(aml.amount_currency, 0) as amount_currency {", COALESCE(aml.name, '') as ref, aml.date as date" if self_obj.is_extra else ''}
     from (
         select sum(aml.balance) as balance,
                sum(aml.amount_currency) as currency_balance,
                 aml.account_id , COALESCE(aml.partner_id, 0) as partner_id {', aml.currency_id' if 'aml.currency_id' in group_by else ''}
         from account_move_line aml
         left join account_account aa on aa.id = aml.account_id
         left join res_partner rp on rp.id = aml.partner_id
         {'left join res_currency rc on rc.id = aml.currency_id' if 'aml.currency_id' in group_by else ''}
         where aml.parent_state = 'posted' and aml.date < '{self_obj.start_date}'
         and aml.company_id = {self_obj.company_id.id} {where_aml}
         group by aml.account_id , aml.partner_id {', aml.currency_id' if 'aml.currency_id' in group_by else ''}
     ) as start_balance
     FULL JOIN 
     (
         select
            COALESCE(aml.partner_id, 0) as partner_id,
            aml.account_id,
            aml.currency_id AS currency_id,
            {select}
        FROM account_move_line aml
        WHERE aml.company_id = {self_obj.company_id.id} AND aml.parent_state IN ('{"', '".join(move_state)}')
        AND aml.date BETWEEN '{self_obj.start_date}' AND '{self_obj.end_date}' {where_aml}
        {group_by}
     ) as aml ON aml.partner_id = start_balance.partner_id AND aml.account_id = start_balance.account_id {'AND aml.currency_id = start_balance.currency_id' if 'aml.currency_id' in group_by else ''}
     LEFT JOIN res_partner rp ON rp.id = COALESCE(aml.partner_id, start_balance.partner_id)
     LEFT JOIN account_account aa ON aa.id = COALESCE(aml.account_id, start_balance.account_id)
     LEFT JOIN res_currency rc ON rc.id =  {'COALESCE(aml.currency_id, start_balance.currency_id)' if 'aml.currency_id' in group_by else 'aml.currency_id'}
     WHERE (start_balance.balance != 0 or (aml.debit != 0 or aml.credit !=0))
     {where}
     {order_by}
    """

        self._cr.execute(qry)
        lines = self._cr.dictfetchall()
        sheet.merge_range("A1:C1", u'Байгууллагын нэр: %s' % (self_obj.company_id.name), data_left_no_border)

        if self_obj.result_selection == 'customer' and self_obj.is_extra == False:
            report_name =  u'Авлагын товчоо тайлан'
        elif self_obj.result_selection == 'customer' and self_obj.is_extra == True:
            report_name =  u'Авлагын дэлгэрэнгүй тайлан'
        elif self_obj.result_selection == 'supplier' and self_obj.is_extra == False:
            report_name =  u'Өглөгийн товчоо тайлан'
        elif self_obj.result_selection == 'supplier' and self_obj.is_extra == True:
            report_name =  u'Өглөгийн дэлгэрэнгүй тайлан'
        elif self_obj.result_selection == 'customer_supplier' and self_obj.is_extra == False:
            report_name =  u'Өглөг, авлагын товчоо тайлан'
        else:
            report_name =  u'Өглөг, авлагийн дэлгэрэнгүй тайлан'

        if self_obj.is_extra:
            sheet.merge_range(1, 0, 1, 9, report_name, head)
            sheet.merge_range(2, 8, 2, 9, u'Тайлант хугацаа: %s - %s'%(self_obj.start_date,self_obj.end_date) ,
                              data_left_no_border)
        else:
            sheet.merge_range(1, 0, 1, 7, report_name, head)
            sheet.merge_range(2, 6, 2, 7, u'Тайлант хугацаа: %s - %s' % (self_obj.start_date, self_obj.end_date),
                              data_left_no_border)
        rowx = 3
        coly = 0
        sheet.merge_range(rowx, coly, rowx+1, coly, u'№', title)
        coly += 1
        sheet.merge_range(rowx, coly, rowx+1, coly, u'Харилцагч', title)
        coly += 1
        sheet.merge_range(rowx, coly, rowx+1, coly, u'Данс', title)
        coly += 1
        sheet.merge_range(rowx, coly, rowx+1, coly, u'Валют', title)
        coly += 1
        if self_obj.is_extra:
            sheet.merge_range(rowx, coly, rowx + 1, coly, u'Огноо', title)
            coly += 1
            sheet.merge_range(rowx, coly, rowx + 1, coly, u'Гүйлгээний утга', title)
            coly += 1
        sheet.merge_range(rowx, coly, rowx+1, coly, u'Эхний үлдэгдэл', title)
        coly += 1
        sheet.merge_range(rowx, coly, rowx, coly+1, u'Гүйлгээ', title)
        sheet.write(rowx+1, coly, u'Дебит', title)
        coly += 1
        sheet.write(rowx+1, coly, u'Кредит', title)
        coly += 1
        sheet.merge_range(rowx, coly, rowx+1, coly, u'Эцсийн үлдэгдэл', title)
        rowx += 2
        sequence = 1
        last_coly = coly
        last_line_end_balance = {}
        last_partner_id = False
        last_account_id = False
        total_start_balance = 0
        total_debit = 0
        total_credit = 0
        for line in lines:
            for group_value in group_values:
                if not group_value['last_value'] or (line[group_value['check_row']] or '0') != group_value['last_value']:
                    group_value['sequence'] += 1
                    if group_value['row']:
                        sheet.write(group_value['row'], last_coly - 3, group_value['start_balance'], group_value['num'])
                        sheet.write(group_value['row'], last_coly - 2, group_value['debit'], group_value['num'])
                        sheet.write(group_value['row'], last_coly - 1, group_value['credit'], group_value['num'])
                        sheet.write(group_value['row'], last_coly,  group_value['start_balance'] + group_value['debit'] - group_value['credit'], group_value['num'])
                        group_value['start_balance'] = 0
                        group_value['debit'] = 0
                        group_value['credit'] = 0
                        group_value['end_balance'] = 0

                    parent_group_sequence = []
                    is_child = False
                    for i in range(len(group_values)):
                        if group_values[i].get('check_row', '0') == group_value['check_row']:
                            is_child = True
                            continue
                        if is_child:
                            group_values[i]['sequence'] = 0
                            group_values[i]['last_value'] = False
                        else:
                            parent_group_sequence.append(group_values[i]['sequence'])
                    if parent_group_sequence:
                        group_sequence = '.'.join(str(p_seq) for p_seq in parent_group_sequence)+'.'+str(group_value['sequence'])
                    else:
                        group_sequence = group_value['sequence']
                    sheet.write(rowx, 0, group_sequence, group_value['str'])
                    sheet.merge_range(rowx, 1, rowx, last_coly-4, line[group_value['write_row']],
                                      group_value['str'])
                    group_value['row'] = rowx
                    group_value['last_value'] = line[group_value['check_row']] or '0'
                    sequence = 1
                    last_line_end_balance = {}
                    rowx += 1
            is_acc_partner_first_balance = False
            if not last_partner_id or not last_account_id or last_partner_id != line['partner_id'] or last_account_id != line['account_id']:
                last_line_end_balance = {}
                last_partner_id = line['partner_id']
                last_account_id = line['account_id']
                is_acc_partner_first_balance = True
            coly = 0
            line_sequence = '.'.join(str(group['sequence']) for group in group_values) if group_values else ''
            line_sequence = line_sequence + '.' + str(sequence) if line_sequence != '' else sequence
            if line['currency'] != "MNT":
                sheet.merge_range(rowx, coly, rowx+1, coly, line_sequence, txt_left)
                coly += 1
                sheet.merge_range(rowx, coly, rowx+1, coly, line['partner_name'], txt_left)
                coly += 1
                sheet.merge_range(rowx, coly, rowx+1, coly, line['account_name'], txt_left)
                coly += 1
                sheet.write(rowx, coly, 'MNT', txt)
                sheet.write(rowx+1, coly, line['currency'], txt)
                coly += 1
                if self_obj.is_extra:
                    sheet.merge_range(rowx, coly, rowx+1, coly, line['date'], format_date)
                    coly += 1
                    sheet.merge_range(rowx, coly, rowx+1, coly, line['ref'], txt_left)
                    coly += 1
                    if sequence == 1:
                        for group in group_values:
                            group['start_balance'] += line['start_balance']
                        total_start_balance += line['start_balance']
                        last_line_end_balance[line['currency']] = line['start_currency_balance']
                        last_line_end_balance['MNT'] = line['start_balance']
                    else:
                        if line['currency'] not in last_line_end_balance.keys():
                            last_line_end_balance[line['currency']] = line['start_currency_balance']
                        if 'MNT' not in last_line_end_balance.keys():
                            last_line_end_balance['MNT'] = line['start_balance']
                        if not group_values and is_acc_partner_first_balance:
                            total_start_balance += line['start_balance']
                    sheet.write(rowx, coly, last_line_end_balance['MNT'], num_right)
                    sheet.write(rowx+1, coly, last_line_end_balance[line['currency']], num_right)
                    last_line_end_balance['MNT'] += (line['debit'] - line['credit'])
                    last_line_end_balance[line['currency']] += line['amount_currency']
                    for group in group_values:
                        group['debit'] += line['debit']
                        group['credit'] += line['credit']
                    total_debit += line['debit']
                    total_credit += line['credit']
                else:
                    for group in group_values:
                        group['start_balance'] += line['start_balance']
                        group['debit'] += line['debit']
                        group['credit'] += line['credit']
                    total_start_balance += line['start_balance']
                    total_debit += line['debit']
                    total_credit += line['credit']
                    sheet.write(rowx, coly, line['start_balance'], num_right)
                    sheet.write(rowx + 1, coly, line['start_currency_balance'], num_right)
                coly += 1
                sheet.write(rowx, coly, line['debit'], num_right)
                sheet.write(rowx+1, coly, line['amount_currency'] if line['amount_currency'] > 0 else 0, num_right)
                coly += 1
                sheet.write(rowx, coly, line['credit'], num_right)
                sheet.write(rowx + 1, coly, abs(line['amount_currency']) if line['amount_currency'] < 0 else 0, num_right)
                coly += 1
                if self_obj.is_extra:
                    sheet.write(rowx, coly, last_line_end_balance['MNT'], num_right)
                    sheet.write(rowx+1, coly, last_line_end_balance[line['currency']], num_right)
                else:
                    sheet.write(rowx, coly, line['start_balance'] + line['debit'] - line['credit'], num_right)
                    sheet.write(rowx + 1, coly,  line['start_currency_balance'] + line['amount_currency'], num_right)
                sheet.write('P%s' % str(rowx+1), "LINE", txt)
                sheet.write('P%s' % str(rowx+2), "LINE", txt)
                rowx += 2
            else:
                sheet.write(rowx, coly, line_sequence, txt_left)
                coly += 1
                sheet.write(rowx, coly, line['partner_name'], txt_left)
                coly += 1
                sheet.write(rowx, coly, line['account_name'], txt_left)
                coly += 1
                sheet.write(rowx, coly, 'MNT', txt)
                coly += 1
                if self_obj.is_extra:
                    sheet.write(rowx, coly, line['date'], format_date)
                    coly += 1
                    sheet.write(rowx, coly, line['ref'], txt_left)
                    coly += 1
                    if sequence == 1:
                        for group in group_values:
                            group['start_balance'] += line['start_balance']
                        total_start_balance += line['start_balance']
                        last_line_end_balance['MNT'] = line['start_balance']
                    else:
                        if not group_values and is_acc_partner_first_balance:
                            total_start_balance += line['start_balance']
                    for group in group_values:
                        group['debit'] += line['debit']
                        group['credit'] += line['credit']
                    total_debit += line['debit']
                    total_credit += line['credit']
                    if 'MNT' not in last_line_end_balance:
                        last_line_end_balance['MNT'] = line['start_balance']
                    sheet.write(rowx, coly, last_line_end_balance['MNT'], num_right)
                    last_line_end_balance['MNT'] += (line['debit'] - line['credit'])
                else:
                    for group in group_values:
                        group['start_balance'] += line['start_balance']
                        group['debit'] += line['debit']
                        group['credit'] += line['credit']
                    total_start_balance += line['start_balance']
                    total_debit += line['debit']
                    total_credit += line['credit']
                    sheet.write(rowx, coly, line['start_balance'], num_right)
                coly += 1
                sheet.write(rowx, coly, line['debit'], num_right)
                coly += 1
                sheet.write(rowx, coly, line['credit'], num_right)
                coly += 1
                if self_obj.is_extra:
                    sheet.write(rowx, coly, last_line_end_balance['MNT'], num_right)
                else:
                    sheet.write(rowx, coly, line['start_balance'] + line['debit'] - line['credit'], num_right)
                sheet.write('P%s' % str(rowx+1), "LINE", txt)
                rowx += 1
            sequence += 1
        for group_value in group_values:
            if group_value['row']:
                sheet.write(group_value['row'], last_coly - 3, group_value['start_balance'], group_value['num'])
                sheet.write(group_value['row'], last_coly - 2, group_value['debit'], group_value['num'])
                sheet.write(group_value['row'], last_coly - 1, group_value['credit'], group_value['num'])
                sheet.write(group_value['row'], last_coly,
                            group_value['start_balance'] + group_value['debit'] - group_value['credit'],
                            group_value['num'])
        sheet.merge_range(rowx, 0, rowx, last_coly-4, 'Нийт', title)
        sheet.write(rowx, last_coly-3, total_start_balance, num_right)
        sheet.write(rowx, last_coly-2, total_debit, num_right)
        sheet.write(rowx, last_coly-1, total_credit, num_right)
        sheet.write(rowx, last_coly, total_start_balance + total_debit - total_credit, num_right)

        rowx += 3
        sheet.merge_range("A%s:E%s" % (rowx, rowx),
                          u'Тайлан гаргасан:................................./.................................../',
                          data_left_no_border)

        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return


class LedgerReportGroupOption(models.Model):
    _name = 'ledger.report.group.option'
    _description = 'Ledger Report Group Option'

    name = fields.Char('Name')
    code = fields.Char('Code')