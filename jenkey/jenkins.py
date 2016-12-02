from multiprocessing import Pool
import datetime
from jenkins import Jenkins
from logging import getLogger, DEBUG, StreamHandler
from sys import stderr

log = getLogger(__name__)
log.setLevel(DEBUG)
log.addHandler(StreamHandler(stderr))


class JenkinsUpdater(Jenkins):
    def _push_job(self, job):
        log.info("Processing job '{}'".format(job.id))
        try:
            if self.get_job_name(job.id):
                log.info("Reconfiguring job '{}'".format(job.id))
                self.reconfig_job(job.id, job.getXML())
            else:
                log.info("Creating job '{}'".format(job.id))
                self.create_job(job.id, job.getXML())
        except Exception as e:
            log.fatal("Failed to upload job '{}':\n{}".format(job.id, job.getXML()))
            log.exception(e)
            exit(-1)

    def push_project(self, project):
        log.info("Processing project '{}'".format(project.vars.get('project_name', 'unknown')))
        for job in project.getJobs().values():
            self._push_job(job)
            if job.vars.get("min_build_number"):
                self.set_next_build_number(job.id, job.vars.get("min_build_number", 1))

        view_name, view_xml = project.getView()
        try:
            if self.get_view_name(view_name):
                log.info("Reconfiguring view '{}'".format(view_name))
                self.reconfig_view(view_name, view_xml)
            else:
                log.info("Creating view '{}'".format(view_name))
                self.create_view(view_name, view_xml)
        except Exception as e:
            log.fatal("Failed to upload view '{}':\n{}".format(view_name, view_xml))
            log.exception(e)
            exit(-1)


def update_jenkins(projects, url='http://127.0.0.1:8080/', username='admin', password='admin', async=False, delete=True):
    jenkins = JenkinsUpdater(url, username, password)
    log.info("Project count: {}".format(len(projects)))
    log.info("Current Jenkins job count: {}\n".format(jenkins.jobs_count()))

    def process_project(project):
        jenk = JenkinsUpdater('http://127.0.0.1:8080/', 'admin', 'admin')
        jenk.push_project(project)

    t_start = datetime.datetime.utcnow()
    if async:
        p = Pool(32)
        p.map(process_project, projects.values()).wait()
    else:
        for project in projects.values():
            process_project(project)
    t_stop = datetime.datetime.utcnow()


    conf_job_list = [job.id for jobs in [job for job in [list(project.getJobs().values()) for project in projects.values()]] for job in jobs]
    cur_job_list = list(map(lambda x: x.get("name"), jenkins.get_all_jobs()))
    del_job_list = []

    for jobname in cur_job_list:
        if jobname not in conf_job_list:
            del_job_list.append(jobname)

    if len(del_job_list) > 0:
        print("Unmanaged jobs to delete:")
        print(' ', '\n  '.join(del_job_list))
        print('\nDelete? (y/N)')

        if 'y' == input().lower() or not delete:
            for job_id in del_job_list:
                log.info("Deleting job: {}".format(job_id))
                jenkins.delete_job(job_id)

    log.info("Processed {} projects ({} jobs) in {}".format(
        len(list(projects.keys())),
        sum([len(x.jobs) for x in projects.values()]),
        (t_stop-t_start).total_seconds()))
