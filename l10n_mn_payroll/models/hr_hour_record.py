# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo import tools, _
_logger = logging.getLogger(__name__)
from datetime import date
from datetime import timedelta
from datetime import datetime
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import json, requests
from pytz import timezone
import io
import xlsxwriter
from odoo.tools import date_utils

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

class HrLeave(models.Model):
    _inherit = "hr.leave"

    maternity_leave_notification_date = fields.Date(copy=False)

    def _get_duration(self, check_leave_type=True, resource_calendar=None):
        days, hours = super(HrLeave, self)._get_duration(check_leave_type, resource_calendar)
        resource_calendar = resource_calendar or self.resource_calendar_id
        if resource_calendar.work_time and (self.holiday_status_id.request_unit == 'day' or days >= 1 or (self.request_date_from == self.request_date_to and hours > 8)):
            hours = days * resource_calendar.work_time
        if self.request_unit_half:
            hours = resource_calendar.work_time / 2
        return (days, hours)


    def _get_maternity_leave_notification_email(self):
        self.ensure_one()
        return self.employee_id.work_email or self.employee_id.user_id.partner_id.email or False

    def _get_maternity_leave_notification_cc(self):
        self.ensure_one()
        cc_emails = []

        manager_candidates = [
            self.employee_id.parent_id,
            self.employee_id.department_id.manager_id,
            self.employee_id.leave_manager_id,
        ]
        for manager in manager_candidates:
            email = manager and (manager.work_email or manager.user_id.partner_id.email)
            if email and email not in cc_emails:
                cc_emails.append(email)

        hr_group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
        if hr_group:
            for user in hr_group.users:
                email = user.partner_id.email or user.email
                if email and email not in cc_emails:
                    cc_emails.append(email)

        return ','.join(cc_emails)

    def _get_next_maternity_work_start_date(self):
        self.ensure_one()
        if not self.request_date_to:
            return False

        next_date = self.request_date_to + timedelta(days=1)
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'open'),
        ], limit=1)
        calendar = contract.resource_calendar_id
        if not calendar:
            return next_date

        work_weekdays = set(calendar.attendance_ids.mapped('dayofweek'))
        if not work_weekdays:
            return next_date

        for _day in range(31):
            if str(next_date.weekday()) not in work_weekdays:
                next_date += timedelta(days=1)
                continue

            day_start = fields.Datetime.to_string(datetime.combine(next_date, datetime.min.time()))
            day_end = fields.Datetime.to_string(datetime.combine(next_date, datetime.max.time()))
            holiday_exists = self.env['resource.calendar.leaves'].search_count([
                ('calendar_id', '=', calendar.id),
                ('date_from', '<=', day_end),
                ('date_to', '>=', day_start),
            ])
            if holiday_exists:
                next_date += timedelta(days=1)
                continue
            return next_date

        return next_date

    @api.model
    def _cron_send_maternity_leave_notifications(self):
        today = fields.Date.today()
        reminder_date = today + timedelta(days=2)
        leaves = self.search([
            ('state', 'in', ['validate', 'validate1']),
            ('holiday_status_id.sub_type', '=', 'maternity_leave'),
            ('request_date_to', '=', reminder_date),
        ])
        for leave in leaves:
            if leave.maternity_leave_notification_date == today:
                continue
            email_to = leave._get_maternity_leave_notification_email()
            if not email_to:
                continue
            email_cc = leave._get_maternity_leave_notification_cc()
            email_from = leave.company_id.email or leave.employee_id.company_id.email or self.env.company.email or 'odoo@example.com'
            work_start_date = leave._get_next_maternity_work_start_date()
            mail_values = {
                'subject': _('Жирэмсний амралт дуусах тухай мэдэгдэл'),
                'email_to': email_to,
                'email_cc': email_cc,
                'email_from': email_from,
                'body_html': _(
                    '<p>Сайн байна уу, %(employee)s.</p>'
                    '<p>Таны жирэмсний амралт %(date_to)s-нд дуусах гэж байна.</p>'
                    '<p>Таны ажил эхлэх огноо: %(work_start_date)s</p>'
                    '<p>Шаардлагатай бол хүний нөөц болон удирдлагатайгаа холбогдоно уу.</p>'
                    '<p>Баярлалаа.</p>'
                ) % {
                    'employee': leave.employee_id.name or '',
                    'date_to': leave.request_date_to or '',
                    'work_start_date': work_start_date or '',
                },
                'auto_delete': True,
            }
            self.env['mail.mail'].sudo().create(mail_values).send()
            leave.sudo().write({'maternity_leave_notification_date': today})

