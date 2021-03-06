'''
###############################################################################
#                                                                             #
# Copyright 2015.  Los Alamos National Security, LLC. This material was       #
# produced under U.S. Government contract DE-AC52-06NA25396 for Los Alamos    #
# National Laboratory (LANL), which is operated by Los Alamos National        #
# Security, LLC for the U.S. Department of Energy. The U.S. Government has    #
# rights to use, reproduce, and distribute this software.  NEITHER THE        #
# GOVERNMENT NOR LOS ALAMOS NATIONAL SECURITY, LLC MAKES ANY WARRANTY,        #
# EXPRESS OR IMPLIED, OR ASSUMES ANY LIABILITY FOR THE USE OF THIS SOFTWARE.  #
# If software is modified to produce derivative works, such modified software #
# should be clearly marked, so as not to confuse it with the version          #
# available from LANL.                                                        #
#                                                                             #
# Additionally, this program is free software; you can redistribute it and/or #
# modify it under the terms of the GNU General Public License as published by #
# the Free Software Foundation; either version 2 of the License, or (at your  #
# option) any later version. Accordingly, this program is distributed in the  #
# hope that it will be useful, but WITHOUT ANY WARRANTY; without even the     #
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    #
# See the GNU General Public License for more details.                        #
#                                                                             #
###############################################################################

@change: 01/06/2014 Original Implementation
@version: 0.8.0
@author: ekkehard j. koch
'''
import unittest
import os
from filehelper import FileHelper
import environment
import logdispatcher
import StateChgLogger


class zzzTestFrameworkfilehelper(unittest.TestCase):

    def setUp(self):
        self.environ = environment.Environment()
        self.environ.setverbosemode(True)
        self.logdispatch = logdispatcher.LogDispatcher(self.environ)
        self.state = StateChgLogger.StateChgLogger(self.logdispatch,
                                                   self.environ)
        self.homedirectory = os.path.expanduser('~')
        self.fh = FileHelper(self.logdispatch)

    def tearDown(self):
        pass

    def test_create_file_and_remove(self):
# Create Files
        addfilesuccess = True
        self.fh.removeAllFiles()
        self.files = {"tf3": {"path": self.homedirectory + "/temp/temp/temp/tf3.txt",
                              "remove": False,
                              "content": None,
                              "permissions": 0o0777,
                              "owner": os.getuid(),
                              "group": "wheel"},
                      "tf2": {"path": self.homedirectory + "/temp/temp/tf2.txt",
                              "remove": False,
                              "content": "This is a test",
                              "permissions": "0777",
                              "owner": "root",
                              "group": 20},
                      "tf1": {"path": self.homedirectory + "/temp/tf1.txt",
                              "remove": False,
                              "content": None,
                              "permissions": None,
                              "owner": None,
                              "group": None}
                      }
        for filelabel, fileinfo in sorted(self.files.items()):
            addfilereturn = self.fh.addFile(filelabel,
                                            fileinfo["path"],
                                            fileinfo["remove"],
                                            fileinfo["content"],
                                            fileinfo["permissions"],
                                            fileinfo["owner"],
                                            fileinfo["group"]
                                            )
            if not addfilereturn:
                addfilesuccess = False
        self.assertTrue(addfilesuccess, "Initial adding of Files to FileHelper failed!")
        filescreated = self.fh.fixFiles()
        self.assertTrue(filescreated, "1st creation of Files Failed!")
# Remove Files without removing directories
        updatefilesuccess = True
        self.files["tf1"]["remove"] = True
        self.files["tf2"]["remove"] = True
        self.files["tf3"]["remove"] = True
        for filelabel, fileinfo in sorted(self.files.items()):
            updatefilereturn = self.fh.updateFile(filelabel,
                                               fileinfo["path"],
                                               fileinfo["remove"],
                                               fileinfo["content"],
                                               fileinfo["permissions"],
                                               fileinfo["owner"],
                                               fileinfo["group"]
                                               )
            if not updatefilereturn:
                updatefilesuccess = False
        self.assertTrue(updatefilesuccess, "1st updateing of Files to FileHelper failed!")
        filesremoval = self.fh.fixFiles()
        self.assertTrue(filesremoval, "1st removal of Files Failed!")
        self.fh.setDefaultRemoveEmptyParentDirectories(True)
# Remove Files without removing directories
        updatefilesuccess = True
        self.files["tf1"]["remove"] = False
        self.files["tf2"]["remove"] = False
        self.files["tf3"]["remove"] = False
        for filelabel, fileinfo in sorted(self.files.items()):
            updatefilereturn = self.fh.updateFile(filelabel,
                                               fileinfo["path"],
                                               fileinfo["remove"],
                                               fileinfo["content"],
                                               fileinfo["owner"],
                                               fileinfo["group"]
                                               )
            if not updatefilereturn:
                updatefilesuccess = False
        filescreated = self.fh.fixFiles()
        self.assertTrue(filescreated, "2nd creation of Files Failed!")
        filesremoval = self.fh.fixFiles()
# Remove Files with removing directories
        updatefilesuccess = True
        self.files["tf1"]["remove"] = True
        self.files["tf2"]["remove"] = True
        self.files["tf3"]["remove"] = True
        for filelabel, fileinfo in sorted(self.files.items()):
            updatefilereturn = self.fh.updateFile(filelabel,
                                               fileinfo["path"],
                                               fileinfo["remove"],
                                               fileinfo["content"],
                                               fileinfo["permissions"],
                                               fileinfo["owner"],
                                               fileinfo["group"]
                                               )
            if not updatefilereturn:
                updatefilesuccess = False
        self.assertTrue(updatefilesuccess, "2nd updateing of Files to FileHelper failed!")
        filesremoval = self.fh.fixFiles()
        self.assertTrue(filesremoval, "2nd removal of Files Failed!")

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    