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
module: tower_project_update_wait
version_added: "2.6"
author: "Pierre Roux (@piroux)"
short_description: Wait for Ansible Tower project to finish.
description:
    - Wait for Ansible Tower job to finish and report success or failure. See
      U(https://www.ansible.com/tower) for an overview.
options:
    project_update_id:
      description:
        - ID of the project_update to monitor.
      required: True
    min_interval:
      description:
        - Minimum interval in seconds, to request an update from Tower.
      default: 1
    max_interval:
      description:
        - Maximum interval in seconds, to request an update from Tower.
      default: 30
    timeout:
      description:
        - Maximum time in seconds to wait for a job to finish.
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
    description: job id that is being waited on
    returned: success
    type: int
    sample: 99
elapsed:
    description: total time in seconds the job took to run
    returned: success
    type: float
    sample: 10.879
started:
    description: timestamp of when the job started running
    returned: success
    type: string
    sample: "2017-03-01T17:03:53.200234Z"
finished:
    description: timestamp of when the job finished running
    returned: success
    type: string
    sample: "2017-03-01T17:04:04.078782Z"
status:
    description: current status of job
    returned: success
    type: string
    sample: successful
'''


from ansible.module_utils.ansible_tower import tower_auth_config, tower_check_mode, tower_argument_spec, HAS_TOWER_CLI
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six.moves import cStringIO as StringIO


try:
    import tower_cli
    import tower_cli.utils.exceptions as exc

    from tower_cli.conf import settings
except ImportError:
    pass


def main():
    argument_spec = tower_argument_spec()
    argument_spec.update(dict(
        project_update_id=dict(type='int', required=True),
        timeout=dict(type='int'),
        min_interval=dict(type='float', default=1),
        max_interval=dict(type='float', default=30),
    ))

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=True
    )

    if not HAS_TOWER_CLI:
        module.fail_json(msg='ansible-tower-cli required for this module')

    json_output = {}
    fail_json = None

    tower_auth = tower_auth_config(module)
    with settings.runtime_values(**tower_auth):
        tower_check_mode(module)
        project_update = tower_cli.get_resource('project_update')
        params = module.params.copy()

        # tower-cli gets very noisy when monitoring.
        # We pass in our our outfile to suppress the out during our monitor call.
        outfile = StringIO()
        params['outfile'] = outfile

        project_update_id = params.pop('project_update_id')
        try:
            result = project_update.monitor(project_update_id, **params)
        except exc.Timeout as excinfo:
            result = project_update.status(project_update_id)
            result['id'] = project_update_id
            json_output['msg'] = 'Timeout waiting for the project update to finish.'
            json_output['timeout'] = True
        except exc.NotFound as excinfo:
            fail_json = dict(msg='Unable to wait, no project update id {0} found: {1}'.format(project_update_id, excinfo), changed=False)
        except (exc.ConnectionError, exc.BadRequest) as excinfo:
            fail_json = dict(msg='Unable to wait for project update: {0}'.format(excinfo), changed=False)

    if fail_json is not None:
        module.fail_json(**fail_json)

    json_output['success'] = True
    for k in ('id', 'status', 'elapsed', 'started', 'finished'):
        json_output[k] = result.get(k)

    module.exit_json(**json_output)


if __name__ == '__main__':
    main()
