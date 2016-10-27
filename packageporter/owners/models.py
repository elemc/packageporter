from django.db import models

class Owners(models.Model):
    owner_id    = models.AutoField(primary_key = True)
    owner_name  = models.TextField(null = False, unique = True)
    def __unicode__(self):
        return self.owner_name
