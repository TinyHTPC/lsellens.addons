# Initializes and launches SABnzbd, Couchpotato, Sickbeard and Headphones

import os
import sys
import shutil
import signal
import subprocess
import urllib2
import hashlib
from xml.dom.minidom import parseString
import logging
import traceback
import platform

logging.basicConfig(filename='/var/log/sabnzbd-suite.log',
                    filemode='w',
                    format='%(asctime)s SABnzbd-Suite: %(message)s',
                    level=logging.WARNING)

# helper functions
# ----------------

def createDir(dir):
    if not os.path.isdir(dir):
        os.makedirs(dir)

def getAddonSetting(doc,id):
    for element in doc.getElementsByTagName('setting'):
        if element.getAttribute('id')==id:
            return element.getAttribute('value')

def loadWebInterface(url,user,pwd):
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, user, pwd)
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)
    pagehandle = urllib2.urlopen(url)
    return pagehandle.read()

# define some things that we're gonna need, mainly paths
# ------------------------------------------------------

# addon
pAddon                = os.path.expanduser('/storage/.xbmc/addons/service.downloadmanager.SABnzbd-Suite')
pAddonHome            = os.path.expanduser('/storage/.xbmc/userdata/addon_data/service.downloadmanager.SABnzbd-Suite')

# settings
pDefaultSuiteSettings = os.path.join(pAddon, 'settings-default.xml')
pSuiteSettings        = os.path.join(pAddonHome, 'settings.xml')
pXbmcSettings         = '/storage/.xbmc/userdata/guisettings.xml'
pSabNzbdSettings      = os.path.join(pAddonHome, 'sabnzbd.ini')
pSickBeardSettings    = os.path.join(pAddonHome, 'sickbeard.ini')
pCouchPotatoServerSettings  = os.path.join(pAddonHome, 'couchpotatoserver.ini')
pHeadphonesSettings   = os.path.join(pAddonHome, 'headphones.ini')
pTransmission_Addon_Settings  ='/storage/.xbmc/userdata/addon_data/service.downloadmanager.transmission/settings.xml'

# directories
pSabNzbdComplete      = '/storage/downloads'
pSabNzbdCompleteTV    = '/storage/downloads/tvshows'
pSabNzbdCompleteMov   = '/storage/downloads/movies'
pSabNzbdCompleteMusic = '/storage/downloads/music'
pSabNzbdIncomplete    = '/storage/downloads/incomplete'
pSickBeardTvScripts   = os.path.join(pAddon, 'SickBeard/autoProcessTV')
pSabNzbdScripts       = os.path.join(pAddonHome, 'scripts')

# pylib
pPylib                = os.path.join(pAddon, 'pylib')

# service commands
sabnzbd               = ['python', os.path.join(pAddon, 'SABnzbd/SABnzbd.py'),
                         '-d', '-f',  pSabNzbdSettings, '-l 0']
sickBeard             = ['python', os.path.join(pAddon, 'SickBeard/SickBeard.py'),
                         '--daemon', '--datadir', pAddonHome, '--config', pSickBeardSettings]
couchPotatoServer     = ['python', os.path.join(pAddon, 'CouchPotatoServer/CouchPotato.py'),
                         '--daemon', '--pid_file', os.path.join(pAddonHome, 'couchpotato.pid'), '--config_file', pCouchPotatoServerSettings]
headphones            = ['python', os.path.join(pAddon, 'Headphones/Headphones.py'),
                         '-d', '--datadir', pAddonHome, '--config', pHeadphonesSettings]

# Other stuff
sabNzbdHost           = 'localhost:8081'

# create directories and settings on first launch
# -----------------------------------------------

firstLaunch = not os.path.exists(pSabNzbdSettings)
sbfirstLaunch = not os.path.exists(pSickBeardSettings)
cp2firstLaunch = not os.path.exists(pCouchPotatoServerSettings)
hpfirstLaunch = not os.path.exists(pHeadphonesSettings)

