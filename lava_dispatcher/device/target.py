# Copyright (C) 2012 Linaro Limited
#
# Author: Andy Doan <andy.doan@linaro.org>
#
# This file is part of LAVA Dispatcher.
#
# LAVA Dispatcher is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# LAVA Dispatcher is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along
# with this program; if not, see <http://www.gnu.org/licenses>.

import contextlib
import logging
import sys

import lava_dispatcher.utils as utils

from cStringIO import StringIO


def get_target(context, device_config):
    ipath = 'lava_dispatcher.device.%s' % device_config.client_type
    m = __import__(ipath, fromlist=[ipath])
    return m.target_class(context, device_config)


class Target(object):
    ''' Defines the contract needed by the dispatcher for dealing with a
    target device
    '''

    # The target deployment functions will point self.deployment_data to
    # the appropriate dictionary below. Code such as actions can contribute
    # to these structures with special handling logic
    android_deployment_data = {}
    ubuntu_deployment_data = {}

    def __init__(self, context, device_config):
        self.context = context
        self.config = device_config
        self.deployment_data = None
        self.sio = SerialIO(sys.stdout)

        self.boot_options = []
        self.scratch_dir = utils.mkdtemp(context.config.lava_image_tmpdir)
        self.deployment_data = {}

    def power_on(self):
        ''' responsible for powering on the target device and returning an
        instance of a pexpect session
        '''
        raise NotImplementedError('power_on')

    def power_off(self, proc):
        ''' responsible for powering off the target device
        '''
        raise NotImplementedError('power_off')

    def deploy_linaro(self, hwpack, rfs):
        raise NotImplementedError('deploy_image')

    def deploy_android(self, boot, system, userdata):
        raise NotImplementedError('deploy_android_image')

    def deploy_linaro_prebuilt(self, image):
        raise NotImplementedError('deploy_linaro_prebuilt')

    @contextlib.contextmanager
    def file_system(self, partition, directory):
        ''' Allows the caller to interact directly with a directory on
        the target. This method yields a directory where the caller can
        interact from. Upon the exit of this context, the changes will be
        applied to the target.

        NOTE: due to difference in target implementations, the caller should
        try and interact with the smallest directory locations possible.
        '''
        raise NotImplementedError('file_system')

    @contextlib.contextmanager
    def runner(self):
        ''' Powers on the target, returning a CommandRunner object and will
        power off the target when the context is exited
        '''
        proc = runner = None
        try:
            proc = self.power_on()
            from lava_dispatcher.client.base import CommandRunner
            runner = CommandRunner(proc, self.config.tester_str)
            yield runner
        finally:
            if proc:
                logging.info('attempting a filesystem sync before power_off')
                runner.run('sync', timeout=5)
                self.power_off(proc)

    def get_test_data_attachments(self):
        return []


class SerialIO(file):
    def __init__(self, logfile):
        self.serialio = StringIO()
        self.logfile = logfile

    def write(self, text):
        self.serialio.write(text)
        self.logfile.write(text)

    def close(self):
        self.serialio.close()
        self.logfile.close()

    def flush(self):
        self.logfile.flush()

    def getvalue(self):
        return self.serialio.getvalue()
