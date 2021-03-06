#
import os
import subprocess
import xbmc
import xbmcaddon
import urllib2
import socket
import time
import datetime
import sys

__scriptname__ = "SABnzbd Suite Foreign"
__author__     = "OpenELEC"
__url__        = "http://www.openelec.tv"
__settings__   = xbmcaddon.Addon(id='service.downloadmanager.SABnzbd-Suite-Foreign')
__cwd__        = __settings__.getAddonInfo('path')
__start__      = xbmc.translatePath(os.path.join(__cwd__, 'bin', "SABnzbd-Suite.py"))
__stop__       = xbmc.translatePath(os.path.join(__cwd__, 'bin', "SABnzbd-Suite.stop"))


checkInterval = 240
timeout       = 20
wake_times    = ['01:00', '03:00', '05:00', '07:00', '09:00', '11:00', '13:00', '15:00', '17:00', '19:00', '21:00',
                 '23:00']
idleTimer     = 0

# Launch Suite
subprocess.call(['python', __start__])

# check for launching sabnzbd
sabNzbdLaunch = (__settings__.getSetting('SABNZBD_LAUNCH').lower() == 'true')

sys.path.append(os.path.join(__cwd__, 'pylib'))
from configobj import ConfigObj

if sabNzbdLaunch:
    # SABnzbd addresses and api key
    sabNzbdAddress    = '127.0.0.1:8081'
    sabNzbdConfigFile = '/storage/.xbmc/userdata/addon_data/service.downloadmanager.SABnzbd-Suite-Foreign/sabnzbd.ini'
    sabConfiguration  = ConfigObj(sabNzbdConfigFile)
    sabNzbdApiKey     = sabConfiguration['misc']['api_key']
    sabNzbdUser       = sabConfiguration['misc']['username']
    sabNzbdPass       = sabConfiguration['misc']['password']
    sabNzbdQueue      = ['http://' + sabNzbdAddress + '/api?mode=queue&output=xml&apikey=' + sabNzbdApiKey +
                         '&ma_username=' + sabNzbdUser + '&ma_password=' + sabNzbdPass]
    sabNzbdHistory    = ['http://' + sabNzbdAddress + '/api?mode=history&output=xml&apikey=' + sabNzbdApiKey +
                         '&ma_username=' + sabNzbdUser + '&ma_password=' + sabNzbdPass]
    sabNzbdQueueKeywords = ['<status>Downloading</status>', '<status>Fetching</status>', '<priority>Force</priority>']
    sabNzbdHistoryKeywords = ['<status>Repairing</status>', '<status>Verifying</status>', '<status>Extracting</status>']

    # start checking SABnzbd for activity and prevent sleeping if necessary
    socket.setdefaulttimeout(timeout)
    
    # perform some initial checks and log essential settings
    shouldKeepAwake = (__settings__.getSetting('SABNZBD_KEEP_AWAKE').lower() == 'true')
    wakePeriodically = (__settings__.getSetting('SABNZBD_PERIODIC_WAKE').lower() == 'true')
    wakeHourIdx = int(__settings__.getSetting('SABNZBD_WAKE_AT'))
    if shouldKeepAwake:
        xbmc.log('SABnzbd-Suite: will prevent idle sleep/shutdown while downloading')
    if wakePeriodically:
        xbmc.log('SABnzbd-Suite: will try to wake system daily at ' + wake_times[wakeHourIdx])


while not xbmc.abortRequested:

    if sabNzbdLaunch:
        # reread setting in case it has changed
        shouldKeepAwake = (__settings__.getSetting('SABNZBD_KEEP_AWAKE').lower() == 'true')
        wakePeriodically = (__settings__.getSetting('SABNZBD_PERIODIC_WAKE').lower() == 'true')
        wakeHourIdx = int(__settings__.getSetting('SABNZBD_WAKE_AT'))

        # check if SABnzbd is downloading
        if shouldKeepAwake:
            idleTimer += 1
            # check SABnzbd every ~60s (240 cycles)
            if idleTimer == checkInterval:
                sabIsActive = False
                idleTimer = 0
                req = urllib2.Request(sabNzbdQueue)
                try:
                    handle = urllib2.urlopen(req)
                except IOError, e:
                    xbmc.log('SABnzbd-Suite: could not determine SABnzbds queue status', level=xbmc.LOGERROR)
                else:
                    queue = handle.read()
                    handle.close()
                    if any(x in queue for x in sabNzbdQueueKeywords):
                        sabIsActive = True

                req = urllib2.Request(sabNzbdHistory)
                try:
                    handle = urllib2.urlopen(req)
                except IOError, e:
                    xbmc.log('SABnzbd-Suite: could not determine SABnzbds history status', level=xbmc.LOGERROR)
                else:
                    history = handle.read()
                    handle.close()
                    if any(x in history for x in sabNzbdHistoryKeywords):
                        sabIsActive = True

                # reset idle timer if queue is downloading/reparing/verifying/extracting
                if sabIsActive:
                    xbmc.executebuiltin('InhibitIdleShutdown(true)')
                    xbmc.log('preventing sleep')
                else:
                    xbmc.executebuiltin('InhibitIdleShutdown(false)')
                    xbmc.log('not preventing sleep')

        # calculate and set the time to wake up at (if any)
        if wakePeriodically:
            wakeHour = wakeHourIdx * 2 + 1
            timeOfDay = datetime.time(hour=wakeHour)
            now = datetime.datetime.now()
            wakeTime = now.combine(now.date(), timeOfDay)
            if now.time() > timeOfDay:
                wakeTime += datetime.timedelta(days=1)
            secondsSinceEpoch = time.mktime(wakeTime.timetuple())
            open("/sys/class/rtc/rtc0/wakealarm", "w").write("0")
            open("/sys/class/rtc/rtc0/wakealarm", "w").write(str(secondsSinceEpoch))

    time.sleep(0.250)

subprocess.Popen(__stop__, shell=True, close_fds=True)
