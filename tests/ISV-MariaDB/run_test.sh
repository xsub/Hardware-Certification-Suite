#!/bin/bash

FULL_LOG=/root/full-mariadb.log

# Initialize MariaDB test environment
echo "MariaDB tests started"
date

# Change to the MariaDB test directory
cd /usr/share/mysql-test

# Run MariaDB tests
if [ "$1" = "all" ]; then
    ./mysql-test-run.pl >> $FULL_LOG 2>&1
else
    ./mysql-test-run.pl --suite=$1 >> $FULL_LOG 2>&1
fi

# Print summary
echo " "
echo "MariaDB tests ended"
date

cat `find ./mysql-test/var/log -name '*.log'`

echo "Full log with MariaDB tests results can be found on SUT here: $FULL_LOG and ./mysql-test/var/log"
echo "success"
