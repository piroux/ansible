#!/usr/bin/python
# coding: utf-8 -*-

# (c) 2017, Wayne Witzel III <wayne@riotousliving.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: tower_inventory_source
author: "Pierre Roux (@piroux)"
version_added: "2.5"
short_description: create, update, or destroy Ansible Tower inventory source.
description:
    - Create, update, or destroy Ansible Tower inventory source. See
      U(https://www.ansible.com/tower) for an overview.
options:
    name:
      description:
        - Name to use for the job_template.
      required: True
    description:
      description:
        - Description to use for the job template.
    job_type:
      description:
        - The job_type to use for the job template.
      required: True
      choices: ["run", "check", "scan"]
    inventory:
      description:
        - Inventory to use for the job template.
    project:
      description:
        - Project to use for the job template.
      required: True
    playbook:
      description:
        - Playbook to use for the job template.
      required: True
    machine_credential:
      description:
        - Machine_credential to use for the job template.
    cloud_credential:
      description:
        - Cloud_credential to use for the job template.
    network_credential:
      description:
        - The network_credential to use for the job template.
    forks:
      description:
        - The number of parallel or simultaneous processes to use while executing the playbook.
    limit:
      description:
        - A host pattern to further constrain the list of hosts managed or affected by the playbook
    verbosity:
      description:
        - Control the output level Ansible produces as the playbook runs.
      choices: ["verbose", "debug"]
    job_tags:
      description:
        - The job_tags to use for the job template.
    skip_tags:
      description:
        - The skip_tags to use for the job template.
    host_config_key:
      description:
        - Allow provisioning callbacks using this host config key.
    extra_vars_path:
      description:
        - Path to the C(extra_vars) YAML file.
    ask_extra_vars:
      description:
        - Prompt user for C(extra_vars) on launch.
      type: bool
      default: 'no'
    ask_tags:
      description:
        - Prompt user for job tags on launch.
      type: bool
      default: 'no'
    ask_job_type:
      description:
        - Prompt user for job type on launch.
      type: bool
      default: 'no'
    ask_inventory:
      description:
        - Propmt user for inventory on launch.
      type: bool
      default: 'no'
    ask_credential:
      description:
        - Prompt user for credential on launch.
      type: bool
      default: 'no'
    become_enabled:
      description:
        - Activate privilege escalation.
      type: bool
      default: 'no'
    state:
      description:
        - Desired state of the resource.
      default: "present"
      choices: ["present", "absent"]
extends_documentation_fragment: tower
'''


EXAMPLES = '''
- name: Create tower Ping job template
  tower_job_template:
    name: Ping
    job_type: run
    inventory: Local
    project: Demo
    playbook: ping.yml
    machine_credential: Local
    state: present
    tower_config_file: "~/tower_cli.cfg"
'''

'''
https://github.com/ansible/awx/blob/9dbcc5934ee1a5774cec58b8f4ce08bea777dd7e/awx/main/models/inventory.py#L935
'''

from ansible.module_utils.ansible_tower import tower_argument_spec, tower_auth_config, tower_check_mode, HAS_TOWER_CLI

try:
    import tower_cli
    import tower_cli.utils.exceptions as exc

    from tower_cli.conf import settings
except ImportError:
    pass

import logging
from pprint import pformat
import ipdb

def configurePirouxLogger():
    # with open('mytest_piroux.log', 'a') as f:
    #     f.write(a)
    logger = logging.getLogger()
    sh = logging.StreamHandler()
    fh = logging.FileHandler('/tmp/ansible_module_debug.log')
    formatter = logging.Formatter('%(asctime)s [%(filename)s:%(lineno)s - %(funcName)s() ] %(name)-12s %(levelname)-8s %(message)s')
    sh.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger.addHandler(sh)
    logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)
    return logger

logger = configurePirouxLogger()


def update_fields(p):
    '''This updates the module field names
    to match the field names tower-cli expects to make
    calling of the modify/delete methods easier.
    '''
    params = p.copy()
    field_map = {
        'job_timeout': 'timeout',
        'source_credential': 'credential',
    }

    params_update = {}
    for old_k, new_k in field_map.items():
        v = params.pop(old_k)
        params_update[new_k] = v

    params.update(params_update)
    return params


def update_resources(module, p):
    params = p.copy()
    identity_map = {
        'inventory': 'name',
        'source_project': 'name',
        'source_credential': 'name',
    }
    for k, v in identity_map.items():
        try:
            if params[k]:
                if '_credential' in k:
                    key = 'credential'
                elif 'source_project' in k:
                    key = 'project'
                else:
                    key = k
                result = tower_cli.get_resource(key).get(**{v: params[k]})
                params[k] = result['id']
        except (exc.NotFound) as excinfo:
            module.fail_json(msg='Failed to update job template: {0}'.format(excinfo), changed=False)
    return params


def main():
    argument_spec = tower_argument_spec()
    argument_spec.update(dict(
        name=dict(required=True),
        description=dict(),
        inventory=dict(required=True),

        source=dict(choices=['file', 'scm', 'ec2', 'vmware', 'gce', 'azure', 'azure_rm', 'openstack', 'satellite6', 'cloudforms', 'custom'], required=True),

        source_project=dict(),
        source_script=dict(),
        source_path=dict(),
        source_vars=dict(),
        source_regions=dict(),

        source_credential=dict(),

        overwrite=dict(type='bool', default=False),
        overwrite_vars=dict(type='bool', default=False),
        update_on_project_update=dict(type='bool', default=False),
        update_on_launch=dict(type='bool', default=False),

        #instance_filters=dict(),
        #group_by=dict(),

        update_cache_timeout=dict(type=int),
        job_timeout=dict(type=int),

        state=dict(choices=['present', 'absent'], default='present'),
    ))

    #logger.debug("argspec: {}".format(pformat(argument_spec)))

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    if not HAS_TOWER_CLI:
        module.fail_json(msg='ansible-tower-cli required for this module')

    name = module.params.get('name')
    state = module.params.get('state')
    json_output = {'inventory_source': name, 'state': state}

    tower_auth = tower_auth_config(module)
    with settings.runtime_values(**tower_auth):
        tower_check_mode(module)
        si = tower_cli.get_resource('inventory_source')

        params = update_resources(module, module.params)
        params = update_fields(params)
        params['create_on_missing'] = True

        logger.debug("params: {}".format(pformat(params)))
        #ipdb.set_trace()
        try:
            if state == 'present':
                result = si.modify(**params)
                json_output['id'] = result['id']
            elif state == 'absent':
                result = si.delete(**params)
        except (exc.ConnectionError, exc.BadRequest, exc.NotFound) as excinfo:
            module.fail_json(msg='Failed to update inventory source: {0}'.format(excinfo), changed=False)

    json_output['changed'] = result['changed']
    module.exit_json(**json_output)


from ansible.module_utils.basic import AnsibleModule
if __name__ == '__main__':
    main()
