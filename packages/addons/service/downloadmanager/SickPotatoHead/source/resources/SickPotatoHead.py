# Initializes and launches Couchpotato V2, Sickbeard and Headphones

import os
import sys
import shutil
import subprocess
import hashlib
import signal
from xml.dom.minidom import parseString
import logging
import traceback
import platform

logging.basicConfig(filename='/var/log/sickpotatohead.log',
                    filemode='w',
                    format='%(asctime)s SickPotatoHead: %(message)s',
                    level=logging.DEBUG)

# helper functions
# ----------------


def create_dir(dirname):
    if not os.path.isdir(dirname):
        os.makedirs(dirname)


def get_addon_setting(doc, ids):
    for element in doc.getElementsByTagName('setting'):
        if element.getAttribute('id') == ids:
            return element.getAttribute('value')


# define some things that we're gonna need, mainly paths
# ------------------------------------------------------

# addon
pAddon                = os.path.expanduser('/storage/.xbmc/addons/service.downloadmanager.SickPotatoHead')
pAddonHome            = os.path.expanduser('/storage/.xbmc/userdata/addon_data/service.downloadmanager.SickPotatoHead')

# settings
pDefaultSuiteSettings         = os.path.join(pAddon, 'settings-default.xml')
pSuiteSettings                = os.path.join(pAddonHome, 'settings.xml')
pXbmcSettings                 = '/storage/.xbmc/userdata/guisettings.xml'
pSickBeardSettings            = os.path.join(pAddonHome, 'sickbeard.ini')
pCouchPotatoServerSettings    = os.path.join(pAddonHome, 'couchpotatoserver.ini')
pHeadphonesSettings           = os.path.join(pAddonHome, 'headphones.ini')
pTransmission_Addon_Settings  = '/storage/.xbmc/userdata/addon_data/service.downloadmanager.transmission/settings.xml'

# directories
pSickPotatoHeadComplete       = '/storage/downloads'
pSickPotatoHeadCompleteTV     = '/storage/downloads/tvshows'
pSickPotatoHeadCompleteMov    = '/storage/downloads/movies'
pSickPotatoHeadWatchDir       = '/storage/downloads/watch'

# pylib
pPylib                = os.path.join(pAddon, 'pylib')

# service commands
sickBeard             = ['python', os.path.join(pAddon, 'SickBeard/SickBeard.py'),
                         '--daemon', '--datadir', pAddonHome, '--config', pSickBeardSettings]
couchPotatoServer     = ['python', os.path.join(pAddon, 'CouchPotatoServer/CouchPotato.py'), '--daemon', '--pid_file',
                         os.path.join(pAddonHome, 'couchpotato.pid'), '--config_file', pCouchPotatoServerSettings]
headphones            = ['python', os.path.join(pAddon, 'Headphones/Headphones.py'),
                         '-d', '--datadir', pAddonHome, '--config', pHeadphonesSettings]

# create directories and settings if missing
# -----------------------------------------------

sbfirstLaunch = not os.path.exists(pSickBeardSettings)
cpfirstLaunch = not os.path.exists(pCouchPotatoServerSettings)
hpfirstLaunch = not os.path.exists(pHeadphonesSettings)
if sbfirstLaunch or cpfirstLaunch or hpfirstLaunch:
    create_dir(pAddonHome)
    create_dir(pSickPotatoHeadComplete)
    create_dir(pSickPotatoHeadCompleteTV)
    create_dir(pSickPotatoHeadCompleteMov)
    create_dir(pSickPotatoHeadWatchDir)

# fix for old installs
if not os.path.exists(pSickPotatoHeadCompleteTV):
    create_dir(pSickPotatoHeadCompleteTV)

# create the settings file if missing
if not os.path.exists(pSuiteSettings):
    shutil.copy(pDefaultSuiteSettings, pSuiteSettings)

# read addon and xbmc settings
# ----------------------------

# Transmission-Daemon
if os.path.exists(pTransmission_Addon_Settings):
    fTransmission_Addon_Settings = open(pTransmission_Addon_Settings, 'r')
    data = fTransmission_Addon_Settings.read()
    fTransmission_Addon_Settings.close()
    transmission_addon_settings = parseString(data)
    transuser                          = get_addon_setting(transmission_addon_settings, 'TRANSMISSION_USER')
    transpwd                           = get_addon_setting(transmission_addon_settings, 'TRANSMISSION_PWD')
    transauth                          = get_addon_setting(transmission_addon_settings, 'TRANSMISSION_AUTH')
else:
    transauth                          = 'false'

