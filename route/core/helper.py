import json
from datetime import datetime
from io import BytesIO as IO

import boto3
from botocore.client import Config
import pandas as pd
import requests
from django.conf import settings
from django.db import models
from django.http import HttpResponse
from rest_framework.response import Response
from retrying import retry
from uam.models import Country, Region, RegionCountry, SupplierGroup

from .constants import (DOCUMENT_DETAIL_URL, DOCUMENT_EXPORT_SHEET_NAME,
                        PAYMENT_TERM_EXPORT_SHEET_NAME,
                        QUALITY_KPIS_EXPORT_SHEET_NAME)

config = Config(connect_timeout=100, read_timeout=100, retries={'max_attempts': 10})

class TimestampModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


def request_mixin(request, url, data=None, indexname=None, aggregator="AND", headers=None):
    '''
    Common request mixin for all third party call (work like a proxy server)
    '''
    if not indexname:
        indexname = settings.ELASTIC_SEARCH_INDEX_KEY

    if not headers:
        headers = {
            'Content-Type': 'application/json'
        }

    query_params = '?aggregator=%s&indexname=%s&%s' % (aggregator, indexname, request.META['QUERY_STRING'])
    if request.method == 'POST':
        response = requests.post(url=url + query_params, headers=headers, data=json.dumps(data))
    elif request.method == 'DELETE':
        response = requests.delete(url=url + query_params, headers=headers)
    else:
        response = requests.get(url=url + query_params, headers=headers)

    if response.status_code == requests.codes.ok:
        return Response(json.loads(response.content), status=response.status_code)
    else:
        return Response({"message": "Connection failed to the services"}, status=response.status_code)


def get_s3_client():
    '''
    Create a connect with aws s3 server/bucket
    '''
    connection_kwargs = {
        "region_name": settings.S3DIRECT_REGION,
        "aws_access_key_id": settings.S3_ACCESS_KEY,
        "aws_secret_access_key": settings.S3_SECRET_KEY,
        "endpoint_url": settings.S3_ENDPOINT_URL
    }
    return boto3.client("s3", **connection_kwargs)


@retry
def upload_image(image_obj, request_id):
    '''
    Upload image object on s3 bucket. Location /dkm/ENVIRONMENT/se/file_name
    '''
    new_file_path = "%s/%s" % (settings.S3_BUCKET_LOCAL_PATH, image_obj.name)
    file_name="%s/%s" % (settings.S3_BUCKET_PATH, new_file_path)
    
    params = {
        "ACL": "public-read",
        'Key': file_name
    }

    connection_kwargs = {
        "region_name": settings.S3DIRECT_REGION,
        "aws_access_key_id": settings.S3_ACCESS_KEY,
        "aws_secret_access_key": settings.S3_SECRET_KEY,
        "endpoint_url": settings.S3_ENDPOINT_URL
    }
    s3_obj = boto3.resource("s3", **connection_kwargs)
    s3_obj.Bucket(settings.S3_BUCKET).put_object(Body=image_obj, **params)
    return new_file_path


@retry
def upload_admin_document(document, document_name, document_type):
    '''
    Upload admin uploaded documents in dkm/customer_file/ location
    '''
    if "supplier_reference_file" == document_type:
        file_name="%s/%s" % (settings.S3_BUCKET_CUSTOMER_FILES_PATH, document_name)
    else:
        file_name="%s/%s" % (settings.S3_BUCKET_DE_FILES_PATH, document_name)

    params = {
        "ACL": "public-read",
        'Key': file_name
    }

    connection_kwargs = {
        "region_name": settings.S3DIRECT_REGION,
        "aws_access_key_id": settings.S3_ACCESS_KEY,
        "aws_secret_access_key": settings.S3_SECRET_KEY,
        "endpoint_url": settings.S3_ENDPOINT_URL,
        "config" : config
    }
    s3_obj = boto3.resource("s3", **connection_kwargs)
    s3_obj.Bucket(settings.S3_BUCKET).put_object(Body=document, **params)
    return file_name


