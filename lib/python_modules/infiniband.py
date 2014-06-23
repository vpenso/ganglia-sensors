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

perfquery = {}

# Identify the number of ports on the Infiniband adapter
def ibstat_ports():
    ports = {}
    ibstat = subprocess.Popen("ibstat", stdout=subprocess.PIPE).stdout.readlines()
    for index,line in enumerate(ibstat):
        line = line.strip()
        match = re.match("Port [0-9]\:",line) 
        if match:
          number = line.split(' ')[1].replace(':','')
          lid = ibstat[index+4].split(':')[1].strip()
          ports[number] = lid
    return ports

def update_metrics(time_max = 20):
    # Buffer for performance metrics
    global perfquery
    # Update metrics only if defined live time is exceeded 
    if (time.time() - perfquery["time"]) > time_max:
        # Iterate over all Infiniband ports
        for port,lid in ibstat_ports().items():
            # Reset metrics structure
            perfquery[port] = {}
            # Use perfquery to read Infiniband port counters
            command = ["sudo","/usr/sbin/perfquery", "-r",lid, port, "0xf000"] 
            # Reset the perfquery counters (with exception of errors)
            trash = subprocess.Popen(command, stdout=subprocess.PIPE).stdout.readlines()
            # accumulate counters for one second
            begin = time.time()
            time.sleep(1)
            end = time.time()
            # Sleep in Python is not real-time, means that depending on system interrupts
            # the relapsed time-frame is bigger then a second
            elapsed = end - begin
            # read the metrics for the past second
            perf_data = subprocess.Popen(command, stdout=subprocess.PIPE).stdout.readlines()
            for line in perf_data:
               line = line.split(':')
               key = line[0]
               value = line[1]
               value = value.replace('.','').strip()
               if key == "RcvPkts":
                  perfquery[port]["rcvpkts"] = int(float(value)/elapsed)
               elif key == "XmtPkts":
                  perfquery[port]["xmtpkts"] = int(float(value)/elapsed)
               # Data port counters indicate octets divided by 4 rather than just octets.
               #
               # It's consistent with what the IB spec says (IBA 1.2 vol 1 p.948) as to
               # how these quantities are counted. They are defined to be octets divided
               # by 4 so the choice is to display them the same as the actual quantity
               # (which is why they are named Data rather than Octets) or to multiply by
               # 4 for Octets. The former choice was made.
               #
               # For simplification the values are multiplied by for to represent 
               # octets/bytes, for better visualization on in graphs "bytes/second"
               elif key == "RcvData":
                  perfquery[port]["rcvdata"] = int((float(value)*4)/elapsed)
               elif key == "XmtData":
                  perfquery[port]["xmtdata"] = int((float(value)*4)/elapsed)
               elif key == "SymbolErrors":
                  perfquery[port]["symbolerrors"] = value
               elif key == "LinkRecovers":
                  perfquery[port]["linkrecovers"] = value
               elif key == "LinkDowned":
                  perfquery[port]["linkdowned"] = value
               elif key == "RcvErrors":
                  perfquery[port]["rcverrors"] = value
               elif key == "RcvRemotePhysErrors":
                  perfquery[port]["rcvremotephyserrors"] = value
               elif key == "RcvSwRelayErrors":
                  perfquery[port]["rcvswrelayerrors"] = value
               elif key == "XmtDiscards":
                  perfquery[port]["xmtdiscards"] = value
               elif key == "XmtConstraintErrors":
                  perfquery[port]["xmtconstrainterrors"] = value
               elif key == "RcvConstraintErrors":
                  perfquery[port]["rcvconstrainterrors"] = value
               elif key == "LinkIntegrityErrors":
                  perfquery[port]["linkintegrityerrors"] = value
               elif key == "ExcBufOverrunErrors":
                  perfquery[port]["excbufoverrunerrors"] = value
               elif key == "VL15Dropped":
                  perfquery[port]["vl15dropped"] = value
            # Buffer a time stamp of the last time metrics have been recorded 
            perfquery["time"] = time.time()

# It takes one parameter, 'name', which is the value defined 
# in the 'name' element in your metric descriptor. 
def metric_handler(name):
    global perfquery
    update_metrics()
    name = name.split('_')
    metric = name[1]
    port = name[2]
    port = port.replace('port','')
    value = float(perfquery[port][metric])
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
    perfquery["time"] = time.time() - int(params["interval"])
    update_metrics()

    # The group in the web front-end with which this metric will 
    # be associated 
    group = "infiniband"
    # Maximum live time of metrics recorded by this module 
    #time_max = int(params["interval"])
    time_max = 60

    # Metric description dictionary, will be returned to the 
    # module caller, basically gmond 
    descriptors = list()

    # Iterate over all Infiniband ports
    for port,lid in ibstat_ports().items():
        
        # Prefix for the metric name, common to all metrics
        # supported by this module
        port = "_port" + port

        # Gather the minimal set of performance metrics related
        # to the network traffic per seconds: packets, bytes
        traffic_metrics = {
            "RcvPkts": "packets/sec", 
            "XmtPkts": "packets/sec", 
            "RcvData": "bytes/sec", 
            "XmtData": "bytes/sec"
        }
        # 
        for name,fmt in traffic_metrics.items():
            metric               = {}
            metric["name"]       = group + "_" + name.lower() + port
            metric["call_back"]  = metric_handler
            metric["time_max"]   = time_max
            metric["value_type"] = "float"
            metric["format"]     = '%.0f'
            metric["slope"]      = "both"
            metric["units"]      = fmt
            metric["groups"]     = group
            # Add this metric to the descriptor list
            descriptors.append(metric)

        # If module parameters enable collection of error metrics
        infiniband_error_metrics = [ 
            "SymbolErrors", 
            "LinkRecovers", 
            "LinkDowned", 
            "RcvErrors", 
            "RcvRemotePhysErrors", 
            "RcvSwRelayErrors", 
            "XmtDiscards", 
            "XmtConstraintErrors", 
            "RcvConstraintErrors", 
            "LinkIntegrityErrors", 
            "ExcBufOverrunErrors", 
            "VL15Dropped" 
        ]
        if params["error_metrics"] == "yes":
            for name in infiniband_error_metrics:
                metric               = {}
                metric["name"]       = group + "_" + name.lower() + port
                metric["call_back"]  = metric_handler
                metric["time_max"]   = time_max
                metric["value_type"] = "float"
                metric["format"]     = '%.0f'
                metric["slope"]      = "both"
                metric["units"]      = "number of"
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

    params = { "interval": "20", "error_metrics": "yes" }

    descriptors = metric_init(params)

    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)
        time.sleep(int(params["interval"]))
