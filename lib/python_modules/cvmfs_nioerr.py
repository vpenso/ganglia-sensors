#*
#* Author: Raffaele Grosso
#*
#* This program is free software: you can redistribute it and/or modify
#* it under the terms of the GNU General Public License as published by
#* the Free Software Foundation, either version 3 of the License, or
#* (at your option) any later version.
#*
#* This program is distributed in the hope that it will be useful,
#* but WITHOUT ANY WARRANTY; without even the implied warranty of
#* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#* GNU General Public License for more details.
#*
#* You should have received a copy of the GNU General Public License
#* along with this program.  If not, see <http://www.gnu.org/licenses/>.
#*****************************************************************************/

import subprocess
import re
import os

descriptors = list()

def attrqg(repository):
    '''Return the output of attr -qg nioerr repository, which is the
    total number of I/O errors encoutered since mounting.
    If a prior findmnt or cvmfs_config probe check fails, then return
    a negative value'''

    # remove the prefix and substitute underscore
    repository = repository.replace('cvmfs_nioerrors','').replace('_','/')
    findmnt_command = "findmnt -t fuse -S cvmfs2"
    probe_command = "/usr/bin/cvmfs_config probe " + repository
    attr_command = ["/usr/bin/attr", "-qg", "nioerr", repository]
    try:
        findmnt_out = subprocess.check_output(findmnt_command, shell=True)
        for mntline in findmnt_out.splitlines():
            if mntline.split()[0] == repository:
                try:
                    probe_out = subprocess.check_output(probe_command, shell=True)
                    for line in probe_out.splitlines():
                        #print "line is: ", line
                        if re.search(repository, line):
                            if re.search(r'OK', line):
                                try:
                                    nioerr = subprocess.Popen(attr_command, stdout=subprocess.PIPE).stdout.readlines()[0]
                                    return int(nioerr)
                                except ValueError:
                                    return -1
                except ValueError:
                    return -1
        # if we get here, there is no matching mounted fuse FS
        return -1
    except subprocess.CalledProcessError:
        return -1

def metric_init(params):
    '''Create the metric definition dictionary object for the metric.'''
    global descriptors
    findmnt_command = "findmnt -t fuse -S cvmfs2"

    all_repositories = []
    if params:
        all_repositories = params["repos"].split(",")
    else:
        try:
            findmnt_out = subprocess.check_output(findmnt_command, shell=True)
            for mntline in findmnt_out.splitlines():
                repo = mntline.split()[0]
                if repo != "TARGET":
                    all_repositories.append(repo)
        except subprocess.CalledProcessError:
            return 0

    for repository in all_repositories:
        name = 'cvmfs_nioerrors' + repository.replace('/','_')
        # we name the metric as the cvmfs repository it monitors
	metric = {'name': name,
                  'call_back': attrqg,
                  'time_max': 120,
                  'value_type': 'uint',
                  'units': 'N',
                  'slope': 'both',
                  'format': '%u',
                  'description': 'ioerrors for ' + repository,
                  'groups': 'cvmfs'}
        descriptors.append(metric)

    return descriptors


def metric_cleanup():
    '''Clean up the metric module.'''
    pass


#This code is for debugging and unit testing
if __name__ == '__main__':
    #params = {}
    params = { "repos": "/cvmfs/alice.cern.ch,/cvmfs/alice-ocdb.cern.ch" }
    metric_init(params)
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s is %u' % (d['name'],  v)