# SickPotatoHead-Suite
fSuiteSettings = open(pSuiteSettings, 'r')
data = fSuiteSettings.read()
fSuiteSettings.close()
suiteSettings = parseString(data)
user                          = get_addon_setting(suiteSettings, 'SICKPOTATOHEAD_USER')
pwd                           = get_addon_setting(suiteSettings, 'SICKPOTATOHEAD_PWD')
host                          = get_addon_setting(suiteSettings, 'SICKPOTATOHEAD_IP')
sickbeard_launch              = get_addon_setting(suiteSettings, 'SICKBEARD_LAUNCH')
couchpotato_launch            = get_addon_setting(suiteSettings, 'COUCHPOTATO_LAUNCH')
headphones_launch             = get_addon_setting(suiteSettings, 'HEADPHONES_LAUNCH')

# merge defaults
fDefaultSuiteSettings         = open(pDefaultSuiteSettings, 'r')
data = fDefaultSuiteSettings.read()
fDefaultSuiteSettings.close()
DefaultSuiteSettings = parseString(data)
if not sickbeard_launch:
    sickbeard_launch          = get_addon_setting(DefaultSuiteSettings, 'SICKBEARD_LAUNCH')
if not couchpotato_launch:
    couchpotato_launch        = get_addon_setting(DefaultSuiteSettings, 'COUCHPOTATO_LAUNCH')
if not headphones_launch:
    headphones_launch         = get_addon_setting(DefaultSuiteSettings, 'HEADPHONES_LAUNCH')

# XBMC
fXbmcSettings                 = open(pXbmcSettings, 'r')
data                          = fXbmcSettings.read()
fXbmcSettings.close()
xbmcSettings                  = parseString(data)
xbmcServices                  = xbmcSettings.getElementsByTagName('services')[0]
xbmcPort                      = xbmcServices.getElementsByTagName('webserverport')[0].firstChild.data
try:
    xbmcUser                      = xbmcServices.getElementsByTagName('webserverusername')[0].firstChild.data
except StandardError:
    xbmcUser                      = ''
try:
    xbmcPwd                       = xbmcServices.getElementsByTagName('webserverpassword')[0].firstChild.data
except StandardError:
    xbmcPwd                       = ''

# prepare execution environment
# -----------------------------
signal.signal(signal.SIGCHLD, signal.SIG_DFL)
parch                         = platform.machine()
pnamemapper                   = os.path.join(pPylib, 'Cheetah/_namemapper.so')
petree                        = os.path.join(pPylib, 'lxml/etree.so')
pobjectify                    = os.path.join(pPylib, 'lxml/objectify.so')
punrar                        = os.path.join(pAddon, 'bin/unrar')

logging.debug(parch + ' architecture detected')

if parch.startswith('arm'):
    parch = 'arm'

if not os.path.exists(pnamemapper):
    try:
        fnamemapper                    = os.path.join(pPylib, 'multiarch/_namemapper.so.' + parch)
        shutil.copy(fnamemapper, pnamemapper)
        logging.debug('Copied _namemapper.so for ' + parch)
    except Exception, e:
        logging.error('Error Copying _namemapper.so for ' + parch)
        logging.exception(e)

if not os.path.exists(petree):
    try:
        fetree                        = os.path.join(pPylib, 'multiarch/etree.so.' + parch)
        shutil.copy(fetree, petree)
        logging.debug('Copied etree.so for ' + parch)
    except Exception, e:
        logging.error('Error Copying etree.so for ' + parch)
        logging.exception(e)

if not os.path.exists(pobjectify):
    try:
        fobjectify                    = os.path.join(pPylib, 'multiarch/objectify.so.' + parch)
        shutil.copy(fobjectify, pobjectify)
        logging.debug('Copied objectify.so for ' + parch)
    except Exception, e:
        logging.error('Error Copying objectify.so for ' + parch)
        logging.exception(e)

if not os.path.exists(punrar):
    try:
        funrar                        = os.path.join(pPylib, 'multiarch/unrar.' + parch)
        shutil.copy(funrar, punrar)
        os.chmod(punrar, 0755)
        logging.debug('Copied unrar for ' + parch)
    except Exception, e:
        logging.error('Error Copying unrar for ' + parch)
        logging.exception(e)

os.environ['PYTHONPATH']      = str(os.environ.get('PYTHONPATH')) + ':' + pPylib
sys.path.append(pPylib)
from configobj import ConfigObj

