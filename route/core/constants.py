"""custom constants"""
import os

from django.conf import settings

HTTP_API_ERROR = 500

HTTP_SUCCESS = 200

NO_RECORD_FOUND = 202

DOCUMENT_EXPORT_SHEET_NAME = "Documents"

PAYMENT_TERM_EXPORT_SHEET_NAME = "Payment Term Documents"

QUALITY_KPIS_EXPORT_SHEET_NAME = "Quality Kpi's Documents"

ADMIN_UPLOAD_COLUMNS = {
    "supplier_reference_file": ["Company ID","Company Name","Supplier Group", "Supplier Group Name"],
    "supplier_reference_file_name":"SbmMappings_replacement_SGN.xlsx",
    "tpd_monthly_report": ["Supplier text", "PT_days"],
    "tpd_monthly_report_name": "TPD.xlsx",
    "spe_zero_defect_report": ["EnterpriseID", "Project","KPI Value"],
    "spe_zero_defect_report_name": "ZD.xlsx",
    "spe_paru_monthly_report":["EnterpriseID", "Project","KPI Value"],
    "spe_paru_monthly_report_name": "PARU.xlsx",
    "spe_sar_monthly_report": ["EnterpriseID", "Project","KPI Value"],
    "spe_sar_monthly_report_name": "SAR.xlsx",
}

DOCUMENT_DETAIL_URL = "http://"+str(os.environ.get("BUSINESS"))+"-"+str(os.environ.get("DOMAIN"))+"-es:5000/dkm/search"
DOCUMENTS_LISTING_URL = "http://"+str(os.environ.get("BUSINESS"))+"-"+str(os.environ.get("DOMAIN"))+"-es:5000/dkm/v2/search"
DOCUMENT_UPLOAD_URL = "http://"+str(os.environ.get("BUSINESS"))+"-"+str(os.environ.get("DOMAIN"))+"-de:5001/submit"
REMOVE_DOCUMENT_URL = "http://"+str(os.environ.get("BUSINESS"))+"-"+str(os.environ.get("DOMAIN"))+"-es:5000/dkm/{0}"
ADMIN_UPLOAD_URL = "http://"+str(os.environ.get("BUSINESS"))+"-"+str(os.environ.get("DOMAIN"))+"-de:5001/dkm/process-supplier"