def is_s3_object_exist(file_name):
    '''
    Verify if object is already uploaded on s3 bucket return True/False
    '''
    s3_obj = get_s3_client()
    filename = '%s/%s/%s' % (settings.S3_BUCKET_PATH, settings.S3_BUCKET_LOCAL_PATH, file_name)
    response = s3_obj.list_objects_v2(Bucket=settings.S3_BUCKET, Prefix=filename)

    for obj in response.get('Contents', []):
        if obj['Key'] == filename:
            return True

    filename = settings.S3_BUCKET_APTTUS_PDF_PATH.format(file_name)
    response = s3_obj.list_objects_v2(Bucket=settings.S3_BUCKET, Prefix=filename)

    for obj in response.get('Contents', []):
        if obj['Key'] == filename:
            return True
    return False


@retry
def remove_s3_object(file_name):
    '''
    Remove s3 objects and related files on s3 bucket
    '''
    s3_obj = get_s3_client()
    extracted_images_filename = settings.S3_BUCKET_EXTRACTED_IMAGES_PATH.format(file_name)

    objects_to_delete = s3_obj.list_objects(Bucket=settings.S3_BUCKET, Prefix=extracted_images_filename)
    delete_keys = [{'Key' : k} for k in [obj['Key'] for obj in objects_to_delete.get('Contents', [])]]

    delete_keys.append({'Key': '%s/%s/%s' % (settings.S3_BUCKET_PATH, settings.S3_BUCKET_LOCAL_PATH, file_name)})
    delete_keys.append({'Key': settings.S3_BUCKET_TESTING_SG_PATH.format(file_name)})
    delete_keys.append({'Key': settings.S3_BUCKET_TXT_VERSION_PATH.format(file_name)})
    delete_keys.append({'Key': settings.S3_BUCKET_CSV_VERSION_PATH.format(file_name)})
    delete_keys.append({'Key': settings.S3_BUCKET_SEARCHABLE_PDF_PATH.format(file_name)})
    delete_keys.append({'Key': settings.S3_BUCKET_OUTPUT_PATH.format(file_name)})
    delete_keys.append({'Key': settings.S3_BUCKET_APTTUS_PDF_PATH.format(file_name)})
    delete_keys.append({'Key': settings.S3_BUCKET_SEARCHABLE_APTTUS_PDF_PATH.format(file_name)})

    return s3_obj.delete_objects(Bucket=settings.S3_BUCKET, Delete={'Objects': delete_keys})


def download_s3_object(file_name):
    '''
    Download s3 object (Source Document File)
    '''
    filename = '%s/%s/%s' % (settings.S3_BUCKET_PATH, settings.S3_BUCKET_LOCAL_PATH, file_name)
    s3_obj = get_s3_client()
    try:
        return True, s3_obj.get_object(Bucket=settings.S3_BUCKET, Key=filename)
    except:
        try:
            return True, s3_obj.get_object(Bucket=settings.S3_BUCKET, Key=settings.S3_BUCKET_APTTUS_PDF_PATH.format(file_name))
        except:
            return False, {}


def download_searchable_s3_object(file_name):
    '''
    Download Searchable pdf file which containes images..
    '''
    s3_obj = get_s3_client()
    try:
        return True, s3_obj.get_object(Bucket=settings.S3_BUCKET, Key=settings.S3_BUCKET_SEARCHABLE_PDF_PATH.format(file_name))
    except:
        try:
            return True, s3_obj.get_object(Bucket=settings.S3_BUCKET, Key=settings.S3_BUCKET_APTTUS_PDF_PATH.format(file_name))
        except:
            return False, {}


def download_admin_files(filename, file_type):
    '''
    Download admin uploaded files
    '''
    s3_obj = get_s3_client()
    if "supplier_reference_file" == file_type:
        filename="%s/%s" % (settings.S3_BUCKET_CUSTOMER_FILES_PATH, filename)
    else:
        filename="%s/%s" % (settings.S3_BUCKET_DE_FILES_PATH, filename)

    try:
        return True, s3_obj.get_object(Bucket=settings.S3_BUCKET, Key=filename)
    except:
        return False, {}


