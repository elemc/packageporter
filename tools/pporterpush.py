#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ================================= #
# Python script                     #
# Author: Alexei Panov              #
# e-mail: me AT elemc DOT name      #
# ================================= #

import os
import sys
from optparse import OptionParser
import logging
import subprocess
import tempfile
import shutil

DBHOST          = "localhost"
DBPORT          = 5432
DBUSER          = "koji"
DBPASSWORD      = ""
DBNAME          = "pkgporter"

# Scripts
SCRIPT_PUSH     = "/home/pushrepo/bin/koji-pp"
SCRIPT_CHK_IDLE = "rsync -a knight.yandex.net::{{repo}}/.idle"

try:
    import psycopg2
except:
    print("Please install psycopg2 and rerun application")
    raise

parser = OptionParser()
parser.add_option("-l", "--log-file", action="store", type="string", dest="logfilename", default="")
parser.add_option("-w", "--log-level", action="store", type="string", dest="loglevel", default="DEBUG")
parser.add_option("-o", "--lock-file", action="store", type="string", dest="lockfilename", default=".pporterd")

external_dists = ['rf', 'el']

class PPorterException(Exception):
    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)
class PPorterSQLException(PPorterException):
    def __init__(self, sqlerr):
        PPorterException.__init__(self, sqlerr.pgerror)
        self.pgcode = sqlerr.pgcode
        self.pgerror = sqlerr.pgerror
    def __str__(self):
        return "[%s] %s" % (self.pgcode, self.pgerror)

