from odoo import http, fields, SUPERUSER_ID
from odoo.http import request, content_disposition
import base64
from io import BytesIO
from docx import Document
from docx.text.paragraph import Paragraph
import tempfile
import subprocess
import os
import json
import ast
from email.utils import encode_rfc2231
from datetime import date, datetime
import num2words
from odoo.addons.l10n_mn_hr.models.hr_decree import verbose_format


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


def transliterate_mongolian_cyrillic(text):
    if not text or not isinstance(text, str):
        return text

    vowels = set("аэиоуөүяеёюыАЭИОУӨҮЯЕЁЮЫ")

    res = []
    n = len(text)
    for i, ch in enumerate(text):
        is_upper = ch.isupper()
        lower_ch = ch.lower()

        next_is_upper = (i + 1 < n and text[i + 1].isupper())
        prev_is_upper = (i > 0 and text[i - 1].isupper())
        all_caps = is_upper and (next_is_upper or prev_is_upper)

        def c(val_title, val_lower, val_upper=None):
            if val_upper is None:
                val_upper = val_title.upper()
            if all_caps:
                return val_upper
            elif is_upper:
                return val_title
            else:
                return val_lower

        if lower_ch == 'а':
            res.append(c('A', 'a'))
        elif lower_ch == 'б':
            res.append(c('B', 'b'))
        elif lower_ch == 'в':
            res.append(c('W', 'w'))
        elif lower_ch == 'г':
            res.append(c('G', 'g'))
        elif lower_ch == 'д':
            res.append(c('D', 'd'))
        elif lower_ch == 'е':
            is_start = (i == 0 or not text[i-1].isalpha() or text[i-1] in vowels)
            if is_start:
                res.append(c('Ye', 'ye', 'YE'))
            else:
                res.append(c('E', 'e'))
        elif lower_ch == 'ё':
            res.append(c('Yo', 'yo', 'YO'))
        elif lower_ch == 'ж':
            res.append(c('J', 'j'))
        elif lower_ch == 'з':
            res.append(c('Z', 'z'))
        elif lower_ch == 'и':
            res.append(c('I', 'i'))
        elif lower_ch == 'й':
            res.append(c('I', 'i'))
        elif lower_ch == 'к':
            res.append(c('K', 'k'))
        elif lower_ch == 'л':
            res.append(c('L', 'l'))
        elif lower_ch == 'м':
            res.append(c('M', 'm'))
        elif lower_ch == 'н':
            res.append(c('N', 'n'))
        elif lower_ch == 'о':
            res.append(c('O', 'o'))
        elif lower_ch == 'ө':
            res.append(c('U', 'u'))
        elif lower_ch == 'п':
            res.append(c('P', 'p'))
        elif lower_ch == 'р':
            res.append(c('R', 'r'))
        elif lower_ch == 'с':
            res.append(c('S', 's'))
        elif lower_ch == 'т':
            res.append(c('T', 't'))
        elif lower_ch == 'у':
            res.append(c('U', 'u'))
        elif lower_ch == 'ү':
            res.append(c('U', 'u'))
        elif lower_ch == 'ф':
            res.append(c('F', 'f'))
        elif lower_ch == 'х':
            res.append(c('Kh', 'kh', 'KH'))
        elif lower_ch == 'ц':
            res.append(c('Ts', 'ts', 'TS'))
        elif lower_ch == 'ч':
            res.append(c('Ch', 'ch', 'CH'))
        elif lower_ch == 'ш':
            res.append(c('Sh', 'sh', 'SH'))
        elif lower_ch == 'щ':
            res.append(c('Sh', 'sh', 'SH'))
        elif lower_ch == 'ъ':
            res.append(c('I', 'i'))
        elif lower_ch == 'ы':
            res.append(c('Y', 'y'))
        elif lower_ch == 'ь':
            res.append(c('I', 'i'))
        elif lower_ch == 'э':
            res.append(c('E', 'e'))
        elif lower_ch == 'ю':
            res.append(c('Yu', 'yu', 'YU'))
        elif lower_ch == 'я':
            res.append(c('Ya', 'ya', 'YA'))
        else:
            res.append(ch)

    return "".join(res)


