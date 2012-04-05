#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ================================= #
# Python script                     #
# Author: Alexei Panov              #
# e-mail: elemc AT atisserv DOT ru  #
# ================================= #

HOST="localhost"
PORT=5432
USER="koji"
PASSWORD="3510"
DBNAME="koji"

import psycopg2
from packageporter.packages.models import Packages, BuildedPackages
from packageporter.owners.models import Owners
from packageporter.repos.models import Repos, RepoTypes
from packageporter.logs.models import UpdateLog
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
import datetime
import subprocess

class UpdateFromKoji(object):
    def __init__(self, user = ''):
        conn_str = "host=%s port=%i dbname=%s user=%s password=%s" % (
            HOST, PORT, DBNAME, USER, PASSWORD)
        try:
            self.koji_conn = psycopg2.connect(conn_str)
        except:
            self.koji_conn = None

        self.user = user

        if self.koji_conn is not None:
            self.update_repos()
            self.update_rt()
            self.update_owners()

    def __del__(self):
        if self.koji_conn is not None:
            self.koji_conn.close()

    def update_repos(self):
        try:
            sys_repo = Repos.objects.get(pk=0)
        except:
            new_sys_repo = Repos(repo_id=0,
                                 repo_name = "unknown")
            new_sys_repo.save()

    def update_rt(self):
        # Releases
        try:
            rt_t = RepoTypes.objects.get(pk=0)
        except:
            new_rt_t = RepoTypes(rt_id=0, rt_name="releases")
            new_rt_t.save()

        # Testing
        try:
            rt_t = RepoTypes.objects.get(pk=1)
        except:
            new_rt_t = RepoTypes(rt_id=1, rt_name="updates-testing")
            new_rt_t.save()
            
        # Updates
        try:
            rt_u = RepoTypes.objects.get(pk=2)
        except:
            new_rt_u = RepoTypes(rt_id=2, rt_name="updates")
            new_rt_u.save()

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

    def __system_update_packages_from_cursor(self, c):
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
            
    def update_packages(self):
        if self.koji_conn is None:
            return
        c = self.koji_conn.cursor()
        c.execute("select * from package")
        self.__system_update_packages_from_cursor(c)
        c.close()

    def update_package(self, pkg_id):
        if self.koji_conn is None:
            return
        c = self.koji_conn.cursor()
        c.execute("select * from package where id='%s'" % pkg_id)
        if c.rowcount == 0:
            return
        self.__system_update_packages_from_cursor(c)
        c.close()
        
    def get_package(self, pkg_id):
        try:
            pkg = Packages.objects.get(pk=pkg_id)
        except:
            self.update_package(pkg_id)
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

        ul = UpdateLog.objects.all().filter(is_last=True)
        if len(ul) == 0:
            c.execute("select * from build where state='1'")
        else:
            c.execute("select * from build where (state='1' and id>'%s')" % ul[0].last_build_id)

        last_build_id = 0

        for record in c:
            _id, pkg_id, version, release, epoch, create_event, completion_time, state, task_id, owner_id = record
            try:
                bp = BuildedPackages.objects.get(pk=_id)
            except:
                package = self.get_package(pkg_id)
                owner   = self.get_owner(owner_id)
                tag_name= self._get_tag_for_build(_id)
                if (package is not None) and (owner is not None):
                    new_bp = BuildedPackages(build_id=_id, 
                                             build_pkg=package, 
                                             version=version,
                                             release=release,
                                             epoch=epoch,
                                             completion_time=completion_time,
                                             task_id=task_id,
                                             owner=owner,
                                             pushed=False,
                                             tag_name=tag_name)
                    new_bp.save()
                    new_bp.oper_build()
                    if last_build_id < _id:
                        last_build_id = _id
        c.close()
        if last_build_id != 0:
            for one_ul in ul:
                one_ul.is_last = False
                one_ul.save()
            new_ul = UpdateLog(is_last=True, 
                               update_timestamp = datetime.datetime.now(),
                               last_build_id = last_build_id,
                               user = self.user)
            new_ul.save()

    def _get_tag_for_build(self, build_id):
        tag_name = ""
        c = self.koji_conn.cursor()
        c.execute("select tag_id from tag_listing where (build_id='%s')" % build_id)
        for record in c:
            tag_id = record[0]
            c_tag = self.koji_conn.cursor()
            c_tag.execute("select name from tag where (id='%s')" % tag_id)
            for r_tag in c_tag:
                tag_name = r_tag[0]
        return tag_name

class PushPackagesToRepo(object):
    dists = {"dist-rfr": "rf",
             "dist-el": 'el'
             }
    
    def __init__(self, build_list = []):
        self.build_list = build_list

    def cancel_package(self, build_id, user, reason):
        try:
            bpkg = BuildedPackages.objects.get(pk=build_id)
        except:
            print("Warning! Build ID %s not found!" % build_id)
            return
        bpkg.pushed = True
        bpkg.push_user = user
        bpkg.save()
        bpkg.remove_old_operations()
        bpkg.oper_block(user, reason)

    def cancel_packages(self):
        if len(self.build_list) == 0:
            return;
        for build_id, build_repo, user, reason in self.build_list:
            self.cancel_package(build_id, user, reason)

    def _dist_and_ver_from_tag(self, tag):
        dist = ""
        ver = ""
        
        for prefix in self.dists.keys():
            begin = tag.find(prefix)
            if begin >= 0:
                dist = self.dists[prefix]
                
                # version
                ver_begin = begin + len(prefix)
                ver_part = tag[ver_begin:]
                if 'rawhide' in ver_part:
                    ver = 'rawhide'
                elif 'devel' in ver_part:
                    ver = 'pre'
                else:
                    ver = ver_part
                break
        return (dist,ver)

    def _generate_call_list(self, build, build_repo):
        dist, ver  = self._dist_and_ver_from_tag(build.tag_name)
        l = []
        l.append('echo')
        l.append('--id %s' % build.build_id)
        l.append('--ver %s' % ver)
        l.append('--repo %s' % build.build_pkg.pkg_repo)
        l.append('--branch %s' % build_repo.rt_name)
        l.append('--dist %s' % dist)
        return l

    def push_to_repo(self):
        if len(self.build_list) == 0:
            return;

        all_stdout = []

        for build_id, build_repo, user,reason in self.build_list:
            if build_repo is None:
                print("Warning! Repo is not defined. Skip this build (%s).", build_id)
                continue
            try:
                bpkg = BuildedPackages.objects.get(pk=build_id)
            except:
                print("Warning! Build ID %s not found!" % build_id)
                continue

            # cmd to push
            cmd = self._generate_call_list(bpkg, build_repo)
            buf = ""
            return_result = subprocess.call(str(' ').join(cmd),shell=True)#, stdout=buf, stderr=buf)
            all_stdout.append(buf)
            if return_result != 0:
                continue
            
            if build_repo.rt_id == 1:
                bpkg.remove_old_operations()
                bpkg.oper_pre_push(user, build_repo)
            else:
                bpkg.remove_old_operations()
                bpkg.oper_push(user, build_repo)

        return all_stdout


class ShareOperations(object):
    @staticmethod
    def get_owner_by_name(owner_name):
        try:
            owner = Owners.objects.get(owner_name=owner_name)
        except:
            return None

        return owner

if __name__ == '__main__':
    ufk = UpdateFromKoji()
    ufk.update_owners()