if firstLaunch:
    logging.debug('First launch, creating directories')
    createDir(pAddonHome)
    createDir(pSabNzbdComplete)
    createDir(pSabNzbdCompleteTV)
    createDir(pSabNzbdCompleteMov)
    createDir(pSabNzbdCompleteMusic)
    createDir(pSabNzbdIncomplete)
    createDir(pSabNzbdScripts)
    shutil.copy(os.path.join(pSickBeardTvScripts,'sabToSickBeard.py'), pSabNzbdScripts)
    shutil.copy(os.path.join(pSickBeardTvScripts,'autoProcessTV.py'), pSabNzbdScripts)
    os.chmod(os.path.join(pSabNzbdScripts,'sabToSickBeard.py'), 0755)

# fix for old installs
if not os.path.exists(pSabNzbdCompleteTV):
    createDir(pSabNzbdCompleteTV)

# the settings file already exists if the user set settings before the first launch
if not os.path.exists(pSuiteSettings):
    shutil.copy(pDefaultSuiteSettings, pSuiteSettings)

# read addon and xbmc settings
# ----------------------------

# Transmission-Daemon
if os.path.exists(pTransmission_Addon_Settings):
    fTransmission_Addon_Settings = open(pTransmission_Addon_Settings, 'r')
    data = fTransmission_Addon_Settings.read()
    fTransmission_Addon_Settings.close
    transmission_addon_settings = parseString(data)
    transuser                          = getAddonSetting(transmission_addon_settings, 'TRANSMISSION_USER')
    transpwd                           = getAddonSetting(transmission_addon_settings, 'TRANSMISSION_PWD')
    transauth                          = getAddonSetting(transmission_addon_settings, 'TRANSMISSION_AUTH')
    if 'true' in transauth:
        logging.debug('Transmission Authentication Enabled')
    else:
        logging.debug('Transmission Authentication Not Enabled')
else:
    transauth                          = 'false'
    logging.debug('Transmission Settings are not present')

# SABnzbd-Suite
fSuiteSettings = open(pSuiteSettings, 'r')
data = fSuiteSettings.read()
fSuiteSettings.close
suiteSettings = parseString(data)
user                 = getAddonSetting(suiteSettings, 'SABNZBD_USER')
pwd                  = getAddonSetting(suiteSettings, 'SABNZBD_PWD')
host                 = getAddonSetting(suiteSettings, 'SABNZBD_IP')
sabNzbdKeepAwake     = getAddonSetting(suiteSettings, 'SABNZBD_KEEP_AWAKE')
sabnzbd_launch       = getAddonSetting(suiteSettings, 'SABNZBD_LAUNCH')
sickbeard_launch     = getAddonSetting(suiteSettings, 'SICKBEARD_LAUNCH')
couchpotato_launch   = getAddonSetting(suiteSettings, 'COUCHPOTATO_LAUNCH')
headphones_launch    = getAddonSetting(suiteSettings, 'HEADPHONES_LAUNCH')

# merge defaults
fDefaultSuiteSettings = open(pDefaultSuiteSettings, 'r')
data = fDefaultSuiteSettings.read()
fDefaultSuiteSettings.close
DefaultSuiteSettings = parseString(data)
if not sabnzbd_launch:
    sabnzbd_launch       = getAddonSetting(DefaultSuiteSettings, 'SABNZBD_LAUNCH')
if not sickbeard_launch:
    sickbeard_launch     = getAddonSetting(DefaultSuiteSettings, 'SICKBEARD_LAUNCH')
if not couchpotato_launch:
    couchpotato_launch   = getAddonSetting(DefaultSuiteSettings, 'COUCHPOTATO_LAUNCH')
if not headphones_launch:
    headphones_launch    = getAddonSetting(DefaultSuiteSettings, 'HEADPHONES_LAUNCH')

# XBMC
fXbmcSettings = open(pXbmcSettings, 'r')
data = fXbmcSettings.read()
fXbmcSettings.close
xbmcSettings = parseString(data)
xbmcServices = xbmcSettings.getElementsByTagName('services')[0]
xbmcPort         = xbmcServices.getElementsByTagName('webserverport')[0].firstChild.data
try:
    xbmcUser     = xbmcServices.getElementsByTagName('webserverusername')[0].firstChild.data
except:
    xbmcUser = ''
try:
    xbmcPwd      = xbmcServices.getElementsByTagName('webserverpassword')[0].firstChild.data
except:
    xbmcPwd = ''

