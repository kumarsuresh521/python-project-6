from django.db import models
from route.core.helper import TimestampModel


class Contract(TimestampModel):
    UPLOADED = 1
    PROCESSING = 2
    PROCESSED = 3
    SUCCESS=4
    FAILED=5

    DOCUMENT_STATUS = (
        (UPLOADED, 'Uploaded'),
        (PROCESSING, 'Processing'),
        (PROCESSED, 'Processed'),
        (SUCCESS, 'Success'),
        (FAILED, 'Failed')
    )

    document_file_name = models.CharField(max_length=500)
    document_path = models.CharField(max_length=500)
    request_id = models.CharField(max_length=100)
    contractId = models.CharField(max_length=100, null=True, blank=True)
    status = models.SmallIntegerField(choices=DOCUMENT_STATUS, default=UPLOADED)
    imported_by = models.CharField(max_length=100)

    def __str__(self):
        return self.document_file_name
