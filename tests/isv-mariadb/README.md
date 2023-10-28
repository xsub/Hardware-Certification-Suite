# ISV-secifc test: MariaDB Test

## Introduction
Ansible playbook designed for running the MariaDB test suite as part of the ALOSF Hardware Certification Suite. 
This is an ISV-specific test created in cooperation with the MariaDB Foundation.

MariaDB is a community-developed, commercially supported fork of the MySQL relational database management system.

**Sources**: [MariaDB GitHub Repository](https://github.com/MariaDB/server)

## How to Run Tests

You can run the MariaDB tests with the provided Ansible playbook separately. Replace `10.0.0.93` with the IP address of the target machine where you want to run the tests.

```bash
$ ansible-playbook -i 10.0.0.93, automated.yml --tags mariadb-test
```

To run a specific test suite, you can use the --extra-vars option to pass in the name of the suite. For example:

```bash
$ ansible-playbook -i 10.0.0.93, automated.yml --tags mariadb-test --extra-vars "suite=suite_name"
```

Replace suite_name with the name of the test suite you'd like to run.
