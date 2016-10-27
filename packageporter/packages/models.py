from django.db import models
from packageporter.repos.models import Repos, RepoTypes
from packageporter.owners.models import Owners

import datetime

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
    wait_to_time        = models.BooleanField(default = False)
    push_user           = models.TextField(null=True)
    push_time           = models.DateTimeField(null=True)
    push_repo_type      = models.ForeignKey(RepoTypes, null=True)
    is_blocked_to_push  = models.BooleanField(default = False)
    tag_name            = models.TextField(null=False)

    class Meta:
        permissions     = (
            ('can_push_all_packages', 'Can push packages from all users'),
            ('can_push_to_updates_directly', 'Can push packages to updates repo directly'),
            )

    def __unicode__(self):
        return "%i - %s" % (self.build_id, self.build_pkg.pkg_name)

    def full_build_package_name(self):
        if self.epoch is None:
            return "%s-%s-%s" % (self.build_pkg.pkg_name, self.version, self.release)
        else:
            return "%i:%s-%s-%s" % (self.epoch, self.build_pkg.pkg_name, self.version, self.release)

    def oper_build(self, user="auto"):
        bo = BuildOperations(build=self, 
                             operation_time=datetime.datetime.now(),
                             operation_user=user,
                             operation_type=0,
                             operation_description="added automaticaly from koji")
        bo.save()

    def oper_block(self, user, reason):
        self.is_blocked_to_push = True
        self.pushed             = True
        self.wait_to_push       = False
        self.save()
        bo = BuildOperations(build=self, 
                             operation_time=datetime.datetime.now(),
                             operation_user=user,
                             operation_type=3,
                             operation_description=reason)
        bo.save()

    def oper_pre_push(self, user, repo_type):
        self.pushed             = True
        self.wait_to_time       = True
        self.push_user          = user
        self.push_repo_type     = repo_type
        self.save()
        
        bo = BuildOperations(build=self, 
                             operation_time=datetime.datetime.now(),
                             operation_user=user,
                             operation_type=1,
                             operation_description="Pre-push to %s" % repo_type.rt_name)
        bo.save()

    def oper_push(self, user, repo_type):
        self.pushed             = True
        self.wait_to_time       = False
        self.push_user          = user
        self.push_repo_type     = repo_type
        self.save()
        bo = BuildOperations(build=self,
                             operation_time=datetime.datetime.now(),
                             operation_user=user,
                             operation_type=2,
                             operation_description="Finally push to %s" % repo_type.rt_name)
        bo.save()

    def remove_old_operations(self):
        # remove old operations
        try:
            list_bo = BuildOperations.objects.filter(build=self)
        except:
            print("Oops, operations is not found!")

        list_bo.delete()

class BuildOperations(models.Model):
    build                       = models.ForeignKey(BuildedPackages)
    operation_time              = models.DateTimeField()
    operation_user              = models.CharField(max_length=50)
    operation_type              = models.IntegerField() # as example: 0 - builded, 1 - pre-push , 2 - push, 3 - block...
    operation_description       = models.TextField() # this field is "to <repo>" for push and pre-push, "<reason>" for block

    def print_type(self):
        if self.operation_type == 0:
            return "Build"
        elif self.operation_type == 1:
            return "Pre-push"
        elif self.operation_type == 2:
            return "Push"
        elif self.operation_type == 3:
            return "Block"

        return "Unknown"

class Push(models.Model):
    build       = models.ForeignKey(BuildedPackages)
    ver         = models.TextField(null = False)
    repo        = models.TextField(null = False)
    branch      = models.TextField(null = False)
    dist        = models.TextField(null = False)
    done        = models.BooleanField(default = False)
