#!/usr/bin/bash

set +ex

TEST_TIME=${1-14400}
PRELOADER=${2-false}

global_result=true

if [ $TEST_TIME -lt 5 ]; then
    TEST_TIME=5
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC="\033[0m"

function error() {
    printf "${RED}[$(date)] $1${NC}\n"
}
function success() {
    printf "${GREEN}[$(date)] $1${NC}\n"
}
function info() {
    printf "${BLUE}[$(date)] $1${NC}\n"
}

function check_raid_devices() {
    device_arr=("$@")
    if [ ${#device_arr[@]} -gt 0 ]; then
        for device_name in ${device_arr[@]}; do
            # [0] Raid Devices : 2
            # [1] Total Devices : 2
            # [2] Active Devices : 2
            # [3] Working Devices : 2
            # [4] Failed Devices : 0
            # [5] Spare Devices : 0
            device_stat=( $(mdadm --detail /dev/"$device_name" | grep -oP 'Devices : (.*)' | sed 's/Devices : //') )
            if [ ${#device_stat[@]} -eq 0 ]; then
                continue
            fi
            if [ ${device_stat[0]} -ne ${device_stat[1]} ] || [ ${device_stat[1]} -ne ${device_stat[2]} ] || [ ${device_stat[2]} -ne ${device_stat[3]} ]; then
                error "Total device does not equal active device count!"
                global_result=false
            fi
            if [ ${device_stat[4]} -ne 0 ] || [ ${device_stat[5]} -ne 0 ]; then
                error "Failed or Spare devices does not equal 0!"
                global_result=false
            fi
        done
    else
        global_result=false
    fi
    if [ "$global_result" == "false" ]; then
        # Failure! Abort test!
        error "Raid status failure! Aborting!"
        info "killing fio stress test process..."
        kill $fio_pid > /dev/null 2>&1 &
    fi
}


info "Starting new test..."

# Check locales
if [ "$(echo $LANG | grep -oP '\w{2}(?=_)')" != "en" ]; then
    error "Your system language is not English! Test aborted!"
    info "SUT lang=$(echo $LANG)"
    global_result=false
fi

# Raid detect
raid_info=$(cat /proc/mdstat | grep -oP 'Personalities : (.*)' | sed 's/Personalities : //' | sed 's/\[//' | sed 's/]//')
if [ "$raid_info" != "" ]; then
    info "Raid detected: $raid_info"
else
    info "Raid not found! Test not running!"
    echo "HCS_UNSUPPORTED: no MD RAID array present on the SUT"
    exit 0
fi

# Run test
if [ "$global_result" == "true" ]; then
    # Catching logical names of raid devices
    raid_devices=( $(cat /proc/mdstat | grep -oP '\w+(?= : active)') )
    if [ ${#raid_devices[@]} -lt 1 ]; then
        error "Raid devices not found! Test aborted!"
        global_result=false
    else
        # fio writes raw random data over the array device. Only stress arrays
        # that are unmounted and carry no filesystem/LVM/LUKS signature, unless
        # the operator explicitly accepts data loss (raid_allow_data_loss=true).
        ALLOW_DATA_LOSS="${HCS_RAID_ALLOW_DATA_LOSS:-false}"
        stress_devices=()
        for device_name in "${raid_devices[@]}"; do
            if lsblk -nro MOUNTPOINT "/dev/$device_name" 2>/dev/null | grep -q '[^[:space:]]'; then
                info "Skipping /dev/$device_name: the array (or a partition on it) is mounted"
                continue
            fi
            if blkid -p "/dev/$device_name" > /dev/null 2>&1 && [ "$ALLOW_DATA_LOSS" != "true" ]; then
                info "Skipping /dev/$device_name: it holds a data signature; raid_allow_data_loss=true stresses it anyway (DESTROYS DATA)"
                continue
            fi
            stress_devices+=("$device_name")
        done

        if [ ${#stress_devices[@]} -lt 1 ]; then
            echo "HCS_UNSUPPORTED: no safely writable MD array (all arrays are mounted or hold data; raid_allow_data_loss=true overrides)"
            exit 0
        fi

        # fio takes colon-separated device paths: /dev/md0:/dev/md1
        raid_devices_string=$(printf '/dev/%s:' "${stress_devices[@]}")
        raid_devices_string="${raid_devices_string%:}"
        info "Stressing: $raid_devices_string"

        # Start storage stress test
        fio_pid=$(nohup fio -direct=1 -iodepth=32 -rw=randrw\
        -bs=4k -numjobs=4 -time_based=1 -runtime="$TEST_TIME"\
        -name=test -size=1G -filename="$raid_devices_string" > /tmp/stress_testing_storage_fio.log 2>&1 & echo $!)

        sleep 1

        kill -0 "$fio_pid"
        if [ $? -gt 0 ]; then
            error "Error running fio!"
            global_result=false
        else
            info "Fio stress test running"
        fi

        # Progress icon
        spin='-\|/'
        icon=0
        repeats=0
        while kill -0 "$fio_pid" 2>/dev/null
        do
            icon=$(( (icon+1) %4 ))
            if [ "$PRELOADER" != "disable-preloader" ]; then
                printf "\r${spin:$icon:1}"
            fi
            sleep 0.1

            # Check Raid status
            repeats=$(( (repeats+1) %200 ))
            if [ $(($repeats %200)) -eq 0 ]; then
                check_raid_devices "${raid_devices[@]}"
            fi
        done
        printf "\n"
        # End progress icon

        # Check after stop storage stress test
        check_raid_devices "${raid_devices[@]}"
    fi
fi

# Print results
if [ "$global_result" == "true" ]; then
    success 'Test status: SUCCESS!'
    exit 0
else
    error 'Test status: FAILED!'
    exit 1
fi