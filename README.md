# Cluster Model

This tool is used for modeling the resources (CPU, RAM, Storage) required
to run a system. The model is quite generic but is designed with CommCare HQ
in mind.

# Usage

    # create a virtual env
    $ python3 -m venv /path/to/new/virtual/environment

    # install requirements
    $ pip install -U pip
    $ pip install -r requirements.txt

    # run tool
    $ python run_model.py -h
    $ python run_model.py /path/to/config.yml

# Model overview
This tool works on the following model:

* Define the expected usage of the system for each month.
* Define the services in use by the system including storage and processing
requirements per unit 'usage' item.

The model will then apply the usage values to the services models
to obtain the CPU, RAM, Storage and number of VMs required to run the service
over the months defined in the model.

# Configuration
The tool takes a config file which defines the parameters of the model
for the system.

The config file is split into 4 sections:

## Global config

| Key                  | Description |
| -------------------- | ----------- |
| etimation_buffer     | Factor to inflate values by to account for estimation difference |
| storage_buffer       | Factor to inflate storage values by |
| storage_display_unit | GB or TB |
| vm_os_storage_gb     | GB storage per VM for OS etc |
| vm_os_storage_group  | Group name for OS storage |
| summary_dates        | List of dates to generate summaries at. Date format: YYYY-MM |


## Usage config
This sections describes the usage of the system e.g. number of users, volume of transactions etc.

This section may have any number of named items in it to describe different
aspects of the system. Each item may be a standalone item or reference
other items.

Each item in this section defines which 'model' it will use to simulate the usage.
The available models are as follows:

### Date range value
This model assigns a specific number to each date range in a list.

Example:
The follow example defined the number of users of the system
in 2018 and 2019.

    users:
        model: 'date_range_value'
        ranges:
          - ['20180101', '20181201', 100000]
          - ['20190101', '20191201', 200000]

### Derived Factor
Multiply another field by a fixed factor.

Example:
10 forms per user per month

    forms:
        model: 'derived_factor'
        start_with: 91000000  # initial value. Defaults to 0.
        dependant_field: 'users'  # Value is derived from this field
        factor: 10  # Factor to multiply the dependant field by

### Derived Sum
Sum multiple other fields

Example:
Total kafka changes

    kafak_changes:
        model: 'derived_sum'
        dependant_fields: ['forms', 'cases', 'case_transactions']

### Cumulative
This model performs a cumulative sum of the values.

Example:
Total forms ever created.

    forms_total:
        model: 'cumulative'
        dependant_field: 'forms'

### Cumulative with limited lifespan
Similar to 'Cumulative' this performs a cumulative sum of the dependant field
but only over the most recent N months.

Example:
Logs that get deleted after 2 months

    device_logs_total:
        model: 'cumulative_limited_lifespan'
        dependant_field: 'device_logs'
        lifespan: 2

## Service config
Each item in the service config defines a service which the system uses.
The services are related to the usage values to calculate required resources.

| Param name                | Description |
| ------------------------- | ----------- |
| usage_capacity_per_node   | The capacity that a single node can handle |
| usage_field               | (optional) Field to reference for usage. Default to 'users' |
| min_nodes                 | (optional) Minimum number of nodes (VMs). Defaults to '1' |
| storage_scales_with_nodes | (optional) True if each new node contains a complete copy of the data e.g. SQL replica |
| storage                   | (optional) Define service storage. Exclude this section for processing only services. |
| process                   | (optional) Define the processing requirements. Exclude this section for storage only services e.g S3 |

### Storage
For storage services the storage section should be included.

    storage:
      group: 'SSD'  # name of the storage group
      redundancy_factor: 1  # Use a value of more than 1 for services that store data redundantly
      static_baseline: 0  # Bytes to include as a static value to account for overhead etc.
      data_models:  # List of data models
        - referenced_field: 'forms_total'
          unit_bytes: 1200
        - referenced_field: 'cases_total'
          unit_bytes: 1800
        - referenced_field: 'case_transactions_total'
          unit_bytes: 515

### Process
For services that require compute resources (CPU / RAM) the 'process' section should be defined.

This section has two modes:

#### Single process
e.g. Django worker

    usage_capacity_per_node: 1000
    process:
      cores_per_node: 4
      ram_per_node: 6

#### Multi-process
e.g. Celery task queues

In this case the `usage_capacity_per_node` field is not required since
the capacity is defined for each sub-process.

    process:
      cores_per_node: 8
      ram_per_node: 16
      cores_per_sub_process: 1
      ram_per_sub_process: 0.5
      sub_processes:
        - name: 'queue1'
          static_number: 30  # regardless of the usage there will always be 30
        - name: 'queue2'
          capacity: 20000  # 1 per 20000 users