class PushToRepo(object):
    def __init__(self, log_filename=None, log_level="DEBUG", lock_file=".pporter"):
        self.logger = self._init_logger(log_filename, log_level)
        self.lock_filename = lock_file

        try:
            self.logger.debug("Try connect to SQL server")
            self.pp_conn = self._init_pgsql()
        except PPorterSQLException, e:
            self.logger.error("SQL %s" % e)
            self.pp_conn = None

        self.temp_dirs = []

    def check_external_idle(self, repo):
        self.logger.debug("Try check .idle file present for '%s'" % repo)
        idle_cmd = SCRIPT_CHK_IDLE.replace('{{repo}}', repo)
        result = self.run_cmd(0, idle_cmd)
        if result == 0:
            return True
        return False

    def _dot_push_file(self, name):
        self.logger.debug("Try create temporary directory")
        temp_dir = tempfile.mkdtemp('pporter')
        self.logger.debug("Temporary directory created '%s'" % temp_dir)
        self.temp_dirs.append(temp_dir)
        filename = os.path.join(temp_dir, name)
        f = open(filename, 'w')
        f.close()
        return filename

    def lock_file_create(self):
        try:
            lock = open(self.lock_filename, 'w')
        except IOError, e:
            self.logger.error(e)
            raise PPorterException(e)

        lock.write("%s" % os.getpid())
        lock.close()

    def another_copy(self):
        if not os.path.exists(self.lock_filename):
            return None

        try:
            lock = open(self.lock_filename, 'r')
        except IOError, e:
            self.logger.debug("Error open file %s" % self.lock_filename)
            return ""

        pid = lock.read()
        return pid

    def lock_file_remove(self):
        self.logger.debug("Try to remove lock file")
        if os.path.exists(self.lock_filename):
            try:
                os.remove(self.lock_filename)
            except IOError, e:
                self.logger.error(e)
                raise PPorterException(e)

    def run_cmd(self, _id, cmd):
        self.logger.debug("Try to start command %s" % cmd)

        fc, fn = tempfile.mkstemp("pporter", "%s" % _id)
        buf = os.fdopen(fc, "rw")
        res = subprocess.call( cmd, stdout = buf, stderr = buf, shell = True )
        buf.seek(0)
        self.logger.debug(buf.read())
        buf.close()
        return res

    def _create_cursor(self, query):
        try:
            self.logger.debug("Create cursor for query '%s'" % query)
            cursor = self.pp_conn.cursor()
            cursor.execute(query)
        except psycopg2.InternalError, err:
            raise PPorterSQLException(err)
        except psycopg2.ProgrammingError, err:
            raise PPorterSQLException(err)

        return cursor

    def skip_push(self, push_id):
        cursor = self._create_cursor("update packages_push set done='true' where id='%s'" % push_id)
        self.logger.debug("Query status message: '%s'" % cursor.statusmessage)
        cursor.close()

    def _close_and_remove(self, iserr = False):
        if self.pp_conn is not None:
            self.pp_conn.commit()
            self.pp_conn.close()

        self.lock_file_remove()
        for dir in self.temp_dirs:
            try:
                shutil.rmtree(dir)
            except:
                self.logger.warning("Remove directory '%s' failed" % dir) 

    def _do_dist(self, dist, cmds):
        if not self.check_external_idle(dist):
            return

        # .startpush
        self.logger.debug("Try create and rsync .startpush")
        dot_start_filename = self._dot_push_file('.startpush')
        result_dot_start = self.run_cmd(0, "rsync -a %s knight.yandex.net::%s/" % (dot_start_filename, dist))
        if result_dot_start != 0:
            self.logger.error("Error while rsync .startpush, skip this dist")
            return

        for pre_cmd in cmds:
            build_id = pre_cmd['id']
            push_id = pre_cmd['push_id']
            cmd = pre_cmd['cmd']
            if self.run_cmd(build_id, cmd) == 0:
                self.logger.debug("Try update sql table")
                try:
                    self.skip_push(push_id)
                except PPorterSQLException, e:
                    self.logger.error(e)
                    cursor.close()
                    self._close_and_remove()
                    continue

        # .endpush
        self.logger.debug("Try create and rsync .endpush")
        dot_end_filename = self._dot_push_file('.endpush')
        result_dot_end = self.run_cmd(0, "rsync -a %s knight.yandex.net::%s/" % (dot_end_filename, dist))
        if result_dot_end != 0:
            self.logger.error("Error while rsync .endpush")

    def push(self):
        self.logger.debug("Check another copy of application")

        ac = self.another_copy()
        if ac is None:
            try:
                self.lock_file_create()
            except PPorterException:
                return
        else:
            if len(ac) == 0:
                self.logger.warning("Another copy of program present. PID unknown")
            else:
                self.logger.warning("Another copy of program present. PID=%s" % ac)

            return

        try:
            cursor = self._create_cursor("select id, build_id, ver, repo, branch, dist from packages_push where done<>'TRUE'")
        except PPorterSQLException, e:
            self.logger.error(e)
            self._close_and_remove()
            return
        
        if cursor.rowcount > 0:
            self.logger.debug("Found %s records" % cursor.rowcount)
            cmd_list_per_dist = {}
            for d in external_dists:
                cmd_list_per_dist[d] = []

            # pre compose
            for record in cursor:
                push_id, build_id, ver, repo, branch, dist = record

                l = []
                l.append(SCRIPT_PUSH)
                l.append('--id %s' % build_id)
                l.append('--ver %s' % ver)
                l.append('--repo %s' % repo)
                l.append('--branch %s' % branch)
                l.append('--dist %s' % dist)

                cmd = {}
                cmd['id'] = build_id
                cmd['push_id'] = push_id
                cmd['cmd'] = str(' ').join(l)
                
                cmd_list_per_dist[dist].append(cmd)

            # run cmds
            for dist_key in cmd_list_per_dist.keys():
                self._do_dist(dist_key, cmd_list_per_dist[dist_key])
                
        else:
            self.logger.debug("Record list is empty, not enough packages to push")
            
        cursor.close()
        self._close_and_remove()

    def _init_logger(self, log_filename = None, loglevel = "DEBUG"):
        logger = logging.getLogger("pporterd")
        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            numeric_level = logging.DEBUG

        # handlers
        if log_filename is not None:
            handler = logging.FileHandler(log_filename)
        else:
            handler = logging.StreamHandler()

        logger.setLevel(numeric_level)
        handler.setLevel(numeric_level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)

        return logger

    def _init_pgsql(self):
        conn_str = "host=%s port=%i dbname=%s user=%s password=%s" % (
            DBHOST, DBPORT, DBNAME, DBUSER, DBPASSWORD)

        try:
            self.logger.debug("Try connect to pgsql://%s:%s@%s:%s/%s" % (DBUSER, DBPASSWORD, DBHOST, DBPORT, DBNAME))
            pp_conn = psycopg2.connect(conn_str)
        except psycopg2.Error, sqlerr:
            pp_conn = None
            raise PPorterSQLException(sqlerr)

        return pp_conn

if __name__ == '__main__':
    (options, args) = parser.parse_args(sys.argv)
    
    log_filename = options.logfilename if len(options.logfilename) > 0 else None
    log_level = options.loglevel
    lock_filename = options.lockfilename

    p = PushToRepo(log_filename, log_level, lock_filename)
    p.push()
    os._exit(0)
