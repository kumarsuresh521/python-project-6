'''
Api requests for module
'''
import json
import uuid
from io import BytesIO as IO

import pandas as pd
import requests
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from route.core.constants import (ADMIN_UPLOAD_COLUMNS, ADMIN_UPLOAD_URL,
                                  DOCUMENT_DETAIL_URL, DOCUMENT_UPLOAD_URL,
                                  DOCUMENTS_LISTING_URL, HTTP_API_ERROR,
                                  HTTP_SUCCESS, NO_RECORD_FOUND,
                                  REMOVE_DOCUMENT_URL)
from route.core.helper import (documents_export, download_admin_files,
                               download_s3_object,
                               download_searchable_s3_object,
                               is_document_in_elastic_db, remove_s3_object,
                               request_mixin, upload_admin_document,
                               upload_image, user_access_control)
from uam.models import SupplierGroup

from .models import Contract


class ExportDocuments(APIView):
    def post(self, request, format=None):
        if 'contains_quality_kpi' in self.request.data:
            records = request_mixin(request, DOCUMENT_DETAIL_URL, self.request.data)
        else:
            records = request_mixin(request, DOCUMENTS_LISTING_URL, self.request.data)

        if records.status_code == status.HTTP_200_OK:
            return documents_export(records, self.request.data, False)
        return Response({"message": "Something went wrong!!!"}, status=HTTP_API_ERROR)


class ExportPaymentTerms(APIView):
    def post(self, request, format=None):
        self.request.data["columns"] = ["filename", "document_number", "document_type", "supplier_group", "supplier_legal_entity",
                                        "country","payment_terms","actual_pt_days"]
        export_payment_terms = True
        records = request_mixin(request, DOCUMENT_DETAIL_URL, self.request.data)

        if records.status_code == status.HTTP_200_OK:
            return documents_export(records, self.request.data, export_payment_terms)
        return Response({"message": "Something went wrong!!!"}, status=HTTP_API_ERROR)


