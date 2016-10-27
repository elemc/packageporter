from django.db import models

class RepoTypes(models.Model):
    rt_id       = models.AutoField(primary_key = True)
    rt_name     = models.TextField(null = False, unique = True)
    def __unicode__(self):
        return self.rt_name

class Repos(models.Model):
    repo_id     = models.AutoField(primary_key = True)
    repo_name   = models.TextField(null = False, unique = True)

    def __unicode__(self):
        return self.repo_name
