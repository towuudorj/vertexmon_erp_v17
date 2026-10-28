# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from odoo import api, fields, models, tools, _
from datetime import date, datetime, time, timedelta
from odoo.tools import date_utils
import io
import json
import xlsxwriter
import base64
import openpyxl
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
               
class ResourceCalendar(models.Model): 
    _inherit = 'resource.calendar'
    
    # is_holiday_time_out = fields.Boolean(string='Holiday time out')
    work_time = fields.Float(string='Working hour')
    lunchtime_start = fields.Float(string='Lunch time start')
    lunchtime_end = fields.Float(string='Lunch time end', compute='_compute_lunchtime_end')

    @api.depends('attendance_ids', 'attendance_ids.hour_from', 'attendance_ids.hour_to', 'two_weeks_calendar')
    def _compute_hours_per_day(self):
        super(ResourceCalendar, self)._compute_hours_per_day()
        for obj in self:
            if obj.work_time:
                obj.hours_per_day = obj.work_time

    @api.onchange('lunchtime_start')
    def _compute_lunchtime_end(self):
        for obj in self:
            if obj.lunchtime_start:
                obj.lunchtime_end = obj.lunchtime_start + 1
            else:
                obj.lunchtime_end = None


class hr_contract(models.Model):
    _inherit = 'hr.contract'
    
    phone_add = fields.Float(string='Phone add')
    administration_add = fields.Float(string='Administration add')
    food_and_vehicle_add = fields.Float(string='Food and vehicle add')
    long_year_add = fields.Float(string='Long year add')
    health_insurance = fields.Float(string='Health insurance')
    accident_insurance = fields.Float(string='Accident insurance')
    voucher = fields.Float(string='Voucher')
    abnormal_add = fields.Float(string='Abnormal add')
    trial_end_date = fields.Float(string='Trial End Date')
    insurance_type_id = fields.Many2one('insurance.type', 'Insurance Type')

