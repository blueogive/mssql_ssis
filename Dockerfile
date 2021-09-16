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
FROM ubuntu:focal-20210723

USER root
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update --fix-missing \
    && apt-get install -y \
        --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        gnupg2 \
        gosu \
        libaio1 \
        locales \
        make \
        openssh-client \
        software-properties-common \
        wget \
        unixodbc-dev \
        unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales \
    && update-locale LANG=en_US.UTF-8

## Install Oracle Instant Client, tools
RUN mkdir /opt/oracle
WORKDIR /opt/oracle
RUN curl -o instantclient-basiclite-linux.x64-19.8.0.0.0dbru.zip \
    https://download.oracle.com/otn_software/linux/instantclient/19800/instantclient-basiclite-linux.x64-19.8.0.0.0dbru.zip \
    && curl -o instantclient-sqlplus-linux.x64-19.8.0.0.0dbru.zip \
    https://download.oracle.com/otn_software/linux/instantclient/19800/instantclient-sqlplus-linux.x64-19.8.0.0.0dbru.zip \
    && unzip -oq 'instantclient-*.zip' \
    && rm instantclient-*.zip

WORKDIR /opt/oracle/instantclient_19_8
RUN mkdir bin \
    && mv sqlplus bin \
    && mkdir -p sqlplus/admin \
    && mv glogin.sql sqlplus/admin \
    && echo /opt/oracle/instantclient_19_8 > \
        /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig

WORKDIR /root
## Install Microsoft and Postgres ODBC drivers and SQL commandline tools
RUN curl -o microsoft.asc https://packages.microsoft.com/keys/microsoft.asc \
    && apt-key add microsoft.asc \
    && rm microsoft.asc \
    && curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && add-apt-repository "$(curl https://packages.microsoft.com/config/ubuntu/18.04/mssql-server-2019.list)" \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
        msodbcsql17 \
        mssql-tools \
        mssql-server-is \
        odbc-postgresql \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm /etc/apt/sources.list.d/mssql-release.list

## Set environment variables
ENV LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    PATH=/opt/conda/bin:/opt/mssql-tools/bin:/opt/ssis/bin:/opt/oracle/instantclient_19_8/bin:${PATH} \
    ORACLE_HOME=/opt/oracle/instantclient_19_8 \
    NLS_LANG=AMERICAN_AMERICA.UTF8 \
    SHELL=/bin/bash \
    CT_USER=docker \
    CT_UID=1000 \
    CT_GID=100 \
    CT_FMODE=0775 \
    CONDA_DIR=/opt/conda

# Add a script that we will use to correct permissions after running certain commands
COPY fix-permissions /usr/local/bin/fix-permissions

## Set a default user. Available via runtime flag `--user docker`
## User should also have & own a home directory (e.g. for linked volumes to work properly).
RUN useradd --create-home --uid ${CT_UID} --gid ${CT_GID} --shell ${SHELL} \
    ${CT_USER} \
    && chmod 0755 /usr/local/bin/fix-permissions

ENV HOME=/home/${CT_USER}

RUN umask 0002 && \
    wget --quiet \
    https://github.com/conda-forge/miniforge/releases/download/4.10.3-5/Mambaforge-4.10.3-5-Linux-x86_64.sh \
    -O /root/mambaforge.sh && \
    if [ "`md5sum /root/mambaforge.sh | cut -d\  -f1`" = "2aff37852fa373bbf2ff897f757cf66f" ]; then \
        /bin/bash /root/mambaforge.sh -b -p /opt/conda; fi && \
    rm -f /root/mambaforge.sh ${HOME}/.wget-hsts && \
    /opt/conda/bin/mamba clean -atipsy && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    fix-permissions ${CONDA_DIR} \
    && fix-permissions /home/${CT_USER}

WORKDIR ${HOME}

ARG CONDA_ENV_FILE=${CONDA_ENV_FILE}
COPY ${CONDA_ENV_FILE} ${CONDA_ENV_FILE}
RUN umask 0002 \
    && /opt/conda/bin/mamba env update -n base --file ${CONDA_ENV_FILE} \
    && /opt/conda/bin/mamba config --add channels conda-forge \
    && /opt/conda/bin/mamba config --set channel_priority strict \
    && /opt/conda/bin/mamba clean -atipy \
    && rm ${CONDA_ENV_FILE} \
    && fix-permissions ${HOME} \
    && chown -R ${CT_USER}:${CT_GID} ${HOME}/.conda \
    && rm -rf ${HOME}/.empty

USER ${CT_USER}

RUN umask 0002 && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ${HOME}/.bashrc && \
    echo "conda activate base" >> ${HOME}/.bashrc && \
    echo "export PATH=${HOME}/.local/bin:${PATH}" >> ${HOME}/.bashrc && \
    mkdir ${HOME}/work && \
    chgrp ${CT_GID} ${HOME}/work
SHELL [ "/bin/bash", "--login", "-c"]

USER root

RUN umask 0002 \
    && source ${HOME}/.bashrc \
    && conda activate base \
    && mkdir -p .config/pip \
    && fix-permissions ${HOME}/work \
    && rm -rf ${HOME}/.cache/pip/*
COPY pip.conf ${HOME}/.config/pip/pip.conf
RUN fix-permissions ${HOME}/.config/pip
WORKDIR ${HOME}/work

RUN source ${HOME}/.bashrc \
    && conda activate base
WORKDIR ${HOME}/work

# Use NPM to install a T-SQL linter
RUN npm install tsqllint -g

ARG VCS_URL=${VCS_URL}
ARG VCS_REF=${VCS_REF}
ARG BUILD_DATE=${BUILD_DATE}

# Add image metadata
LABEL org.label-schema.license="https://opensource.org/licenses/MIT" \
    org.label-schema.vendor="Dockerfile provided by Mark Coggeshall" \
    org.label-schema.name="MSSQL CLI Tools, SSIS for Linux" \
    org.label-schema.description="Docker image including Microsoft SQL Server Commandline Tools and SSIS for Linux." \
    org.label-schema.vcs-url=${VCS_URL} \
    org.label-schema.vcs-ref=${VCS_REF} \
    org.label-schema.build-date=${BUILD_DATE} \
    maintainer="Mark Coggeshall <mark.coggeshall@gmail.com>"

# The ssisconfhelper.py file is part of Microsoft's SSIS package. Unfortunately,
# it attempts to use systemd to start a telemetry service. Since systemd is
# not running within a Docker container, I modified the file to prevent it
# from starting the telemetry service.
COPY ssisconfhelper.py /opt/ssis/lib/ssis-conf/
COPY docker-entrypoint /usr/local/bin
ENV SSIS_PID=Developer \
    ACCEPT_EULA=Y
WORKDIR ${HOME}/work

RUN /opt/ssis/bin/ssis-conf -n setup \
    && chmod 0755 /usr/local/bin/docker-entrypoint

USER ${CT_USER}

ENTRYPOINT [ "/usr/local/bin/docker-entrypoint" ]

CMD [ "/bin/bash" ]
