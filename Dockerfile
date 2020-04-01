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
FROM ubuntu:bionic-20191202

USER root

RUN apt-get update --fix-missing \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
        --no-install-recommends \
        ca-certificates \
        curl \
        gnupg2 \
        gosu \
        locales \
        make \
        software-properties-common \
        wget \
        unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales \
    && update-locale LANG=en_US.UTF-8

## Install Microsoft and Postgres ODBC drivers and SQL commandline tools
RUN curl -o microsoft.asc https://packages.microsoft.com/keys/microsoft.asc \
    && apt-key add microsoft.asc \
    && rm microsoft.asc \
    && curl https://packages.microsoft.com/config/ubuntu/18.04/prod.list > /etc/apt/sources.list.d/mssql-release.list \
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
    PATH=/opt/conda/bin:/opt/mssql-tools/bin:/opt/ssis/bin:${PATH} \
    SHELL=/bin/bash \
    DEBIAN_FRONTEND=noninteractive \
    CT_USER=docker \
    CT_UID=1000 \
    CT_GID=100 \
    CT_FMODE=0775 \
    CONDA_DIR=/opt/conda

RUN wget --quiet \
    https://repo.anaconda.com/miniconda/Miniconda3-4.7.12.1-Linux-x86_64.sh \
    -O /root/miniconda.sh && \
    if [ "`md5sum /root/miniconda.sh | cut -d\  -f1`" = "81c773ff87af5cfac79ab862942ab6b3" ]; then \
        /bin/bash /root/miniconda.sh -b -p /opt/conda; fi && \
    rm /root/miniconda.sh && \
    /opt/conda/bin/conda clean -tipsy && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh

# Add a script that we will use to correct permissions after running certain commands
COPY fix-permissions /usr/local/bin/fix-permissions

## Set a default user. Available via runtime flag `--user docker`
## User should also have & own a home directory (e.g. for linked volumes to work properly).
RUN useradd --create-home --uid ${CT_UID} --gid ${CT_GID} --shell ${SHELL} \
    ${CT_USER} \
    && chmod 0755 /usr/local/bin/fix-permissions

ENV HOME=/home/${CT_USER}

RUN fix-permissions ${CONDA_DIR} \
    && fix-permissions ${HOME}

WORKDIR ${HOME}

ARG CONDA_ENV_FILE=${CONDA_ENV_FILE}
COPY ${CONDA_ENV_FILE} ${CONDA_ENV_FILE}
RUN /opt/conda/bin/conda update -n base -c defaults conda \
    && /opt/conda/bin/conda config --add channels conda-forge \
    && /opt/conda/bin/conda config --set channel_priority strict

RUN /opt/conda/bin/conda install conda-build --yes \
    && /opt/conda/bin/conda env update -n base --file ${CONDA_ENV_FILE} \
    && /opt/conda/bin/conda build purge-all \
    && rm ${CONDA_ENV_FILE} \
    && fix-permissions ${HOME}

RUN echo ". /opt/conda/etc/profile.d/conda.sh" >> ${HOME}/.bashrc && \
    echo "conda activate base" >> ${HOME}/.bashrc && \
    echo "export PATH=${HOME}/.local/bin:${PATH}" >> ${HOME}/.bashrc && \
    mkdir ${HOME}/work
SHELL [ "/bin/bash", "--login", "-c"]

RUN source ${HOME}/.bashrc \
    && conda activate base
WORKDIR ${HOME}/work

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
ENV SSIS_PID=Developer \
    ACCEPT_EULA=Y
WORKDIR ${HOME}/work
RUN /opt/ssis/bin/ssis-conf -n setup
CMD [ "/bin/bash" ]
