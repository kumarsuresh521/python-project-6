import json

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Contract


class DocumetsTestCase(APITestCase):
    def test_document_listing(self):
        data = {"columns":["filename","document_number","document_type","supplier_group","region","country","start_date","end_date","origin","import_datetime","real_pdf"]}
        response = self.client.post('/orch/api/documents/?from=0&to=5', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_document_details(self):
        data = {"document_id.keyword":"Project Agreement_Sublime Wireless Swap - signed.pdf"}
        response = self.client.post('/orch/api/document/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)["totalRecords"], 1)

    def test_verify_document_is_exists(self):
        data = {"files":["Project Agreement_Sublime Wireless Swap - signed.pdf"]}
        response = self.client.post('/orch/api/verify-document/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_download_source_document(self):
        data = "Project Agreement_Sublime Wireless Swap - signed.pdf"
        response = self.client.get('/orch/api/source-document/' + data + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_download_searchable_document(self):
        data = "Project Agreement_Sublime Wireless Swap - signed.pdf"
        response = self.client.get('/orch/api/searchable-document/' + data + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_documents_export(self):
        response = self.client.post('/orch/api/export-documents/?from=0&to=5', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_document_delete(self):
        data = "Project Agreement_ _Sublime Wireless Swap - signed.pdf"
        response = self.client.delete('/orch/api/remove-document/' + data + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_payment_terms_listing(self):
        data = {"columns":["filename","document_number","document_type","supplier_legal_entity","country","payment_terms","actual_pt_days"],"contains_payment_terms":"true"}
        response = self.client.post('/orch/api/documents/?from=0&to=5', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_quality_kpis_listing(self):
        data = {"columns":["filename","document_number","document_type","supplier_group","country"],"contains_quality_kpi":"true"}
        response = self.client.post('/orch/api/quality-kpis/?from=0&to=5', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_qualiky_kpis_details(self):
        data = {"document_id.keyword":"Project Agreement_ _Sublime Wireless Swap - signed.pdf"}
        response = self.client.post('/orch/api/payment-terms/?from=0&to=5', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)["totalRecords"], 1)