from django.db import models
from packageporter.repos.models import Repos, RepoTypes
from packageporter.owners.models import Owners

class Packages(models.Model):
    pkg_id      = models.AutoField(primary_key = True)
    pkg_name    = models.TextField(null = False, unique = True)
    pkg_repo    = models.ForeignKey(Repos, null=True)
    pkg_owner   = models.ForeignKey(Owners)
    def __unicode__(self):
        return self.pkg_name

class BuildedPackages(models.Model):
    build_id            = models.AutoField(primary_key = True)
    build_pkg           = models.ForeignKey(Packages)
    version             = models.TextField(null = False)
    release             = models.TextField(null = False)
    epoch               = models.IntegerField(null = True)
    completion_time     = models.DateTimeField(null = False)
    task_id             = models.IntegerField()
    owner               = models.ForeignKey(Owners)
    pushed              = models.BooleanField(default = False)
    push_user           = models.TextField(null=True)
    push_time           = models.DateTimeField(null=True)
    push_repo_type      = models.ForeignKey(RepoTypes, null=True)

    def __unicode__(self):
        return "%i - %s" % (self.build_id, self.build_pkg.pkg_name)

    def full_build_package_name(self):
        if self.epoch is None:
            return "%s-%s-%s" % (self.build_pkg.pkg_name, self.version, self.release)
        else:
            return "%i:%s-%s-%s" % (self.epoch, self.build_pkg.pkg_name, self.version, self.release)
