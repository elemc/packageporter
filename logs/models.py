from django.db import models


class UpdateLog(models.Model):
    is_last             = models.BooleanField(default=False)
    update_timestamp    = models.DateTimeField(null=False)
    last_build_id       = models.IntegerField(null=False)
    user                = models.CharField(max_length=100, null=False)