class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    dep_id = fields.Many2one('hr.department', string='Department')
    payslip_type = fields.Selection([('advance', 'Урьдчилгаа цалин'),
                                     ('final', 'Сүүл цалин')],
                                    string='Цалингийн төрөл', required=True, default='final')
    advance_run_id = fields.Many2one('hr.payslip.run', string='Урьдчилгаа цалингийн багц',
                                     domain="[('payslip_type', '=', 'advance'), ('state', '=', 'done'), ('id', '!=', id)]",
                                     help='Сүүл цалин бодоход энэ багцын урьдчилгааг ADV суутгалд татна.')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.onchange('payslip_type')
    def _onchange_payslip_type(self):
        if self.payslip_type == 'advance':
            self.advance_run_id = False

    def get_report_data(self):
        data = {
            'self_id': self.id
        }
        return data

    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'hr.payslip.run',
                     'output_format': 'xlsx',
                     'options': json.dumps(data, default=date_utils.json_default),
                     'report_name': self.name}
        }

    def action_open_import_wizard(self):
        self.ensure_one()
        return {
            'name': _('Цалингийн тайлан импортлох'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_run_id': self.id},
        }


    def get_xlsx_report(self, data, response, get_file=False):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
            'align': 'center',
            'bold': True,
            'font_size': 14
        })

        title = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bold': True,
            'text_wrap': True,
            'font_size': 12,
            'bg_color': '#FBCEB1',
            'color': 'black'
        })

        data_right = workbook.add_format({
            'align': 'right',
            'border': 1,
            'text_wrap': True,
            'font_size': 12,
            'num_format': '#,##0.00'
        })
        data_left = workbook.add_format({
            'align': 'left',
            'border': 1,
            'font_size': 12,
            'num_format': '#,##0.00'
        })
        data_left_borderless = workbook.add_format({
            'align': 'left',
            'border': 0,
            'font_size': 12,
            'num_format': '#,##0.00'
        })
        data_bold_center = workbook.add_format({
            'align': 'center',
            'bold': True,
            'border': 1,
            'font_size': 12,
            'num_format': '#,##0.00'
        })
        header_txt = workbook.add_format({
                                    'align': 'center',
                                    'bold': True,
                                    'font_size': 12,
                                    'border': 1,
                                    'text_wrap': True,
                                    })
        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0)
        self_obj = self.env['hr.payslip.run'].browse(data.get('self_id')) if data.get('self_id') else self

        if self_obj.payslip_type == 'advance':
            # -------------------------------------------------------------
            # Урьдчилгаа цалингийн тайлан (Зөвхөн 7 багана + нуусан ID)
            # Баганууд: №, Овог, Нэр, Хэлтэс тасаг, Дансны дугаар, Урьдчилгаа цалин СС, Регистр, ID
            # -------------------------------------------------------------
            sheet.set_column(0, 0, 5)
            sheet.set_column(1, 2, 15)
            sheet.set_column(3, 4, 20)
            sheet.set_column(5, 5, 22)
            sheet.set_column(6, 6, 15)
            sheet.set_column(7, 7, None, None, {'hidden': True})

            sheet.merge_range(0, 0, 0, 3, self_obj.company_id.name, title)
            sheet.merge_range(1, 0, 1, 6, 'БАТЛАВ: ГҮЙЦЭТГЭХ ЗАХИРАЛ .....................................................Д.МЭНДСАЙХАН', data_left_borderless)
            sheet.merge_range("A3:G3", '%s %s' % (self_obj.name, 'урьдчилгаа цалин'), head)

            rowx = 3
            sheet.merge_range(rowx, 0, rowx+1, 0, u'№', title)
            sheet.merge_range(rowx, 1, rowx+1, 1, u'Овог', title)
            sheet.merge_range(rowx, 2, rowx+1, 2, u'Нэр', title)
            sheet.merge_range(rowx, 3, rowx+1, 3, u'Хэлтэс тасаг', title)
            sheet.merge_range(rowx, 4, rowx+1, 4, u'Дансны дугаар', title)
            sheet.merge_range(rowx, 5, rowx+1, 5, u'Урьдчилгаа цалин СС', title)
            sheet.merge_range(rowx, 6, rowx+1, 6, u'Регистр', title)
            sheet.merge_range(rowx, 7, rowx+1, 7, u'ID', title)
            rowx += 2

            number = 1
            for slip in self_obj.slip_ids:
                account_number = ''
                if slip.employee_id.work_contact_id.bank_ids:
                    b = slip.employee_id.work_contact_id.bank_ids[0]
                    account_number = getattr(b, 'acc_number', getattr(b, 'account_number', '')) or ''
                elif slip.employee_bank_account:
                    account_number = slip.employee_bank_account
                elif slip.employee_id.bank_account_id:
                    account_number = slip.employee_id.bank_account_id.acc_number or ''

                adv_val = 0.0
                advp_line = slip.line_ids.filtered(lambda l: l.code == 'ADVP')
                if advp_line:
                    adv_val = advp_line[0].total or advp_line[0].amount or 0.0
                if not adv_val:
                    adv_val = slip.prepayment_amount or slip.net_amount or 0.0

                reg_no = slip.employee_id.ssnid or slip.employee_id.identification_id or ''

                sheet.write(rowx, 0, number, data_left)
                sheet.write(rowx, 1, slip.employee_id.last_name or '', data_left)
                sheet.write(rowx, 2, slip.employee_id.name or '', data_left)
                sheet.write(rowx, 3, slip.employee_id.department_id.name or '', data_left)
                sheet.write(rowx, 4, account_number, data_left)
                sheet.write(rowx, 5, adv_val, data_right)
                sheet.write(rowx, 6, reg_no, data_right)
                sheet.write(rowx, 7, slip.id, data_right)

                rowx += 1
                number += 1

            sheet.merge_range(rowx, 0, rowx, 4, u'Нийт дүн:', data_bold_center)
            rowx += 1
            if rowx - 1 >= 6:
                sheet.write("F%s" % rowx, '=sum(F6:F%s)' % (rowx - 1), header_txt)
            else:
                sheet.write("F%s" % rowx, 0.0, header_txt)
            sheet.write("G%s" % rowx, '', header_txt)
            sheet.write("H%s" % rowx, '', header_txt)

            workbook.close()
            output.seek(0)
            if get_file:
                res_data = output.getvalue()
                output.close()
                return res_data
            if response:
                response.stream.write(output.read())
            output.close()
            return

        # -------------------------------------------------------------
        # Сүүл цалингийн тайлан (28 багана + томьёонууд + нуусан баганууд)
        # -------------------------------------------------------------
        sheet.set_column(0, 0, 5)
        sheet.set_column(1, 27, 18)
        max_ceiling = 7920000.0
        si_rule = self.env['hr.salary.rule'].search([
            ('code', '=', 'SI11'),
            '|', ('company_id', '=', self_obj.company_id.id if self_obj else False), ('company_id', '=', False)
        ], limit=1)
        if si_rule and si_rule.amount_python_compute:
            import re
            m = re.search(r'momn_min_salary\s*=\s*(\d+)', si_rule.amount_python_compute)
            if m:
                max_ceiling = float(m.group(1)) * 10

        sheet.merge_range(0, 0, 0, 3, self_obj.company_id.name, title)
        sheet.merge_range(1, 0, 1, 8, 'БАТЛАВ: ГҮЙЦЭТГЭХ ЗАХИРАЛ .....................................................Д.МЭНДСАЙХАН', data_left_borderless)
        sheet.merge_range("A3:AB3", '%s %s'%(self_obj.name, 'сүүл цалин'), head)
        rowx = 3
        colly = 0
        sheet.merge_range(rowx, colly , rowx+1, colly, u'№', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Овог', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Нэр', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Хэлтэс тасаг', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Дансны дугаар', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Үндсэн цалин', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Сарын ажлын хоног', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Сарын ажлын фонд цаг', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Ажилласан хоног СС', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Ажилласан цаг СС', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Илүү цаг', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Илүү цагийн нэмэгдэл', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Бодогдсон цалин', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Амралтын мөнгө', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Гүйцэтгэлийн нэмэгдэл', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Бусад нэмэгдэл СС', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Нэмэгдлийн дүн', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Олговол зохих', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'НДШ төлөв', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Урьдчилгаа цалин СС', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'НДШ-Даатгуулагчаас', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'НДШ Ажил олгогчоос', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'ХАОАТ', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Утасны суутгал', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Ажилчдаас авлага', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Суутгалын дүн', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Гарт олгох', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'Регистр №', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'ID', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'EMP_NDSH_RATE', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'COMP_NDSH_RATE', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'MAX_NDSH_CEIL', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'PIT_RATE', title)
        colly += 1
        sheet.merge_range(rowx, colly , rowx+1, colly, u'PIT_RELIEF', title)
        sheet.set_column(28, colly, None, None, {'hidden': True})
        rowx += 2

        number = 1
        for slip in self_obj.slip_ids:
            account_number = ''
            if slip.employee_id.work_contact_id.bank_ids:
                b = slip.employee_id.work_contact_id.bank_ids[0]
                account_number = getattr(b, 'acc_number', getattr(b, 'account_number', '')) or ''
            elif slip.employee_bank_account:
                account_number = slip.employee_bank_account
            elif slip.employee_id.bank_account_id:
                account_number = slip.employee_id.bank_account_id.acc_number or ''
            colly = 0
            sheet.write(rowx, colly, number, data_left)
            colly += 1
            sheet.write(rowx, colly, slip.employee_id.last_name or '', data_left)
            colly += 1
            name = slip.employee_id.name
            if name and '.' in name:
                list = name.split(".")
                name = list[0] if len(list[1]) == 1 else list[1]
            sheet.write(rowx, colly, name or '', data_left)
            colly += 1
            sheet.write(rowx, colly, slip.employee_id.department_id.name or '', data_left)
            colly += 1
            sheet.write(rowx, colly, account_number, data_left)
            colly += 1
            sheet.write(rowx, colly, slip.contract_id.wage or 0.0, data_left)
            colly += 1
            sheet.write(rowx, colly, slip.month_work_days or 0.0, data_left)
            colly += 1
            sheet.write(rowx, colly, slip.month_work_hours or 0.0, data_left)
            colly += 1
            sheet.write(rowx, colly, slip.worked_days or 0.0, data_left)
            colly += 1
            sheet.write(rowx, colly, slip.worked_hours or 0.0, data_left)
            colly += 1
            sheet.write(rowx, colly, slip.overtime_hours or 0.0, data_left)
            colly += 1
            sheet.write(rowx, colly, u'=F%s/H%s*K%s*1.5' % (rowx + 1, rowx + 1, rowx + 1), data_right)
            colly += 1
            sheet.write(rowx, colly, u'=F%s/H%s*J%s+L%s' % (rowx + 1, rowx + 1, rowx + 1, rowx + 1), data_right)
            colly += 1
            sheet.write(rowx, colly, slip.vacation_amount or 0.0, data_right)
            colly += 1
            sheet.write(rowx, colly, slip.performance_amount or 0.0, data_right)
            colly += 1
            sheet.write(rowx, colly, slip.other_allowance_amount or 0.0, data_right)
            colly += 1
            sheet.write(rowx, colly, '=SUM(N%s:P%s)' % (rowx + 1, rowx + 1), data_right)
            colly += 1
            sheet.write(rowx, colly, '=M%s+Q%s' % (rowx + 1, rowx + 1), data_right)
            colly += 1
            ndsh_state = 'Төлнө' if slip.ndsh_employee_amount else 'Төлөхгүй'
            sheet.write(rowx, colly, ndsh_state, data_right)
            colly += 1
            adv_val = slip.prepayment_amount if slip.payslip_type == 'advance' else (slip.advance_amount or 0.0)
            sheet.write(rowx, colly, adv_val, data_right)
            colly += 1
            r_num = rowx + 1

            has_ndsh = bool(slip.ndsh_employee_amount or (slip.contract_id.insurance_type_id and slip.contract_id.insurance_type_id.insurance_percent_employee > 0))
            if has_ndsh and slip.payslip_type != 'advance':
                emp_ndsh_rate = (slip.contract_id.insurance_type_id.insurance_percent_employee / 100.0) if slip.contract_id.insurance_type_id else 0.115
                comp_ndsh_rate = (slip.contract_id.insurance_type_id.insurance_percent_employer / 100.0) if slip.contract_id.insurance_type_id else 0.125
            else:
                emp_ndsh_rate = 0.0
                comp_ndsh_rate = 0.0

            pit_rate = 0.10 if slip.payslip_type != 'advance' else 0.0

            # U: НДШ-Даатгуулагчаас
            if slip.payslip_type == 'advance':
                sheet.write(rowx, colly, 0.0, data_right)
            else:
                sheet.write(rowx, colly, u'=ROUND(MIN(R%s,AF%s)*AD%s, 2)' % (r_num, r_num, r_num), data_right)
            colly += 1

            # V: НДШ Ажил олгогчоос
            if slip.payslip_type == 'advance':
                sheet.write(rowx, colly, 0.0, data_right)
            else:
                sheet.write(rowx, colly, u'=ROUND(R%s*AE%s, 2)' % (r_num, r_num), data_right)
            colly += 1

            # W: ХАОАТ
            if slip.payslip_type == 'advance':
                sheet.write(rowx, colly, 0.0, data_right)
            else:
                sheet.write(rowx, colly, u'=ROUND(MAX(0, (R%s-U%s)*AG%s-AH%s), 2)' % (r_num, r_num, r_num, r_num), data_right)
            colly += 1

            # X: Утасны суутгал
            sheet.write(rowx, colly, slip.phone_deduction_amount or 0.0, data_right)
            colly += 1

            # Y: Ажилчдаас авлага
            sheet.write(rowx, colly, slip.receivable_deduction_amount or 0.0, data_right)
            colly += 1

            # Z: Суутгалын дүн
            sheet.write(rowx, colly, '=Y%s+X%s+W%s+U%s+T%s' % (r_num, r_num, r_num, r_num, r_num), data_right)
            colly += 1

            # AA: Гарт олгох
            if slip.payslip_type == 'advance':
                sheet.write(rowx, colly, slip.prepayment_amount or slip.net_amount or 0.0, data_right)
            else:
                sheet.write(rowx, colly, '=R%s-Z%s' % (r_num, r_num), data_right)
            colly += 1

            # AB: Регистр №
            sheet.write(rowx, colly, slip.employee_id.ssnid or slip.employee_id.identification_id or '', data_right)
            colly += 1

            # AC: ID (Hidden)
            sheet.write(rowx, colly, slip.id, data_right)
            colly += 1

            # AD: EMP_NDSH_RATE (Hidden)
            sheet.write(rowx, colly, emp_ndsh_rate, data_right)
            colly += 1

            # AE: COMP_NDSH_RATE (Hidden)
            sheet.write(rowx, colly, comp_ndsh_rate, data_right)
            colly += 1

            # AF: MAX_NDSH_CEIL (Hidden)
            sheet.write(rowx, colly, max_ceiling, data_right)
            colly += 1

            # AG: PIT_RATE (Hidden)
            sheet.write(rowx, colly, pit_rate, data_right)
            colly += 1

            # AH: PIT_RELIEF (Hidden)
            if slip.payslip_type == 'advance':
                sheet.write(rowx, colly, 0.0, data_right)
            else:
                relief_formula = (
                    u'=IF(R%s-U%s<=500000,20000,IF(R%s-U%s<=1000000,18000,IF(R%s-U%s<=1500000,16000,'
                    u'IF(R%s-U%s<=2000000,14000,IF(R%s-U%s<=2500000,12000,IF(R%s-U%s<=3000000,10000,0))))))'
                    % (r_num, r_num, r_num, r_num, r_num, r_num, r_num, r_num, r_num, r_num, r_num, r_num)
                )
                sheet.write(rowx, colly, relief_formula, data_right)
            colly += 1

            rowx += 1
            number += 1

        sheet.merge_range(rowx, 0, rowx,  4, u'Нийт дүн:', data_bold_center)
        rowx += 1
        sheet.write("F%s" % rowx, '=sum(F6:F%s)' % (rowx - 1), header_txt)
        sheet.write("G%s" % rowx, '=sum(G6:G%s)' % (rowx - 1), header_txt)
        sheet.write("H%s" % rowx, '=sum(H6:H%s)' % (rowx - 1), header_txt)
        sheet.write("I%s" % rowx, '=sum(I6:I%s)' % (rowx - 1), header_txt)
        sheet.write("J%s" % rowx, '=sum(J6:J%s)' % (rowx - 1), header_txt)
        sheet.write("K%s" % rowx, '=sum(K6:K%s)' % (rowx - 1), header_txt)
        sheet.write("L%s" % rowx, '=sum(L6:L%s)' % (rowx - 1), header_txt)
        sheet.write("M%s" % rowx, '=sum(M6:M%s)' % (rowx - 1), header_txt)
        sheet.write("N%s" % rowx, '=sum(N6:N%s)' % (rowx - 1), header_txt)
        sheet.write("O%s" % rowx, '=sum(O6:O%s)' % (rowx - 1), header_txt)
        sheet.write("P%s" % rowx, '=sum(P6:P%s)' % (rowx - 1), header_txt)
        sheet.write("Q%s" % rowx, '=sum(Q6:Q%s)' % (rowx - 1), header_txt)
        sheet.write("R%s" % rowx, '=sum(R6:R%s)' % (rowx - 1), header_txt)
        sheet.write("S%s" % rowx, '', header_txt)
        sheet.write("T%s" % rowx, '=sum(T6:T%s)' % (rowx - 1), header_txt)
        sheet.write("U%s" % rowx, '=sum(U6:U%s)' % (rowx - 1), header_txt)
        sheet.write("V%s" % rowx, '=sum(V6:V%s)' % (rowx - 1), header_txt)
        sheet.write("W%s" % rowx, '=sum(W6:W%s)' % (rowx - 1), header_txt)
        sheet.write("X%s" % rowx, '=sum(X6:X%s)' % (rowx - 1), header_txt)
        sheet.write("Y%s" % rowx, '=sum(Y6:Y%s)' % (rowx - 1), header_txt)
        sheet.write("Z%s" % rowx, '=sum(Z6:Z%s)' % (rowx - 1), header_txt)
        sheet.write("AA%s" % rowx, '=sum(AA6:AA%s)' % (rowx - 1), header_txt)
        sheet.write("AB%s" % rowx, '', header_txt)
        sheet.write("AC%s" % rowx, '', header_txt)
        sheet.write("AD%s" % rowx, '', header_txt)
        sheet.write("AE%s" % rowx, '', header_txt)
        sheet.write("AF%s" % rowx, '', header_txt)
        sheet.write("AG%s" % rowx, '', header_txt)
        sheet.write("AH%s" % rowx, '', header_txt)

        workbook.close()
        output.seek(0)
        if get_file:
            res_data = output.getvalue()
            output.close()
            return res_data
        if response:
            response.stream.write(output.read())
        output.close()
        return

