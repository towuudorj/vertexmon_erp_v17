# -*- coding: utf-8 -*#
import io
import json
import xlsxwriter
import time
from odoo import fields, models, _
from odoo.tools import date_utils


class AccountPartnerLedgerExcelReport(models.TransientModel):
    _name = 'account.partner.ledger.excel.report'
    _description = 'account partner ledger excel report'
    

    
    def _get_all_journal(self):
        company_id = self.env['res.company']._company_default_get('account.partner.ledger.excel.employee.report')
        return self.env['account.journal'].search([('company_id','=',company_id.id)])
    
    # def _get_account_id(self):
    #     company_id = self.env['res.company']._company_default_get('account.partner.ledger.excel.employee.report')
    #     account_id = self.env['account.account'].search([('company_id','=',company_id.id),('code','=','12000001')],limit=1)
    #     return account_id.id


    company_id = fields.Many2one('res.company',u'Компани',required=True, default=lambda self: self.env.company)
    account_id = fields.Many2one('account.account',u'Данс')
    target_move = fields.Selection([('posted',u'Батлагдсан гүйлгээ'),
                                    ('all',u'Бүх гүйлгээ')],u'Зорилтот гүйлгээ',required=True,default='posted')
    result_selection = fields.Selection([('customer',u'Авлагын данс'),
                                         ('supplier',u'Өглөгийн данс'),
                                         ('customer_supplier',u'Өглөг авлагийн данс')],u'Харилцагчийн',required=True,default='customer')
    partner_id = fields.Many2one('res.partner',u'Харилцагч')
    is_extra = fields.Boolean(u'Задаргаатай эсэх')
    start_date = fields.Date(u'Эхлэх огноо',default=lambda *a: time.strftime('%Y-%m-01'))
    end_date = fields.Date(u'Дуусах огноо',default=lambda *a: time.strftime('%Y-%m-%d'))
    account_journal_ids = fields.Many2many('account.journal', 'account_partner_new_ledger_excel_journal_rel', 'account_id', 'journal_id',
                                          string='Journals', domain="[('type', '!=', 'opening'), ('company_id', '=', company_id)]")
    preview_html = fields.Html(compute="_compute_preview_html", sanitize=False)
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
            'partner_id': self.partner_id.id,
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

    def get_report_data(self):
        return {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'target_move': self.target_move,
            'result_selection': self.result_selection,
            'account_id': self.account_id.id,
            'partner_id': self.partner_id.id,
            'is_extra': self.is_extra,
            'res_id': self.id,
            'account_journal_ids': self.account_journal_ids.ids
        }

    def return_main_view(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner ledger report'),
            'view_mode': 'form',
            'view_id': self.env.ref('l10n_mn_account_report.account_partner_ledger_excel_report_view').id,
            'target': 'new',
            'res_id': self.id,
            'res_model': self._name
        }

    def _compute_preview_html(self):
        for rec in self:
            rec.preview_html = f"""
                <iframe
                    src={f"/partner_ledger/report/pdf/{rec.id}"}
                    style="width:100%; height:100%; border:none;"
                    scrolling="true"
                    allow="autoplay; fullscreen; picture-in-picture" allowFullScreen="true"
                    frameborder="0"
                ></iframe>
            """

    def action_preview_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('PDF View'),
            'view_mode': 'form',
            'view_id':  self.env.ref('l10n_mn_account_report.account_partner_ledger_excel_report_preview').id,
            'target': 'new',
            'res_id': self.id,
            'res_model': self._name
        }

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
            'bg_color': '#b0f6ff',
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
        group2_num['bg_color'] = '#dbfbff'
        group_2_num = workbook.add_format(group2_num)
        group2_str = group2_num.copy()
        group2_str['num_format'] = 'General'
        group2_str['align'] = 'left'
        group_2_str = workbook.add_format(group2_str)
        group3_num = group1_num.copy()
        group3_num['bg_color'] = '#f2feff'
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
        sheet.set_column(3, 14, 20)
        sheet.set_column('P:P', None, None, {'hidden': 1})
        sheet.freeze_panes(5, 3)
        group_values = []
        group_formats = {
            1: {'str': group_1_str, 'num': group_1_num},
            2: {'str': group_2_str, 'num': group_2_num},
            3: {'str': group_3_str, 'num': group_3_num}
        }
        move_state = ['draft', 'posted']
        if data['result_selection'] == 'customer':
            account_type = ['asset_receivable']
        elif data['result_selection']=='supplier':
            account_type = ['liability_payable']
        else:
            account_type = ['asset_receivable','liability_payable']
        if data['target_move'] == 'posted':
            move_state = ['posted']

        where = "and aa.account_type in ('%s')" % "', '".join(type for type in account_type)
        order_by = []
        group_by = []
        select = ""
        if data['partner_id']:
            where += f" and rp.id = {data['partner_id']}"
        self = self.browse(data['res_id'])
        if self.group_option_ids:
            for i in range(len(self.group_option_ids)):
                if self.group_option_ids[i].code == 'currency':
                    order_by.append("rc.id")
                    if not data['is_extra']:
                        group_by.append("rc.id")
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
                if self.group_option_ids[i].code == 'partner':
                    order_by.append("rp.id")
                    if not data['is_extra']:
                        group_by.append("rp.id")
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
                if self.group_option_ids[i].code == 'account':
                    order_by.append("aa.id")
                    if not data['is_extra']:
                        group_by.append("aa.id")
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
        if not data['is_extra']:
            select += ("sum(aml.debit)  as debit,"
                       "sum(aml.credit) as credit,"
                       "sum(aml.amount_currency) as amount_currency")
            group_by += ["rp.name", "rp.ref", "rp.id", "rc.name", "aml.account_id", "aa.code", "aa.name", "start_balance.balance", "start_balance.currency_balance"]
        else:
            select += ("aml.debit as debit,"
                       "aml.credit as credit,"
                       "aml.amount_currency as amount_currency,"
                       "aml.name as ref,"
                       "aml.date as date")
            order_by.append("aml.date ASC")
            # group_by += ['aml.account_id']
        if group_by:
            group_by = '\nGROUP BY ' + ', '.join(group for group in group_by)
        else:
            group_by = ''
        if 'partner_id' not in order_by:
            order_by.append('partner_id')
        if 'account_id' not in order_by:
            order_by.append('account_id')
        order_by = '\nORDER BY ' + ', '.join(order for order in order_by)

        if self.account_journal_ids:
            where += f" and aml.journal_id in ({', '.join(str(j_id.id) for j_id in self.account_journal_ids)})"

        if self.account_id:
            where += f" and aml.account_id = {self.account_id.id}"

        qry = f"""
             select rp.id           as partner_id,
                    COALESCE(rp.name, '')||COALESCE('['||rp.code||']', '') as partner_name,
                    rc.name         as currency,
                    aml.account_id  as account_id,
                    aa.code||' '|| (aa.name::jsonb->>'mn_MN')::text as account_name,
                    COALESCE(start_balance.balance, 0) as start_balance,
                    COALESCE(start_balance.currency_balance, 0) as start_currency_balance,
                    {select}
             from account_move_line aml
             left join res_partner rp on aml.partner_id = rp.id
             left join res_currency rc on aml.currency_id = rc.id
             left join account_account aa on aml.account_id = aa.id
             left join
             (
                 select case when eoy.balance is not null
                             then eoy.balance + sum(aml.balance)
                             else sum(aml.balance)
                             end as balance,
                        case when eoy.amount_currency is not null
                              then eoy.amount_currency + sum(aml.amount_currency)
                              else sum(aml.amount_currency)
                              end as currency_balance,
                        aml.account_id , aml.partner_id
                 from account_move_line aml
                 left join account_move am on am.id = aml.move_id
                 left join account_account aa on aa.id = aml.account_id
                 left join res_partner rp on rp.id = aml.partner_id
                 left join account_journal aj on aj.id = aml.journal_id
                 left join (
                     select aml.account_id, aml.partner_id, aml.date, aml.balance, aml.amount_currency,
                     RANK() OVER (PARTITION BY aml.account_id, aml.partner_id ORDER BY aml.date DESC) as rank
                     from account_move_line aml
                     left join account_journal aj on aj.id = aml.journal_id
                     where aj.type ='opening' and aml.company_id = {self.company_id.id} and aml.date < '{data['start_date']}'
                 ) as eoy on eoy.account_id = aa.id and eoy.partner_id = rp.id 
                 where am.state = 'posted' 
                 and aml.company_id = {self.company_id.id} and
                 (eoy.rank = 1 or eoy.rank is null) and aml.date < '{data['start_date']}' and (eoy.date IS NULL OR aml.date >= eoy.date)
                 group by eoy.balance, aml.account_id , aml.partner_id, eoy.amount_currency
             ) as start_balance on (start_balance.account_id = aml.account_id and start_balance.partner_id = rp.id)
             where
                 aml.date >= '{data['start_date']}'
                 and aml.date <= '{data['end_date']}'
                 and aml.move_id in (select id from account_move where state in ('{"', '".join(str(move) for move in move_state)}'))
                 and aml.company_id = {self.company_id.id} 
                 {where}
             {group_by}
             {order_by}
             """
        self._cr.execute(qry)
        lines = self._cr.dictfetchall()
        sheet.merge_range("A1:C1", u'Байгууллагын нэр: %s' % (data['company_name']), data_left_no_border)

        if data['result_selection'] == 'customer' and data['is_extra'] == False:
            report_name =  u'Авлагын товчоо тайлан'
        elif data['result_selection'] == 'customer' and data['is_extra'] == True:
            report_name =  u'Авлагын дэлгэрэнгүй тайлан'
        elif data['result_selection'] == 'supplier' and data['is_extra'] == False:
            report_name =  u'Өглөгийн товчоо тайлан'
        elif data['result_selection'] == 'supplier' and data['is_extra'] == True:
            report_name =  u'Өглөгийн дэлгэрэнгүй тайлан'
        elif data['result_selection'] == 'customer_supplier' and data['is_extra'] == False:
            report_name =  u'Өглөг, авлагын товчоо тайлан'
        else:
            report_name =  u'Өглөг, авлагийн дэлгэрэнгүй тайлан'

        if self.is_extra:
            sheet.merge_range(1, 0, 1, 9, report_name, head)
            sheet.merge_range(2, 8, 2, 9, u'Тайлант хугацаа: %s - %s'%(data['start_date'],data['end_date']) ,
                              data_left_no_border)
        else:
            sheet.merge_range(1, 0, 1, 7, report_name, head)
            sheet.merge_range(2, 6, 2, 7, u'Тайлант хугацаа: %s - %s' % (data['start_date'], data['end_date']),
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
        if self.is_extra:
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
                if not group_value['last_value'] or line[group_value['check_row']] != group_value['last_value']:
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
                        if group_values[i]['check_row'] == group_value['check_row']:
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
                    group_value['last_value'] = line[group_value['check_row']]
                    sequence = 1
                    last_line_end_balance = {}
                    rowx += 1
            if not last_partner_id or not last_account_id or last_partner_id != line['partner_id'] or last_account_id != line['account_id']:
                last_line_end_balance = {}
                last_partner_id = line['partner_id']
                last_account_id = line['account_id']
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
                if self.is_extra:
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
                if self.is_extra:
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
                if self.is_extra:
                    sheet.write(rowx, coly, line['date'], format_date)
                    coly += 1
                    sheet.write(rowx, coly, line['ref'], txt_left)
                    coly += 1
                    if sequence == 1:
                        for group in group_values:
                            group['start_balance'] += line['start_balance']
                        total_start_balance += line['start_balance']
                        last_line_end_balance['MNT'] = line['start_balance']
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
                if self.is_extra:
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