def is_document_in_elastic_db(file):
    '''
    Verify document is exists on elastice db or not return True/False
    '''
    data = {"document_id.keyword":file}
    response = requests.post(url=DOCUMENT_DETAIL_URL + "?indexname="+settings.ELASTIC_SEARCH_INDEX_KEY, data=json.dumps(data))
    records = json.loads(response.content)
    return records["totalRecords"] > 0


def get_all_region_country(user_region, user_country):
    '''
    Get user assigned regions/countries
    '''
    all_region = Region.objects.all()
    for region in all_region:
        if region.display_name not in user_region:
            user_region.append(region.display_name)

    all_country = Country.objects.all()
    for country in all_country:
        if country.display_name not in user_country:
            user_country.append(country.display_name)
    return user_region, user_country


def get_region_countries(region, user_country):
    '''
    Get user assigned regions/countries
    '''
    try:
        slt_region = Region.objects.get(display_name__iexact=region)
        slt_countries = RegionCountry.objects.filter(region_id=slt_region.id)
        for country in slt_countries:
            if country.country.display_name not in user_country:
                user_country.append(country.country.display_name.strip())
    except (Region.DoesNotExist, RegionCountry.DoesNotExist):
        pass
    return user_country


def get_user_region_country(data, user_region, user_country):
    '''
    Get user assigned regions/countries
    user_region, user_country = get_all_region_country(user_region, user_country)
    '''
    if 'All' == data['region'].strip():
        user_region = ["*"]
        user_country = ["*"]
    else:
        if data['region'].strip() not in user_region:
            user_region.append(data["region"].strip())

        if 'All' == data['country'].strip():
            user_country = get_region_countries(data['region'], user_country)
        else:
            if data['country'].strip() not in user_country:
                user_country = user_country + [c.strip() for c in data["country"].split(",") if c != " "]
    return user_country, user_region

def get_user_suppliers(request):
    '''
    user_supplier = request.session.get("supplyGroup", "")
    access_supplier = ["*"] if 'All' in user_supplier else [string.strip() for string in user_supplier.split(',') if string != '']
    user_supplier = "9074967,9088277,9011705,9075447"
    '''
    supplier_groups = request.session.get("supplyGroup", "")
    if "All" in supplier_groups:
        return ["*"]
    else:
        suppliers = [string.strip() for string in supplier_groups.split(',') if string != '']
        suppliers_obj = SupplierGroup.objects.filter(supplier_group__in=suppliers).values('supplier_group_name')
        return [supplier["supplier_group_name"] for supplier in suppliers_obj]


def user_access_control(request):
    ''' 
    regionCountry = [{'region': 'APA', 'country': 'Bhutan,Bangladesh'}, {'region': 'CHI', 'country': 'All'},
    {'region': 'EUR', 'country': 'Belarus,Bulgaria'}]
    user_supplier = ",NEXWAVE,GURSAS,TITAN 4,"
    user_suppliers = get_user_suppliers(request)
    '''
    user_country = []
    user_region = []

    regionCountry = request.session.get("regionCountry", "")

    for data in regionCountry:
        user_country, user_region = get_user_region_country(data, user_region, user_country)

    user_suppliers = get_user_suppliers(request)

    request.data["access_region"] = user_region
    request.data["access_country"] = user_country
    request.data["access_supplier"] = user_suppliers
    return request


