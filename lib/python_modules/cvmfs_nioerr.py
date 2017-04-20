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
import threading

descriptors = list()

def timeout_command(command_tokens, timeout_secs):
    """ Launch the command received as argument as a timed process.

    input: list of command strings, containing command name and command arguments
    output: process returncode, stdout, stderr
    The process return code is "-15" in case the command is timed out.
    The use of process groups allows to kill also subprocesses (omitting to do this
    in favor of a process.kill() or process.terminate() was letting the calling part hanging. """
    kill = lambda process: os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    wrapped_process = subprocess.Popen(command_tokens, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
    timer = threading.Timer(timeout_secs, kill, [wrapped_process])
    try:
        timer.start()
        stdout, stderr = wrapped_process.communicate()
    finally:
        timer.cancel()
    return ([wrapped_process.returncode, stdout, stderr])

def attrqg(repository):
    '''Return the output of attr -qg nioerr repository, which is the
    total number of I/O errors encoutered since mounting.
    If a prior findmnt or cvmfs_config probe check fails, then return
    a negative value'''

    # remove the prefix and substitute underscore
    repository = repository.replace('cvmfs_nioerrors','').replace('_','/')
    findmnt_command = ["findmnt", "-t", "fuse", "-S", "cvmfs2"]
    probe_command = ["/usr/bin/cvmfs_config", "probe", repository]
    attr_command = ["/usr/bin/attr", "-qg", "nioerr", repository]
    try:
	[retcode, findmnt_out, err] = timeout_command(findmnt_command, 1)
        for mntline in findmnt_out.splitlines():
            if mntline.split()[0] == repository:
                try:
		    [retcode, probe_out, err] = timeout_command(probe_command, 3)
                    for line in probe_out.splitlines():
                        if re.search(repository, line):
                            if re.search(r'OK', line):
                                try:
				    [retcode, attr_out, err] = timeout_command(attr_command, 1)
                                    nioerr = attr_out.splitlines()[0]
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
    findmnt_command = ["findmnt", "-t", "fuse", "-S", "cvmfs2"]

    all_repositories = []
    if params:
        all_repositories = params["repos"].split(",")
    else:
        try:
	    [retcode, findmnt_out, err] = timeout_command(findmnt_command, 1)
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
