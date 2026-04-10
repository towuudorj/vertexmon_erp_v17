from odoo import http, fields
from odoo.http import request, content_disposition
import base64
from io import BytesIO
from docx import Document
import tempfile
import subprocess
import os
from email.utils import encode_rfc2231


def convert_docx_to_pdf(file_content):

    tmp_dir = tempfile.mkdtemp()
    xls_path = os.path.join(tmp_dir, "temp.docx")

    with open(xls_path, "wb") as f:
        f.write(file_content)

    pdf_path = os.path.join(tmp_dir, "temp.pdf")

    subprocess.run([
        "libreoffice",
        "--headless",
        "--convert-to", "pdf",
        xls_path,
        "--outdir", tmp_dir
    ], check=True)

    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    os.remove(xls_path)
    os.remove(pdf_path)
    os.rmdir(tmp_dir)
    return pdf_data


class DocxController(http.Controller):

    @http.route('/download/modified_docx/<int:conf_id>/<int:record_id>', type='http', auth='user')
    def download_docx(self, conf_id, record_id):
        conf = request.env['contract.decree.conf'].browse(conf_id)

        if not conf.file:
            return request.not_found()

        file_content = base64.b64decode(conf.file)

        doc = Document(BytesIO(file_content))

        model_obj = request.env[conf.model_id.model].browse(record_id)
        replacements_dict = self.get_replacement_dict(conf.line_ids, model_obj)

        for para in doc.paragraphs:
            for run in para.runs:
                for key, val in replacements_dict.items():
                    if key in run.text:
                        run.text = run.text.replace(key, val)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for key, val in replacements_dict.items():
                        if key in cell.text:
                            cell.text = cell.text.replace(key, val)

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        file_content = buffer.read()

        if conf.type == 'pdf':
            pdf_base64 = convert_docx_to_pdf(file_content)
            return request.make_response(
                pdf_base64,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ("Content-Disposition",
                    (
                        "inline; filename*=%s.pdf"
                        % encode_rfc2231(conf.file_name + '_'+ str(fields.Date.today()), "utf-8")
                    ),),
                ]
            )

        return request.make_response(
            file_content,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                ('Content-Disposition', content_disposition('%s.docx' % (conf.file_name + '_'+ str(fields.Date.today())))),
            ]
        )

    def get_replacement_dict(self, line_ids, model_obj):
        replacement_dict = {}
        jumpable_types = ['many2many', 'one2many', 'many2one']
        for line in line_ids:
            value = False
            field2 = False
            model2 = False
            if line.field.ttype not in jumpable_types:
                if line.field.ttype == 'selection':
                    value = dict(model_obj.fields_get(line.field.name)[line.field.name]['selection'])[model_obj[line.field.name]]
                else:
                    value = model_obj[line.field.name]
                replacement_dict[line.text] = str(value) if value else '.....................'
                continue
            if line.field2 and line.field and line.field.ttype in jumpable_types:
                field2 = request.env['ir.model.fields'].search(
                    [('name', '=', line.field2), ('model', '=', model_obj[line.field.name]._name)])
                model2 = request.env[field2.model_id.model].browse(model_obj[line.field.name].ids[0])
                if field2.ttype not in jumpable_types:
                    if field2.ttype == 'selection':
                        value = dict(model2.fields_get(line.field2)[line.field2]['selection'])[model2[line.field2]]
                    else:
                        value = model_obj[line.field.name][line.field2]
                    replacement_dict[line.text] = str(value) if value else '.....................'
                    continue
            if line.field3 and model2[field2.name] and field2 and field2.ttype in jumpable_types:
                field3 = request.env['ir.model.fields'].search(
                    [('name', '=', line.field3), ('model_id', '=', field2.model_id.id)])
                model3 = request.env[field3.model_id.model].browse(model2[field2.name].ids[0])
                if field3.ttype not in jumpable_types:
                    if field3.ttype == 'selection':
                        value = dict(model3.fields_get(line.field3)[line.field3]['selection'])[model3[line.field3]]
                    else:
                        value = model2[line.field2][line.field3]
                    replacement_dict[line.text] = str(value) if value else '.....................'
                    continue
                else:
                    model4 = model3[line.field3]
                    if model4 and 'name' in model4[0]:
                        replacement_dict[line.text] = model4[0]['name']
                        continue
            replacement_dict[line.text] = '.....................'
        return replacement_dict