def documents_export_result(records):
    '''
    Document Listing : Modify Exported data..
    '''
    for rec in records:
        try:
            rec["import_datetime"] = datetime.strptime(rec["import_datetime"], '%Y-%m-%dT%H:%M:%S.%f').strftime('%d-%m-%Y %H:%M:%S')
        except Exception as e:
            rec["import_datetime"] = rec["import_datetime"]

        rec["zero_defect_target"] = rec["zero_defect"]["target"]
        rec["zero_defect_liquidated_damages_min"] = rec["zero_defect"]["liquidated_damages_min"]
        rec["zero_defect_liquidated_damages_max"] = rec["zero_defect"]["liquidated_damages_max"]
        rec["paru_target"] = rec["paru"]["target"]
        rec["paru_liquidated_damages_min"] = rec["paru"]["liquidated_damages_min"]
        rec["paru_liquidated_damages_max"] = rec["paru"]["liquidated_damages_max"]
        rec["seqi_target"] = rec["seqi"]["target"]
        rec["seqi_liquidated_damages_min"] = rec["seqi"]["liquidated_damages_min"]
        rec["seqi_liquidated_damages_max"] = rec["seqi"]["liquidated_damages_max"]
        rec["sar_target"] = rec["sar"]["target"]
        rec["sar_liquidated_damages_min"] = rec["sar"]["liquidated_damages_min"]
        rec["sar_liquidated_damages_max"] = rec["sar"]["liquidated_damages_max"]
        rec["stilt_target"] = rec["stilt"]["target"]
        rec["stilt_liquidated_damages_min"] = rec["stilt"]["liquidated_damages_min"]
        rec["stilt_liquidated_damages_max"] = rec["stilt"]["liquidated_damages_max"]
        rec["liquidated_damages_percent"] = rec["liquidated_damages_main_percent"]["liquidated_damages_percent"]
        rec["liquidated_damages_percent_min"] = rec["liquidated_damages_main_percent"]["liquidated_damages_percent_min"]
        rec["liquidated_damages_percent_max"] = rec["liquidated_damages_main_percent"]["liquidated_damages_percent_max"]
        rec["liquidated_damages_raw"] = rec["liquidated_damages_main_raw"]["liquidated_damages_raw"]
        rec["liquidated_damages_raw_min"] = rec["liquidated_damages_main_raw"]["liquidated_damages_raw_min"]
        rec["liquidated_damages_raw_max"] = rec["liquidated_damages_main_raw"]["liquidated_damages_raw_max"]
        try:
            rec["payment_term_days_1"] = "Not Found" if rec["payment_terms"][0]["payment_term_days"] == "-1" else rec["payment_terms"][0]["payment_term_days"]
            rec["payment_term_days_2"] = "Not Found" if rec["payment_terms"][1]["payment_term_days"] == "-1" else rec["payment_terms"][1]["payment_term_days"]
        except Exception as e:
            rec["payment_term_days_1"] = ''
            rec["payment_term_days_2"] = ''

    new_columns = {'filename': 'Filename',
                   'origin': 'Origin',
                   'import_datetime': 'Import Date',
                   'document_number': 'Document Number',
                   'document_type': 'Document Type',
                   'parent_document_number': 'Parent Document Number',
                   'region': 'Region',
                   'country': 'Country',
                   'project_name': 'Project Name',
                   '_legal_entity': ' Legal Entity',
                   'supplier_legal_entity': 'Supplier Legal Entity',
                   'supplier_group': 'Supplier Group',
                   'start_date': 'Start Date',
                   'end_date': 'End Date',
                   'signed': 'Signed',
                   'zero_defect_target': 'Zero Defect Target',
                   'zero_defect_liquidated_damages_min': 'Zero Defect LD Min', 
                   'zero_defect_liquidated_damages_max': 'Zero Defect LD Max',
                   'paru_target': 'PARU Target', 
                   'paru_liquidated_damages_min': 'PARU LD Min', 
                   'paru_liquidated_damages_max': 'PARU LDs Max',
                   'seqi_target': 'SeQi Target', 
                   'seqi_liquidated_damages_min': 'SeQi LD Min', 
                   'seqi_liquidated_damages_max': 'SeQi LD Max',
                   'sar_target': 'SAR Target', 
                   'sar_liquidated_damages_min': 'SAR LD Min', 
                   'sar_liquidated_damages_max': 'SAR LD Max',
                   'stilt_target': 'S-TILT Target', 
                   'stilt_liquidated_damages_min': 'S-TILT LD Min', 
                   'stilt_liquidated_damages_max': 'S-TILT LD Max',
                   'liquidated_damages_formula': 'Liquidated Damages Formula',
                   'liquidated_damages_percent': 'Liquidated Damages Percent',
                   'liquidated_damages_percent_min': 'LD Percent Min',
                   'liquidated_damages_percent_max': 'LD Percent Max',
                   'liquidated_damages_raw': 'Liquidated Damages Raw',
                   'liquidated_damages_raw_min': 'LD Raw Min',
                   'liquidated_damages_raw_max': 'LD Raw Max',
                   'payment_term_days_1': 'Payment Terms In Days - 1',
                   'payment_term_days_2': 'Payment Terms In Days - 2'
                   }

    column_size = [75,30,30,30,30,30,30,30,30,60,
                    60,30,30,60,20,20,20,20,20,20,
                    20,20,20,20,20,20,20,20,20,20,
                    40,40,20,20,40,20,20,25,25,40,
                    20,20,20,20,20,20,20,20,20,20,
                    20,20,20,20,20,20,20,20,20,20,
                    20,20,20,20,20,20,20,20,20,20]
    return records, new_columns, column_size, DOCUMENT_EXPORT_SHEET_NAME