# prepare execution environment
# -----------------------------
signal.signal(signal.SIGCHLD, signal.SIG_DFL)
parch                         = platform.machine()
pnamemapper                   = os.path.join(pPylib, 'Cheetah/_namemapper.so')
pssl                          = os.path.join(pPylib, 'OpenSSL/SSL.so')
prand                         = os.path.join(pPylib, 'OpenSSL/rand.so')
pcrypto                       = os.path.join(pPylib, 'OpenSSL/crypto.so')
petree                        = os.path.join(pPylib, 'lxml/etree.so')
pobjectify                    = os.path.join(pPylib, 'lxml/objectify.so')
pyenc                         = os.path.join(pPylib, '_yenc.so')
ppar2                         = os.path.join(pAddon, 'bin/par2')
punrar                        = os.path.join(pAddon, 'bin/unrar')
punzip                        = os.path.join(pAddon, 'bin/unzip')

logging.debug(parch + ' architecture detected')

if parch.startswith('arm'):
    parch = 'arm'

if not os.path.exists(pnamemapper):
    try:
        fnamemapper                   = os.path.join(pPylib, 'multiarch/_namemapper.so.' + parch)
        shutil.copy(fnamemapper, pnamemapper)
        logging.debug('Copied _namemapper.so for ' + parch)
    except Exception,e:
        logging.error('Error Copying _namemapper.so for ' + parch)
        logging.exception(e)

if not os.path.exists(pssl):
    try:
        fssl                          = os.path.join(pPylib, 'multiarch/SSL.so.' + parch)
        shutil.copy(fssl, pssl)
        logging.debug('Copied SSL.so for ' + parch)
    except Exception,e:
        logging.error('Error Copying SSL.so for ' + parch)
        logging.exception(e)

if not os.path.exists(prand):
    try:
        frand                         = os.path.join(pPylib, 'multiarch/rand.so.' + parch)
        shutil.copy(frand, prand)
        logging.debug('Copied rand.so for ' + parch)
    except Exception,e:
        logging.error('Error Copying rand.so for ' + parch)
        logging.exception(e)

if not os.path.exists(pcrypto):
    try:
        fcrypto                       = os.path.join(pPylib, 'multiarch/crypto.so.' + parch)
        shutil.copy(fcrypto, pcrypto)
        logging.debug('Copied crypto.so for ' + parch)
    except Exception,e:
        logging.error('Error Copying crypto.so for ' + parch)
        logging.exception(e)

if not os.path.exists(petree):
    try:
        fetree                        = os.path.join(pPylib, 'multiarch/etree.so.' + parch)
        shutil.copy(fetree, petree)
        logging.debug('Copied etree.so for ' + parch)
    except Exception,e:
        logging.error('Error Copying etree.so for ' + parch)
        logging.exception(e)

if not os.path.exists(pobjectify):
    try:
        fobjectify                    = os.path.join(pPylib, 'multiarch/objectify.so.' + parch)
        shutil.copy(fobjectify, pobjectify)
        logging.debug('Copied objectify.so for ' + parch)
    except Exception,e:
        logging.error('Error Copying objectify.so for ' + parch)
        logging.exception(e)

if not os.path.exists(pyenc):
    try:
        fyenc                         = os.path.join(pPylib, 'multiarch/_yenc.so.' + parch)
        shutil.copy(fyenc, pyenc)
        logging.debug('Copied _yenc.so for ' + parch)
    except Exception,e:
        logging.error('Error Copying _yenc.so for ' + parch)
        logging.exception(e)

if not os.path.exists(ppar2):
    try:
        fpar2                         = os.path.join(pPylib, 'multiarch/par2.' + parch)
        shutil.copy(fpar2, ppar2)
        os.chmod(ppar2, 0755)
        logging.debug('Copied par2 for ' + parch)
    except Exception,e:
        logging.error('Error Copying par2 for ' + parch)
        logging.exception(e)

if not os.path.exists(punrar):
    try:
        funrar                        = os.path.join(pPylib, 'multiarch/unrar.' + parch)
        shutil.copy(funrar, punrar)
        os.chmod(punrar, 0755)
        logging.debug('Copied unrar for ' + parch)
    except Exception,e:
        logging.error('Error Copying unrar for ' + parch)
        logging.exception(e)

if not os.path.exists(punzip):
    try:
        funzip                        = os.path.join(pPylib, 'multiarch/unzip.' + parch)
        shutil.copy(funzip, punzip)
        os.chmod(punzip, 0755)
        logging.debug('Copied unzip for ' + parch)
    except Exception,e:
        logging.error('Error Copying unzip for ' + parch)
        logging.exception(e)