class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"
    
    sub_type = fields.Selection([
                        ('legal_leave', 'Legal leave'),
                        ('sick', 'Sick'),
                        ('out_work', 'Out work'),
                        ('night_out_work', 'Night out work'),
                        ('payroll', 'Payroll'),
                        ('unpayroll', 'Unpayroll'),
                        ('over_time','Over time'),
                        ('public_holiday', 'Public holiday'),
                        ('maternity_leave', 'Maternity leave')
                    ], string='Sub type', required=True)
    

class HrHourRecord(models.Model):
    """ АЖИЛЧДЫН ЦАГИЙН БҮРТГЭЛ """
    _name = 'hr.hour.record'
    _inherit = ['mail.thread']
    _description = "Employee hour record"
    
    department = fields.Many2one('hr.department',string='Department')
    name = fields.Char(string='Working time register', default='/', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                 default=lambda self: self.env.company)
    start_date = fields.Datetime(string='Start date', required=True, 
                                default=fields.Date.context_today)
    end_date = fields.Datetime(string='End date',required=True, 
                                default=fields.Date.context_today)
    work_day = fields.Float(string="Work day")
    holiday_day = fields.Float(string='Holiday day')
    is_compute = fields.Boolean(string='Is compute')
    line_id = fields.One2many('hr.hour.record.line', 'parentd_id', string='Hour record')
    state = fields.Selection([
                        ('draft', 'Draft'),
                        ('confirmed', 'Confirmed'),
                        ('posted','Posted'),
                        ('done','Done'),
                    ], string='States', default='draft',
                    readonly=True, tracking=True)

    

    def hour_record(self, employee_id=False):
        hr_data = self
        emp_info = self.env['hr.hour.record.line']
        emp_obj = self.env['hr.employee']
        att_obj = self.env['hr.attendance']
        holiday_obj = self.env['hr.leave']
        self.delete_lines()
        company = hr_data.company_id
        domain = [('company_id','=',company.id), '|', ('attendance_id', '!=', ''), ('timely_id', '!=', 0)]

        if hr_data.department:
            domain.append(('department_id','=',hr_data.department.id))
            emp_id = emp_obj.search(domain, order='department_id')
        else:
            domain.append(('company_id','=',company.id))
            emp_id = emp_obj.search(domain)
        if employee_id:
            if employee_id.attendance_id == '' and employee_id.timely_id == 0:
                return {'miss_time': 0}
            emp_id = employee_id
        start_date = hr_data.start_date + timedelta(hours=8)
        end_times = hr_data.end_date + timedelta(hours=8)

        end_time = end_times.replace(minute=59, hour=23, second=59)
        start_date = start_date.replace(minute=00, hour=00, second=00)


        tz = company.partner_id.tz if company.partner_id.tz else 'Asia/Ulaanbaatar'
        company_tz = timezone(tz)

        start_date = start_date.replace(minute=00, hour=00, second=00)
        # emp_attendance_ids = emp_id.mapped('timely_id')
        # timely_data = self.get_timely_data(emp_attendance_ids)
        # timely_worker_ids = timely_data.keys() if timely_data else []
        public_holiday_ids = self.env['resource.calendar.leaves'].search([('date_from', '>=', start_date), ('date_to', '<=', end_time)])
        for line in emp_id:
            due_time=0
            due_day=0
            in_time = 0.0
            n_time = 0.00
            out_n_time = 0.0
            worked_day = 0.0
            over_time = 0.0

            payroll_time = 0.0
            unpayroll_time = 0.0
            shift_time = 0.0
            out_time = 0.0
            official_time = 0.0
            sick_time = 0.0
            shift_day = 0.0
            lost_time = 0.0
            free_time1 = 0.0
            total_active_time = 0.0
            work_day = start_date
            att_id = att_obj.search([('employee_id','=',line.id),('check_in','>=',start_date),('check_out','<=',end_time)])
            if not line.resource_calendar_id:
                raise UserError(u"%s ажилтны ажлын цагийг тохируулаагүй байна!" % line.name)
            must_work_hour = line.resource_calendar_id.work_time if line.resource_calendar_id.work_time > 0 else 8

            emp_public_holiday_ids = public_holiday_ids.filtered(lambda x: x.calendar_id.id == line.resource_calendar_id.id)
            public_holiday = []
            for p_holiday in emp_public_holiday_ids:
                public_holiday.append(p_holiday.date_from.date())

            if att_id:
                work_weekdays = line.resource_calendar_id.attendance_ids.mapped('dayofweek')
                while work_day <= end_time:
                    if work_day.date() in public_holiday:
                        work_day = work_day + timedelta(days=1)
                        continue
                    worked_hour = 0
                    if str(work_day.weekday()) in work_weekdays:
                        due_day += 1
                        due_time += must_work_hour
                        for att_line1 in att_id:
                            if att_line1.check_in.date() == work_day.date():
                                check_in = att_line1.check_in
                                check_out = att_line1.check_out
                                check_in = check_in.astimezone(company_tz)
                                check_out = check_out.astimezone(company_tz)
                                delta = check_out - check_in
                                total_active_time += (delta.total_seconds() / 60 / 60)
                                lunch_hour = 1
                                lunch_start_time = check_in
                                lunch_end_time = check_in
                                work_start_time = check_in
                                work_end_time = check_in
                                contract_att_line = line.resource_calendar_id.attendance_ids.filtered(
                                    lambda x: x.dayofweek == str(work_day.weekday()))[0]
                                work_start_time = work_start_time.replace(hour=int(round(contract_att_line.hour_from, 0)),
                                                                          minute=int(contract_att_line.hour_from%1*60), second=0, microsecond=0)
                                work_end_time = work_end_time.replace(hour=int(round(contract_att_line.hour_to, 0)),
                                                                          minute=int(contract_att_line.hour_to%1*60), second=0, microsecond=0)
                                if line.resource_calendar_id.lunchtime_start:
                                    lunch_start_time = lunch_start_time.replace(hour=int(round(line.resource_calendar_id.lunchtime_start, 0)),
                                                                          minute=int(line.resource_calendar_id.lunchtime_start%1*60), second=0, microsecond=0)
                                    lunch_end_time = lunch_end_time.replace(hour=int(round(line.resource_calendar_id.lunchtime_end, 0)),
                                                                        minute=int(line.resource_calendar_id.lunchtime_end%1*60), second=0, microsecond=0)
                                else:
                                    lunch_start_time = lunch_start_time.replace(hour=12, minute=0, second=0, microsecond=0)
                                    lunch_end_time = lunch_end_time.replace(hour=13, minute=0, second=0, microsecond=0)

                                if lunch_start_time < check_in < lunch_end_time:
                                    delta = check_in - lunch_start_time
                                    lunch_hour = lunch_hour - delta.total_seconds() / 60 / 60
                                if lunch_start_time < check_out < lunch_end_time:
                                    delta = lunch_end_time - check_out
                                    lunch_hour = lunch_hour - delta.total_seconds() / 60 / 60
                                if check_in >= lunch_end_time or check_out <= lunch_start_time:
                                    lunch_hour = 0
                                if lunch_hour < 0:
                                    lunch_hour = 0

                                if work_start_time < check_in:
                                    delta = (work_end_time if work_end_time <= check_out else check_out) - check_in
                                else:
                                    delta = (check_in + timedelta(hours=must_work_hour+1) if check_in + timedelta(hours=must_work_hour+1) < check_out else check_out) - check_in
                                worked_hour = float(delta.total_seconds() / 60 / 60) - lunch_hour

                        if worked_hour > 0:
                            in_time += worked_hour

                            worked_day += 1
                            lost_time += must_work_hour - worked_hour if must_work_hour > worked_hour else 0
                        else:
                            lost_time += must_work_hour
                    work_day = work_day + timedelta(days=1)

            holiday_id1 = holiday_obj.search([('employee_id','=',line.id),('date_from','>=',start_date),('state','=','validate')])
            if holiday_id1:
                for lines1 in holiday_id1:
                    if lines1.holiday_status_id.sub_type == 'public_holiday':
                        if lines1.date_to <= end_time:
                            shift_time = lines1.number_of_days
                        elif lines1.date_from > end_time:
                            shift_time = 0
                        else:
                            shift_time = 0
                            s_date = lines1.date_from
                            while s_date <= end_time:
                                shift_time += 1
                                s_date = s_date + timedelta(days=1)


            holiday_id = holiday_obj.search([('employee_id','=',line.id),('date_from','>=',start_date),('state','=','validate')])
            if holiday_id:
                for lines in holiday_id:
                    if lines.date_from:
                        if lines.date_to <= end_time:
                            holiday_days = lines.number_of_days
                        elif lines.date_from > end_time:
                            holiday_days = 0
                        else:
                            holiday_days = 0
                            s_date = lines.date_from
                            while s_date <= end_time:
                                holiday_days += 1
                                s_date = s_date + timedelta(days=1)

                        if lines.number_of_days_display >= 1:
                            if lines.holiday_status_id.sub_type == 'night_out_work':
                                n_time += holiday_days*must_work_hour

                            elif lines.holiday_status_id.sub_type == 'over_time':
                                over_time += holiday_days*must_work_hour

                            elif lines.holiday_status_id.sub_type == 'unpayroll':
                                unpayroll_time += holiday_days*must_work_hour

                            elif lines.holiday_status_id.sub_type == 'out_work':
                                out_n_time +=holiday_days*must_work_hour

                            elif lines.holiday_status_id.sub_type == 'payroll':
                                free_time1 +=holiday_days*mach

                            elif lines.holiday_status_id.sub_type == 'legal_leave':
                                official_time +=holiday_days*must_work_hour

                            elif lines.holiday_status_id.sub_type == 'sick':
                                sick_time +=holiday_days*must_work_hour

                        else:
                            if lines.date_to <= end_time:
                                if lines.holiday_status_id.sub_type == 'night_out_work':
                                    n_time +=lines.number_of_hours_display

                                elif lines.holiday_status_id.sub_type == 'over_time':
                                    over_time += lines.number_of_hours_display
                                elif lines.holiday_status_id.sub_type == 'unpayroll':

                                    unpayroll_time += lines.number_of_hours_display
                                elif lines.holiday_status_id.sub_type == 'out_work':
                                    out_n_time +=lines.number_of_hours_display

                                elif lines.holiday_status_id.sub_type == 'payroll':
                                    free_time1 +=lines.number_of_hours_display

                                elif lines.holiday_status_id.sub_type == 'legal_leave':
                                    official_time +=lines.number_of_hours_display

                                elif lines.holiday_status_id.sub_type == 'sick':
                                    sick_time +=lines.number_of_hours_display

            # if str(line.timely_id) in timely_worker_ids:
            #     emp_hour_balance = timely_data[str(line.timely_id)]
            #     due_day += emp_hour_balance['attd']['work']['day']
            #     due_time += emp_hour_balance['attd']['work']['time']
            #     worked_day += emp_hour_balance['attd']['total_worked']['day']
            #     in_time += emp_hour_balance['attd']['total_worked']['time']
            #     # sick_time += emp_hour_balance['attd']['sick_time']
            #     n_time += emp_hour_balance['attd']['overtime_night']['time']
            #     # shift_time += emp_hour_balance['attd']['vacation_day']
            #     lost_time += emp_hour_balance['attd']['total_unworked']['time']
            #     # free_time1 += emp_hour_balance['attd']['salary_leave_time']
            #     unpayroll_time_api = 0
            #     for request in emp_hour_balance['request']:
            #         if request['code'] == 'app_leave_normal':
            #             unpayroll_time_api += request['totalTime']
            #     unpayroll_time += unpayroll_time_api
            #     over_time += emp_hour_balance['attd']['overtime_subtraction']['time']
            #     official_time += emp_hour_balance['attd']['holiday_worked']['time']
            total_time = in_time + official_time + sick_time + out_n_time + n_time
            lost_time = lost_time - (shift_time*must_work_hour) - out_n_time - n_time - sick_time - free_time1 - unpayroll_time - official_time
            vals = {
                'work_day':worked_day,
                'employee_id': line.id,
                'parentd_id': self.id,
                'position': line.job_id.id,
                'due_day': due_day,
                'due_time': due_time,
                'shift_holiday':shift_time,
                'outer_night_time':out_n_time,
                'night_time':n_time,
                'sick_time':sick_time,
                'miss_time':lost_time,
                'free_time1':free_time1,
                'free_time2':unpayroll_time,
                'more_time':over_time,
                'more_time1':official_time,
                'work_time':in_time,
                'active_time':total_active_time,
                'total_time':total_time
            }
            if employee_id:
                return vals
            else:
                emp_info.create(vals)
        return None


    def delete_lines(self):
        for invoice in self:
            for line in invoice.line_id:
                line.unlink()
        return True
    
    def workdaysub(uid,start_date, end_date):
        '''
        Calculate the number of working days between two dates inclusive
        (start_date <= end_date).
    
        The actual working days can be set with the optional whichdays
        parameter
        (default is MON-FRI)
        '''
        (MON, TUE, WED, THU, FRI, SAT, SUN) = range(7)
        whichdays=(MON,TUE,WED,THU,FRI)
        delta_days = (end_date - start_date).days + 1
        full_weeks, extra_days = divmod(delta_days, 7)
        # num_workdays = how many days/week you work * total # of weeks
        num_workdays = (full_weeks + 1) * len(whichdays)
        # subtract out any working days that fall in the 'shortened week'
        for d in range(1, 8 - extra_days):
                    if (end_date + timedelta(d)).weekday() in whichdays:
                                    num_workdays -= 1
        return num_workdays
    
    def action_posted(self):
        return {
            self.write({'state' : 'posted',
                                          })
        }
    def action_done(self):
        return {
            self.write({'state' : 'done',
                                          })
        }
    
    def action_cancel(self):
        return {
            self.write({'state' : 'draft',
                                          })
        }
    def action_confirm(self):
         hr_obj = self.env['hr.hour.record']
         seq = self.env['ir.sequence'].get('hr.hour.record')
         self.write({
                                      'name':seq,
                                      'state' : 'confirmed',
                                  })

         return True

    def action_compute(self):
        obj = self
        line_obj = self.env['hr.hour.record.line']
        total_time = 0.0
        for line in obj.line_id:
            total_time =line.work_time+line.night_time+line.free_time1+line.outer_night_time
            line.write({
                     'total_time':total_time
                     })
            
        return True

    def action_print_xls_report(self):
        data = {
            'res_id': self.id,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': self._name,
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': u'Цагийн тайлан'}
        }


    def get_xlsx_report(self, data, response, get_file=False):
        self_obj = self.env[self._name].browse(data['res_id'])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        sheet.set_landscape()
        sheet.set_paper(9)  # A4
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.repeat_rows(0, 0)
        head = workbook.add_format({
            'align': 'left',
            'font_size': 12
        })
        head_title = workbook.add_format({
            'align': 'center',
            'font_size': 16,
            'text_wrap': True,
            'bold': True
        })
        data_right = workbook.add_format({
            'align': 'right',
            'border': 1,
            'font_size': 12,
            'text_wrap': True,
            'num_format': '#,##0.00'
        })
        data_left = workbook.add_format({
            'align': 'left',
            'border': 1,
            'font_size': 12,
            'text_wrap': True,
            'num_format': '#0'
        })
        data_center_bold = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 12,
            'text_wrap': True,
            'bold': True,
        })
        sheet.set_column(0, 0, 5)
        sheet.set_row(3, 40)
        sheet.set_column(1, 1, 40)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 20, 14)
        sheet.merge_range(0, 0, 0, 2, u'Байгууллагын нэр: %s' % self_obj.company_id.name, head)
        sheet.merge_range(1, 0, 1, 16, u'Цагийн тайлан', head_title)
        sheet.merge_range(2, 0, 2, 2, u'Тайлант хугацаа: %s - %s' % (self_obj.start_date.date(), self_obj.end_date.date()), head)
        rowx = 3
        colly = 0
        sheet.write(rowx, colly, u'№', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ажилтны нэр', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Албан тушаал', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ажиллавал зохих /хоног/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ажиллавал зохих /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ажилласан /хоног/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ажилласан /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Шөнө ажилласан /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Гадуур ажилласан /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Өвчтэй /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Ээлжийн амралт /хоног/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Тасалсан /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Цалинтай чөлөө /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Цалингүй чөлөө /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Илүү цаг /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Амралтын өдөр ажилсан /цаг/', data_center_bold)
        colly += 1
        sheet.write(rowx, colly, u'Нийт тооцоолсон цаг /цаг/', data_center_bold)
        rowx += 1
        total_1 = 0
        total_2 = 0
        total_3 = 0
        total_4 = 0
        total_5 = 0
        total_6 = 0
        total_7 = 0
        total_8 = 0
        total_9 = 0
        total_10 = 0
        total_11 = 0
        total_12 = 0
        total_13 = 0
        total_14 = 0
        numbering = 1
        if self_obj.line_id:
            for line in self_obj.line_id:
                colly = 0
                sheet.write(rowx, colly, numbering, data_left)
                colly += 1
                sheet.write(rowx, colly, line.employee_id.name, data_left)
                colly += 1
                sheet.write(rowx, colly, line.position.name, data_left)
                colly += 1
                sheet.write(rowx, colly, line.due_day, data_right)
                colly += 1
                sheet.write(rowx, colly, line.due_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.work_day, data_right)
                colly += 1
                sheet.write(rowx, colly, line.work_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.night_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.outer_night_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.sick_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.shift_holiday, data_right)
                colly += 1
                sheet.write(rowx, colly, line.miss_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.free_time1, data_right)
                colly += 1
                sheet.write(rowx, colly, line.free_time2, data_right)
                colly += 1
                sheet.write(rowx, colly, line.more_time, data_right)
                colly += 1
                sheet.write(rowx, colly, line.more_time1, data_right)
                colly += 1
                sheet.write(rowx, colly, line.total_time, data_right)
                colly += 1

                total_1 += line.due_day
                total_2 += line.due_time
                total_3 += line.work_day
                total_4 += line.work_time
                total_5 += line.night_time
                total_6 += line.outer_night_time
                total_7 += line.sick_time
                total_8 += line.shift_holiday
                total_9 += line.miss_time
                total_10 += line.free_time1
                total_11 += line.free_time2
                total_12 += line.more_time
                total_13 += line.more_time1
                total_14 += line.total_time

                rowx += 1
                numbering += 1

        sheet.merge_range(rowx, 0, rowx, 2, u'Нийт', data_center_bold)
        sheet.write(rowx, 3, total_1, data_right)
        sheet.write(rowx, 4, total_2, data_right)
        sheet.write(rowx, 5, total_3, data_right)
        sheet.write(rowx, 6, total_4, data_right)
        sheet.write(rowx, 7, total_5, data_right)
        sheet.write(rowx, 8, total_6, data_right)
        sheet.write(rowx, 9, total_7, data_right)
        sheet.write(rowx, 10, total_8, data_right)
        sheet.write(rowx, 11, total_9, data_right)
        sheet.write(rowx, 12, total_10, data_right)
        sheet.write(rowx, 13, total_11, data_right)
        sheet.write(rowx, 14, total_12, data_right)
        sheet.write(rowx, 15, total_13, data_right)
        sheet.write(rowx, 16, total_14, data_right)

        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return


class hr_hour_record_line(models.Model):
    '''
    Ажилтаны цагийн бүртгэлийн мөр
    '''
    _name = "hr.hour.record.line"
    _order = "position"
    _description = 'Information on a employee'
    

    employee_id = fields.Many2one('hr.employee', 'Employee name')
    position = fields.Many2one('hr.job','Position')
    due_day = fields.Integer('due day')
    due_time = fields.Integer('due time')
    work_day = fields.Integer('work day')
    work_time = fields.Float('work time')
    sick_time = fields.Float('sick time')
    outer_night_time = fields.Float('Гадуур ажилсан')
    shift_holiday = fields.Float('Shift holiday')
    miss_time = fields.Float('miss time')
    night_time = fields.Float('Night work time')
    free_time1 = fields.Float(u'Гадуур ажил')
    free_time2 = fields.Float('free time2')
    more_time = fields.Float('more time')
    more_time1 = fields.Float('Legal holiday')
    active_time = fields.Float('Active time')
    late_minut = fields.Float('late minut')
    total_time = fields.Float('Total compute time')
    fine_size = fields.Integer('Attendance  bonus')
    execution_percent = fields.Integer('execution percent')
    parentd_id = fields.Many2one('hr.hour.record')
        
    
    def onchange_change_time(self, day):
        obj = self.browse(cr, uid, ids)
        due_time = 0.0
        miss_time = 0.0
        over_time = 0.0
        diff_time = 0.0
        if day:
            due_time = day*8
            diff_time = obj.work_time-due_time
            if diff_time > 0.0:
                over_time = diff_time
            else:
                miss_time = -diff_time
            
        
        res = {'value':{
                        'due_time':due_time,
                        'miss_time':miss_time,
                        'more_time':over_time,
                            }}
        return res
    
    def onchange_work_time(self, work):
        obj = self.browse(cr, uid, ids)
        miss_time = 0.0
        over_time = 0.0
        diff_time = 0.0
        if work:
            diff_time = work-obj.due_time
            if diff_time > 0.0:
                over_time = diff_time
            else:
                miss_time = -diff_time
            
        
        res = {'value':{
                        'work_time':work,
                        'miss_time':miss_time,
                        'more_time':over_time,
                        }}
        return res

    def see_attendance(self):
        self.ensure_one()
        if self.parentd_id:
            attendance_ids = self.env['hr.attendance'].search([
                ('employee_id', '=', self.employee_id.id),
                ('check_in', '>=', self.parentd_id.start_date),
                ('check_in', '<=', self.parentd_id.end_date)
            ])
            action = self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_attendance_action')
            action['domain'] = [('id', 'in', attendance_ids.ids)]
            return action
        return None
   
