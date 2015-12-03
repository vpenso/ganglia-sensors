
# Gmetric

All metrics in Ganglia have a **name**, **value**, **type** and optionally **units**:

~~~
» gmetric --name temperature --type int16 --units Celsius --value 45
~~~

By default the host executing is considered to be the source of the collected metric. It is possible to send metrics for other nodes using the `--spoof` option:

~~~
» gmetric -spoof 10.1.1.25:lxdev02.devops.test […]
~~~

String values send to Ganglia are not persistent, and will be lost once gmetad/gmond get restarted:

~~~
» gmetric --type string --name "Service" --value "Ganglia Monitoring Server"
~~~

## Scripts

The following script **gmetric-mpstat** is a more elaborate example. It collects per core statistics using `mpstat`, and sends these to Ganglia. It uses the `--group` option to define a metric collection "cpu_cores".

~~~bash
#!/usr/bin/env bash

args="--type float --group cpu_cores --units percent"

mpstat -P ALL | tail -n +5 | tr -s ' ' | cut -d' ' -f3,4,6,7,12 | while 
  read -r cpu usr sys iowait idle
do 
  `gmetric $args --name "cpu_core_"$cpu"_usr" --value $usr` 
  `gmetric $args --name "cpu_core_"$cpu"_sys" --value $sys` 
  `gmetric $args --name "cpu_core_"$cpu"_iowait" --value $iowait` 
  `gmetric $args --name "cpu_core_"$cpu"_idle" --value $idle`
done
~~~

The option `--name` defines the graph title and file name on the Ganglia server:

    »  ls -1 /var/lib/ganglia/rrds/$cluster/$hostname/cpu_core*
    /var/lib/ganglia/rrds/[…]/cpu_core_0_idle.rrd
    /var/lib/ganglia/rrds/[…]/cpu_core_0_iowait.rrd
    /var/lib/ganglia/rrds/[…]/cpu_core_0_sys.rrd
    /var/lib/ganglia/rrds/[…]/cpu_core_0_usr.rrd

## Crontab

Execute gmetric scripts with Cron by adding files to `/etc/cron.d`.

Here illustrated with a script called **gmetric-perfquery**:

~~~
» cat /etc/cron.d/gmetric-perfquery 
PATH=/usr/sbin:/usr/sbin:/usr/bin:/sbin:/bin
# Send Infiniband perfquery metrics to Ganglia every 60 seconds
* * * * * root gmetric-perfquery -L info -e -o -i 60
~~~

Make sure all dependency scripts are in path. Check if the script is executed by cron:

    » tail -f /var/log/syslog | grep CRON
    […]
    […] (*system*gmetric-perfquery) RELOAD (/etc/cron.d/gmetric-perfquery)
    […] (root) CMD (gmetric-perfquery -L info -e -o -i 60)
    […]

# Modules

Ganglia can be extended by Python and C/C++ modules. Modules are executed (in intervals) by gmond in contrast to data collected with gmetric.

The Debian package **ganglia-monitor-python** provides the required environment to enable Python modules.


## Configuration

Path | Description
-----|----------------------
`/usr/lib/ganglia/python_modules` | Default directory for Python modules
`/etc/ganglia/conf.d/*.pyconf` | Module configuration files

Their **module** section of the configuration file requires following attributes:

- The **name** value matches the file name of the Python module’s `.py` file.
- The **language** value for a Python module must be "python".
- Each **param** block must include a name and a value, which are passed to the `metric_init()` function of the module. The name of the param block represents the key that corresponds to the parameter value in the Python dictionary object. The value directive specifies the parameter value (always a string!).

The **collection_group** section must contain:

- **name_match** uses PCRE regex matching to configure metrics using.
- **title** is displayed in the web-interface as name of the graph.

Following examples illustrates the configuration of a module called infiniband:

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

## Development

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
