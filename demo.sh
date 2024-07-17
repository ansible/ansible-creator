#!/bin/bash


cmd () {
  clear
  echo -e "\033[1;97m $ ansible-creator $1 --help\033[0m"
  echo
  ansible-creator $1 --help
  sleep 2
}

cmd ""
cmd "init"
cmd "init collection"
cmd "init playbook"
cmd "add"
cmd "add plugin"
cmd "add plugin action"
cmd "add plugin filter"
cmd "add plugin lookup"
cmd "add resource"
cmd "add resource devcontainer"
cmd "add resource devfile"
cmd "add resource role"