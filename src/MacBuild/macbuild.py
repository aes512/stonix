#!/usr/bin/python

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

# ============================================================================ #
#               Filename          $RCSfile: macbuild.py $
#
#               Description       Build script to use Xcode's command line 
#                                 tools, Qt, PyQt, Pyinstaller, and luggage
#                                 to create a mac stonix4mac.app and stonix.app.
#                                 stonix4mac.app facilitates running stonix.app 
#                                 (in stonix4mac.app's Resources directory) 
#                                 as the user running stonix4mac.app, or, running
#                                 stonix.app with elevated privilege.
#                                 
#               OS                Mac OS X
#               Author            Roy Nielsen
#               Last updated by   Eric Ball
#               Notes             
#               Release           $Revision: 1.0 $
#               Modified Date     $Date:  $
# ============================================================================ #


import os
import stat
import time
import optparse
import hashlib
import macbuildlib as mbl
from tempfile import mkdtemp
from Queue import LifoQueue
from subprocess import call
from shutil import rmtree, copy2
# For setupRamdisk() and detachRamdisk()
from macRamdisk import RamDisk, detach
from log_message import log_message

class MacBuilder():
    DEFAULT_RAMDISK_SIZE = 2 * 1024 * 500
    
    def __init__(self):
        parser = optparse.OptionParser()
        parser.add_option("-v", "--version", action="store", dest="version", type="string",
                          default="0", help="Set the STONIX build version number", metavar="version")
        parser.add_option("-g", "--gui", action="store_true", dest="compileGui",
                          default=False, help="If set, the PyQt files will be recompiled")
        options, __ = parser.parse_args()
        
        #####
        # If version was not included at command line, use hardcoded version number
        if options.version == "0":
            self.APPVERSION="0.8.13.10"
        else:
            self.APPVERSION=options.version
    
        #####
        # REQUIRED when tarring up stuff on the Mac filesystem - 
        # IF this is not done, tar will pick up resource forks from HFS+
        # filesystems, and when un-archiving, create separate files
        # of the resource forks and make a MESS of the filesystem.
        os.environ["COPYFILE_DISABLE"] = "true"
                
        self.RSYNC="/usr/bin/rsync"
        self.HDIUTIL="/usr/bin/hdiutil"
        self.PYUIC = mbl.getpyuicpath()
        
        # Create directory queue to replace pushd/popd
        self.dirq = LifoQueue(0)
        
        self.dirq.put(os.getcwd())
        os.chdir("..")
        
        print " "
        print " "
        print "   ******************************************************************"
        print "   ******************************************************************"
        print "   ***** App Version: " + self.APPVERSION
        print "   ******************************************************************"
        print "   ******************************************************************"
        print " "
        print " "    

        os.chdir(self.dirq.get())
        
        self.STONIX="stonix"
        self.STONIXICON="stonix_icon"
        self.STONIXVERSION=self.APPVERSION
        self.STONIX4MAC="stonix4mac"
        self.STONIX4MACICON="stonix_icon"
        self.STONIX4MACVERSION=self.APPVERSION
        
        ###############################################################################
        ###############################################################################
        ###############################################################################
        #####
        ##### Logical script start
        #####
        ###############################################################################
        ###############################################################################
        ###############################################################################
        
        #####
        # Check that user building stonix has uid 0
        self.CURRENT_USER, self.RUNNING_ID = mbl.checkBuildUser()
        
        #####
        # Create temp home directory for building with pyinstaller
        DIRECTORY = os.environ["HOME"]
        
        self.TMPHOME=mkdtemp(prefix=self.CURRENT_USER + ".")
        os.environ["HOME"] = self.TMPHOME
        os.chmod(self.TMPHOME, 0755)
        
        # Create a ramdisk and mount it to the ${self.TMPHOME}  Not yet ready for prime time
        DEVICE=self.setupRamdisk(1300, self.TMPHOME)
        print "Device for tmp ramdisk is: " + DEVICE
        
        #####
        # Copy src dir to /tmp/<username> so shutil doesn't freak about long filenames...
        # ONLY seems to be a problem on Mavericks..
        self.dirq.put(os.getcwd())
        os.chdir("../..")
        call([self.RSYNC, "-aqp", "--exclude=\".svn\"",  "--exclude=\"*.tar.gz\"", "--exclude=\"*.dmg\"", \
              "src", self.TMPHOME])
        
        #####
        # capture current directory, so we can copy back to it..
        START_BUILD_DIR=os.getcwd()
        print START_BUILD_DIR
        
        #####
        # Keep track of the directory we're starting from...
        self.dirq.put(os.getcwd())
        os.chdir(self.TMPHOME + "/src/MacBuild")
        print os.getcwd()
        
        #####
        # Compile .ui files to .py files
        if options.compileGui:
            self.compileStonix4MacAppUiFiles()
        
        # Change the versions in the program_arguments.py in both stonix and stonix4mac
        self.setProgramArgumentsVersion()
        
        # Copy stonix source to scratch build directory
        self.prepStonixBuild()
        
        #####
        # Compile the two apps...
        self.compileApp(self.STONIX, self.STONIXVERSION, self.STONIXICON)
        self.compileApp(self.STONIX4MAC, self.STONIX4MACVERSION, self.STONIX4MACICON)
        
        #####
        # Restore the HOME environment variable
        os.environ["HOME"] = DIRECTORY
        
        #####
        # Copy and create all neccessary resources to app Resources dir
        self.buildStonix4MacAppResources(self.STONIX4MAC)
        
        #####
        # tar up build & create dmg with luggage
        self.tarAndBuildStonix4MacAppPkg(self.STONIX4MAC, self.STONIX4MACVERSION)
        
        self.makeSelfUpdatePackage()
        
        os.chdir(self.TMPHOME)
        
        #####
        # Copy back to pseudo-build directory
        call([self.RSYNC, "-aqp", self.TMPHOME + "/src", START_BUILD_DIR])
        
        os.chdir(self.dirq.get())
        mbl.chownR(self.CURRENT_USER, "src")
        #####
        # chmod so it's readable by everyone, writable by the group
        mbl.chmodR(stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH|stat.S_IWGRP, "src", "append")
        
        #####
        # Return to the start dir...
        os.chdir(self.dirq.get())
        
        #####
        # Eject the ramdisk.. Not yet ready for prime time
        #self.detachRamdisk(DEVICE)
        
        print " "
        print " "
        print "    Done building stonix4mac.app..."
        print " "
        print " "    
    
    def setupRamdisk(self, size=DEFAULT_RAMDISK_SIZE, mntpnt=""):
        # TODO: Add debug/verbose options
        message_level = "normal"
        ramdisk = RamDisk(str(size), mntpnt, message_level)
        
        if not ramdisk.success:
            raise Exception("Ramdisk setup failed...")
        
        return ramdisk.getDevice()
        
    def detachRamdisk(self, device):
        # TODO: Add debug/verbose options
        message_level = "normal"
        
        if detach(device, message_level):
            log_message(r"Successfully detached disk: " + str(device).strip(), "verbose", message_level)
        else:
            log_message(r"Couldn't detach disk: " + str(device).strip())
            raise Exception(r"Cannot eject disk: " + str(device).strip())

    def compileStonix4MacAppUiFiles(self):
        ############################################################################
        ############################################################################
        ##### 
        ##### compile the .ui files to .py files for stonix4mac.app
        ##### 
        ############################################################################
        ############################################################################
    
        self.dirq.put(os.getcwd())
        os.chdir(self.STONIX4MAC)
    
        print "Starting compileStonix4MacAppUiFiles..."
        print os.getcwd()
    
        ###################################################
        # to compile the .ui files to .py files:
        print "Compiling Qt ui files to python files, for stonix4mac.app..."
        call([self.PYUIC, "admin_credentials.ui"], stdout=open("admin_credentials_ui.py", "w"))
        call([self.PYUIC, "stonix_wrapper.ui"], stdout=open("stonix_wrapper_ui.py", "w"))
        call([self.PYUIC, "general_warning.ui"], stdout=open("general_warning_ui.py", "w"))
    
        os.chdir(self.dirq.get())
        
        print "compileStonix4MacAppUiFiles Finished..."
        
    def setProgramArgumentsVersion(self):
        print "Changing versions in localize.py..."
    
        mbl.regexReplace("../stonix_resources/localize.py", r"^STONIXVERSION =.*$", r"STONIXVERSION = '" + self.APPVERSION + "'", 
                         backupname="../stonix_resources/localize.py.bak")
    
        print "Finished changing versions in localize.py..."

    def prepStonixBuild(self):
        ############################################################################
        ############################################################################
        ##### 
        ##### Copy stonix source to app build directory
        ##### 
        ############################################################################
        ############################################################################
    
        print "Starting prepStonixBuild..."
    
        #####
        # Make sure the "stonix" directory exists, so we can put
        # together and create the stonix.app
        if not os.path.isdir("stonix"):
            os.mkdir("stonix")
        elif os.path.islink("stonix"):
            os.unlink(stonix)
        else:
            #####
            # Cannot use mkdtmp here because it will make the directory on the
            # root filesystem instead of the ramdisk, then it will try to link
            # across filesystems which won't work
            TMPFILE= "stonix" + str(self.timeStamp())
            #TMPFILE=mkdtemp(prefix="stonix.")
            os.rename("stonix", TMPFILE)
            os.mkdir("stonix")
        
        copy2("../stonix.py", "stonix")
        call([self.RSYNC, "-ap", "--exclude=\".svn\"", "--exclude=\"*.tar.gz\"", \
              "--exclude=\"*.dmg\"", "../stonix_resources", "./stonix"])
    
        print "prepStonixBuild Finished..."

    def timeStamp(self):
        ############################################################################
        ############################################################################
        #####
        ##### get a time stamp
        ##### 
        ############################################################################
        ############################################################################
        #####
        # Get time in seconds
        ts = time.time()
        return ts

    def compileApp(self, appName, appVersion, appIcon):
        ############################################################################
        ############################################################################
        ##### 
        ##### Compiling stonix4mac.app
        ##### 
        ############################################################################
        ############################################################################
    
        APPNAME=appName
        APPVERSION=appVersion
        APPICON=appIcon
    
        print "Started compileApp with " + APPNAME + ", " + APPVERSION + ", " + APPICON
                
        self.dirq.put(os.getcwd())
        os.chdir(APPNAME)
                
        if os.path.isdir("build"):
            rmtree("build")
        if os.path.isdir("dist"):
            rmtree("dist")
    
        ###################################################
        # to compile a pyinstaller spec file for app creation:
        print "Creating a pyinstaller spec file for the project..."
        print mbl.pyinstMakespec([APPNAME + ".py"], True, True, False, "../" + APPICON + ".icns", \
                                 pathex=["stonix_resources/rules:stonix_resources"], specpath=os.getcwd())
        
        ###################################################
        #to build:
        print "Building the app..."
        mbl.pyinstBuild(APPNAME + ".spec", "private/tmp", os.getcwd() + "/dist", True, True)
    
        plist = "./dist/" + APPNAME + ".app/Contents/Info.plist"
        
        #####
        # Change version string of the app
        print "Changing .app version string..."
        mbl.modplist(os.getcwd() + "/dist/" + APPNAME + ".app/Contents/Info.plist", \
                     "CFBundleShortVersionString", APPVERSION)
    
        #####
        # Change icon name in the app
        print "Changing .app icon..."
        mbl.modplist(os.getcwd() + "/dist/" + APPNAME + ".app/Contents/Info.plist", \
                     "CFBundleIconFile", APPICON + ".icns")
    
        #####
        # Copy icons to the resources directory
        copy2("../" + APPICON + ".icns", "./dist/" + APPNAME + ".app/Contents/Resources")
        
        #####
        # Change mode of Info.plist to 0755
        os.chmod(plist, 0755)
    
        os.chdir(self.dirq.get())
    
        print "compileApp with " + APPNAME + ", " + APPVERSION + " Finished..."
    
    def buildStonix4MacAppResources(self, appName):
        ############################################################################
        ############################################################################
        ##### 
        ##### Copy and/or create all necessary files to the Resources directory 
        ##### of stonix4mac.app
        ##### 
        ############################################################################
        ############################################################################
    
        APPNAME=appName
        mypwd=os.getcwd()
    
        print "Started buildStonix4MacAppResources with \"" + APPNAME + "\" in " + mypwd + "..."
    
        ###################################################
        # Copy source to app dir
        call([self.RSYNC, "-aqp", "--exclude=\".svn\"" , "--exclude=\"*.tar.gz\"", "--exclude=\"*.dmg\"",\
              "../stonix_resources", "./stonix/dist/stonix.app/Contents/MacOS"])
        mypwd=os.getcwd()
        print "pwd: " + mypwd
    
        #####
        # Copy stonix.app to the stonix4mac Resources directory
        call([self.RSYNC, "-aqp", "--exclude=\".svn\"",  "--exclude=\"*.tar.gz\"", "--exclude=\"*.dmg\"", \
              "./stonix/dist/stonix.app", "./" + APPNAME + "/dist/" + APPNAME + ".app/Contents/Resources"])
        
        # Create an empty stonix.conf file
        open("./" + APPNAME + "/dist/" + APPNAME + \
              ".app/Contents/Resources/stonix.conf", "w")
        
        copy2("./stonix/dist/stonix.app/Contents/MacOS/stonix_resources/localize.py", \
              "./" + APPNAME + "/dist/" + APPNAME + ".app/Contents/MacOS")
        mypwd=os.getcwd()
        print "pwd: " + mypwd
        print "buildStonix4MacAppResources Finished..."
    
    def tarAndBuildStonix4MacAppPkg(self, appName, appVersion):
        ################################################################################
        ################################################################################
        ##### 
        ##### Archive, build installer package and wrap into a dmg:
        ##### stonix4mac.app
        #####
        ################################################################################
        ################################################################################
    
        APPNAME=appName
        APPVERSION=appVersion
        
        print "Started tarAndBuildStonix4MacApp..."
        mypwd=os.getcwd()
        print "pwd: " + mypwd
            
        #####
        # Make sure the "tarfiles" directory exists, so we can archive
        # tarfiles of the name $APPNAME-$APPVERSION.app.tar.gz there
        if not os.path.isdir("tarfiles"):
            os.mkdir("tarfiles")
        else:
            #####
            # Cannot use mkdtmp here because it will make the directory on the
            # root filesystem instead of the ramdisk, then it will try to link
            # across filesystems which won't work
            TMPFILE= "tarfiles" + str(self.timeStamp())
            #TMPFILE=mkdtemp(prefix="tariles.")
            os.rename("tarfiles", TMPFILE)
            os.mkdir("tarfiles")
        
        #####
        # tar up the app and put it in the tarfiles directory
        print "Tarring up the app & putting the tarfile in the ../tarfiles directory"
        self.dirq.put(os.getcwd())
        os.chdir("./" + APPNAME + "/dist")
        mypwd=os.getcwd()
        print "pwd: " + mypwd
        mbl.makeTarball(APPNAME + ".app", "../../tarfiles/" + APPNAME + "-" + APPVERSION + ".app.tar.gz") 
        os.chdir(self.dirq.get())
        mypwd=os.getcwd()
        print "pwd: " + mypwd
            
        ###################################################
        # to create the package
        self.dirq.put(os.getcwd())
        os.chdir(APPNAME)
        print "Putting new version into Makefile..."
        mbl.regexReplace("Makefile", r"PACKAGE_VERSION=", "PACKAGE_VERSION=" + APPVERSION)
        ###
        # Currently Makefile does not actually have a LUGGAGE_TMP variable
        mbl.regexReplace("Makefile", r"LUGGAGE_TMP\S+", "LUGGAGE_TMP=" + self.TMPHOME)
        
        if not os.path.isdir("../dmgs"):
            os.mkdir("../dmgs")
        else:
            #####
            # Cannot use mkdtmp here because it will make the directory on the
            # root filesystem instead of the ramdisk, then it will try to link
            # across filesystems which won't work
            TMPFILE= "dmgs" + str(self.timeStamp())
            #TMPFILE=mkdtemp(prefix="dmgs.")
            os.rename("../dmgs", TMPFILE)
            os.mkdir("../dmgs")
        
        print "Creating a .dmg file with a .pkg file inside for installation purposes..."
        call(["make", "dmg", "PACKAGE_VERSION=" + APPVERSION,"USE_PKGBUILD=1"])
        print "Moving the dmg to the dmgs directory."
        dmgname = APPNAME + "-" + APPVERSION + ".dmg"
        os.rename(dmgname, "../dmgs/" + dmgname)
    
        os.chdir(self.dirq.get())
    
        print "tarAndBuildStonix4MacApp... Finished"
    
    def makeSelfUpdatePackage(self):
        self.dirq.put(os.getcwd())
        os.chdir("dmgs")
        
        #####
        # Mount the dmg
        call([self.HDIUTIL, "attach", self.STONIX4MAC + "-" + self.APPVERSION + ".dmg"])
        
        #####
        # Copy the pkg to the local directory for processing
        call(["cp", "-a", "/tmp/the_luggage/" + self.STONIX4MAC + "-" + self.APPVERSION + \
              "/payload/" + self.STONIX4MAC + "-" + self.APPVERSION + ".pkg", self.STONIX4MAC + ".pkg"])  
        
        #####
        # Eject the dmg
        call([self.HDIUTIL, "eject", "/Volumes/" + self.STONIX4MAC + "-" + self.APPVERSION])
    
        #####
        # Zip up the pkg - this will be what is served for self-update
        mbl.makeZip(self.STONIX4MAC + ".pkg", self.STONIX4MAC + ".zip")

        #####
        # Create the MD5 file - used to ensure package downloads without problem
        # (NOT FOR SECURITY'S SAKE)
        md5 = hashlib.md5(open(self.STONIX4MAC + ".zip", "rb").read())
        open(self.STONIX4MAC + ".md5.txt", "w").write(md5.hexdigest())
    
        #####
        # Create the version file to put up on the server
        open(self.STONIX4MAC + ".version.txt", "w").write(self.APPVERSION)
        
        os.chdir(self.dirq.get())

if __name__ == '__main__':
    stonix4mac = MacBuilder()
