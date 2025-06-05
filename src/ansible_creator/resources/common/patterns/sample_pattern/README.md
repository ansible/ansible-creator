## Configure EC2 Instance Pattern

### Description

This pattern is designed to help get an EC2 instance up and running.

To enable SSH access to the EC2 instance from your local machine, you need to do
2 things:

1. Provide the Key Name: Specify an existing key name in the key_name parameter
   in the survey. The EC2 instance will be associated with the key pair
   corresponding to the provided name. If the key pair is unavailable, you will
   not be able to access the instance from your local machine.

2. Add a Security Group Rule for SSH Access: Configure a security group rule to
   allow inbound SSH traffic from your local machine's IP address. Provide this
   rule in the sg_rules parameter in the survey. Following is an example of the
   security group rule:

```
  - proto: tcp
    ports: 22
    cidr_ip: 203.0.113.0/3
```

### What This Pattern Covers

Projects

- AWS Operations / Configure EC2 Instance Pattern Project: Defined in setup.yml,
  this project helps organize and manage all necessary components for the
  Configure EC2 Instance pattern. It ensures that relevant files, roles, and
  configurations are logically arranged, making it easier to maintain and
  execute automation tasks.

Job Templates

- AWS Operations / Create EC2 Instance: This job template is designed to
  streamline the process of creating an EC2 instance.
- AWS Operations / Terminate EC2 Instance: This job template is designed to
  streamline the process of terminating (deleting) an EC2 instance.

Playbooks

- Create EC2 Instance Playbook: This playbook creates an EC2 instance with
  optional networking configurations.
- Terminate EC2 Instance Playbook: This playbook terminates (deletes) an
  existing EC2 instance and associated networking resources.

Surveys

- Create EC2 Instance Survey: This survey provides an interactive way to specify
  parameters for creating the EC2 instance.
- Terminate EC2 Instance Survey: This survey provides an interactive way to
  specify parameters for terminating the EC2 instance.

### Resources Created by This Pattern

1. Project

- Ensures that all relevant files, roles, and configurations are logically
  arranged, facilitating easier maintenance and execution of automation tasks.

2. Job Templates

- Outline the necessary parameters and configurations to perform network backups
  using the provided playbooks.
- Provide surveys for specifying parameters needed to run the job templates.

### How to Use

1. Use Seed Red Hat Pattern Job

- Ensure the custom EE is correctly built and available in your Ansible
  Automation Platform. Execute the "Seed Red Hat Pattern" job within the Ansible
  Automation Platform, and select the "AWS Operations" category to load this
  pattern.

2. Use the Job Templates

- In the AWS Operations / EC2 Instance Patterns execute the required job
  template to create the EC2 instance. Monitor the job execution and verify that
  the instance has been successfully created.

### Contribution

Contributions to this project are welcome. Please fork the repository, make your
changes, and submit a pull request.

### License

GNU General Public License v3.0 or later.

See LICENSE to see the full text. This project is licensed under the MIT
License. See the LICENSE file for details.