# Цалингийн хуудсын багцын жагсаалтын багана -> цалингийн дүрмийн код(ууд)
PAYSLIP_OUTPUT_COLUMN_CODES = {
    'wage_amount': ('BS',),
    'overtime_amount': ('OVERADD',),
    'computed_salary': ('CBS',),
    'allowance_total': ('ADT',),
    'gross_amount': ('CS',),
    'ndsh_employee_amount': ('SI11', 'SI15', 'SI10'),
    'ndsh_company_amount': ('NDSH',),
    'pit_amount': ('LLL',),
    'deduction_total': ('TE',),
    'net_amount': ('GIVE', 'ADVP'),
}

PAYSLIP_COLUMN_CODES = {
    'wage_amount': ('BS',),
    'month_work_days': ('MWD',),
    'month_work_hours': ('MWT',),
    'worked_days': ('WDD',),
    'worked_hours': ('WDT',),
    'overtime_hours': ('OVER',),
    'overtime_amount': ('OVERADD',),
    'computed_salary': ('CBS',),
    'vacation_amount': ('RS',),
    'performance_amount': ('KPI',),
    'other_allowance_amount': ('OTA',),
    'allowance_total': ('ADT',),
    'gross_amount': ('CS',),
    'advance_amount': ('ADV',),
    'ndsh_employee_amount': ('SI11', 'SI15', 'SI10'),
    'ndsh_company_amount': ('NDSH',),
    'pit_amount': ('LLL',),
    'phone_deduction_amount': ('PH',),
    'receivable_deduction_amount': ('EDE', 'PAY', 'FAULT'),
    'deduction_total': ('TE',),
    # ADVP мөр зөвхөн урьдчилгаа цалингийн хуудсанд байна
    'net_amount': ('GIVE', 'ADVP'),
}

