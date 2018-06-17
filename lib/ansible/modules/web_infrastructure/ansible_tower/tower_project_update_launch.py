#!/usr/bin/python
# coding: utf-8 -*-

# (c) 2017, Wayne Witzel III <wayne@riotousliving.com>
# (c) 2018, Pierre Roux <pierre.roux01@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: tower_project_update_launch
author: "Pierre Roux (@piroux)"
version_added: "2.5"
short_description: Launch an Ansible Tower project update.
description:
    - Launch an Ansible Tower project update. See
      U(https://www.ansible.com/tower) for an overview.
options:
    project:
      description:
        - Name of the project to use.
      required: True
    organization:
      description:
        - Organization of the project.
extends_documentation_fragment: tower
'''

EXAMPLES = '''
- name: Launch a job
  tower_job_launch:
    job_template: "My Job Template"
  register: job
- name: Wait for job max 120s
  tower_job_wait:
    job_id: job.id
    timeout: 120
'''

RETURN = '''
id:
    description: job id of the newly launched job
    returned: success
    type: int
    sample: 86
status:
    description: status of newly launched job
    returned: success
    type: string
    sample: pending
'''


from ansible.module_utils.basic import AnsibleModule

from ansible.module_utils.ansible_tower import tower_auth_config, tower_check_mode, tower_argument_spec, HAS_TOWER_CLI

try:
    import tower_cli
    import tower_cli.utils.exceptions as exc

    from tower_cli.conf import settings
except ImportError:
    pass


def main():
    """
    project Resource project    The project field.  False   False   True    True
    name    String  The name field. True    False   True    False
    launch_type Choices: manual,relaunch,relaunch,callback,scheduled,dependency,workflow,sync,scm   The launch_type field.  True    False   True    True
    status  Choices: new,pending,waiting,running,successful,failed,error,canceled   The status field.   True    False   True    True
    job_type    Choices: run,check  The job_type field. True    False   True    True
    job_explanation String  The job_explanation field.  True    False   True    False
    created String  The created field.  True    False   True    False
    elapsed String  The elapsed field.  True    False   True    False
    scm_type    mapped_choice   The scm_type field. False   False   True    True
    """
    argument_spec = tower_argument_spec()
    argument_spec.update(dict(
        project=dict(required=True),
        organization=dict(),
    ))

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=True
    )

    if not HAS_TOWER_CLI:
        module.fail_json(msg='ansible-tower-cli required for this module')

    json_output = dict(changed=False)

    """
    print('--- DEBUG (before tower_auth_config')
    from pprint import pformat
    print('# module.params:\n', pformat(module.params))
    """

    tower_auth = tower_auth_config(module)
    with settings.runtime_values(**tower_auth):
        tower_check_mode(module)
        try:
            params = module.params.copy()
            project = tower_cli.get_resource('project')

            """
            print('--- DEBUG after')
            from pprint import pformat
            print('# module.params:\n', pformat(module.params))
            print('# params:\n', pformat(params))
            print('# tower_auth:\n', pformat(tower_auth))
            """
            try:
                name = params.pop('project')
                organization_name = params.pop('organization')
                organization = tower_cli.get_resource('organization').get(name=organization_name)
                """
                print('# org:\n', pformat(organization))
                """
                result = project.get(name=name, organization=organization['id'])
                params['pk'] = result['id']
            except exc.NotFound as excinfo:
                module.fail_json(msg='Unable to launch project update, {0}/{1} was not found: {2}'.format('project', name, excinfo), changed=False)

            result = project.update(**params)
            json_output['id'] = result['id']
            json_output['changed'] = result['changed']
            result = project.status(params['pk'], detail=True)
            json_output['status'] = result
        except (exc.ConnectionError, exc.BadRequest) as excinfo:
            module.fail_json(msg='Unable to launch project update: {0}'.format(excinfo), changed=False)

    module.exit_json(**json_output)


if __name__ == '__main__':
    main()
