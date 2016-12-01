from os.path import join
from os import environ, getcwd
from sys import stderr
from .jinja_ext import JenkeyEnvironment
from jinja2.loaders import FileSystemLoader
from jinja2 import StrictUndefined, UndefinedError, TemplateNotFound
from logging import getLogger, DEBUG, StreamHandler

log = getLogger(__name__)
log.setLevel(DEBUG)
log.addHandler(StreamHandler(stderr))

templates_path = [
    "/usr/share/jenkey/templates",
    "{}/.local/share/jenkey/templates".format(environ.get('HOME')),
    "{}/templates".format(getcwd()),
]

env = JenkeyEnvironment(
    loader=FileSystemLoader(templates_path, followlinks=True),
    undefined=StrictUndefined,
    lstrip_blocks=False
)

class JenkinsJob():
    def __init__(self, id, vars=None, type="default", meta=None):
        self.id = id
        self.type = type

        self.actions    = []
        self.properties = []
        self.scms       = []
        self.triggers   = []
        self.builders   = []
        self.publishers = []
        self.wrappers   = []

        self.meta       = meta      if meta != None     else {}
        self.vars       = vars      if vars != None     else {}

        self._formatted = False


    def _getTypeTemplate(self):
        return join("jobtypes", "{}.j2".format(self.type))

    def _getBitXML(self, bit_class, bit):
        bit_name, bit_data = bit
        try:
            template = env.get_template("{}/{}.j2".format(bit_class, bit_name))
            return template.render(bit_data)
        except UndefinedError as e:
            log.fatal("Failed to render bit '{}' in job '{}':\n{}".format(bit_class, self.id, bit))
            exit(-1)
        except TemplateNotFound as e:
            log.fatal("Failed to find bit '{}/{}.j2' for job '{}' in following locations:\n{}".format(
                        bit_class, bit_name, self.id, ',\n'.join(env.loader.searchpath)))
            exit(-1)

    def _getBitRenderer(self, bit_class):
        return lambda x: self._getBitXML(bit_class, x)

    def _replaceStr(self, str):
        try:
            str = str.format(**self.vars)
        except (ValueError, KeyError) as e:
            log.error("Failed to replace in:\n{}".format(str))
            log.exception(e)
            exit(-1)
        return str
    def _replace(self, d):
        if isinstance(d, str):
            d = self._replaceStr(d)
        if isinstance(d, (list, tuple)):
            for i,item in enumerate(d):
                if isinstance(item, str) and not isinstance(d, tuple):
                    d[i] = self._replaceStr(item)
                if isinstance(item, (tuple, dict, list)):
                    self._replace(item)
        if isinstance(d, dict):
            for k,v in d.items():
                if isinstance(v, str):
                    d[k] = self._replaceStr(v)
                if isinstance(v, (tuple, dict, list)):
                    self._replace(v)
        return d

    def _replacePlaceholders(self):
        if self._formatted:
            return
        for prop, value in vars(self).items():
            try:
                setattr(self, prop, self._replace(value))
            except (ValueError, KeyError) as e:
                log.error("Error while parsing job '{}'->'{}': {}".format(self.id, prop, e))
                log.exception(e)
                exit(-1)
        self._formatted = True

    def getXML(self):
        vars = {
            "id": self.id,
            "type": self.type,
            "meta": self.meta,
            "actions":      list(map(self._getBitRenderer('actions'),       self.actions)),
            "properties":   list(map(self._getBitRenderer('properties'),    self.properties)),
            "scms":         list(map(self._getBitRenderer('scms'),          self.scms)),
            "triggers":     list(map(self._getBitRenderer('triggers'),      self.triggers)),
            "builders":     list(map(self._getBitRenderer('builders'),      self.builders)),
            "publishers":   list(map(self._getBitRenderer('publishers'),    self.publishers)),
            "wrappers":     list(map(self._getBitRenderer('wrappers'),      self.wrappers)),
        }
        vars = {**vars, **self.vars}
        try:
            return env.get_template(self._getTypeTemplate()).render(vars)
        except UndefinedError as e:
            log.fatal("Failed to render job '{}' ({}):\n{}".format(self.id, self.type, e))
            exit(-1)
        except TemplateNotFound as e:
            log.fatal("Failed to find job template 'jobtypes/{}.j2' in following locations:\n{}".format(
                self.type, ',\n'.join(env.loader.searchpath)))
            exit(-1)

    def addAction(self, name, data):
        self.actions.append((name, data))
        return self
    def addProperty(self, name, data):
        self.properties.append((name, data))
        return self
    def addScm(self, name, data):
        self.scms.append((name, data))
        return self
    def addTrigger(self, name, data):
        self.triggers.append((name, data))
        return self
    def addBuilder(self, name, data):
        self.builders.append((name, data))
        return self
    def addPublisher(self, name, data):
        self.publishers.append((name, data))
        return self
    def addWrapper(self, name, data):
        self.wrappers.append((name, data))
        return self

    def replaceActions(self, name, data):
        self.actions = [(name, data)]
        return self
    def replaceProperties(self, name, data):
        self.properties = [(name, data)]
        return self
    def replaceScms(self, name, data):
        self.scms = [(name, data)]
        return self
    def replaceTriggers(self, name, data):
        self.triggers = [(name, data)]
        return self
    def replaceBuilders(self, name, data):
        self.builders = [(name, data)]
        return self
    def replacePublishers(self, name, data):
        self.publishers = [(name, data)]
        return self
    def replaceWrappers(self, name, data):
        self.wrappers = [(name, data)]
        return self

    def insertAction(self, name, data, idx=0):
        self.actions.insert(idx, (name, data))
        return self
    def insertProperty(self, name, data, idx=0):
        self.properties.insert(idx, (name, data))
        return self
    def insertScm(self, name, data, idx=0):
        self.scms.insert(idx, (name, data))
        return self
    def insertTrigger(self, name, data, idx=0):
        self.triggers.insert(idx, (name, data))
        return self
    def insertBuilder(self, name, data, idx=0):
        self.builders.insert(idx, (name, data))
        return self
    def insertPublisher(self, name, data, idx=0):
        self.publishers.insert(idx, (name, data))
        return self
    def insertWrapper(self, name, data, idx=0):
        self.wrappers.insert(idx, (name, data))
        return self


class JenkinsProject():
    def __init__(self, vars=None):
        self.vars = vars if vars else {}
        self.jobs = {}

    def _fillJobsVars(self):
        for k,v in self.jobs.items():
            self.jobs[k].vars = {**self.vars, **v.vars}

    def addJob(self, id, vars=None, type="default", meta=None):
        job = JenkinsJob(id, vars, type, meta)
        self.jobs[id] = job
        return job

    def getJobs(self):
        self._fillJobsVars()
        for name, job in self.jobs.items():
            job._replacePlaceholders()
        return self.jobs

    def getView(self):
        self._fillJobsVars()
        for name, job in self.jobs.items():
            job._replacePlaceholders()
        name = self.vars.get("project_name", "unsorted")
        tpl = env.get_template('views/project.j2')
        return (name, tpl.render({
            "name": name,
            "jobs": list(map(lambda x: x.id, self.jobs.values())),
        }))