# Excel тайлангийн толгой баганууд -> PAYSLIP_COLUMN_CODES түлхүүрийн харгалзаа
PAYSLIP_HEADER_TO_COLUMN_KEY = [
    (('Үндсэн цалин',), 'wage_amount'),
    (('Сарын ажлын хоног',), 'month_work_days'),
    (('Сарын ажлын фонд цаг', 'Сарын ажлын цаг'), 'month_work_hours'),
    (('Ажилласан хоног СС', 'Ажилласан хоног'), 'worked_days'),
    (('Ажилласан цаг СС', 'Ажилласан цаг'), 'worked_hours'),
    (('Илүү цаг',), 'overtime_hours'),
    (('Илүү цагийн нэмэгдэл',), 'overtime_amount'),
    (('Бодогдсон цалин',), 'computed_salary'),
    (('Амралтын мөнгө',), 'vacation_amount'),
    (('Гүйцэтгэлийн нэмэгдэл',), 'performance_amount'),
    (('Бусад нэмэгдэл СС', 'Бусад нэмэгдэл'), 'other_allowance_amount'),
    (('Нэмэгдлийн дүн',), 'allowance_total'),
    (('Олговол зохих',), 'gross_amount'),
    (('Урьдчилгаа цалин СС', 'Урьдчилгаа цалин'), 'advance_amount'),
    (('НДШ-Даатгуулагчаас', 'НДШ даатгуулагчаас', 'НДШ - Даатгуулагчаас'), 'ndsh_employee_amount'),
    (('НДШ Ажил олгогчоос', 'НДШ ажил олгогчоос', 'НДШ - Ажил олгогчоос'), 'ndsh_company_amount'),
    (('ХАОАТ', 'ХХОАТ'), 'pit_amount'),
    (('Утасны суутгал',), 'phone_deduction_amount'),
    (('Ажилчдаас авлага',), 'receivable_deduction_amount'),
    (('Суутгалын дүн',), 'deduction_total'),
    (('Гарт олгох',), 'net_amount'),
]


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    dep_id = fields.Many2one('hr.department', string='Department')
    # Буцаалтын хуудас багцгүй хуулагддаг тул related биш, хуулагддаг compute
    payslip_type = fields.Selection([('advance', 'Урьдчилгаа цалин'),
                                     ('final', 'Сүүл цалин')],
                                    string='Цалингийн төрөл', compute='_compute_payslip_type',
                                    store=True, readonly=False, copy=True)
    advance_must_hours = fields.Float(string='Ажиллах ёстой цаг', compute='_compute_advance_hours',
                                      store=True, readonly=False, copy=True,
                                      help='Цагийн бүртгэлээс авна. Гараар засаж болно.')
    advance_worked_hours = fields.Float(string='Ажилласан цаг (урьдчилгаа)', compute='_compute_advance_hours',
                                        store=True, readonly=False, copy=True,
                                        help='Цагийн бүртгэлээс авна. Гараар засаж болно.')
    prepayment_amount = fields.Float(string='Урьдчилгаа олгох дүн', compute='_compute_prepayment_amount',
                                     store=True, readonly=False, copy=True,
                                     help='Гэрээний цалин × урьдчилгааны % × ажилласан цаг / ажиллах ёстой цаг. '
                                          'Гараар засаж болно.')

    employee_last_name = fields.Char(string='Овог', compute='_compute_employee_info')
    employee_first_name = fields.Char(string='Нэр', compute='_compute_employee_info')
    employee_department_id = fields.Many2one('hr.department', string='Хэлтэс тасаг', compute='_compute_employee_info')
    employee_bank_account = fields.Char(string='Дансны дугаар', compute='_compute_employee_info')
    employee_register = fields.Char(string='Регистр №', compute='_compute_employee_info')

    wage_amount = fields.Float(string='Үндсэн цалин', compute='_compute_payslip_columns', store=True)
    month_work_days = fields.Float(string='Сарын ажлын хоног')
    month_work_hours = fields.Float(string='Сарын ажлын фонд цаг')
    worked_days = fields.Float(string='Ажилласан хоног')
    worked_hours = fields.Float(string='Ажилласан цаг')
    overtime_hours = fields.Float(string='Илүү цаг')
    overtime_amount = fields.Float(string='Илүү цагийн нэмэгдэл', compute='_compute_payslip_columns', store=True)
    computed_salary = fields.Float(string='Бодогдсон цалин', compute='_compute_payslip_columns', store=True)
    vacation_amount = fields.Float(string='Амралтын мөнгө')
    performance_amount = fields.Float(string='Гүйцэтгэлийн нэмэгдэл')
    other_allowance_amount = fields.Float(string='Бусад нэмэгдэл')
    allowance_total = fields.Float(string='Нэмэгдлийн дүн', compute='_compute_payslip_columns', store=True)
    gross_amount = fields.Float(string='Олговол зохих', compute='_compute_payslip_columns', store=True)
    advance_amount = fields.Float(string='Урьдчилгаа цалин')
    ndsh_employee_amount = fields.Float(string='НДШ-Даатгуулагчаас', compute='_compute_payslip_columns', store=True)
    ndsh_company_amount = fields.Float(string='НДШ Ажил олгогчоос', compute='_compute_payslip_columns', store=True)
    pit_amount = fields.Float(string='ХАОАТ', compute='_compute_payslip_columns', store=True)
    phone_deduction_amount = fields.Float(string='Утасны суутгал')
    receivable_deduction_amount = fields.Float(string='Ажилчдаас авлага')
    deduction_total = fields.Float(string='Суутгалын дүн', compute='_compute_payslip_columns', store=True)
    net_amount = fields.Float(string='Гарт олгох', compute='_compute_payslip_columns', store=True)

    @api.depends('employee_id')
    def _compute_employee_info(self):
        for slip in self:
            emp = slip.employee_id.sudo()
            slip.employee_last_name = emp['last_name'] if 'last_name' in emp._fields else False
            slip.employee_first_name = emp.name
            slip.employee_department_id = emp.department_id
            slip.employee_bank_account = emp.bank_account_id.acc_number
            slip.employee_register = emp['ssnid'] if 'ssnid' in emp._fields else False

    @api.depends('line_ids.code', 'line_ids.total')
    def _compute_payslip_columns(self):
        for slip in self:
            totals = {}
            for line in slip.line_ids:
                totals[line.code] = totals.get(line.code, 0.0) + line.total
            vals = {
                field_name: sum(totals.get(code, 0.0) for code in codes)
                for field_name, codes in PAYSLIP_OUTPUT_COLUMN_CODES.items()
            }
            # Урьдчилгааны хуудсанд BS дүрэм бодогдохгүй тул гэрээний цалинг харуулна
            if slip.contract_id.contract_type_id and slip.contract_id.contract_type_id.code == 'Part-Time':
                vals['wage_amount'] = slip.contract_id.wage * slip.month_work_hours
            if slip.payslip_type == 'advance' and not vals['wage_amount']:
                if slip.contract_id.contract_type_id and slip.contract_id.contract_type_id.code == 'Part-Time':
                    vals['wage_amount'] = slip.contract_id.wage * slip.advance_must_hours
                else:
                    vals['wage_amount'] = slip.contract_id.wage
            slip.update(vals)

    @api.depends('payslip_run_id.payslip_type')
    def _compute_payslip_type(self):
        for slip in self:
            if slip.payslip_run_id:
                slip.payslip_type = slip.payslip_run_id.payslip_type
            elif not slip.payslip_type:
                slip.payslip_type = 'final'

    @api.depends('payslip_type', 'worked_days_line_ids.code', 'worked_days_line_ids.number_of_hours')
    def _compute_advance_hours(self):
        for slip in self:
            if slip.payslip_type != 'advance':
                slip.advance_must_hours = slip.advance_worked_hours = 0.0
            elif slip.state == 'draft':
                hours = {wd.code: wd.number_of_hours for wd in slip.worked_days_line_ids}
                slip.advance_must_hours = hours.get('MUST_WORK', 0.0)
                slip.advance_worked_hours = hours.get('WORK100', 0.0)

    @api.depends('payslip_type', 'contract_id.wage',
                 'advance_must_hours', 'advance_worked_hours')
    def _compute_prepayment_amount(self):
        for slip in self:
            if slip.payslip_type != 'advance':
                slip.prepayment_amount = 0.0
            elif slip.state == 'draft':
                # Батлагдсан хуудасны дүнг гэрээ өөрчлөгдсөн ч хөндөхгүй
                # Ажиллах ёстой цаг 0 бол цагаар хуваахгүй, бүтэн цалингаас бодно
                if slip.contract_id.contract_type_id and slip.contract_id.contract_type_id.code == 'Part-Time':
                    slip.prepayment_amount = slip.company_id.currency_id.round(
                        slip.contract_id.wage * slip.advance_must_hours * 0.4)
                else:
                    ratio = (slip.advance_worked_hours / slip.advance_must_hours
                             if slip.advance_must_hours else 1.0)
                    slip.prepayment_amount = slip.company_id.currency_id.round(
                        slip.contract_id.wage * 40 / 100.0 * ratio)


    def _update_worked_days_record(self, code, field_name, value):
        self.ensure_one()
        wd = self.worked_days_line_ids.filtered(lambda w: w.code == code)
        c_id = self.contract_id.id or (
            self.get_contract(self.employee_id, self.date_from, self.date_to)[:1].id
            if self.date_from and self.date_to else False
        )
        val = value or 0.0
        if wd:
            if round(wd[0][field_name] or 0.0, 2) != round(val, 2):
                wd[0].with_context(skip_sync_payslip=True).write({field_name: val})
        elif val:
            name_map = {
                'MUST_WORK': _('Must work'),
                'WORK100': _('Worked'),
            }
            self.env['hr.payslip.worked_days'].with_context(skip_sync_payslip=True).create({
                'payslip_id': self.id,
                'contract_id': c_id,
                'name': name_map.get(code, code),
                'code': code,
                field_name: val,
                'sequence': 1,
            })

    def _update_input_record(self, code, value, alt_codes=None):
        self.ensure_one()
        all_codes = [code] + (alt_codes or [])
        inps = self.input_line_ids.filtered(lambda i: i.code in all_codes)
        c_id = self.contract_id.id or (
            self.get_contract(self.employee_id, self.date_from, self.date_to)[:1].id
            if self.date_from and self.date_to else False
        )
        val = value or 0.0
        if inps:
            target = inps[0]
            if round(target.amount or 0.0, 2) != round(val, 2):
                target.with_context(skip_sync_payslip=True).write({'amount': val})
            for other in inps[1:]:
                if other.amount:
                    other.with_context(skip_sync_payslip=True).write({'amount': 0.0})
        elif val:
            rule_input = self.env['hr.rule.input'].search([('code', 'in', all_codes)], limit=1)
            name = rule_input.name if rule_input else code
            actual_code = rule_input.code if rule_input else code
            self.env['hr.payslip.input'].with_context(skip_sync_payslip=True).create({
                'payslip_id': self.id,
                'contract_id': c_id,
                'name': name,
                'code': actual_code,
                'amount': val,
            })

    def _sync_inputs_to_columns(self):
        for slip in self:
            wd_days = {wd.code: wd.number_of_days for wd in slip.worked_days_line_ids}
            wd_hours = {wd.code: wd.number_of_hours for wd in slip.worked_days_line_ids}
            inps = {inp.code: inp.amount for inp in slip.input_line_ids}
            vals = {}
            if 'MUST_WORK' in wd_days and not slip.month_work_days:
                vals['month_work_days'] = wd_days['MUST_WORK']
            if 'MUST_WORK' in wd_hours and not slip.month_work_hours:
                vals['month_work_hours'] = wd_hours['MUST_WORK']
            if 'WORK100' in wd_days and not slip.worked_days:
                vals['worked_days'] = wd_days['WORK100']
            if 'WORK100' in wd_hours and not slip.worked_hours:
                vals['worked_hours'] = wd_hours['WORK100']
            if 'OVER' in inps and not slip.overtime_hours:
                vals['overtime_hours'] = inps['OVER']
            if 'RS' in inps and not slip.vacation_amount:
                vals['vacation_amount'] = inps['RS']
            if 'KPI' in inps and not slip.performance_amount:
                vals['performance_amount'] = inps['KPI']
            if 'OTA' in inps and not slip.other_allowance_amount:
                vals['other_allowance_amount'] = inps['OTA']
            if ('PHONE_DEDUCTION' in inps or 'PH' in inps) and not slip.phone_deduction_amount:
                vals['phone_deduction_amount'] = inps.get('PHONE_DEDUCTION', inps.get('PH', 0.0))
            if any(c in inps for c in ('EDE', 'PAY', 'FAULT')) and not slip.receivable_deduction_amount:
                vals['receivable_deduction_amount'] = sum(inps.get(c, 0.0) for c in ('EDE', 'PAY', 'FAULT'))
            if 'ADV' in inps and not slip.advance_amount:
                vals['advance_amount'] = inps['ADV']
            if vals:
                super(HrPayslip, slip).write(vals)

    def write(self, vals):
        res = super(HrPayslip, self).write(vals)
        # Урьдчилгааны хувь, дүнг гараар зассан бол мөрийг шууд шинэчилнэ
        if not self.env.context.get('skip_compute_advance') and {'prepayment_amount', 'advance_must_hours', 'advance_worked_hours'} & set(vals):
            self.filtered(lambda s: s.payslip_type == 'advance' and s.state == 'draft')._compute_advance_sheet()

        # Input/worked_days sync
        input_or_wd_fields = {
            'month_work_days', 'month_work_hours', 'worked_days', 'worked_hours',
            'overtime_hours', 'vacation_amount', 'performance_amount',
            'other_allowance_amount', 'phone_deduction_amount',
            'receivable_deduction_amount', 'advance_amount'
        }
        if not self.env.context.get('skip_sync_inputs') and (input_or_wd_fields & set(vals)):
            for slip in self:
                if 'month_work_days' in vals:
                    slip._update_worked_days_record('MUST_WORK', 'number_of_days', vals['month_work_days'])
                    slip._update_input_record('MWD', vals['month_work_days'])
                if 'month_work_hours' in vals:
                    slip._update_worked_days_record('MUST_WORK', 'number_of_hours', vals['month_work_hours'])
                    slip._update_input_record('MWT', vals['month_work_hours'])
                if 'worked_days' in vals:
                    slip._update_worked_days_record('WORK100', 'number_of_days', vals['worked_days'])
                    slip._update_input_record('WDD', vals['worked_days'])
                if 'worked_hours' in vals:
                    slip._update_worked_days_record('WORK100', 'number_of_hours', vals['worked_hours'])
                    slip._update_input_record('WDT', vals['worked_hours'])
                if 'overtime_hours' in vals:
                    slip._update_input_record('OVER', vals['overtime_hours'])
                if 'vacation_amount' in vals:
                    slip._update_input_record('RS', vals['vacation_amount'])
                if 'performance_amount' in vals:
                    slip._update_input_record('KPI', vals['performance_amount'])
                if 'other_allowance_amount' in vals:
                    slip._update_input_record('OTA', vals['other_allowance_amount'])
                if 'phone_deduction_amount' in vals:
                    slip._update_input_record('PHONE_DEDUCTION', vals['phone_deduction_amount'], alt_codes=['PH'])
                if 'receivable_deduction_amount' in vals:
                    slip._update_input_record('EDE', vals['receivable_deduction_amount'], alt_codes=['PAY', 'FAULT'])
                if 'advance_amount' in vals:
                    if not slip.payslip_run_id.advance_run_id:
                        slip._update_input_record('ADV', vals['advance_amount'])

        if not self.env.context.get('skip_recompute_sheet') and (input_or_wd_fields & set(vals)):
            draft_slips = self.filtered(lambda s: s.payslip_type != 'advance' and s.state == 'draft')
            if draft_slips:
                draft_slips.with_context(skip_sync_payslip=True, skip_recompute_sheet=True).compute_sheet()
        return res

    def compute_sheet(self):
        advance_slips = self.filtered(lambda s: s.payslip_type == 'advance')
        final_slips = self - advance_slips
        final_slips._apply_advance_inputs()
        final_slips._sync_inputs_to_columns()
        res = super(HrPayslip, final_slips).compute_sheet()
        advance_slips._compute_advance_sheet()
        return res

    def _compute_advance_sheet(self):
        """Урьдчилгаа цалингийн хуудас: цалингийн дүрмүүдийг бодохгүй, зөвхөн ADVP мөр үүсгэнэ."""
        for slip in self:
            rule = slip._get_advance_rule()
            contract = slip.contract_id or self.env['hr.contract'].browse(
                self.get_contract(slip.employee_id, slip.date_from, slip.date_to)[:1])
            if not contract:
                raise ValidationError(_("No running contract found for the employee: %s or no contract in the given period") % slip.employee_id.name)
            slip.line_ids.unlink()
            line_vals = {
                'salary_rule_id': rule.id,
                'contract_id': contract.id,
                'employee_id': slip.employee_id.id,
                'name': rule.name,
                'code': rule.code,
                'category_id': rule.category_id.id,
                'sequence': rule.sequence,
                'appears_on_payslip': rule.appears_on_payslip,
                'condition_select': 'none',
                'amount_select': 'fix',
                'register_id': rule.register_id.id,
                'amount': slip.prepayment_amount,
                'quantity': 1.0,
                'rate': 100.0,
            }
            slip_vals = {
                'number': slip.number or self.env['ir.sequence'].next_by_code('salary.slip'),
                'line_ids': [(0, 0, line_vals)],
            }
            # contract_id-г дахин бичвэл гараар зассан prepayment_amount дахин бодогдоно
            if not slip.contract_id:
                slip_vals['contract_id'] = contract.id
            super(HrPayslip, slip).write(slip_vals)

    def _get_advance_rule(self):
        """Хуудасны компанийн ADVP дүрэм. Компани бүр өөрийн данстай ADVP дүрэмтэй байж болно."""
        self.ensure_one()
        company = self.company_id or self.env.company
        rules = self.env['hr.salary.rule'].search([
            ('code', '=', 'ADVP'), ('company_id', 'in', [company.id, False])])
        rule = rules.filtered(lambda r: r.company_id == company)[:1] or rules[:1] \
            or self.env.ref('l10n_mn_payroll.adv_salary_rule')
        accounts = rule.sudo().account_debit | rule.sudo().account_credit
        wrong = accounts.filtered(lambda a: a.company_id not in company.parent_ids)
        if wrong:
            raise UserError(_('"%(rule)s" (ADVP) цалингийн дүрмийн данс %(accounts)s нь %(company)s компанийнх биш байна. '
                              'Цалингийн дүрэм дээр тухайн компанийн дансыг тохируулна уу.',
                              rule=rule.name, accounts=', '.join(wrong.mapped('code')), company=company.name))
        return rule

    def _apply_advance_inputs(self):
        """Багц дээр сонгосон урьдчилгааны багцаас ажилтны урьдчилгааг ADV оролтод татна."""
        for slip in self:
            advance_run = slip.payslip_run_id.advance_run_id
            if not advance_run:
                continue
            advance_slips = advance_run.slip_ids.filtered(
                lambda s: s.employee_id == slip.employee_id and s.state == 'done')
            amount = sum(s.net_amount * (-1 if s.credit_note else 1) for s in advance_slips)
            adv_input = slip.input_line_ids.filtered(lambda i: i.code == 'ADV')
            if adv_input:
                adv_input[0].amount = amount
                (adv_input - adv_input[0]).unlink()
            elif slip.contract_id:
                self.env['hr.payslip.input'].create({
                    'payslip_id': slip.id,
                    'name': _('Урьдчилгаа'),
                    'code': 'ADV',
                    'amount': amount,
                    'contract_id': slip.contract_id.id,
                })

    def refund_sheet(self):
        for payslip in self:
            if  payslip.credit_note == True:
                raise UserError(_(u'Буцаалт хийгдсэн тул дахин буцаалт хийхгүй.'))
            copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name})
            copied_payslip.compute_sheet()
            copied_payslip.action_payslip_done()
        formview_ref = self.env.ref('hr_payroll_community.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('hr_payroll_community.view_hr_payslip_tree', False)
        
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = super(HrPayslip, self).get_worked_day_lines(contracts, date_from, date_to)
        res = [line for line in res if line.get('code') != 'WORK100']
        employee_id = self.employee_id or contracts.employee_id
        if employee_id or contracts:
            start_date = date_from or self.date_from
            end_date = date_to or self.date_to
            hr_hour_record = self.env['hr.hour.record'].new({
                'start_date': datetime.combine(start_date, time(0, 1)) - timedelta(hours=8),
                'end_date': datetime.combine(end_date, time(23, 59)) - timedelta(hours=8),
                'company_id': self.employee_id.company_id.id
            })
            line_vals = hr_hour_record.hour_record(employee_id=employee_id)
            work_day = 0
            work_hour = 0
            worked_day = 0
            worked_hour = 0
            if 'due_day' in line_vals.keys() and 'work_day' in line_vals.keys():
                work_day = line_vals['due_day']
                work_hour = round(line_vals['due_time'], 2)
                worked_day = line_vals['work_day']
                worked_hour = round(line_vals['work_time'] + line_vals['free_time1'], 2)
            must_work = {
                'name': _("Must work"),
                'sequence': 1,
                'code': 'MUST_WORK',
                'number_of_days': work_day,
                'number_of_hours': work_hour,
                'contract_id': contracts.id
            }
            worked = {
                'name': _("Worked"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': worked_day,
                'number_of_hours': worked_hour,
                'contract_id': contracts.id
            }

            res.append(must_work)
            res.append(worked)
        return res

    @api.model
    def _get_payslip_lines(
        self,
        contract_ids,
        payslip_id,
        from_sequence=None,
    ):

        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(
                    localdict,
                    category.parent_id,
                    amount
                )

            localdict['categories'].dict[category.code] = (
                localdict['categories'].dict[category.code] + amount
                if category.code in localdict['categories'].dict
                else amount
            )

            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, data, env):
                self.employee_id = employee_id
                self.dict = data
                self.env = env

            def __getattr__(self, attr):
                return (
                    self.dict[attr]
                    if attr in self.dict
                    else 0.0
                )

        class DummyInput:
            amount = 0.0
            def __getattr__(self, _):
                return 0.0
            def __float__(self):
                return 0.0
            def __bool__(self):
                return False

        class DummyWorkedDay:
            number_of_days = 0.0
            number_of_hours = 0.0
            def __getattr__(self, _):
                return 0.0
            def __float__(self):
                return 0.0
            def __bool__(self):
                return False

        class InputLine(BrowsableObject):

            def __getattr__(self, attr):
                if attr in self.dict:
                    return self.dict[attr]
                return DummyInput()

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()

                self.env.cr.execute("""
                    SELECT sum(amount)
                    FROM hr_payslip hp
                    JOIN hr_payslip_input pi
                        ON hp.id = pi.payslip_id
                    WHERE hp.employee_id = %s
                      AND hp.state = 'done'
                      AND hp.date_from >= %s
                      AND hp.date_to <= %s
                      AND pi.code = %s
                """, (
                    self.employee_id,
                    from_date,
                    to_date,
                    code,
                ))

                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):

            def __getattr__(self, attr):
                if attr in self.dict:
                    return self.dict[attr]
                return DummyWorkedDay()

            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()

                self.env.cr.execute("""
                    SELECT
                        sum(number_of_days),
                        sum(number_of_hours)
                    FROM hr_payslip hp
                    JOIN hr_payslip_worked_days pi
                        ON hp.id = pi.payslip_id
                    WHERE hp.employee_id = %s
                      AND hp.state = 'done'
                      AND hp.date_from >= %s
                      AND hp.date_to <= %s
                      AND pi.code = %s
                """, (
                    self.employee_id,
                    from_date,
                    to_date,
                    code,
                ))

                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()

                self.env.cr.execute("""
                    SELECT sum(
                        CASE
                            WHEN hp.credit_note = FALSE
                            THEN pl.total
                            ELSE -pl.total
                        END
                    )
                    FROM hr_payslip hp
                    JOIN hr_payslip_line pl
                        ON hp.id = pl.slip_id
                    WHERE hp.employee_id = %s
                      AND hp.state = 'done'
                      AND hp.date_from >= %s
                      AND hp.date_to <= %s
                      AND pl.code = %s
                """, (
                    self.employee_id,
                    from_date,
                    to_date,
                    code,
                ))

                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []

        payslip = self.env['hr.payslip'].browse(payslip_id)

        # ---------------------------------------------------------
        # Worked days
        # ---------------------------------------------------------

        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line

        # ---------------------------------------------------------
        # Inputs
        # ---------------------------------------------------------

        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        # ---------------------------------------------------------
        # Browsable objects
        # ---------------------------------------------------------

        categories = BrowsableObject(
            payslip.employee_id.id,
            {},
            self.env
        )

        inputs = InputLine(
            payslip.employee_id.id,
            inputs_dict,
            self.env
        )

        worked_days = WorkedDays(
            payslip.employee_id.id,
            worked_days_dict,
            self.env
        )

        payslips = Payslips(
            payslip.employee_id.id,
            {},
            self.env
        )

        rules = BrowsableObject(
            payslip.employee_id.id,
            rules_dict,
            self.env
        )

        baselocaldict = {
            'categories': categories,
            'rules': rules,
            'payslip': payslips,
            'worked_days': worked_days,
            'inputs': inputs,
        }

        # ---------------------------------------------------------
        # Contracts
        # ---------------------------------------------------------

        contracts = self.env['hr.contract'].browse(contract_ids)

        if not contracts:
            return []

        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(
                set(
                    payslip.struct_id
                    ._get_parent_structure()
                    .ids
                )
            )
        else:
            structure_ids = contracts.get_all_structures()

        # ---------------------------------------------------------
        # Salary rules
        # ---------------------------------------------------------

        rule_ids = (
            self.env['hr.payroll.structure']
            .browse(structure_ids)
            .get_all_rules()
        )

        sorted_rule_ids = [
            rule_id
            for rule_id, sequence in sorted(
                rule_ids,
                key=lambda x: x[1]
            )
        ]

        sorted_rules = self.env['hr.salary.rule'].browse(
            sorted_rule_ids
        )

        # ---------------------------------------------------------
        # Process contracts
        # ---------------------------------------------------------

        for contract in contracts:

            employee = contract.employee_id

            localdict = dict(
                baselocaldict,
                employee=employee,
                contract=contract,
            )

            # Existing lines for this contract
            existing_lines = payslip.line_ids.filtered(
                lambda line:
                    line.contract_id.id == contract.id
            )

            # -----------------------------------------------------
            # Run rules by sequence
            # -----------------------------------------------------

            for rule in sorted_rules:

                key = f'{rule.code}-{contract.id}'

                # =================================================
                # IMPORTANT:
                #
                # If from_sequence is provided and this rule is
                # before/equal to changed line sequence:
                #
                # DO NOT calculate it again.
                #
                # Instead use existing line values to rebuild:
                #   - localdict[rule.code]
                #   - rules
                #   - categories
                #   - result_dict
                # =================================================

                if (
                    from_sequence is not None
                    and rule.sequence <= from_sequence
                ):
                    existing_line = existing_lines.filtered(
                        lambda line:
                            line.salary_rule_id.id == rule.id
                    )[:1]

                    if existing_line:

                        total = existing_line.total

                        # This is what later Python rules use:
                        #
                        # BASIC
                        # GROSS
                        # NET
                        # etc.
                        localdict[rule.code] = total

                        # rules.BASIC / rules.GROSS ...
                        rules_dict[rule.code] = rule

                        # Categories must also be reconstructed.
                        localdict = _sum_salary_rule_category(
                            localdict,
                            rule.category_id,
                            total
                        )

                        # Keep existing line in result
                        result_dict[key] = {
                            'salary_rule_id': rule.id,
                            'contract_id': contract.id,
                            'name': rule.name,
                            'code': rule.code,
                            'category_id': rule.category_id.id,
                            'sequence': rule.sequence,
                            'appears_on_payslip':
                                rule.appears_on_payslip,
                            'condition_select':
                                rule.condition_select,
                            'condition_python':
                                rule.condition_python,
                            'condition_range':
                                rule.condition_range,
                            'condition_range_min':
                                rule.condition_range_min,
                            'condition_range_max':
                                rule.condition_range_max,
                            'amount_select':
                                rule.amount_select,
                            'amount_fix':
                                rule.amount_fix,
                            'amount_python_compute':
                                rule.amount_python_compute,
                            'amount_percentage':
                                rule.amount_percentage,
                            'amount_percentage_base':
                                rule.amount_percentage_base,
                            'register_id':
                                rule.register_id.id,
                            'amount':
                                existing_line.amount,
                            'employee_id':
                                contract.employee_id.id,
                            'quantity':
                                existing_line.quantity,
                            'rate':
                                existing_line.rate,
                        }

                    # IMPORTANT:
                    # Do not calculate this rule again.
                    continue

                # =================================================
                # From here:
                # rule.sequence > from_sequence
                #
                # These rules WILL be recalculated.
                # =================================================

                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100

                # -------------------------------------------------
                # Condition
                # -------------------------------------------------

                if rule._satisfy_condition(
                    localdict
                ) and rule.id not in blacklist:

                    # -------------------------------------------------
                    # Calculate rule
                    # -------------------------------------------------

                    amount, qty, rate = rule._compute_rule(
                        localdict
                    )

                    previous_amount = (
                        localdict.get(rule.code, 0.0)
                    )

                    total = (
                        contract.company_id.currency_id.round(
                            amount * qty * rate / 100.0
                        )
                    )

                    # -------------------------------------------------
                    # Update localdict
                    # -------------------------------------------------

                    localdict[rule.code] = total

                    rules_dict[rule.code] = rule

                    # -------------------------------------------------
                    # Update categories
                    # -------------------------------------------------

                    localdict = _sum_salary_rule_category(
                        localdict,
                        rule.category_id,
                        total - previous_amount
                    )

                    # -------------------------------------------------
                    # Save recalculated result
                    # -------------------------------------------------

                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip':
                            rule.appears_on_payslip,
                        'condition_select':
                            rule.condition_select,
                        'condition_python':
                            rule.condition_python,
                        'condition_range':
                            rule.condition_range,
                        'condition_range_min':
                            rule.condition_range_min,
                        'condition_range_max':
                            rule.condition_range_max,
                        'amount_select':
                            rule.amount_select,
                        'amount_fix':
                            rule.amount_fix,
                        'amount_python_compute':
                            rule.amount_python_compute,
                        'amount_percentage':
                            rule.amount_percentage,
                        'amount_percentage_base':
                            rule.amount_percentage_base,
                        'register_id':
                            rule.register_id.id,
                        'amount': amount,
                        'employee_id':
                            contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }

                else:

                    # -------------------------------------------------
                    # Condition false:
                    # blacklist rule and its children
                    # -------------------------------------------------

                    blacklist += [
                        rule_id
                        for rule_id, seq
                        in rule._recursive_search_of_rules()
                    ]

            # end rule loop

        # end contract loop

        return list(result_dict.values())


