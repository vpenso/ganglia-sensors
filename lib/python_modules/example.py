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
import logging

# Data structure used to hold all monitoring metrics 
# collected by this sensor
metrics = {}

def update_metrics():
    
    global metrics
    
    logging.debug("Update metrics...")
    
    # Set values for individual metrics
    metrics["example"] = 123

# It takes one parameter, 'name', which is the value defined 
# in the 'name' element in your metric descriptor. 
def metric_handler(name):

    global metrics

    logging.debug("Call for metric: %s", name)

    # Make sure to update metrics for this execution interval
    update_metrics()

    # Return the value for a particular metric
    return metrics[name]
            

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
    
    # Metric description dictionary, will be returned to the 
    # module caller Gmond. 
    descriptors = list()

    # Define a metric
    metric = {
        "name":       "example",
        "call_back":  metric_handler,
        "time_max":   20,
        "value_type": "float",
        "format":     '%.0f',
        "slope":      "both",
        "units":      "Counter",
        "groups":     "Example",
    };
    # Add this metric to the descriptor list
    logging.debug("Register metric: %s", metric["name"])
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

    logging.root.setLevel(logging.DEBUG) 

    params = { "maximum_life_time": "20" }

    descriptors = metric_init(params)

    while True:
        for d in descriptors:
            v = d['call_back'](d['name'])
            print 'value for %s is %u' % (d['name'],  v)

        time.sleep( int(params["maximum_life_time"]) - 1 )