# SickBeard start
try:
    # write SickBeard settings
    # ------------------------
    sickBeardConfig = ConfigObj(pSickBeardSettings, create_empty=True)
    defaultConfig = ConfigObj()
    defaultConfig['General'] = {}
    defaultConfig['General']['launch_browser']      = '0'
    defaultConfig['General']['version_notify']      = '0'
    defaultConfig['General']['web_port']            = '8082'
    defaultConfig['General']['web_host']            = host
    defaultConfig['General']['web_username']        = user
    defaultConfig['General']['web_password']        = pwd
    defaultConfig['General']['cache_dir']           = pAddonHome + '/sbcache'
    defaultConfig['General']['log_dir']             = pAddonHome + '/logs'
    defaultConfig['XBMC'] = {}
    defaultConfig['XBMC']['use_xbmc']               = '1'
    defaultConfig['XBMC']['xbmc_host']              = 'localhost:' + xbmcPort
    defaultConfig['XBMC']['xbmc_username']          = xbmcUser
    defaultConfig['XBMC']['xbmc_password']          = xbmcPwd

    if 'true' in transauth:
        defaultConfig['TORRENT'] = {}
        defaultConfig['TORRENT']['torrent_username']         = transuser
        defaultConfig['TORRENT']['torrent_password']         = transpwd
        defaultConfig['TORRENT']['torrent_path']             = pSickPotatoHeadCompleteTV
        defaultConfig['TORRENT']['torrent_host']             = 'http://localhost:9091/'

    if sbfirstLaunch:
        defaultConfig['General']['tv_download_dir']       = pSickPotatoHeadComplete
        defaultConfig['General']['metadata_xbmc_12plus']  = '0|0|0|0|0|0|0|0|0|0'
        defaultConfig['General']['keep_processed_dir']    = '0'
        defaultConfig['General']['use_banner']            = '1'
        defaultConfig['General']['rename_episodes']       = '1'
        defaultConfig['General']['naming_ep_name']        = '0'
        defaultConfig['General']['naming_use_periods']    = '1'
        defaultConfig['General']['naming_sep_type']       = '1'
        defaultConfig['General']['naming_ep_type']        = '1'
        defaultConfig['General']['root_dirs']             = '0|/storage/tvshows'
        defaultConfig['General']['naming_custom_abd']     = '0'
        defaultConfig['General']['naming_abd_pattern']    = '%SN - %A-D - %EN'
        defaultConfig['Blackhole'] = {}
        defaultConfig['Blackhole']['torrent_dir']         = pSickPotatoHeadWatchDir
        defaultConfig['EZRSS'] = {}
        defaultConfig['EZRSS']['ezrss']                   = '1'
        defaultConfig['PUBLICHD'] = {}
        defaultConfig['PUBLICHD']['publichd']             = '1'
        defaultConfig['KAT'] = {}
        defaultConfig['KAT']['kat']                       = '1'
        defaultConfig['THEPIRATEBAY'] = {}
        defaultConfig['THEPIRATEBAY']['thepiratebay']     = '1'
        defaultConfig['Womble'] = {}
        defaultConfig['Womble']['womble']                 = '0'
        defaultConfig['XBMC']['xbmc_notify_ondownload']   = '1'
        defaultConfig['XBMC']['xbmc_notify_onsnatch']     = '1'
        defaultConfig['XBMC']['xbmc_update_library']      = '1'
        defaultConfig['XBMC']['xbmc_update_full']         = '1'

    sickBeardConfig.merge(defaultConfig)
    sickBeardConfig.write()

    # launch SickBeard
    # ----------------
    if "true" in sickbeard_launch:
        subprocess.call(sickBeard, close_fds=True)
except Exception, e:
    logging.exception(e)
    print 'SickBeard: exception occurred:', e
    print traceback.format_exc()
# SickBeard end