class HrPayslipRunImportWizard(models.TransientModel):
    _name = 'hr.payslip.run.import.wizard'
    _description = 'Hr Payslip Run Import Wizard'

    run_id = fields.Many2one('hr.payslip.run', string='Цалингийн багц', required=True)
    data_file = fields.Binary(string='Excel файл', required=True)
    filename = fields.Char(string='Файлын нэр')

    def action_import(self):
        self.ensure_one()
        if not self.data_file:
            raise UserError(_('Excel файлаа сонгоно уу!'))

        file_data = base64.b64decode(self.data_file)
        try:
            wb = openpyxl.load_workbook(filename=io.BytesIO(file_data), data_only=True)
        except Exception as e:
            raise UserError(_('Excel файл уншихад алдаа гарлаа: %s') % str(e))

        sheet = wb.active

        # 1. Баганын нэрсийг олох (Мөр 4 болон 5 дээрх толгой баганууд)
        header_map = {}
        for r in range(4, 6):
            rows = list(sheet.iter_rows(min_row=r, max_row=r, values_only=True))
            if not rows:
                continue
            row_cells = rows[0]
            for col_idx, cell in enumerate(row_cells):
                if cell is not None and str(cell).strip():
                    raw_name = str(cell).strip()
                    clean_name = ' '.join(raw_name.split())
                    for n in (raw_name, clean_name):
                        if n not in header_map:
                            header_map[n] = col_idx

        updated_count = 0
        run = self.run_id

        def get_val(row_vals, header_names, default=None):
            if isinstance(header_names, str):
                header_names = (header_names,)
            for h in header_names:
                idx = header_map.get(h)
                if idx is None:
                    idx = header_map.get(' '.join(h.split()))
                if idx is not None and idx < len(row_vals):
                    val = row_vals[idx]
                    if val is not None and str(val).strip() != '':
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            clean_str = str(val).strip()
                            if clean_str in ('-', '—', '–'):
                                return 0.0
                            try:
                                clean_val = clean_str.replace(',', '').replace(' ', '').replace("'", '').strip()
                                if clean_val in ('-', '—', '–'):
                                    return 0.0
                                return float(clean_val)
                            except (ValueError, TypeError):
                                return default
            return default

        for row in sheet.iter_rows(min_row=6, values_only=True):
            if not any(row):
                continue
            first_val = str(row[0]).strip() if row[0] is not None else ''
            if 'Нийт' in first_val or 'Нийт дүн' in first_val or any(c is not None and 'Нийт дүн' in str(c) for c in row[:5]):
                break

            # Ажилтны цалингийн хуудсыг олох:
            # 1-рт: Нуусан ID баганаар
            slip = False
            id_idx = header_map.get('ID')
            if id_idx is not None and id_idx < len(row) and row[id_idx]:
                try:
                    s_id = int(float(str(row[id_idx]).strip()))
                    slip = run.slip_ids.filtered(lambda s: s.id == s_id)
                except (ValueError, TypeError):
                    pass

            # 2-рт: Регистр / Регистр № баганаар
            if not slip:
                reg_idx = header_map.get('Регистр')
                if reg_idx is None:
                    reg_idx = header_map.get('Регистр №')
                if reg_idx is None:
                    reg_idx = header_map.get('Регистрийн дугаар')
                if reg_idx is not None and reg_idx < len(row) and row[reg_idx]:
                    val = row[reg_idx]
                    if isinstance(val, float) and val.is_integer():
                        reg = str(int(val)).strip().upper()
                    else:
                        reg = str(val).strip().upper()
                    slip = run.slip_ids.filtered(
                        lambda s: (s.employee_id.ssnid and s.employee_id.ssnid.strip().upper() == reg) or
                                  (s.employee_id.identification_id and s.employee_id.identification_id.strip().upper() == reg)
                    )

            # 3-рт: Нэр баганаар (давхардсан бол Овог баганаар нягтлах)
            if not slip:
                name_idx = header_map.get('Нэр')
                if name_idx is not None and name_idx < len(row) and row[name_idx]:
                    emp_name = str(row[name_idx]).strip()
                    matched_slips = run.slip_ids.filtered(lambda s: s.employee_id.name and s.employee_id.name.strip() == emp_name)
                    if len(matched_slips) > 1:
                        last_name_idx = header_map.get('Овог')
                        if last_name_idx is not None and last_name_idx < len(row) and row[last_name_idx]:
                            ln = str(row[last_name_idx]).strip()
                            refined = matched_slips.filtered(lambda s: s.employee_id.last_name and s.employee_id.last_name.strip() == ln)
                            if refined:
                                matched_slips = refined
                    slip = matched_slips

            if not slip:
                continue

            slip = slip[0]
            is_advance = (run.payslip_type == 'advance') or (slip.payslip_type == 'advance')

            # Гэрээг олох
            contract = slip.contract_id or slip.employee_id.contract_id
            if not contract and hasattr(slip, 'get_contract'):
                contract_ids = slip.get_contract(slip.employee_id, slip.date_from, slip.date_to)
                if contract_ids:
                    contract = self.env['hr.contract'].browse(contract_ids[0])
            if not contract:
                contract = self.env['hr.contract'].sudo().search([
                    ('employee_id', '=', slip.employee_id.id),
                    ('company_id', '=', slip.company_id.id),
                    ('state', 'in', ('open', 'close', 'draft')),
                ], order='state asc, date_start desc, id desc', limit=1)
            if not contract:
                contract = self.env['hr.contract'].sudo().search([
                    ('employee_id', '=', slip.employee_id.id),
                ], order='state asc, date_start desc, id desc', limit=1)

            if contract and not slip.contract_id:
                slip.contract_id = contract

            c_id = (contract.id if contract else False) or (slip.contract_id.id if slip.contract_id else False)

            # -------------------------------------------------------------
            # Урьдчилгаа цалингийн импорт:
            # "Урьдчилгаа цалин СС" баганад орж ирсэн утгыг ADVP кодтой hr.payslip.line-д оруулна
            # -------------------------------------------------------------
            if is_advance:
                adv_amt = get_val(row, ('Урьдчилгаа цалин СС', 'Урьдчилгаа цалин', 'Гарт олгох'), default=None)
                if adv_amt is not None:
                    slip.with_context(skip_compute_advance=True).write({'prepayment_amount': adv_amt})
                    advp_lines = slip.line_ids.filtered(lambda l: l.code == 'ADVP')
                    if advp_lines:
                        advp_lines[0].with_context(skip_recompute_following=True).write({
                            'amount': adv_amt,
                            'total': adv_amt,
                            'quantity': 1.0,
                            'rate': 100.0,
                        })
                        if len(advp_lines) > 1:
                            advp_lines[1:].unlink()
                    else:
                        rule = False
                        if hasattr(slip, '_get_advance_rule'):
                            try:
                                rule = slip._get_advance_rule()
                            except Exception:
                                pass
                        if not rule:
                            rule = self.env['hr.salary.rule'].search([
                                ('code', '=', 'ADVP'),
                                '|', ('company_id', '=', slip.company_id.id), ('company_id', '=', False)
                            ], limit=1)
                        if rule:
                            if not c_id:
                                raise UserError(_("'%s' ажилтанд хөдөлмөрийн гэрээ бүртгэгдээгүй байна! Цалин тооцохын тулд гэрээг бүртгэнэ үү.") % slip.employee_id.name)
                            self.env['hr.payslip.line'].with_context(skip_recompute_following=True).create({
                                'slip_id': slip.id,
                                'salary_rule_id': rule.id,
                                'contract_id': c_id,
                                'employee_id': slip.employee_id.id,
                                'name': rule.name,
                                'code': rule.code,
                                'category_id': rule.category_id.id if rule.category_id else False,
                                'sequence': rule.sequence or 100,
                                'appears_on_payslip': rule.appears_on_payslip,
                                'condition_select': 'none',
                                'amount_select': 'fix',
                                'register_id': rule.register_id.id if rule.register_id else False,
                                'amount': adv_amt,
                                'quantity': 1.0,
                                'rate': 100.0,
                                'total': adv_amt,
                            })
                    for inp_code in ('ADV', 'ADVP'):
                        inps = slip.input_line_ids.filtered(lambda i: i.code == inp_code)
                        if inps:
                            inps.write({'amount': adv_amt})
                slip._compute_payslip_columns()
                updated_count += 1
                continue

            # -------------------------------------------------------------
            # Сүүл цалин:
            # A. hr.payslip.worked_days шинэчлэх
            # -------------------------------------------------------------
            if not c_id:
                raise UserError(_("'%s' ажилтанд хөдөлмөрийн гэрээ бүртгэгдээгүй байна! Цалин тооцохын тулд гэрээг бүртгэнэ үү.") % slip.employee_id.name)

            must_work = slip.worked_days_line_ids.filtered(lambda w: w.code == 'MUST_WORK')
            old_mwd = must_work[0].number_of_days if must_work else (slip.month_work_days or 0.0)
            old_mwt = must_work[0].number_of_hours if must_work else (slip.month_work_hours or 0.0)

            work100 = slip.worked_days_line_ids.filtered(lambda w: w.code == 'WORK100')
            old_wdd = work100[0].number_of_days if work100 else (slip.worked_days or 0.0)
            old_wdt = work100[0].number_of_hours if work100 else (slip.worked_hours or 0.0)

            mwd = get_val(row, ('Сарын ажлын хоног',), default=old_mwd)
            mwt = get_val(row, ('Сарын ажлын фонд цаг', 'Сарын ажлын цаг'), default=old_mwt)
            wdd = get_val(row, ('Ажилласан хоног СС', 'Ажилласан хоног'), default=old_wdd)
            wdt = get_val(row, ('Ажилласан цаг СС', 'Ажилласан цаг'), default=old_wdt)

            if must_work:
                must_work.write({'number_of_days': mwd, 'number_of_hours': mwt})
            elif mwd or mwt:
                must_work = self.env['hr.payslip.worked_days'].create({
                    'payslip_id': slip.id,
                    'contract_id': c_id,
                    'name': _('Must work'),
                    'code': 'MUST_WORK',
                    'number_of_days': mwd,
                    'number_of_hours': mwt,
                    'sequence': 1,
                })

            if work100:
                work100.write({'number_of_days': wdd, 'number_of_hours': wdt})
            elif wdd or wdt:
                work100 = self.env['hr.payslip.worked_days'].create({
                    'payslip_id': slip.id,
                    'contract_id': c_id,
                    'name': _('Worked'),
                    'code': 'WORK100',
                    'number_of_days': wdd,
                    'number_of_hours': wdt,
                    'sequence': 1,
                })

            wd_changed = (
                round(mwd, 2) != round(old_mwd, 2) or
                round(mwt, 2) != round(old_mwt, 2) or
                round(wdd, 2) != round(old_wdd, 2) or
                round(wdt, 2) != round(old_wdt, 2)
            )

            # -------------------------------------------------------------
            # B. hr.payslip.line болон input шинэчлэх
            # -------------------------------------------------------------
            def update_input(code, val):
                if not code:
                    return
                # Шууд кодоор slip.input_line_ids-аас хайх
                inps = slip.input_line_ids.filtered(lambda i: i.code == code)
                # Тухайн дүрмийн input_ids-ээс мөн хайх
                rule = self.env['hr.salary.rule'].search([
                    ('code', '=', code),
                    '|', ('company_id', '=', slip.company_id.id), ('company_id', '=', False)
                ], limit=1)
                if rule and rule.input_ids:
                    target_codes = [inp_def.code for inp_def in rule.input_ids]
                    rule_inps = slip.input_line_ids.filtered(lambda i: i.code in target_codes)
                    inps = inps | rule_inps
                    if not inps and val:
                        self.env['hr.payslip.input'].create({
                            'payslip_id': slip.id,
                            'contract_id': c_id,
                            'name': rule.input_ids[0].name or code,
                            'code': rule.input_ids[0].code or code,
                            'amount': val,
                        })
                        return

                if inps:
                    inps.write({'amount': val})

            def update_line(codes, val):
                if not codes:
                    return None
                line = False
                for c in codes:
                    matched = slip.line_ids.filtered(lambda l: l.code == c)
                    if matched:
                        line = matched[0]
                        break
                if line:
                    line.with_context(skip_recompute_following=True).write({
                        'amount': val,
                        'quantity': 1.0,
                        'rate': 100.0,
                        'total': val,
                    })
                    return line
                elif val:
                    # Хоногийн дүрэм (MWD, WDD)-ийг slip.line_ids дээр шинээр үүсгэхгүй
                    if any(c in ('MWD', 'WDD') for c in codes):
                        return None

                    # Ажилтны бүтцэд байгаа дүрмийг эхлээд хайх
                    rule = False
                    if slip.struct_id:
                        for c in codes:
                            r = slip.struct_id.rule_ids.filtered(lambda x: x.code == c)
                            if r:
                                rule = r[0]
                                break
                    if not rule:
                        primary_code = codes[0]
                        if slip.payslip_type == 'advance' and 'ADVP' in codes:
                            primary_code = 'ADVP'
                        rule = self.env['hr.salary.rule'].search([
                            ('code', '=', primary_code),
                            '|', ('company_id', '=', slip.company_id.id), ('company_id', '=', False)
                        ], limit=1)
                    if rule:
                        new_line = self.env['hr.payslip.line'].with_context(skip_recompute_following=True).create({
                            'slip_id': slip.id,
                            'salary_rule_id': rule.id,
                            'contract_id': c_id,
                            'employee_id': slip.employee_id.id,
                            'name': rule.name,
                            'code': rule.code,
                            'category_id': rule.category_id.id,
                            'sequence': rule.sequence,
                            'appears_on_payslip': rule.appears_on_payslip,
                            'amount': val,
                            'quantity': 1.0,
                            'rate': 100.0,
                            'total': val,
                        })
                        return new_line
                return None

            # Сүүл цалингийн дүрмийн мөрүүдийг шинэчлэх
            changed_lines = []

            # Ажилласан цаг, өдөр (worked_days) өөрчлөгдсөн бол харгалзах дүрмийн мөрүүдийг шинэчлэх
            if wd_changed:
                for wd_code, wd_val in [('MWT', mwt), ('WDT', wdt), ('MWD', mwd), ('WDD', wdd)]:
                    w_lines = slip.line_ids.filtered(lambda l: l.code == wd_code)
                    if w_lines:
                        if round(wd_val, 2) != round(w_lines[0].amount, 2):
                            mod_line = update_line((wd_code,), wd_val)
                            if mod_line and mod_line not in changed_lines:
                                changed_lines.append(mod_line)
                            update_input(wd_code, wd_val)
                    elif wd_val and wd_code in ('MWT', 'WDT'):
                        if slip.struct_id and slip.struct_id.rule_ids.filtered(lambda r: r.code == wd_code):
                            new_line = update_line((wd_code,), wd_val)
                            if new_line and new_line not in changed_lines:
                                changed_lines.append(new_line)
                            update_input(wd_code, wd_val)

            # Excel тайлангийн багануудаар шалгаж зөвхөн өөрчлөгдсөн утгуудыг бичих
            for header_names, col_key in PAYSLIP_HEADER_TO_COLUMN_KEY:
                if col_key in ('month_work_days', 'month_work_hours', 'worked_days', 'worked_hours'):
                    continue

                # Хэрэв багц дээр урьдчилгаа цалингийн багц (advance_run_id) сонгогдсон бол урьдчилгаа цалинг Excel-ээс өөрчлөхгүй
                if col_key == 'advance_amount' and run.advance_run_id:
                    continue

                codes = PAYSLIP_COLUMN_CODES.get(col_key, ())
                if not codes:
                    continue
                val = get_val(row, header_names, default=None)
                if val is None:
                    continue

                existing_lines = slip.line_ids.filtered(lambda l: l.code in codes)
                if existing_lines:
                    cur_amt = sum(l.amount for l in existing_lines)
                    if round(val, 2) != round(cur_amt, 2):
                        target_line = update_line(codes, val)
                        if target_line and target_line not in changed_lines:
                            changed_lines.append(target_line)
                        if target_line:
                            update_input(target_line.code, val)
                            # Олон кодтой багана (жишээ нь EDE, PAY, FAULT) байвал сонгогдоогүй бусад мөр/input-ийг 0 болгох
                            for c in codes:
                                if c != target_line.code:
                                    other_lines = slip.line_ids.filtered(lambda l: l.code == c)
                                    if other_lines and round(other_lines[0].amount, 2) != 0.0:
                                        update_line((c,), 0.0)
                                        update_input(c, 0.0)
                elif val:
                    target_line = update_line(codes, val)
                    if target_line and target_line not in changed_lines:
                        changed_lines.append(target_line)
                    if target_line:
                        update_input(target_line.code, val)

            # Хэрэв мөр өөрчлөгдсөн бол хамгийн бага sequence-тэй мөрнөөс эхлэн дараах дүрмүүдийг дахин бодох
            if changed_lines:
                min_seq = min(l.sequence for l in changed_lines)
                trigger_line = slip.line_ids.filtered(lambda l: l.sequence == min_seq)[:1]
                if trigger_line:
                    if not trigger_line.contract_id and contract:
                        trigger_line.contract_id = contract
                    trigger_line.action_recompute_following_lines()

            # Дүнгийн багануудыг дахин тооцоолох
            slip._compute_payslip_columns()
            updated_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Амжилттай'),
                'message': _('Нийт %s ажилтны цагийн болон цалингийн мэдээлэл амжилттай импортлогдлоо.') % updated_count,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('skip_sync_payslip'):
            for wd in self:
                if wd.payslip_id and wd.payslip_id.state == 'draft':
                    slip = wd.payslip_id
                    sync_vals = {}
                    if wd.code == 'MUST_WORK':
                        if 'number_of_days' in vals:
                            sync_vals['month_work_days'] = wd.number_of_days
                            slip._update_input_record('MWD', wd.number_of_days)
                        if 'number_of_hours' in vals:
                            sync_vals['month_work_hours'] = wd.number_of_hours
                            slip._update_input_record('MWT', wd.number_of_hours)
                    elif wd.code == 'WORK100':
                        if 'number_of_days' in vals:
                            sync_vals['worked_days'] = wd.number_of_days
                            slip._update_input_record('WDD', wd.number_of_days)
                        if 'number_of_hours' in vals:
                            sync_vals['worked_hours'] = wd.number_of_hours
                            slip._update_input_record('WDT', wd.number_of_hours)
                    if sync_vals:
                        slip.with_context(skip_sync_inputs=True, skip_sync_payslip=True, skip_recompute_sheet=True).write(sync_vals)
                    slip.with_context(skip_sync_payslip=True, skip_recompute_sheet=True).compute_sheet()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_sync_payslip'):
            for wd in records:
                if wd.payslip_id and wd.payslip_id.state == 'draft':
                    wd.write({})
        return records


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('skip_sync_payslip'):
            for inp in self:
                if inp.payslip_id and inp.payslip_id.state == 'draft':
                    slip = inp.payslip_id
                    sync_vals = {}
                    if inp.code == 'OVER':
                        sync_vals['overtime_hours'] = inp.amount
                    elif inp.code == 'RS':
                        sync_vals['vacation_amount'] = inp.amount
                    elif inp.code == 'KPI':
                        sync_vals['performance_amount'] = inp.amount
                    elif inp.code == 'OTA':
                        sync_vals['other_allowance_amount'] = inp.amount
                    elif inp.code in ('PHONE_DEDUCTION', 'PH'):
                        sync_vals['phone_deduction_amount'] = inp.amount
                    elif inp.code in ('EDE', 'PAY', 'FAULT'):
                        sync_vals['receivable_deduction_amount'] = sum(
                            i.amount for i in slip.input_line_ids if i.code in ('EDE', 'PAY', 'FAULT')
                        )
                    elif inp.code == 'ADV' and not slip.payslip_run_id.advance_run_id:
                        sync_vals['advance_amount'] = inp.amount
                    elif inp.code == 'MWD':
                        sync_vals['month_work_days'] = inp.amount
                        slip._update_worked_days_record('MUST_WORK', 'number_of_days', inp.amount)
                    elif inp.code == 'MWT':
                        sync_vals['month_work_hours'] = inp.amount
                        slip._update_worked_days_record('MUST_WORK', 'number_of_hours', inp.amount)
                    elif inp.code == 'WDD':
                        sync_vals['worked_days'] = inp.amount
                        slip._update_worked_days_record('WORK100', 'number_of_days', inp.amount)
                    elif inp.code == 'WDT':
                        sync_vals['worked_hours'] = inp.amount
                        slip._update_worked_days_record('WORK100', 'number_of_hours', inp.amount)
                    if sync_vals:
                        slip.with_context(skip_sync_inputs=True, skip_sync_payslip=True, skip_recompute_sheet=True).write(sync_vals)
                    slip.with_context(skip_sync_payslip=True, skip_recompute_sheet=True).compute_sheet()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_sync_payslip'):
            for inp in records:
                if inp.payslip_id and inp.payslip_id.state == 'draft':
                    inp.write({})
        return records
