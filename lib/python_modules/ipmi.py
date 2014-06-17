#
# Copyright:: 2014 
# Author:: Victor Penso
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import time
import subprocess
import re

data = {}

def update_metrics(time_max = 20):
    # Buffer for performance metrics
    global data
    # Update metrics only if defined live time is exceeded 
    if (time.time() - data["time"]) > time_max:
        # Use perfquery to read Infiniband port counters
        command = ["sudo","ipmitool","sensor"] 
        sensors = subprocess.Popen(command, stdout=subprocess.PIPE).stdout.readlines()
        for line in sensors:
            line = line.split('|')
            key = line[0].strip().lower().replace(" ", "_")
            value = line[1].strip()
            if key == "system_temp":
                data[key] = float(value)
        # Buffer a time stamp of the last time metrics have been recorded 
        data["time"] = time.time()

# It takes one parameter, 'name', which is the value defined 
# in the 'name' element in your metric descriptor. 
def metric_handler(name):
    global data
    update_metrics()
    name = name.split('_')
    name = '_'.join(str(x) for x in name[1:])
    value = data[name]
    return value
            

# This function must exist!  
#
# It will be called once at initialization time - that is, 
# once when gmond starts up. It can be used to do any kind 
# of initialization that the module requires in order to 
# properly gather the intended metric. 
# 
# Takes a single dictionary type parameter which contains 
# configuration directives that were designated for this 
# module in the gmond.conf file.
def metric_init(params):

    global perfquery

    # Initialize the first time stamp in the past to make sure 
    # that the perfquery data gets initialized on first execution
    data["time"] = time.time() - int(params["interval"])
    update_metrics()

    # The group in the web front-end with which this metric will 
    # be associated 
    group = "ipmi"
    # Maximum live time of metrics recorded by this module 
    time_max = int(params["interval"]) + 10

    # Metric description dictionary, will be returned to the 
    # module caller, basically gmond 
    descriptors = list()

    metric               = {}
    metric["name"]       = group + "_system_temp"
    metric["call_back"]  = metric_handler
    metric["time_max"]   = time_max
    metric["value_type"] = "float"
    metric["format"]     = '%.0f'
    metric["slope"]      = "both"
    metric["units"]      = "celsius"
    metric["groups"]     = group
    # Add this metric to the descriptor list
    descriptors.append(metric)

    # Register metrics provided by this module
    return descriptors

# This function must exist! 
#
# It will be called only once when gmond is shutting down. Any 
# module clean up code can be executed here and the function must 
# not return a value. 
def metric_cleanup():
    pass

if __name__ == '__main__':

    params = { "interval": "20" }

    descriptors = metric_init(params)

    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)
        time.sleep(int(params["interval"]))
