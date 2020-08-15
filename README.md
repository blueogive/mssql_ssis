# MSSQL SSIS

This repo contains a `Dockerfile` to build
a Linux [Docker](https://www.docker.com) image containing the Microsoft
[SQL Server Tools](https://docs.microsoft.com/en-us/sql/linux/sql-server-linux-setup-tools?view=sql-server-linux-2017)
and [SSIS](https://docs.microsoft.com/en-us/sql/linux/sql-server-linux-setup-ssis?view=sql-server-linux-2017)
packages for Linux. The image also includes Microsoft's
[ODBC driver for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/microsoft-odbc-driver-for-sql-server?view=sql-server-linux-2017)
and a working Python 3.7 environment based on the
[Miniconda](https://conda.io/miniconda.html)
environment management system developed by
[Anaconda, Inc](https://www.anaconda.com/). Finally, the image includes the
[Oracle Instant Client, SDK, and SQL*Plus tool](https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html).


## Usage

To instantiate an ephemeral container from the image, mount the current
directory within the container, and open a bash prompt within the `base` conda
Python environment:

```bash
docker run -it --rm -v $(pwd):/home/docker/work blueogive/mssql_ssis:latest
```

## Relevant Documentation

How to:

* [Run SSIS packages on Linux](https://docs.microsoft.com/en-us/sql/linux/sql-server-linux-migrate-ssis?view=sql-server-linux-2017)
* [Schedule SSIS package execution using cron](https://docs.microsoft.com/en-us/sql/linux/sql-server-linux-schedule-ssis-packages?view=sql-server-linux-2017)

You will be running as root within the container, but the image includes the
[gosu](https://github.com/tianon/gosu) utility. This allows you to conveniently execute commands as other users:

```bash
gosu 1000:100 dtexec /F path/to/package
```

Contributions are welcome.