class SearchableDocument(APIView):
    def post(self, request):
        filename = self.request.data["document_id"]
        file_status, file =  download_searchable_s3_object(filename)
        if file_status is True:
            response = HttpResponse(file['Body'], content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            return response
        return Response({"message": "Requested file not exist"}, status=HTTP_API_ERROR)


class SourceDocument(APIView):
    def post(self, request):
        filename = self.request.data["document_id"]
        file_status, file =  download_s3_object(filename)
        if file_status is True:
            response = HttpResponse(file['Body'], content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            return response
        return Response({"message": "Requested file not exist"}, status=HTTP_API_ERROR)


class DocumentDetails(APIView):
    def post(self, request, format=None):
        return request_mixin(request, DOCUMENT_DETAIL_URL, self.request.data)


class DocumentsListing(APIView):
    def update_user_request(self, request):
        page_to =  int(request.GET.get("to"))
        page_from =  int(request.GET.get("from"))
        contract_list = Contract.objects.filter(status=Contract.UPLOADED,
            updated__gte=timezone.now() - timezone.timedelta(minutes=15)).order_by("updated")[page_from:page_to]

        try:
            param_list =  request.META['QUERY_STRING'].split('&')
            com_list = [n for n, x in enumerate(param_list) if 'to=' in x]
            param_list[com_list[0]] = 'to={0}'.format(page_to - contract_list.count())
            request.META['QUERY_STRING'] = '&'.join(param_list)
        except Exception as e:
            pass
        return contract_list

    def update_user_data(self, request, contract_list, data):
        for contract in contract_list:
            record = {}
            for rec in request.data["columns"]:
                record[rec] = ''
            record["status"] = contract.status
            record['filename'] = contract.document_file_name
            record['origin'] = contract.imported_by
            record["import_datetime"] = contract.updated
            data["data"].insert(0, record)
        return data

    def post(self, request, format=None):
        user_access_control(request)
        if settings.IS_NOTIFICATION_REQUIRED is True:
            contract_list = self.update_user_request(request)

        query_params = '?aggregator=AND&indexname=%s&%s' % (settings.ELASTIC_SEARCH_INDEX_KEY, request.META['QUERY_STRING'])
        response = requests.post(url=DOCUMENTS_LISTING_URL + query_params, data=json.dumps(request.data))
        
        if response.status_code == status.HTTP_200_OK:
            data = json.loads(response.content)

            if settings.IS_NOTIFICATION_REQUIRED is True:
                data = self.update_user_data(request, contract_list, data)

            return Response(data, status=response.status_code)
        return Response({"message": "Something went wrong !!!"}, status=HTTP_API_ERROR)


class RemoveDocument(APIView):
    def post(self, request):
        filename = self.request.data["document_id"]
        remove_s3_object(filename)
        Contract.objects.filter(document_file_name__iexact=filename).delete()
        query_params = '?indexname=%s&%s' % (settings.ELASTIC_EXTRACTED_INDEX_KEY, request.META['QUERY_STRING'])
        requests.delete(url=REMOVE_DOCUMENT_URL.format(filename.replace(" ", "")) + query_params)

        query_params = '?indexname=%s&%s' % (settings.APTTUS_DOCUMENTS_INDEX_KEY, request.META['QUERY_STRING'])
        requests.delete(url=REMOVE_DOCUMENT_URL.format(filename.replace(" ", "")) + query_params)

        query_params = '?indexname=%s&%s' % (settings.ELASTIC_SEARCH_INDEX_KEY, request.META['QUERY_STRING'])
        response = requests.delete(url=REMOVE_DOCUMENT_URL.format(filename.replace(" ", "")) + query_params)

        data = json.loads(response.content)
        return Response(data, status=response.status_code)


class DocumentsUpload(APIView):
    def process_user_data(self, request, username, request_id):
        files = []
        overwrite = "True" if request.POST.get('already_exists') == 'true' else "False"

        for myfile in request.FILES.getlist('myfile'):
            contractId = str(uuid.uuid4())
            new_file_name = upload_image(myfile, request_id)
            files.append({"filename": new_file_name, "overwrite": overwrite, "contractId": contractId, "actual_name": myfile.name})

        for val in files:
            Contract.objects.update_or_create(document_file_name=val["actual_name"],
                                              defaults={'document_path': val["filename"],
                                                        'request_id': request_id,
                                                        'contractId': val["contractId"],
                                                        'status': Contract.UPLOADED,
                                                        'imported_by': username,
                                                        'updated': timezone.now()})
        return files

    def post(self, request, format=None):
        request_id = str(uuid.uuid4())
        username = request.session.get('name', '')
        files = self.process_user_data(request, username, request_id)

        request_data = {
            "userId": username,
            "requestId": request_id,
            "files": files
        }
        return request_mixin(request, DOCUMENT_UPLOAD_URL, request_data)


class AdminUpload(APIView):
    @transaction.atomic
    def saving_supplier_group(self, records):
        records = records.fillna('')
        for data in records.values:
            if data.size > 5 and data[5] != '' and data[6] != '':
                try:
                    supplier, created = SupplierGroup.objects.get_or_create(supplier_group=data[5], defaults={'supplier_group_name': data[6]})
                    if not created:
                        supplier.supplier_group_name = data[6]
                        supplier.save()
                except SupplierGroup.DoesNotExist:
                    pass

    def post(self, request, format=None):
        document_type = request.POST.get('document_type')
        if 'tpd_monthly_report' in  document_type:
            df = pd.read_excel(self.request.FILES["document"], skiprows = [0,1])
        else:
            df = pd.read_excel(self.request.FILES["document"])
        df.drop_duplicates(keep=False, inplace=True)
        if all(elem in df.columns  for elem in ADMIN_UPLOAD_COLUMNS[document_type]):
            if 'supplier_reference_file' == document_type:
                self.saving_supplier_group(df)
            excel_file = IO()
            xlwriter = pd.ExcelWriter(excel_file, engine='xlsxwriter')
            df.to_excel(xlwriter, sheet_name="Sheet1", index=False)
            xlwriter.save()
            xlwriter.close()
            excel_file.seek(0)
            upload_admin_document(excel_file.read(), ADMIN_UPLOAD_COLUMNS[document_type + "_name"], document_type)
            if 'supplier_reference_file' == document_type:
                requests.get(url=ADMIN_UPLOAD_URL)
            return Response({"message": "File processed successfully !!!"}, status=HTTP_SUCCESS)
        else:
          return Response({"message": "Required columns are not exists"}, status=NO_RECORD_FOUND)


class AdminDownload(APIView):
    def post(self, request, format=None):
        filename = self.request.data["filename"]
        file_status, file =  download_admin_files(ADMIN_UPLOAD_COLUMNS[filename + "_name"], filename)
        if file_status is True:
            response = HttpResponse(file['Body'], content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(ADMIN_UPLOAD_COLUMNS[filename + "_name"])
            return response
        return Response({"message": "Requested file not exist"}, status=HTTP_API_ERROR)


class DocumentTree(APIView):
    def post(self, request, format=None):
        return request_mixin(request, DOCUMENTS_LISTING_URL, self.request.data, settings.DOCUMENT_TREE_INDEX_KEY, "OR")


class PaymentTermDetails(APIView):
    def post(self, request, format=None):
        return request_mixin(request, DOCUMENT_DETAIL_URL, self.request.data)


class PaymentTermsList(APIView):
    def post(self, request, format=None):
        user_access_control(request)
        return request_mixin(request, DOCUMENTS_LISTING_URL, self.request.data)

class DocumentPrice(APIView):
    def post(self, request, format=None):
        user_access_control(request)
        return request_mixin(request, DOCUMENTS_LISTING_URL, self.request.data)


class QualityKpiDetails(APIView):
    def post(self, request, format=None):
        return request_mixin(request, DOCUMENT_DETAIL_URL, self.request.data)


class QualityKpisList(APIView):
    def post(self, request, format=None):
        user_access_control(request)
        return request_mixin(request, DOCUMENTS_LISTING_URL, self.request.data)


class VerifyExistingDocuments(APIView):
    def post(self, request, format=None):
        coming_document_list = self.request.data.get('files')
        response = []
        for rec in coming_document_list:
           response.append({"filename": rec, "already_exists": is_document_in_elastic_db(rec)})
        return Response(response, status=HTTP_SUCCESS)


class PushNotification(APIView):
    def post(self, request):
        status = self.request.data.get('status')
        contractId = self.request.data.get('contractId')

        response = []
        if status == '100' or status == '101':
            response.append({"status": "Processing"})
        
        if status == '200':
            Contract.objects.filter(contractId__in=contractId).update(status=Contract.SUCCESS)
            response.append({"status": "success"})

        if status == '111':
            contract_list = Contract.objects.filter(contractId__in=contractId)
            for contract_id in contract_list:
                filename = contract_id.document_file_name

                Contract.objects.filter(document_file_name__iexact=filename).delete()
                remove_document_url = REMOVE_DOCUMENT_URL.format(filename.replace(" ", ""))

                query_params = '?aggregator=AND&indexname=%s' % settings.ELASTIC_SEARCH_INDEX_KEY
                requests.delete(url=remove_document_url + query_params)

                query_params = '?aggregator=AND&indexname=%s' % settings.ELASTIC_EXTRACTED_INDEX_KEY
                requests.delete(url=remove_document_url + query_params)

                remove_s3_object(filename)
                response.append({"status": "failed"})
        return Response(response, status=HTTP_SUCCESS)