# CouchPotatoServer start
try:
    # empty password hack
    if pwd == '':
        md5pwd = ''
    else:
        #convert password to md5
        md5pwd = hashlib.md5(str(pwd)).hexdigest()

    # write CouchPotatoServer settings
    # --------------------------
    couchPotatoServerConfig = ConfigObj(pCouchPotatoServerSettings, create_empty=True, list_values=False)
    defaultConfig = ConfigObj()
    defaultConfig['core'] = {}
    defaultConfig['core']['username']               = user
    defaultConfig['core']['password']               = md5pwd
    defaultConfig['core']['port']                   = '8083'
    defaultConfig['core']['launch_browser']         = '0'
    defaultConfig['core']['host']                   = host
    defaultConfig['core']['data_dir']               = pAddonHome
    defaultConfig['core']['show_wizard']            = '0'
    defaultConfig['core']['debug']                  = '0'
    defaultConfig['core']['development']            = '0'
    defaultConfig['updater'] = {}
    defaultConfig['updater']['enabled']             = '0'
    defaultConfig['updater']['notification']        = '0'
    defaultConfig['updater']['automatic']           = '0'
    defaultConfig['xbmc'] = {}
    defaultConfig['xbmc']['enabled']                = '1'
    defaultConfig['xbmc']['host']                   = 'localhost:' + xbmcPort
    defaultConfig['xbmc']['username']               = xbmcUser
    defaultConfig['xbmc']['password']               = xbmcPwd

    if 'true' in transauth:
        defaultConfig['transmission'] = {}
        defaultConfig['transmission']['username']         = transuser
        defaultConfig['transmission']['password']         = transpwd
        defaultConfig['transmission']['directory']        = pSickPotatoHeadCompleteMov
        defaultConfig['transmission']['host']             = 'localhost:9091'

    if cpfirstLaunch:
        defaultConfig['xbmc']['xbmc_update_library']      = '1'
        defaultConfig['xbmc']['xbmc_update_full']         = '1'
        defaultConfig['xbmc']['xbmc_notify_onsnatch']     = '1'
        defaultConfig['xbmc']['xbmc_notify_ondownload']   = '1'
        defaultConfig['blackhole'] = {}
        defaultConfig['blackhole']['directory']           = pSickPotatoHeadWatchDir
        defaultConfig['blackhole']['use_for']             = 'torrent'
        defaultConfig['blackhole']['enabled']             = '0'
        defaultConfig['Renamer'] = {}
        defaultConfig['Renamer']['enabled']               = '0'
        defaultConfig['Renamer']['from']                  = pSickPotatoHeadCompleteMov
        defaultConfig['Renamer']['separator']             = '.'
        defaultConfig['Renamer']['cleanup']               = '0'
        defaultConfig['nzbindex'] = {}
        defaultConfig['nzbindex']['enabled']              = '0'
        defaultConfig['mysterbin'] = {}
        defaultConfig['mysterbin']['enabled']             = '0'
        defaultConfig['core']['permission_folder']        = '0644'
        defaultConfig['core']['permission_file']          = '0644'
        defaultConfig['searcher'] = {}
        defaultConfig['searcher']['preferred_method']     = 'torrent'

    couchPotatoServerConfig.merge(defaultConfig)
    couchPotatoServerConfig.write()

    # launch CouchPotatoServer
    # ------------------
    if "true" in couchpotato_launch:
        subprocess.call(couchPotatoServer, close_fds=True)
except Exception, e:
    logging.exception(e)
    print 'CouchPotatoServer: exception occurred:', e
    print traceback.format_exc()
# CouchPotatoServer end

# Headphones start
try:
    # write Headphones settings
    # -------------------------
    headphonesConfig = ConfigObj(pHeadphonesSettings, create_empty=True)
    defaultConfig = ConfigObj()
    defaultConfig['General'] = {}
    defaultConfig['General']['launch_browser']            = '0'
    defaultConfig['General']['http_port']                 = '8084'
    defaultConfig['General']['http_host']                 = host
    defaultConfig['General']['http_username']             = user
    defaultConfig['General']['http_password']             = pwd
    defaultConfig['General']['check_github']              = '0'
    defaultConfig['General']['check_github_on_startup']   = '0'
    defaultConfig['General']['cache_dir']                 = pAddonHome + '/hpcache'
    defaultConfig['General']['log_dir']                   = pAddonHome + '/logs'
    defaultConfig['XBMC'] = {}
    defaultConfig['XBMC']['xbmc_enabled']                 = '1'
    defaultConfig['XBMC']['xbmc_host']                    = 'localhost:' + xbmcPort
    defaultConfig['XBMC']['xbmc_username']                = xbmcUser
    defaultConfig['XBMC']['xbmc_password']                = xbmcPwd

    if 'true' in transauth:
        defaultConfig['Transmission'] = {}
        defaultConfig['Transmission']['transmission_username'] = transuser
        defaultConfig['Transmission']['transmission_password'] = transpwd
        defaultConfig['Transmission']['transmission_host']     = 'http://localhost:9091'

    if hpfirstLaunch:
        defaultConfig['XBMC']['xbmc_update']                  = '1'
        defaultConfig['XBMC']['xbmc_notify']                  = '1'
        defaultConfig['General']['music_dir']                 = '/storage/music'
        defaultConfig['General']['destination_dir']           = '/storage/music'
        defaultConfig['General']['torrentblackhole_dir']      = pSickPotatoHeadWatchDir
        defaultConfig['General']['download_torrent_dir']      = pSickPotatoHeadComplete
        defaultConfig['General']['move_files']                = '1'
        defaultConfig['General']['rename_files']              = '1'
        defaultConfig['General']['folder_permissions']        = '0644'
        defaultConfig['General']['isohunt']                   = '1'
        defaultConfig['General']['kat']                       = '1'
        defaultConfig['General']['mininova']                  = '1'
        defaultConfig['General']['piratebay']                 = '1'

    headphonesConfig.merge(defaultConfig)
    headphonesConfig.write()

    # launch Headphones
    # -----------------
    if "true" in headphones_launch:
        subprocess.call(headphones, close_fds=True)
except Exception, e:
    logging.exception(e)
    print 'Headphones: exception occurred:', e
    print traceback.format_exc()
# Headphones end