os.environ['PYTHONPATH'] = str(os.environ.get('PYTHONPATH')) + ':' + pPylib
sys.path.append(pPylib)
from configobj import ConfigObj

# SABnzbd start
try:
    # write SABnzbd settings
    # ----------------------
    sabNzbdConfig = ConfigObj(pSabNzbdSettings,create_empty=True)
    defaultConfig = ConfigObj()
    defaultConfig['misc'] = {}
    defaultConfig['misc']['disable_api_key']   = '0'
    defaultConfig['misc']['check_new_rel']     = '0'
    defaultConfig['misc']['auto_browser']      = '0'
    defaultConfig['misc']['username']          = user
    defaultConfig['misc']['password']          = pwd
    defaultConfig['misc']['port']              = '8081'
    defaultConfig['misc']['https_port']        = '9081'
    defaultConfig['misc']['https_cert']        = 'server.cert'
    defaultConfig['misc']['https_key']         = 'server.key'
    defaultConfig['misc']['host']              = host
    defaultConfig['misc']['web_dir']           = 'Plush'
    defaultConfig['misc']['web_dir2']          = 'Plush'
    defaultConfig['misc']['web_color']         = 'gold'
    defaultConfig['misc']['web_color2']        = 'gold'
    defaultConfig['misc']['log_dir']           = 'logs'
    defaultConfig['misc']['admin_dir']         = 'admin'
    defaultConfig['misc']['nzb_backup_dir']    = 'backup'
    defaultConfig['misc']['script_dir']        = 'scripts'

    if firstLaunch:
        defaultConfig['misc']['download_dir']  = pSabNzbdIncomplete
        defaultConfig['misc']['complete_dir']  = pSabNzbdComplete
        servers = {}
        servers['localhost'] = {}
        servers['localhost']['host']           = 'localhost'
        servers['localhost']['port']           = '119'
        servers['localhost']['enable']         = '0'
        categories = {}
        categories['tv'] = {}
        categories['tv']['name']               = 'tv'
        categories['tv']['script']             = 'sabToSickBeard.py'
        categories['tv']['priority']           = '-100'
        categories['movies'] = {}
        categories['movies']['name']           = 'movies'
        categories['movies']['dir']            = 'movies'
        categories['movies']['priority']       = '-100'
        categories['music'] = {}
        categories['music']['name']            = 'music'
        categories['music']['dir']             = 'music'
        categories['music']['priority']        = '-100'
        defaultConfig['servers'] = servers
        defaultConfig['categories'] = categories

    sabNzbdConfig.merge(defaultConfig)
    sabNzbdConfig.write()

    # also keep the autoProcessTV config up to date
    autoProcessConfig = ConfigObj(os.path.join(pSabNzbdScripts, 'autoProcessTV.cfg'), create_empty=True)
    defaultConfig = ConfigObj()
    defaultConfig['SickBeard'] = {}
    defaultConfig['SickBeard']['host']         = 'localhost'
    defaultConfig['SickBeard']['port']         = '8082'
    defaultConfig['SickBeard']['username']     = user
    defaultConfig['SickBeard']['password']     = pwd
    autoProcessConfig.merge(defaultConfig)
    autoProcessConfig.write()

    # launch SABnzbd and get the API key
    # ----------------------------------
    if firstLaunch or "true" in sabnzbd_launch:
        logging.debug('Launching SABnzbd...')
        subprocess.call(sabnzbd,close_fds=True)
        logging.debug('...done')

        # SABnzbd will only complete the .ini file when we first access the web interface
        if firstLaunch:
            loadWebInterface('http://' + sabNzbdHost,user,pwd)
        sabNzbdConfig.reload()
        sabNzbdApiKey = sabNzbdConfig['misc']['api_key']
        logging.debug('SABnzbd api key: ' + sabNzbdApiKey)
        if firstLaunch and "false" in sabnzbd_launch:
            urllib2.urlopen('http://' + sabNzbdHost + '/api?mode=shutdown&apikey=' + sabNzbdApiKey)
            logging.debug('Shutting SABnzbd down...')
except Exception,e:
    logging.exception(e)
    print 'SABnzbd: exception occurred:', e
    print traceback.format_exc()