def price_export_result(records):
    '''
    Price Listing : Modify Exported data..
    '''
    new_records = []
    for rec in records:
        nrec = {}
        nrec["filename"] = rec["filename"]
        nrec["document_number"] = rec["document_number"]
        nrec["document_type"] = rec["document_type"]
        nrec["country"] = rec["country"]
        nrec["project_name"] = rec["project_name"]
        nrec["supplier_legal_entity"] = rec["supplier_legal_entity"]
        nrec["supplier_group"] = rec["supplier_group"]

        if "pricing_table" in rec and len(rec["pricing_table"]) > 0:
            for dec in rec["pricing_table"]:
                pec = {}
                pec["price_material_number"] = dec["material_number"]
                pec["price_description"] = dec["description"]
                pec["price_unit_price"] = dec["unit_price"]
                pec["price_currency"] = dec["currency"]
                pec["price_quantity"] = dec["quantity"]
                pec["price_quantity_unit"] = dec["quantity_unit"]
                pec["price_multiple_price"] = dec["multiple_price_flag"]
                pec["price_page"] = dec["page"]

                stec = {**nrec, **pec}
                new_records.append(stec)
        else:
            nrec["price_material_number"] = ""
            nrec["price_description"] = ""
            nrec["price_unit_price"] = ""
            nrec["price_currency"] = ""
            nrec["price_quantity"] = ""
            nrec["price_quantity_unit"] = ""
            nrec["price_multiple_price"] = ""
            nrec["price_page"] = ""
            new_records.append(nrec)

    new_columns = {'filename': 'Filename',
                   'document_number': 'Document Number',
                   'document_type': 'Document Type',
                   'country': 'Country',
                   'project_name': 'Project Name',
                   'supplier_legal_entity': 'Supplier Legal Entity',
                   'supplier_group': 'Supplier Group',
                   'price_material_number': 'Material Number',
                   'price_description': 'Description',
                   'price_unit_price': 'Unit Price',
                   'price_currency': 'Currency',
                   'price_quantity': 'Quantity',
                   'price_quantity_unit': 'Quantity Unit',
                   'price_multiple_price': 'Multiple Price',
                   'price_page': 'Page'}

    column_size = [75,30,30,20,70,70,50,15,50,10,10,10,10,60,20,20,20,20,20,20,
                    60,30,30,60,20,20,20,20,20,20,60,30,30,60,20,20,20,20,20,20,
                    60,30,30,60,20,20,20,20,20,20,60,30,30,60,20,20,20,20,20,20,
                    60,30,30,60,20,20,20,20,20,20,60,30,30,60,20,20,20,20,20,20,]
    return new_records, new_columns, column_size, DOCUMENT_EXPORT_SHEET_NAME


