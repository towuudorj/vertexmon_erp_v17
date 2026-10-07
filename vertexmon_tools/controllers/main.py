import io
import os
import tempfile
import subprocess
from email.utils import encode_rfc2231

from odoo import http, _
from odoo.http import request

# xlsxwriter томъёоны бодсон утгыг 0 гэж хадгалдаг. LibreOffice анхдагчаар файлд хадгалсан утгыг
# харуулдаг тул хөл дүн 0 гарна. Тусгай профайлаар xlsx/ods нээх бүрт томъёог дахин бодуулна.
LO_PROFILE_DIR = os.path.join(tempfile.gettempdir(), 'odoo_libreoffice_recalc_profile')
LO_RECALC_CONFIG = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="ODFRecalcMode" oor:op="fuse"><value>0</value></prop></item>
</oor:items>
"""


def _get_libreoffice_profile():
    """Томъёог үргэлж дахин боддог LibreOffice профайлын URL."""
    config_path = os.path.join(LO_PROFILE_DIR, 'user', 'registrymodifications.xcu')
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            f.write(LO_RECALC_CONFIG)
    return 'file://' + LO_PROFILE_DIR


class MyReportController(http.Controller):

    @http.route('/report/to_pdf/<string:record_model>/<int:record_id>', type='http', auth='user')
    def download_pdf(self, record_model, record_id):
        record = request.env[record_model].browse(record_id)
        report_data = record.get_report_data()
        xml_data = record.get_xlsx_report(report_data, False, get_file=True)
        tmp_dir = tempfile.mkdtemp()
        xls_path = os.path.join(tmp_dir, "report.xlsx")

        with open(xls_path, "wb") as f:
            f.write(xml_data)

        pdf_path = os.path.join(tmp_dir, "report.pdf")

        subprocess.run([
            "libreoffice",
            "-env:UserInstallation=%s" % _get_libreoffice_profile(),
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

        return request.make_response(
            pdf_data,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_data)),
                (
                    "Content-Disposition",
                    (
                        "inline; filename*=%s.pdf"
                        % encode_rfc2231('PDF Report', "utf-8")
                    ),
                ),
            ],
        )