# SABnzbd end

# SickBeard start
try:
    # write SickBeard settings
    # ------------------------
    sickBeardConfig = ConfigObj(pSickBeardSettings,create_empty=True)
    defaultConfig = ConfigObj()
    defaultConfig['General'] = {}
    defaultConfig['General']['launch_browser'] = '0'
    defaultConfig['General']['version_notify'] = '0'
    defaultConfig['General']['web_port']       = '8082'
    defaultConfig['General']['web_host']       = host
    defaultConfig['General']['web_username']   = user
    defaultConfig['General']['web_password']   = pwd
    defaultConfig['General']['cache_dir']      = pAddonHome + '/sbcache'
    defaultConfig['General']['log_dir']        = pAddonHome + '/logs'
    defaultConfig['SABnzbd'] = {}
    defaultConfig['XBMC'] = {}
    defaultConfig['XBMC']['use_xbmc']          = '1'
    defaultConfig['XBMC']['xbmc_host']         = 'localhost:' + xbmcPort
    defaultConfig['XBMC']['xbmc_username']     = xbmcUser
    defaultConfig['XBMC']['xbmc_password']     = xbmcPwd

    if "true" in sabnzbd_launch:
        defaultConfig['SABnzbd']['sab_username']   = user
        defaultConfig['SABnzbd']['sab_password']   = pwd
        defaultConfig['SABnzbd']['sab_apikey']     = sabNzbdApiKey
        defaultConfig['SABnzbd']['sab_host']       = 'http://' + sabNzbdHost + '/'

    if 'true' in transauth:
        defaultConfig['TORRENT'] = {}
        defaultConfig['TORRENT']['torrent_username']         = transuser
        defaultConfig['TORRENT']['torrent_password']         = transpwd
        defaultConfig['TORRENT']['torrent_path']             = pSabNzbdCompleteTV
        defaultConfig['TORRENT']['torrent_host']             = 'http://localhost:9091/'

    if sbfirstLaunch:
        defaultConfig['General']['tv_download_dir']       = pSabNzbdComplete
        defaultConfig['General']['metadata_xbmc_12plus']  = '0|0|0|0|0|0|0|0|0|0'
        defaultConfig['General']['nzb_method']            = 'sabnzbd'
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
        defaultConfig['SABnzbd']['sab_category']          = 'tv'
        # workaround: on first launch, sick beard will always add 
        # 'http://' and trailing '/' on its own
        defaultConfig['SABnzbd']['sab_host']              = sabNzbdHost
        defaultConfig['XBMC']['xbmc_notify_ondownload']   = '1'
        defaultConfig['XBMC']['xbmc_update_library']      = '1'
        defaultConfig['XBMC']['xbmc_update_full']         = '1'

    sickBeardConfig.merge(defaultConfig)
    sickBeardConfig.write()

    # launch SickBeard
    # ----------------
    if "true" in sickbeard_launch:
        logging.debug('Launching SickBeard...')
        subprocess.call(sickBeard,close_fds=True)
        logging.debug('...done')