def payment_terms_export_result(records):
    '''
    Payment Terms : Modify Exported data..
    extra_keys = {"actual_pt_days": [{"payment_term_days": "60"},{"payment_term_days": "90"}]}
    for key, value in enumerate(records):
        records[key] = {**value, **extra_keys}
    '''
    new_columns = {'filename': 'Filename',
                   'document_number': 'Document Number',
                   'document_type': 'Document Type',
                   'supplier_group': 'Supplier Group',
                   'supplier_legal_entity': 'Supplier Legal Entity',
                   'country': 'Country'}

    column_size = [75,25,25,45,45,20,20,20,20,20,20]

    for key, rec in enumerate(records):
        for pt_key, pt_value in enumerate(rec["payment_terms"]):
            new_column_key_value = pt_key + 1
            new_column_key = "{0}_{1}".format("paryment_terms", new_column_key_value)
            new_column_value = "{0}_{1}".format("Payment Terms in Days ", new_column_key_value)
            new_columns = {**new_columns, **{new_column_key : new_column_value}}

            column_size.append(20)

            records[key][new_column_key] = "Not Found" if pt_value["payment_term_days"]  == '-1' else pt_value["payment_term_days"]

        for ptd_key, ptd_value in enumerate(rec["actual_pt_days"]):
            new_column_key_value_d = ptd_key + 1
            new_column_key_d = "{0}_{1}".format("actual_pt_days", new_column_key_value_d)
            new_column_value_d = "{0}_{1}".format("TPD PT Days ", new_column_key_value_d)
            new_columns = {**new_columns, **{new_column_key_d : new_column_value_d}}

            column_size.append(20)

            records[key][new_column_key_d] = "Not Found" if ptd_value["payment_term_days"]  == "-1" else ptd_value["payment_term_days"]

    return records, new_columns, column_size, PAYMENT_TERM_EXPORT_SHEET_NAME


def quality_kpis_export_result(records):
    '''
    QualityKpi's : Modify Exported data..
    '''
    new_columns = {'filename': 'Filename',
                   'document_number': 'Document Number',
                   'document_type': 'Document Type',
                   'supplier_group': 'Supplier Group',
                   'country': 'Country',
                   'liquidated_damages_formula': 'Liquidated Damages Formula',
                   'liquidated_damages_percent': 'Liquidated Damages Percent',
                   'liquidated_damages_percent_min': 'LD Percent Min',
                   'liquidated_damages_percent_max': 'LD Percent Max',
                   'liquidated_damages_raw': 'Liquidated Damages Raw',
                   'liquidated_damages_raw_min': 'LD Raw Min',
                   'liquidated_damages_raw_max': 'LD Raw Max',
                   'zero_defect_target': 'Zero Defect Target',
                   'zero_defect_liquidated_damages_min': 'Zero Defect LD Min', 
                   'zero_defect_liquidated_damages_max': 'Zero Defect LD Max',
                   'paru_target': 'PARU Target', 
                   'paru_liquidated_damages_min': 'PARU LD Min', 
                   'paru_liquidated_damages_max': 'PARU LDs Max',
                   'sar_target': 'SAR Target', 
                   'sar_liquidated_damages_min': 'SAR LD Min', 
                   'sar_liquidated_damages_max': 'SAR LD Max'}

    column_size = [75,30,30,30,30,60,60,60,60,60,
                    60,60,20,20,20,20,20,20,20,20,
                    20,20,20,20,20,20,20,20,20,20,
                    40,40,20,20,40,20,20,25,25,40,
                    40,40,40,40,40,40,40,20,20,20,
                    20,20,20,20,20,20,20,20,20,20,
                    20,20,20,20,20,20,20,20,20,20,20,20,20]

    for key, rec in enumerate(records):
        records[key]["liquidated_damages_percent"] = rec["liquidated_damages_main_percent"]["liquidated_damages_percent"]
        records[key]["liquidated_damages_percent_min"] = rec["liquidated_damages_main_percent"]["liquidated_damages_percent_min"]
        records[key]["liquidated_damages_percent_max"] = rec["liquidated_damages_main_percent"]["liquidated_damages_percent_max"]
        records[key]["liquidated_damages_raw"] = rec["liquidated_damages_main_raw"]["liquidated_damages_raw"]
        records[key]["liquidated_damages_raw_min"] = rec["liquidated_damages_main_raw"]["liquidated_damages_raw_min"]
        records[key]["liquidated_damages_raw_max"] = rec["liquidated_damages_main_raw"]["liquidated_damages_raw_max"]
        records[key]["zero_defect_target"] = rec["zero_defect"]["target"]
        records[key]["zero_defect_liquidated_damages_min"] = rec["zero_defect"]["liquidated_damages_min"]
        records[key]["zero_defect_liquidated_damages_max"] = rec["zero_defect"]["liquidated_damages_max"]
        records[key]["paru_target"] = rec["paru"]["target"]
        records[key]["paru_liquidated_damages_min"] = rec["paru"]["liquidated_damages_min"]
        records[key]["paru_liquidated_damages_max"] = rec["paru"]["liquidated_damages_max"]
        records[key]["sar_target"] = rec["sar"]["target"]
        records[key]["sar_liquidated_damages_min"] = rec["sar"]["liquidated_damages_min"]
        records[key]["sar_liquidated_damages_max"] = rec["sar"]["liquidated_damages_max"]
        if 'actual_kpi' in rec:
            for pt_key, pt_value in enumerate(rec["actual_kpi"]):
                new_column_key_value = pt_key + 1

                new_column_key = "{0}_{1}".format("actual_kpis_project", new_column_key_value)
                new_column_value = "{0}_{1}".format("Project ", new_column_key_value)
                new_columns = {**new_columns, **{new_column_key : new_column_value}}
                column_size.append(20)
                records[key][new_column_key] = "Not Found" if pt_value["project"]  == '-1' else pt_value["project"]

                new_column_key = "{0}_{1}".format("actual_kpis_actual_zd", new_column_key_value)
                new_column_value = "{0}_{1}".format("Actual ZD ",new_column_key_value)
                new_columns = {**new_columns, **{new_column_key : new_column_value}}
                column_size.append(20)
                records[key][new_column_key] = "Not Found" if pt_value["actual_zd"]  == '-1' else pt_value["actual_zd"]

                new_column_key = "{0}_{1}".format("actual_kpis_actual_sar", new_column_key_value)
                new_column_value = "{0}_{1}".format("Actual SAR ",new_column_key_value)
                new_columns = {**new_columns, **{new_column_key : new_column_value}}
                column_size.append(20)
                records[key][new_column_key] = "Not Found" if pt_value["actual_sar"]  == '-1' else pt_value["actual_sar"]

                new_column_key = "{0}_{1}".format("actual_kpis_actual_paru", new_column_key_value)
                new_column_value = "{0}_{1}".format("Actual PARU ",new_column_key_value)
                new_columns = {**new_columns, **{new_column_key : new_column_value}}
                column_size.append(20)
                records[key][new_column_key] = "Not Found" if pt_value["actual_paru"]  == '-1' else pt_value["actual_paru"]

    return records, new_columns, column_size, QUALITY_KPIS_EXPORT_SHEET_NAME