class DocxController(http.Controller):

    def is_translit_person_name(self, target_model_name, target_field_name=None):
        if target_model_name in ('hr.employee', 'res.partner'):
            if not target_field_name or target_field_name in ('name', 'last_name', 'surname'):
                return True
        return False

    def format_value(self, value, ftype, hel='mongol', bichwer='toogoor', is_translit=False):
        if value is False or value is None or value == '':
            return '.....................'

        # Date / Datetime
        if ftype in ('date', 'datetime'):
            dt = False
            try:
                dt = fields.Date.to_date(value)
            except Exception:
                return str(value)
            if not dt:
                return '.....................'

            if bichwer == 'ugeer':
                if hel == 'english':
                    # Example: May 11, 2026
                    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
                else:
                    # Example: 2026 оны 5 дугаар сарын 11
                    return f"{dt.year} оны {dt.month} дугаар сарын {dt.day}"
            else:
                # Example: 2026-05-11
                return dt.strftime('%Y-%m-%d')

        # Float / Monetary / Integer
        if ftype in ('float', 'monetary', 'integer'):
            try:
                num = float(value)
            except (ValueError, TypeError):
                return str(value)

            is_int = (num % 1 == 0)

            if bichwer == 'ugeer':
                if hel == 'english':
                    try:
                        words = num2words.num2words(int(num) if is_int else num, lang='en')
                    except Exception:
                        words = str(int(num) if is_int else num)
                    return words
                else:
                    if num == 0:
                        words = 'тэг'
                    else:
                        words = verbose_format(num, None)
                    if words:
                        return f"{words.strip()} төгрөг"
                    return f"{int(num) if is_int else num} төгрөг"
            else:
                str_num = f"{int(num):,}" if is_int else f"{num:,.2f}"
                return str_num

        str_val = str(value)
        if bichwer == 'galig' or (hel == 'english' and is_translit):
            str_val = transliterate_mongolian_cyrillic(str_val)

        return str_val

    def replace_in_doc(self, doc, replacements_dict):
        sorted_keys = sorted([k for k in replacements_dict.keys() if k], key=len, reverse=True)

        def replace_in_element(element):
            # 1. Direct text node replacement (preserves exact formatting, covers shapes, textboxes, drawingml, tables)
            for t in element.xpath('.//*[local-name()="t"]'):
                if not t.text:
                    continue
                for key in sorted_keys:
                    rep_val = replacements_dict[key]
                    rep_val = rep_val if (rep_val is not False and rep_val is not None) else '......................'
                    if key in t.text:
                        t.text = t.text.replace(key, rep_val)

            # 2. Paragraph-level replacement (handles placeholders split across runs)
            for p_elem in element.xpath('.//w:p'):
                p = Paragraph(p_elem, doc)
                if not p.text:
                    continue
                for key in sorted_keys:
                    rep_val = replacements_dict[key]
                    rep_val = rep_val if (rep_val is not False and rep_val is not None) else '......................'
                    if key in p.text:
                        for run in p.runs:
                            if key in run.text:
                                run.text = run.text.replace(key, rep_val)
                        if key in p.text:
                            p.text = p.text.replace(key, rep_val)

        # Replace in document body (including tables, shapes, textboxes)
        replace_in_element(doc._element)

        # Replace in headers and footers (including shapes/textboxes inside them)
        for section in doc.sections:
            for hf in [section.header, section.footer,
                       getattr(section, 'first_page_header', None), getattr(section, 'first_page_footer', None),
                       getattr(section, 'even_page_header', None), getattr(section, 'even_page_footer', None)]:
                if hf and hasattr(hf, '_element') and hf._element is not None:
                    replace_in_element(hf._element)

    @http.route('/download/modified_docx/<int:conf_id>/<int:record_id>', type='http', auth='user')
    def download_docx(self, conf_id, record_id, custom_dict=None, **kwargs):
        if custom_dict is None:
            custom_dict = {}
        elif isinstance(custom_dict, str):
            try:
                custom_dict = json.loads(custom_dict)
            except Exception:
                try:
                    custom_dict = ast.literal_eval(custom_dict)
                except Exception:
                    custom_dict = {}
        elif isinstance(custom_dict, dict):
            custom_dict = dict(custom_dict)
        else:
            custom_dict = {}

        if kwargs:
            for k, v in kwargs.items():
                if k not in custom_dict:
                    custom_dict[k] = v

        sudo_env = request.env(user=SUPERUSER_ID)
        conf = sudo_env['contract.decree.conf'].browse(conf_id)

        if not conf.exists() or not conf.file:
            return request.not_found()

        file_content = base64.b64decode(conf.file)

        doc = Document(BytesIO(file_content))

        model_name = conf.model_id.model if conf.model_id else conf.model_char
        model_obj = sudo_env[model_name].browse(record_id) if (model_name and record_id) else False
        replacements_dict = self.get_replacement_dict(conf.line_ids, model_obj, custom_dict=custom_dict, conf=conf)

        # Perform replacement across all text: body, shapes, textboxes, tables, headers, footers
        self.replace_in_doc(doc, replacements_dict)

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

    def get_replacement_dict(self, line_ids, model_obj, custom_dict=None, conf=None):
        if custom_dict is None:
            custom_dict = {}
        elif isinstance(custom_dict, str):
            try:
                custom_dict = json.loads(custom_dict)
            except Exception:
                try:
                    custom_dict = ast.literal_eval(custom_dict)
                except Exception:
                    custom_dict = {}
        elif isinstance(custom_dict, dict):
            custom_dict = dict(custom_dict)
        else:
            custom_dict = {}

        base_env = model_obj.env if model_obj else (line_ids.env if line_ids else (conf.env if conf else request.env))
        sudo_env = base_env(user=SUPERUSER_ID)

        if line_ids:
            line_ids = line_ids.with_env(sudo_env)
        if model_obj:
            model_obj = model_obj.with_env(sudo_env)
        if conf:
            conf = conf.with_env(sudo_env)

        if not conf and line_ids:
            try:
                conf = line_ids[0].contract_conf_id
            except Exception:
                conf = False

        is_doc_english = False
        if conf:
            code = (conf.code or '').lower()
            name = (conf.name or '').lower()
            if code.endswith('_en') or '_en_' in code or code.startswith('en_'):
                is_doc_english = True
            elif 'eng' in name or 'english' in name or 'англи' in name:
                is_doc_english = True

        if not is_doc_english and line_ids:
            english_count = sum(1 for l in line_ids if l.hel == 'english')
            if english_count > 0 and english_count >= (len(line_ids) / 2):
                is_doc_english = True

        replacement_dict = {}
        jumpable_types = ['many2many', 'one2many', 'many2one']

        for line in line_ids:
            if not line.text:
                continue

            hel = line.hel
            if is_doc_english and (not hel or hel == 'mongol'):
                hel = 'english'
            elif not hel:
                hel = 'mongol'

            bichwer = line.bichwer or 'toogoor'
            lang = 'en_US' if hel == 'english' else 'mn_MN'

            line_model_obj = model_obj.with_context(lang=lang) if model_obj else False
            line_env = sudo_env(context=dict(sudo_env.context, lang=lang))

            value = False
            field2 = False
            model2 = False

            # Check if custom_dict overrides this line by field name, text, or related fields
            found_in_custom = False
            custom_val = None
            target_type = False

            custom_key_used = None
            if line.field and line.field.name in custom_dict:
                found_in_custom = True
                custom_key_used = line.field.name
                custom_val = custom_dict[line.field.name]
                target_type = line.field.ttype
            elif line.text in custom_dict:
                found_in_custom = True
                custom_key_used = line.text
                custom_val = custom_dict[line.text]
                target_type = line.field.ttype if line.field else False
            elif line.field2 and line.field2 in custom_dict:
                found_in_custom = True
                custom_key_used = line.field2
                custom_val = custom_dict[line.field2]
                if line.field and line_model_obj:
                    rel_obj = line_model_obj[line.field.name]
                    if rel_obj:
                        f2 = line_env['ir.model.fields'].search(
                            [('name', '=', line.field2), ('model', '=', rel_obj._name)], limit=1)
                        if f2:
                            target_type = f2.ttype
            elif line.field3 and line.field3 in custom_dict:
                found_in_custom = True
                custom_key_used = line.field3
                custom_val = custom_dict[line.field3]

            if found_in_custom:
                if isinstance(custom_val, dict):
                    custom_val = custom_val.get(lang, custom_val.get('mn_MN', custom_val.get('en_US', str(custom_val))))
                target_model_name = False
                target_field_name = False
                if line.field:
                    if line.field2:
                        rel_obj = line_model_obj[line.field.name] if line_model_obj else False
                        target_model_name = rel_obj._name if rel_obj else line.field.relation
                        target_field_name = line.field2
                    else:
                        target_model_name = line.field.model
                        target_field_name = line.field.name
                elif model_obj:
                    target_model_name = model_obj._name
                    target_field_name = custom_key_used

                is_translit = self.is_translit_person_name(target_model_name, target_field_name)
                replacement_dict[line.text] = self.format_value(custom_val, target_type, hel, bichwer, is_translit=is_translit)
                continue

            if not line.field or not line_model_obj:
                replacement_dict[line.text] = '.....................'
                continue

            if line.field.ttype not in jumpable_types:
                if line.field.ttype == 'selection':
                    sel_dict = dict(line_model_obj.fields_get(line.field.name)[line.field.name]['selection'])
                    raw_val = line_model_obj[line.field.name]
                    value = sel_dict.get(raw_val, raw_val)
                else:
                    value = line_model_obj[line.field.name]
                is_translit = self.is_translit_person_name(line_model_obj._name, line.field.name)
                replacement_dict[line.text] = self.format_value(value, line.field.ttype, hel, bichwer, is_translit=is_translit)
                continue

            if line.field2 and line.field.ttype in jumpable_types:
                rel_obj = line_model_obj[line.field.name]
                if not rel_obj:
                    replacement_dict[line.text] = '.....................'
                    continue
                field2 = line_env['ir.model.fields'].search(
                    [('name', '=', line.field2), ('model', '=', rel_obj._name)], limit=1)
                if not field2:
                    replacement_dict[line.text] = '.....................'
                    continue
                model2 = line_env[field2.model_id.model].browse(rel_obj.ids[0])
                if field2.ttype not in jumpable_types:
                    if field2.ttype == 'selection':
                        sel_dict = dict(model2.fields_get(line.field2)[line.field2]['selection'])
                        raw_val = model2[line.field2]
                        value = sel_dict.get(raw_val, raw_val)
                    else:
                        value = model2[line.field2]
                    is_translit = self.is_translit_person_name(model2._name, line.field2)
                    replacement_dict[line.text] = self.format_value(value, field2.ttype, hel, bichwer, is_translit=is_translit)
                    continue
                elif not line.field3 and field2.ttype == 'many2one':
                    target2_obj = model2[line.field2]
                    if target2_obj:
                        val = target2_obj.name if (hasattr(target2_obj, 'name') and target2_obj.name) else target2_obj.display_name
                        is_translit = self.is_translit_person_name(target2_obj._name, 'name')
                        replacement_dict[line.text] = self.format_value(val, 'char', hel, bichwer, is_translit=is_translit)
                        continue

            if line.field3 and field2 and field2.ttype in jumpable_types and model2 and model2[field2.name]:
                rel_obj2 = model2[field2.name]
                field3 = line_env['ir.model.fields'].search(
                    [('name', '=', line.field3), ('model', '=', rel_obj2._name)], limit=1)
                if not field3:
                    replacement_dict[line.text] = '.....................'
                    continue
                model3 = line_env[field3.model_id.model].browse(rel_obj2.ids[0])
                if field3.ttype not in jumpable_types:
                    if field3.ttype == 'selection':
                        sel_dict = dict(model3.fields_get(line.field3)[line.field3]['selection'])
                        raw_val = model3[line.field3]
                        value = sel_dict.get(raw_val, raw_val)
                    else:
                        value = model3[line.field3]
                    is_translit = self.is_translit_person_name(model3._name, line.field3)
                    replacement_dict[line.text] = self.format_value(value, field3.ttype, hel, bichwer, is_translit=is_translit)
                    continue
                else:
                    model4 = model3[line.field3]
                    if model4:
                        disp = model4[0].display_name if hasattr(model4[0], 'display_name') else (model4[0].name if hasattr(model4[0], 'name') else str(model4[0]))
                        is_translit = self.is_translit_person_name(model4._name, 'name')
                        replacement_dict[line.text] = self.format_value(disp, 'char', hel, bichwer, is_translit=is_translit)
                        continue

            if not line.field2 and line.field.ttype == 'many2one':
                rel_obj = line_model_obj[line.field.name]
                if rel_obj:
                    val = rel_obj.name if (hasattr(rel_obj, 'name') and rel_obj.name) else rel_obj.display_name
                    is_translit = self.is_translit_person_name(rel_obj._name, 'name')
                    replacement_dict[line.text] = self.format_value(val, 'char', hel, bichwer, is_translit=is_translit)
                    continue

            replacement_dict[line.text] = '.....................'

        # Also add any custom_dict keys that were not mapped by line_ids
        for key, val in custom_dict.items():
            if not isinstance(key, str):
                continue
            if key not in replacement_dict:
                ftype = False
                if model_obj and key in model_obj._fields:
                    ftype = model_obj._fields[key].type
                is_translit = False
                if model_obj and self.is_translit_person_name(model_obj._name, key):
                    is_translit = True
                custom_hel = 'english' if is_doc_english else 'mongol'
                replacement_dict[key] = self.format_value(val, ftype, hel=custom_hel, is_translit=is_translit)

        return replacement_dict
