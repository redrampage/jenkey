Jenkey
======

Simple and flexible python-based DSL for [Jenkins](https://jenkins.io/).

##### Project State

Early development, breaking changes possible.

HowTo
=====

Jenkey's main idea is that your Jenkins configuration consists of projects,
which is a group of Jenkins jobs, sharing some common properties, which
in their turn consist of job-bits, which is a XML configuration pieces templated
by jinja2.

Firstly let's create our first project, it is done by extending the
`JenkeyProject` class:

```python
from jenkey import JenkinsProject, JenkinsJob

class MyProject(JenkinsProject):
    def __init__(self):
        super().__init__()

        # Define some vars, those will be available for all project's jobs
        self.vars = {
            "project_name": "MyProject",  # This is an important var
            "package_name": "foo",
            "repo_name": "bar",
        }
```

Next, we want to add some jobs to our project to do all the dirty work.
All `'.format()'` style placeholders in job id and variables will be
replaced by either job variables or project variables.

```python
from jenkey import JenkinsProject, JenkinsJob

class MyProject(JenkinsProject):
    def __init__(self):
        super().__init__()

        # Define some vars, those will be available for all project's jobs
        self.vars = {
            "project_name": "MyProject",  # This is an important var
            "package_name": "foo",
            "repo_name": "bar",
        }

        # Yes, '{project_name}' place holder in job_id will be replaced
        # by project variable 'project_name'
        self.jobs["build_package_{}".format(self.vars["package_name"])] = \
            JenkinsJob('id_of_the_job_in_jenkins_for_{project_name}', {
                "job_local_variable": "bar",
                "make_threads": 8,
            }

        # Let's deploy in multiple locations
        for env in ['testing', 'staging']:
            self.jobs["deploy_pachage_to_{}".format(env)] = \
                JenkinsJob('deploy_to_{environment}', {
                    "environment": env,
                     "process_baz": True,
                })

```

After jobs have been added, we should fill them with actual doing. Let's add
some bits to them.

```python
        self.jobs["build_package_{}".format(self.vars["package_name"])].\
            addTrigger('poll_scm', {
                "spec": "* * * * *",        # Bit specific variables
                                            # We can form job/project vars
                                            # to bit arguments
            }).addBuilder('shell', {
                "script": """
                    #!/bin/bash

                    if [ -f ".ready" ]; then
                        make -j {make_threads}
                    fi
                """
            }).addPublisher('archive_artifacts', {
                "artifacts": "{package_name}.zip",
            })

        for env in ["testing", "staging"]:
            self.jobs["deploy_pachage_to_{}".format(env)]. \
                addTrigger("reverse", {
                    "jobs": self.jobs["build_package_{}".\
                                format(self.vars["package_name"])].id
                }).addBuilder("shell", {
                    "script": "make deploy DEST={environment}"
                })
```

And now we can loadup our project into jenkins.

```python

from jenkey import update_jenkins

def main():
    update_jenkins({
        "my_project": MyProject(),
    })

if __name__ == "__main__":
    main()
```

Special Variables
=================

* `project_name` -      used in many log messages to identify the project,
                        somewhat required
* `min_job_number` -    used to set minimal build number for the job
                        (for all jobs if specified in project), will not lower
                        current build number, only increase it

Job Bits
========

Job bits are small pieces of jenkins job configuration XML. They are
placed in `templates` directory an divided on seven categories:

* actions
* properties
* scms
* triggers
* builders
* publishers
* wrappers

Bits are templated using jinja2 template engine and use their own
arguments to fill their fields. They cannot see project/job variables.
Bit arguments should be created using project/job vars explicitly.

For example:

```python
JenkinsJob('build_something', {
    # job variables here
    "make_target": "build_amd64",
    "threads": 8,
}).\
addBuilder('shell', {
    "script": "/usr/bin/make -j {threads} {make_target}"
})
```

This will produce bit XML:

```xml
<hudson.tasks.Shell>
  <command>
    /usr/bin/make -j 8 build_amd64
  </command>
</hudson.tasks.Shell>

```

Job Types
=========

Job type are jinja2 template of a whole job XML which glue bits together.
They are located in `templates/jobtypes` directory.