def get_documents_exported_data(records, requested_data, export_payment_terms):
    if 'contains_payment_terms' in requested_data and export_payment_terms is True:
        records, new_columns, column_size, sheetname = payment_terms_export_result(records)
    elif 'contains_quality_kpi' in requested_data:
        records, new_columns, column_size, sheetname = quality_kpis_export_result(records)
    elif 'contains_prices' in requested_data:
        records, new_columns, column_size, sheetname = price_export_result(records)
    else:
        records, new_columns, column_size, sheetname = documents_export_result(records)
    return records, new_columns, column_size, sheetname


def documents_export(records, requested_data, export_payment_terms):
    records = records.data["data"]
    records, new_columns, column_size, sheetname = get_documents_exported_data(records, requested_data, export_payment_terms)

    df = pd.DataFrame(records)
    df.rename(columns=new_columns, inplace=True)

    excel_file = IO()
    xlwriter = pd.ExcelWriter(excel_file, engine='xlsxwriter', datetime_format='dd-MM-yyyy hh:mm:ssa', date_format='dd-MM-yyyy')
    columns_order = [value[1] for _, value in enumerate(new_columns.items())]

    df[columns_order].to_excel(xlwriter, sheetname, index=False)
    worksheet = xlwriter.sheets[sheetname]

    for idx, _ in enumerate(df):
        worksheet.set_column(idx, idx, column_size[idx])

    xlwriter.save()
    xlwriter.close()
    excel_file.seek(0)

    response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=' + sheetname + '.xlsx'
    return response
