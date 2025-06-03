# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID
from io import BytesIO
from xlwt import easyxf
from lxml import etree
from dateutil.relativedelta import relativedelta

class report_excel_output(models.Model):
    _name = 'report.excel.output'
    _description = "Excel Report Output"
    
    name = fields.Char(string='Filename', readonly=True)
    data = fields.Binary(string='File', readonly=True, required=True)
    date = fields.Datetime(string='Creation Date', readonly=True, required=True)
    

class Abstract_Report_Excel(models.Model):
    _name = 'abstract.report.excel'
    _description = 'Abstract Report Excel'
    
    def get_easyxf_styles(self):
        
        styledict = {
            'title_xf': easyxf('font: bold on, height 250; align: wrap off, vert centre, horiz left;'),
            'small_title_xf': easyxf('font: bold on, height 190; align: wrap off, vert centre, horiz left;'),
            'heading_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin, top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_color pale_blue'),
            'too': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center,rota 90; borders: top thin, left thin, bottom thin, right thin, top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_color pale_blue'),
            'heading_xf-1': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour light_turquoise'),
            'heading_grey_text_center_bold_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour gray25'),
            'text_xf': easyxf('font: bold off, height 160; align: wrap on, vert centre, horiz left; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50'),
            'text_right_xf': easyxf('font: bold off, height 160; align: wrap on, vert centre, horiz right; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50;'),
            'text_bold_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz left; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50;'),
            'text_bold_right_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz right; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50;'),
            'text_center_bold_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50;'),
            'text_center_xf': easyxf('font: bold off, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50;'),
            'number_xf': easyxf('font: height 160; align: vert centre, horz right; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50;', num_format_str='#,##0.00'),
            'number_bold_xf': easyxf('font: height 160, bold on; align: horz right; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50;', num_format_str='#,##0.00'),
            'grey_text_bold_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz left; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour gray25'),
            'grey_text_bold_right_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz right; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour gray25'),
            'grey_text_center_bold_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour gray25'),
            'grey_number_bold_xf': easyxf('font: height 160, bold on; align: horz right; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour light_turquoise', num_format_str='#,##0.00'),
            'gold_text_bold_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz left; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour gold'),
            'gold_text_bold_right_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz right; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour gold'),
            'gold_text_center_bold_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour gold'),
            'gold_number_bold_xf': easyxf('font: height 160, bold on; align: horz right; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour pale_blue', num_format_str='#,##0.00'),
            'text_cntr_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50;'),
            'text_bold_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz left; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50;'),
            'number_boldg_xf': easyxf('font: height 160, bold on; align: wrap on, vert centre, horiz left; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour light_turquoise', num_format_str='#,##0.00'),
            'text_grey_text_center_bold_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50; pattern: pattern solid, fore_colour light_turquoise'),
            'text_boldtotal_xf': easyxf('font: bold on, height 160; align: wrap on, vert centre, horiz center; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50 ; pattern: pattern solid, fore_colour pale_blue'),
            'number_boldtotal_xf': easyxf('font: height 160, bold on; align: wrap on, vert centre, horiz right; borders: top thin, left thin, bottom thin, right thin , top_colour gray50,bottom_colour gray50,left_colour gray50,right_colour gray50 ;pattern: pattern solid, fore_colour pale_blue ', num_format_str='#,##0.00'),
            'tt_11_xf':easyxf('font: bold off, height 160; align: wrap on, vert centre, horiz left; borders: top thin, left thin, bottom thin, right thin , top_colour black,bottom_colour black,left_colour black,right_colour black')

        }
        return styledict

    def export_report(self):

        d1 = datetime.datetime.now()
        res = self.get_export_data()
        
        book = res['data'] # Workbook object instance.
        buffer = BytesIO()
        book.save(buffer)
        buffer.seek(0)
        
        out = base64.encodestring(buffer.getvalue())
        buffer.close()
        
        filename = self._name.replace('.', '_')
        filename = "%s.xls" % (filename)
        if 'xlsx' in res:
            filename += 'x' # Office 2007
        
        excel_id = self.env['report.excel.output'].create({
                                'data':out,
                                'date': time.strftime('%Y-%m-%d'),
                                'name':filename
        })
        
        mod_obj = self.env['ir.model.data']
        compose_form = self.env.ref('l10n_mn_asset.action_excel_output_view', False)
        
        dta = datetime.datetime.now() - d1
        if dta.seconds > 60 :
            tm = '%sm %ss' %(dta.seconds / 60, dta.seconds % 60)
        else :
            tm = '%ss' % dta.seconds
        
        return {
             'name': _('Export'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': excel_id.id,
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'res_model': 'report.excel.output',

        }
    
    def get_export_data(self):
        raise osv.except_osv(_('Programming Error!'), _('Unimplemented method.'))
