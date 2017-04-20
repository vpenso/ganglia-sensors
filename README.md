## Description

This repository contains code used to collect monitoring metrics for [Ganglia](https://github.com/ganglia):

> Ganglia is a scalable distributed monitoring system for high-performance computing systems such as clusters and Grids. […] It uses carefully engineered data structures and algorithms to achieve very low per-node overheads and high concurrency. [cf.](http://ganglia.info/)

## Daemons

Send monitoring information to Ganglia with [gmetric](docs/gmetric.md):

Program | Description
--------|---------------------
[ganglia-monitor-infiniband](bin/ganglia-monitor-infiniband) | Collect Infiniband channel adapter metrics with `perfquery`  
[ganglia-monitor-slurm](bin/ganglia-monitor-slurm) | Collect jobs, node and scheduler statistics from [Slurm](https://github.com/SchedMD/slurm) 

## Modules

Ganglia can be extended by Python and C/C++ modules. Modules are executed (in intervals) by gmond in contrast to data collected with gmetric. The Debian package **ganglia-monitor-python** provides the required environment to enable Python modules.

Module | Configuration  | Description
-------|----------------|--------------
[infiniband.py](lib/python_modules/infiniband.py) | [infiniband.pyconf](etc/conf.d/infiniband.pyconf) | Read Infiniband host channel performance metrics from `perfquery`
[ipmi.py](lib/python_modules/infiniband.py) | [ipmi.pyconf](etc/conf.d/ipmi.pyconf) | Read the BMC sensors with `ipmitool`
[cvmfs_nioerr.py]((lib/python_modules/cvmfs_nioerr.py)| [cvmfs_nioerr.pyconf](etc/conf.d/cvmfs_nioerr.pyconf) | Count I/O errors on CernVM-FS mounts

### Configuration

Path | Description
-----|----------------------
`/usr/lib/ganglia/python_modules` | Default directory for Python modules
`/etc/ganglia/conf.d/*.pyconf` | Module configuration files

The **module** section of the configuration file requires following attributes:

- The **name** value matches the file name of the Python module’s `.py` file.
- The **language** value for a Python module must be "python".
- Each **param** block must include a name and a value, which are passed to the `metric_init()` function of the module. The name of the param block represents the key that corresponds to the parameter value in the Python dictionary object. The value directive specifies the parameter value (always a string!).

The **collection_group** section must contain:

- The **name_match** uses PCRE regex matching to configure metrics.
- The **title** is displayed in the web-interface as name of the graph.

Following examples illustrates the configuration of a module called "infiniband":

~~~
modules {
  module {
    name = "infiniband"
    language = "python"
    param "interval" { value = 20 }
    param "error_metrics" { value = yes }
  }
}

collection_group {

  collect_every = 15
  time_threshold = 45
  metric { 
    name_match = "infiniband_xmtdata_port" 
    title = "Infiniband Send Bytes"
  }
  […]
}
~~~

### Development

Start developing new Python modules from ↴<tt>[lib/python_modules/example.py](lib/python_modules/example.py)</tt>

Check if the metric description is correctly used by gmond:

    » gmond -c /etc/ganglia/gmond.conf -m | grep infini
    infiniband_rcvconstrainterrors_port1     (module python_module)
    infiniband_rcvswrelayerrors_port1        (module python_module)
    infiniband_vl15dropped_port1     (module python_module)
    infiniband_symbolerrors_port1    (module python_module)
    infiniband_rcverrors_port1       (module python_module)
    […]
    » gmond -c /etc/ganglia/gmond.conf -d 2 -f
    […]

Run gmond in foreground and debugging mode the see if everything works as expected.

## Graphs

Extension code for the Ganglia [Web Frontend](https://github.com/ganglia/ganglia-web)

File | Description
-----|--------------------
[infiniband_report.json](etc/graph.d/infiniband_report.json) | Incoming and outgoing traffic on an Infiniband adapter in bytes per second
[slurm_job_states_report.json](etc/graph.d/slurm_job_states_report.json) | Number of running/pending jobs in Slurm 

### Configuration

The file name must end with `_report.json`. Graph configuration attributes are:

Attribute       | Description
----------------|-----------------------------
report_name     | Name of the report that web UI uses
title           | Title of the report to show on a graph
vertical_label  | Y-axis description (optional)
series          | An array of metrics to use to compose a graph

The attributes inside the **series key** contain:

Attribute       | Description
----------------|-----------------------------
metric          | Name of a metric, such as load_one and cpu_system. If the metric doesn’t exist it will be skipped.
color           | A 6 hex-decimal color code, such as 000000 for black.
label           | Metric label, such as Load 1.
type            | Item type. It can be either line or stack.
line_width      | If type is set to line, this value will be used as a line width. If this value is not specified, it defaults to 2. If type is stack, it’s ignored even if set. 

### Deployment 

Deploy custom composite graphs:

1. Copy the JSON configuration file into the directory `/usr/share/ganglia-webfrontend/graph.d` on the server hosting the web frontend.
2. Enable a graph using the "Edit Optional Graphs" button in the user interface of the web frontend.

## Packages

Create Debian package with the configuration in [debian/](debian/)

```
apt -y install debhelper devscripts
dch -i                                             # adjust changelog if required
dpkg-buildpackage -b -us -uc -tc                   # build package
dpkg -c ../ganglia-monitor-slurm_*_all.deb         # list package content
```


## License

Copyright 2014-2016 Victor Penso

This is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.