except Exception,e:
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
        md5pwd =  hashlib.md5(str(pwd)).hexdigest()

    # write CouchPotatoServer settings
    # --------------------------
    couchPotatoServerConfig = ConfigObj(pCouchPotatoServerSettings,create_empty=True, list_values=False)
    defaultConfig = ConfigObj()
    defaultConfig['core'] = {}
    defaultConfig['core']['username']            = user
    defaultConfig['core']['password']            = md5pwd
    defaultConfig['core']['port']                = '8083'
    defaultConfig['core']['launch_browser']      = '0'
    defaultConfig['core']['host']                = host
    defaultConfig['core']['data_dir']            = pAddonHome
    defaultConfig['core']['show_wizard']         = '0'
    defaultConfig['core']['debug']               = '0'
    defaultConfig['core']['development']         = '0'
    defaultConfig['updater'] = {}
    defaultConfig['updater']['enabled']          = '0'
    defaultConfig['updater']['notification']     = '0'
    defaultConfig['updater']['automatic']        = '0'
    defaultConfig['xbmc'] = {}
    defaultConfig['xbmc']['enabled']             = '1'
    defaultConfig['xbmc']['host']                = 'localhost:' + xbmcPort
    defaultConfig['xbmc']['username']            = xbmcUser
    defaultConfig['xbmc']['password']            = xbmcPwd
    defaultConfig['Sabnzbd'] = {}

    if "true" in sabnzbd_launch:
        defaultConfig['Sabnzbd']['username']     = user
        defaultConfig['Sabnzbd']['password']     = pwd
        defaultConfig['Sabnzbd']['api_key']      = sabNzbdApiKey
        defaultConfig['Sabnzbd']['host']         = sabNzbdHost

    if 'true' in transauth:
        defaultConfig['transmission'] = {}
        defaultConfig['transmission']['username']         = transuser
        defaultConfig['transmission']['password']         = transpwd
        defaultConfig['transmission']['directory']        = pSabNzbdCompleteMov
        defaultConfig['transmission']['host']             = 'localhost:9091'

    if cp2firstLaunch:
        defaultConfig['xbmc']['xbmc_update_library']      = '1'
        defaultConfig['xbmc']['xbmc_update_full']         = '1'
        defaultConfig['xbmc']['xbmc_notify_onsnatch']     = '1'
        defaultConfig['xbmc']['xbmc_notify_ondownload']   = '1'
        defaultConfig['blackhole'] = {}
        defaultConfig['blackhole']['use_for']             = 'both'
        defaultConfig['blackhole']['enabled']             = '0'
        defaultConfig['Sabnzbd']['category']              = 'movies'
        defaultConfig['Sabnzbd']['pp_directory']          = pSabNzbdCompleteMov
        defaultConfig['renamer'] = {}
        defaultConfig['renamer']['enabled']               = '1'
        defaultConfig['renamer']['from']                  = pSabNzbdCompleteMov
        defaultConfig['renamer']['to']                    = '/storage/videos'
        defaultConfig['renamer']['separator']             = '.'
        defaultConfig['renamer']['cleanup']               = '0'
        defaultConfig['core']['permission_folder']        = '0644'
        defaultConfig['core']['permission_file']          = '0644'

    couchPotatoServerConfig.merge(defaultConfig)
    couchPotatoServerConfig.write()

    # launch CouchPotatoServer
    # ------------------
    if "true" in couchpotato_launch:
        logging.debug('Launching CouchPotatoServer...')
        subprocess.call(couchPotatoServer,close_fds=True)
        logging.debug('...done')
except Exception,e:
    logging.exception(e)
    print 'CouchPotatoServer: exception occurred:', e
    print traceback.format_exc()
# CouchPotatoServer end

# Headphones start
try:
    # write Headphones settings
    # -------------------------
    headphonesConfig = ConfigObj(pHeadphonesSettings,create_empty=True)
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
    defaultConfig['SABnzbd'] = {}

    if "true" in sabnzbd_launch:
        defaultConfig['SABnzbd']['sab_apikey']         = sabNzbdApiKey
        defaultConfig['SABnzbd']['sab_host']           = sabNzbdHost
        defaultConfig['SABnzbd']['sab_username']       = user
        defaultConfig['SABnzbd']['sab_password']       = pwd

    if 'true' in transauth:
        defaultConfig['Transmission'] = {}
        defaultConfig['Transmission']['transmission_username'] = transuser
        defaultConfig['Transmission']['transmission_password'] = transpwd
        defaultConfig['Transmission']['transmission_host']     = 'http://localhost:9091'

    if hpfirstLaunch:
        defaultConfig['SABnzbd']['sab_category']       = 'music'
        defaultConfig['XBMC']['xbmc_update']           = '1'
        defaultConfig['XBMC']['xbmc_notify']           = '1'
        defaultConfig['General']['music_dir']          = '/storage/music'
        defaultConfig['General']['destination_dir']    = '/storage/music'
        defaultConfig['General']['download_dir']       = pSabNzbdCompleteMusic
        defaultConfig['General']['move_files']         = '1'
        defaultConfig['General']['rename_files']       = '1'
        defaultConfig['General']['folder_permissions'] = '0644'

    headphonesConfig.merge(defaultConfig)
    headphonesConfig.write()

    # launch Headphones
    # -----------------
    if "true" in headphones_launch:
        logging.debug('Launching Headphones...')
        subprocess.call(headphones,close_fds=True)
        logging.debug('...done')
except Exception,e:
    logging.exception(e)
    print 'Headphones: exception occurred:', e
    print traceback.format_exc()
# Headphones end
