import os
import jinja2

class JenkeyEnvironment(jinja2.Environment):
    """Override join_path() to enable relative template paths."""
    def join_path(self, template, parent):
        return os.path.join(os.path.dirname(parent), template)
