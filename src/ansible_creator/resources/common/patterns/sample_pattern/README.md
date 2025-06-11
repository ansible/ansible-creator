## Weather Forecasting Pattern

### Description

This pattern is designed to help get the weather forecast for a given location.
It uses the `site.yml` playbook to retrieve the weather forecast for a specified
location.

### What This Pattern Covers

- Retrieves the weather forecast for a given location.
- Uses the `site.yml` playbook to perform the weather forecasting task.

### Resources Created by This Pattern

1. Project

- Ensures that all relevant files and configurations are logically arranged,
  facilitating easier maintenance and execution of automation tasks.
- This project is used to organize and manage the weather forecasting task.

2. Execution Environment

- A custom EE configuration to provide the necessary dependencies and
  environment for the task execution.

3. Job Templates

- Outline the necessary parameters and configurations to perform weather
  forecasting task using the provided playbook.

### How to Use

1. Load the pattern

- Ensure the custom EE is correctly built and available in your Ansible
  Automation Platform. Use the pattern service to load the pattern within the
  Ansible Automation Platform.

2. Use the Job Templates

- In the Weather Forecasting Patterns execute the required job template to
  retrieve the weather forecast for a given airport code. Monitor the job
  execution and verify that the forecast has been successfully retrieved.

### Contribution

Contributions to this project are welcome. Please fork the repository, make your
changes, and submit a pull request.

### License

GNU General Public License v3.0 or later.

See LICENSE to see the full text. This project is licensed under the MIT
License. See the LICENSE file for details.
