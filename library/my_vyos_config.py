#!/usr/bin/python
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

ANSIBLE_METADATA = {'metadata_version': '1.2',
                    'status': ['preview'],
                    'supported_by': 'network'}


DOCUMENTATION = """
---
module: my_vyos_config
version_added: "2.2"
author: "Nathaniel Case (@qalthos), Esa Varemo (@varesa)"
short_description: Manage VyOS configuration on remote device
description:
  - This module provides configuration file management of VyOS
    devices.  It provides arguments for managing both the
    configuration file and state of the active configuration.   All
    configuration statements are based on `set` and `delete` commands
    in the device configuration.
extends_documentation_fragment: vyos
notes:
  - Tested against VYOS 1.2.0
options:
  lines:
    description:
      - The ordered set of configuration lines to be managed and
        compared with the existing configuration on the remote
        device.
  src:
    description:
      - The C(src) argument specifies the path to the source config
        file to load.  The source config file can either be in
        bracket format or set format.  The source file can include
        Jinja2 template variables.
  backup:
    description:
      - The C(backup) argument will backup the current devices active
        configuration to the Ansible control host prior to making any
        changes.  The backup file will be located in the backup folder
        in the playbook root directory or role root directory, if
        playbook is part of an ansible role. If the directory does not
        exist, it is created.
    type: bool
    default: 'no'
  comment:
    description:
      - Allows a commit description to be specified to be included
        when the configuration is committed.  If the configuration is
        not changed or committed, this argument is ignored.
    default: 'configured by my_vyos_config'
  save:
    description:
      - The C(save) argument controls whether or not changes made
        to the active configuration are saved to disk.  This is
        independent of committing the config.  When set to True, the
        active configuration is saved.
    type: bool
    default: 'no'
"""

EXAMPLES = """
- name: configure the remote device
  my_vyos_config:
    lines:
      - set system host-name {{ inventory_hostname }}
      - set service lldp
      - delete service dhcp-server

- name: backup and load from file
  my_vyos_config:
    src: vyos.cfg
    backup: yes

- name: for idempotency, use full-form commands
  my_vyos_config:
    lines:
      # - set int eth eth2 description 'OUTSIDE'
      - set interface ethernet eth2 description 'OUTSIDE'
"""

RETURN = """
commands:
  description: The list of configuration commands sent to the device
  returned: always
  type: list
  sample: ['...', '...']
filtered:
  description: The list of configuration commands removed to avoid a load failure
  returned: always
  type: list
  sample: ['...', '...']
backup_path:
  description: The full path to the backup file
  returned: when backup is yes
  type: string
  sample: /playbooks/ansible/backup/my_vyos_config.2016-07-16@22:28:34
"""

import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.vyos.vyos import load_config, get_config, run_commands
from ansible.module_utils.network.vyos.vyos import vyos_argument_spec, get_connection


DEFAULT_COMMENT = 'configured by my_vyos_config'


def get_candidate(module):
    contents = module.params['src'] or module.params['lines']

    if module.params['src']:
        contents = format_commands(contents.splitlines())

    contents = '\n'.join(contents)
    return contents


def format_commands(commands):
    return [line for line in commands if len(line.strip()) > 0]


def run(module, result):

    # create loadable config that includes only the configuration updates
    commands = get_candidate(module)
    result['commands'] = commands

    commit = not module.check_mode
    comment = module.params['comment']

    diff = None
    if commands:
        diff = load_config(module, commands, commit=commit, comment=comment)
        module.debug("Diff: ")
        module.debug(diff)

        result['changed'] = diff is not None

    if module._diff:
        result['diff'] = {'prepared': diff}


def main():
    argument_spec = dict(
        src=dict(type='path'),
        lines=dict(type='list'),

        comment=dict(default=DEFAULT_COMMENT),
        backup=dict(type='bool', default=False),
        save=dict(type='bool', default=False),
    )

    argument_spec.update(vyos_argument_spec)
    mutually_exclusive = [('lines', 'src')]

    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=mutually_exclusive,
        supports_check_mode=True
    )

    warnings = list()

    result = dict(changed=False, warnings=warnings)

    if module.params['backup']:
        result['__backup__'] = get_config(module=module)

    if any((module.params['src'], module.params['lines'])):
        run(module, result)

    if module.params['save']:
        diff = run_commands(module, commands=['configure', 'compare saved'])[1]
        if diff != '[edit]':
            run_commands(module, commands=['save'])
            result['changed'] = True
        run_commands(module, commands=['exit'])

    module.exit_json(**result)


if __name__ == '__main__':
    main()
