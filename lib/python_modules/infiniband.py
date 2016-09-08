#
# Copyright:: 2014, GSI HPC Department
#
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
import logging
import time
import subprocess
import re

# Data structure used to hold all monitoring metrics
# collected by this sensor
metrics = {}

# Identify the ports and LIDs of the Infiniband adapters
def ibstat_ports():
    ports = {}
    ibstat = subprocess.Popen("ibstat", stdout=subprocess.PIPE).stdout.readlines()
    for index,line in enumerate(ibstat):
        line = line.strip()
        match = re.match("Port [0-9]\:",line)
        if match:
            number = line.split(' ')[1].replace(':','')
            state = ibstat[index+1].split(':')[1].strip()
            an = re.match("Active",state)
            if an:
                lid = ibstat[index+4].split(':')[1].strip()
                if error_counter(lid, number):
                    ports[number] = lid
    return ports

# Match input line to be a counter, e.g.:
#
#    PortXmitData:....................405429
#
# Return a key-value pair, eventually empty if the line didn't match
def parse_counter_line(line, ignored_keys):
    if re.match("^[a-zA-z0-9]*\:\.\.\.*[0-9]*$",line):
        line = line.split(':')
        key = line[0]
        if not key in ignored_keys:
            value = line[1].replace('.','').strip()
            return (key.lower(), int(value))
    return ("",0)

# Parse the complete input from perfquery for lines matching counters,
# and return all counters and their values as dictionary
def parse_counters(counters, ignored_keys):
    counts = {}
    for line in counters:
        key, value = parse_counter_line(line, ignored_keys)
        # Omit empty return values...
        if key:
          logging.debug("[parse_counters] Found counter: %s=%s", key, value)
          counts[key] = value
    return counts

# Call perfquery for error counters
def error_counter(lid, port = 1):
    command = ["sudo", "/usr/sbin/perfquery", lid, port]
    logging.debug("[error_counters] Execute command: %s", " ".join(command))
    counters = subprocess.Popen(command, stdout=subprocess.PIPE).stdout.readlines()
    return parse_counters(counters, ["PortSelect","CounterSelect","XmtData","RcvData","XmtPkts","RcvPkts","PortXmitData","PortRcvData","PortXmitPkts","PortRcvPkts"])

# Call perfquery for extended traffic counters, and reset the counters
def traffic_counter(lid, port = 1):
    command = ["sudo", "/usr/sbin/perfquery", "-x", lid, port]
    logging.debug("[traffic_counters] Execute command: %s", " ".join(command))
    counters = subprocess.Popen(command, stdout=subprocess.PIPE).stdout.readlines()
    return parse_counters(counters, ["PortSelect","CounterSelect"])

def update_metrics():
    
    global metrics

    time_since_last_update = time.time() - metrics["last_update"]

    # Update metric after their maximum life time is exceeded
    if time_since_last_update > metrics["maximum_life_time"] - 5:
    # This is useful to prevent updated for every call to the metric_handler()
    # function, too.
        logging.debug("[update_metrics] Update metrics after %ss", time_since_last_update)

        # Iterate over all Infiniband ports
        for port,lid in ibstat_ports().items():
            
            # Call perfquery to collect counters
            traffic = traffic_counter(lid, port)
            errors = error_counter(lid, port)
            
            # Store counters for this port
            metrics[port] = dict(errors.items() + traffic.items())
            
            # Data port counters indicate octets divided by 4 rather than just octets.
            #
            # It's consistent with what the IB spec says (IBA 1.2 vol 1 p.948) as to
            # how these quantities are counted. They are defined to be octets divided
            # by 4 so the choice is to display them the same as the actual quantity
            # (which is why they are named Data rather than Octets) or to multiply by
            # 4 for Octets. The former choice was made.
            #
            # For simplification the values are multiplied by 4 to represent octets/bytes
            data_counters = [ "portxmitdata","portrcvdata" ]
            for metric in data_counters:
                # Multiply by four to calculate bytes
                octets = metrics[port][metric]*4
                # New key to represent bytes per second
                key = metric.replace("data","bytes")
                # Divide package counter by seconds since last measurement
                metrics[port][key] = octets
        # Buffer a time stamp of the last time metrics have been recorded
        metrics["last_update"] = time.time()

# It takes one parameter, 'name', which is the value defined
# in the 'name' element in your metric descriptor.
def metric_handler(metric):

    global metrics

    # Make sure to update metrics if required
    update_metrics()

    # Extract the metric name and port from the metric
    # descriptor name
    metric = metric.split('_')
    key = metric[1]
    port = metric[2]
    port = port.replace("port","")

    # Return the value for the queried metric
    return metrics[port][key]

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
    
    global logger
    global metrics

    maximum_life_time = int(params["maximum_life_time"])

    # Initialize the first time stamp in the past to make sure
    # that the perfquery data gets initialized on first execution
    metrics["last_update"] = time.time() - maximum_life_time
    # Maximum live time of metrics recorded by this module
    metrics["maximum_life_time"] = maximum_life_time


    # The group in the web front-end with which this metric will
    # be associated
    metric_group = "infiniband"
    
    # Metric description dictionary, will be returned to the
    # module caller Gmond.
    descriptors = list()
    
    update_metrics()

    # Iterate over all Infiniband ports
    for port,lid in ibstat_ports().items():

        for key in metrics[port]:

            # Determine the unit format for all metrics
            if key in ["portrcvbytes","portxmitbytes"]:
                unit = "bytes/sec"
            elif key in ["portrcvdata","portxmitdata"]:
                unit = "32bits/sec"
            elif key in [
                "portxmitpkts","portrcvpkts"
                "portunicastxmitpkts", "portunicastrcvpkts",
                "portmulticastxmitpkts", "portmulticastrcvpkts" ]:
                unit = "packets/sec"
            else:
                unit = "counts/sec"

            # Metric descriptor name
            name = metric_group + "_" + key + "_port" + port
            # Define a metric
            metric = {
                "name":       name,
                "call_back":  metric_handler,
                "time_max":   maximum_life_time + 10,
                "value_type": "double",
                "format":     "%.0f",
                "slope":      "positive",
                "units":      unit,
                "groups":     metric_group
            };
            # Add this metric to the descriptor list
            logging.debug("[metric_init] Register metric %s=%s", metric["name"], unit)
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

# This is code for debugging!
#
# You can run this directly with the python interpreter, in order
# to debug the code without gmond...

if __name__ == '__main__':

    logging.root.setLevel(logging.DEBUG)

    params = {
        "maximum_life_time": "20"
    }

    descriptors = metric_init(params)

    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %0.f' % (d['name'],  v)

        time.sleep( int(params["maximum_life_time"]) - 1 )
