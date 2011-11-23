#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ================================= #
# Python script                     #
# Author: Alexei Panov              #
# e-mail: elemc AT atisserv DOT ru  #
# ================================= #

HOST="localhost"
PORT=5432
USER="alex"
PASSWORD="3510"
DBNAME="koji"

import psycopg2
from packageporter.packages.models import Packages, BuildedPackages
from packageporter.owners.models import Owners
from packageporter.repos.models import Repos

class UpdateFromKoji(object):
    def __init__(self):
        conn_str = "host=%s port=%i dbname=%s user=%s password=%s" % (
            HOST, PORT, DBNAME, USER, PASSWORD)
        try:
            self.koji_conn = psycopg2.connect(conn_str)
        except:
            self.koji_conn = None

    def __del__(self):
        if self.koji_conn is not None:
            self.koji_conn.close()

    def update_repos(self):
        try:
            sys_repo = Repos.objects.get(pk=0)
        except:
            new_sys_repo = Repos(repo_id=0,
                                 repo_name = "Unknown")
            new_sys_repo.save()

    def update_owners(self):
        if self.koji_conn is None:
            return
        c = self.koji_conn.cursor()
        c.execute("select * from users where usertype='0'")

        for record in c:
            _id, name, pwd, status, usertype, krb = record
            try:
                owner = Owners.objects.get(pk=_id)
            except:
                new_owner = Owners(owner_id=_id, owner_name=name)
                new_owner.save()
        c.close()
            
    def update_packages(self):
        if self.koji_conn is None:
            return
        c = self.koji_conn.cursor()
        c.execute("select * from package")
        for record in c:
            _id, name = record
            
            try:
                pkg = Packages.objects.get(pk=_id)
            except:
                ctp = self.koji_conn.cursor()
                ctp.execute("select owner,tag_id from tag_packages where package_id=%s" % _id)
                owner = None
                last_tag_id = 0
                for record_ctp in ctp:
                    owner_id, tag_id = record_ctp
                    if tag_id > last_tag_id:
                        owner = owner_id
                owner_obj = self.get_owner(owner)
                if owner_obj is None:
                    ctp.close()
                    c.close()
                    return
                
                try:
                    null_repo = Repos.objects.get(pk=0)
                except:
                    self.update_repos()
                    null_repo = Repos.objects.get(pk=0)
                new_pkg = Packages(pkg_id = _id,
                                   pkg_name = name,
                                   pkg_owner = owner_obj,
                                   pkg_repo = null_repo)
                new_pkg.save()
                ctp.close()
        c.close()


    def get_package(self, pkg_id):
        try:
            pkg = Packages.objects.get(pk=pkg_id)
        except:
            self.update_packages()
            try:
                pkg = Packages.objects.get(pk=pkg_id)
            except:
                return None
        return pkg

    def get_owner(self, owner_id):
        try:
            owner = Owners.objects.get(pk=owner_id)
        except:
            self.update_owners()
            try:
                owner = Owners.objects.get(pk=owner_id)
            except:
                return None
        return owner

    def update_builds(self):
        if self.koji_conn is None:
            return
        c = self.koji_conn.cursor()
        # state is
        # 1 - done
        # 2 - deleted
        # 3 - failed
        # 4 - cancelled
        # select only success builds state=1
        c.execute("select * from build where state='1'") 

        for record in c:
            _id, pkg_id, version, release, epoch, create_event, completion_time, state, task_id, owner_id = record
            try:
                bp = BuildedPackages.objects.get(pk=_id)
            except:
                package = self.get_package(pkg_id)
                owner   = self.get_owner(owner_id)
                if (package is not None) and (owner is not None):
                    new_bp = BuildedPackages(build_id=_id, 
                                             build_pkg=package, 
                                             version=version,
                                             release=release,
                                             epoch=epoch,
                                             completion_time=completion_time,
                                             task_id=task_id,
                                             owner=owner,
                                             pushed=False)
                    new_bp.save()
        c.close()

                                             

if __name__ == '__main__':
    ufk = UpdateFromKoji()
    ufk.update_owners()
