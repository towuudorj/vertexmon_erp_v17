# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models, api
from odoo.tools import date_utils


class HrAttendanceExcelReport(models.TransientModel):
    _name = 'hr.attendance.excel.report'
    _description = 'Hr attendance'
    
    company_id = fields.Many2one('res.company',string='Company', readonly=True, 
                                 default=lambda self: self.env.user.company_id)
    department_id = fields.Many2one('hr.department', string='Department', 
                                    required=True, readonly=True)
    start_date = fields.Date(string='Start date', required=True, readonly=True)
    end_date = fields.Date(string='End date', required=True, readonly=True)
    
    @api.model
    def default_get(self, fields):
        res = super(HrAttendanceExcelReport, self).default_get(fields)
        res_ids = self._context.get('active_ids')
        hour_data = self.env['hr.hour.record'].browse(res_ids)
        res.update({
            'department_id': hour_data.department.id,
            'start_date':hour_data.start_date,
            'end_date':hour_data.end_date
        })
        return res
    



    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'start_date': self.start_date,
            'end_date': self.end_date,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'hr.attendance.excel.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Hr attendance report'}
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': '20px'
                                    })
        txt = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12
                                })
        sheet.set_column(0, 8, 24)

        sheet.write('A1', u'№', head)
        sheet.write('B1', u'Ажилтны нэр', head)
        sheet.write('C1', u'Хэлтэс', head)
        sheet.write('D1', u'Ажиллах ёстой хоног', head)
        sheet.write('E1', u'Ажилласан хоног', head)
        sheet.write('F1', u'Ажиллах цаг', head)
        sheet.write('G1', u'Ажилласан цаг', head)
        sheet.write('H1', u'Хоцролт', head)
        sheet.write('I1', u'Чөлөө /цалинтай/', head)
        sheet.write('J1', u'Чөлөө /цалингүй/', head)
        sheet.write('K1', u'Өвчтэй',head)
        sheet.write('L1', u'Ээлжийн амралт', head)
        sheet.write('M1', u'Гадуур ажилласан', head)
        sheet.write('N1', u'Нийт ажилласан цаг', head)


        rowx = 2
        num = 0
        attendance_obj = self.env['hr.hour.record']
        attendance_id = attendance_obj.search([('start_date','=',data['start_date']),('end_date','<=',data['end_date']),('department','=',data['department_id'])])
        if attendance_id.id != False:
            for line in attendance_id.line_id:
                sheet.write(rowx, 0, u'%s'%num, txt)
                sheet.write(rowx, 1, u'%s'%(line.employee_id.name), txt)
                sheet.write(rowx, 2, u'%s'%(self.department_id.name), txt)
                sheet.write(rowx, 3, u'%s'%round(line.due_day,2), txt)
                sheet.write(rowx, 4, u'%s'%round(line.work_day,2), txt)
                sheet.write(rowx, 5, u'%s'%str("%02d:%02d")%divmod((line.due_time * 60), 60), txt)
                sheet.write(rowx, 6, u'%s'%str("%02d:%02d")%divmod((line.work_time * 60), 60), txt)
                sheet.write(rowx, 7, u'%s'%str("%02d:%02d")%divmod((line.miss_time_morning * 60), 60), txt)
                sheet.write(rowx, 8, u'%s'%str("%02d:%02d")%divmod((line.free_time1 * 60), 60), txt)
                sheet.write(rowx, 9, u'%s'%str("%02d:%02d")%divmod((line.free_time2 * 60), 60), txt)
                sheet.write(rowx, 10, u'%s'%str("%02d:%02d")%divmod((line.sick_time * 60), 60), txt)
                sheet.write(rowx, 11, u'%s'%str("%02d:%02d")%divmod((line.shift_holiday * 60), 60), txt)
                sheet.write(rowx, 12, u'%s'%str("%02d:%02d")%divmod((line.out_work * 60), 60), txt)
                sheet.write(rowx, 13, u'%s'%str("%02d:%02d")%divmod((line.total_time * 60), 60), txt)

                num +=1
 
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


    
        
    