#!/usr/bin/python3

"""
 kernelstub
 The automatic manager for using the Linux Kernel EFI Stub to boot

 Copyright 2017-2018 Ian Santopietro <isantop@gmail.com>

Permission to use, copy, modify, and/or distribute this software for any purpose
with or without fee is hereby granted, provided that the above copyright notice
and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
THIS SOFTWARE.

Please see the provided LICENSE.txt file for additional distribution/copyright
terms.
"""

import os, logging, subprocess

class NoBlockDevError(Exception):
    pass

class UUIDNotFoundError(Exception):
    pass

class Drive():

    drive_name = 'none'
    root_fs = '/'
    root_path = '/'
    root_uuid = '12345-12345-12345'
    esp_fs = '/boot/efi'
    esp_path = '/boot/efi'
    esp_num = 0

    def __init__(self, root_path="/", esp_path="/boot/efi"):
        self.log = logging.getLogger('kernelstub.Drive')
        self.log.debug('loaded kernelstub.Drive')

        self.esp_path = esp_path
        self.root_path = root_path
        self.log.debug('root path = %s' % self.root_path)
        self.log.debug('esp_path = %s' % self.esp_path)

        # If the esp partion is an autofs mount, listdir will trigger a mount.
        os.listdir(esp_path)
        self.mtab = self.get_drives()

        try:
            self.root_fs = self.get_part_dev(self.root_path)
            self.esp_fs = self.get_part_dev(self.esp_path)
            self.drive_name = self.get_drive_dev(self.esp_fs)
            self.esp_num = self.esp_fs[-1]
            self.root_uuid = self.get_uuid(self.root_path)
        except NoBlockDevError as e:
            self.log.exception('Could not find a block device for the a ' +
                               'partition. This is a critical error and we ' +
                               'cannot continue.')
            self.log.debug(e)
            exit(174)
        except UUIDNotFoundError as e:
            self.log.exception('Could not get a UUID for the a filesystem. ' +
                               'This is a critical error and we cannot continue')
            self.log.debug(e)
            exit(177)


        self.log.debug('Root is on /dev/%s' % self.drive_name)
        self.log.debug('root_fs = %s ' % self.root_fs)
        self.log.debug('root_uuid is %s' % self.root_uuid)


    def get_drives(self):
        self.log.debug('Getting a list of drives')
        with open('/proc/mounts', mode='r') as proc_mounts:
            mtab = proc_mounts.readlines()

        self.log.debug(mtab)
        return mtab

    def get_mtab_entry(self, path):
        self.log.debug('Getting mtab entry for %s' % path)
        for mount in self.mtab:
            drive = mount.split(" ")
            if drive[1] == path and drive[2] != 'autofs':
                return drive
        raise NoBlockDevError('Couldn\'t find the mtab entry for %s' % path)

    def get_part_dev(self, path):
        self.log.debug('Getting the block device file for %s' % path)
        mtab_entry = self.get_mtab_entry(path)
        part_dev = os.path.realpath(mtab_entry[0])
        self.log.debug('%s is on %s' % (path, part_dev))
        return part_dev

    def get_part_fs(self, path):
        self.log.debug('Getting the filesystem type for %s' % path)
        mtab_entry = self.get_mtab_entry(path)
        fstype = mtab_entry[2]
        self.log.debug('%s is on %s filesystem' % (path, fstype))
        return fstype

    def get_part_options(self, path):
        self.log.debug('Getting the mount options for %s' % path)
        mtab_entry = self.get_mtab_entry(path)
        options = mtab_entry[3]
        self.log.debug('Mount options for %s are %s' % (path, options))
        return options

    def get_drive_dev(self, esp):
        # Ported from bash, out of @jackpot51's firmware updater
        efi_name = os.path.basename(esp)
        efi_sys = os.readlink('/sys/class/block/%s' % efi_name)
        disk_sys = os.path.dirname(efi_sys)
        disk_name = os.path.basename(disk_sys)
        self.log.debug('ESP is a partition on /dev/%s' % disk_name)
        return disk_name

    def get_uuid(self, path):
        self.log.debug('Looking for UUID for path %s' % path)
        try:
            args = ['findmnt', '-n', '-o', 'UUID', '--mountpoint', path]
            result = subprocess.run(args, stdout=subprocess.PIPE)
            uuid = result.stdout.decode('ASCII')
            uuid = uuid.strip()
            return uuid
        except OSError as e:
            raise UUIDNotFoundError from e

