
## Gmetric

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

### Scripts

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

