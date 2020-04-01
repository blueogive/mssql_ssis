#!/usr/bin/python
# coding=utf-8
# Copyright (c) Microsoft. All rights reserved.

# Helper python script with utility methods

import sys
import os
import grp
import pwd
import getpass
import unicodedata
import subprocess
import platform
import gettext
import locale
import re
from ConfigParser import ConfigParser

#
# Static configuration values
#
ssisPathRoot = "/var/opt/ssis"
configurationFilePath = os.path.join(ssisPathRoot, "ssis.conf")
ssisUserPathRoot = os.path.expanduser("~/.ssis")
customConfigPath = os.path.join(ssisUserPathRoot, "ssis.conf")
ssisBinPath = "/opt/ssis/bin"
ssisLicenseBinPath = os.path.join(ssisBinPath, "ssis-license")
eulaConfigSection = "EULA"
eulaConfigSetting = "accepteula"
licenseConfigSection = "LICENSE"
licenseConfigRegistered = "registered"
licenseConfigPid = "pid"
telemetryConfigSection = "TELEMETRY"
telemetryConfigEnabled = "enabled"
errorExitCode = 1
successExitCode = 0
directoryOfScript = os.path.dirname(os.path.realpath(__file__))
checkInstallScript = directoryOfScript + "/checkinstall.sh"
invokeSqlservrScript = directoryOfScript + "/invokesqlservr.sh"
sudo = "sudo"
ssisUser = "ssis"
mssqlLcidEnvVariable = "MSSQL_LCID"
ssisPidEnvVariable = "SSIS_PID"
language = "language"
lcid = "lcid"
expressEdition = "express"
evaluationEdition = "evaluation"
developerEdition = "developer"
webEdition = "web"
standardEdition = "standard"
enterpriseEdition = "enterprise"
enterpriseCoreEdition = "enterprisecore"
supportedLcids = ['1033', '1031', '3082', '1036', '1040',
                  '1041', '1042', '1046', '1049', '2052', '1028']

#
# Colors to use when printing to standard out
#
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def printError(text):
    """printError

    Args:
        text(str): Text to print
    """

    _printTextInColor(text, bcolors.RED)

def printWarning(text):
    """printWarning

    Args:
        text(str): Text to print
    """

    _printTextInColor(text, bcolors.WARNING)

def checkColorSupported():
    """Check if color is supported

    Returns:
        True if color is supported, False otherwise
    """

    plat = sys.platform
    supported_platform = plat != 'Pocket PC' and (plat != 'win32' or 'ANSICON' in os.environ)
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    if not supported_platform or not is_a_tty:
        return False

    return True

def languageSelect(noprompt=False):
    """Select language

    Args:
        noprompt(boolean): True if --noprompt specified, false otherwise
    """

    lcidFromEnv = os.environ.get(mssqlLcidEnvVariable)

    if (lcidFromEnv != None):
        print _("Setting language using LCID from environment variable %s") % mssqlLcidEnvVariable
        writeLcidToConfFile(lcidFromEnv)
        return

    if(noprompt == False):
        language = locale.getdefaultlocale()[0]
        if(language == None or language == "" or language.lower() == "en_us"):
            # en_US will be chosen by default by the engine
            writeLcidToConfFile('1033')
            return
        else:
            print ""
            print _("Choose the language for %s:") % "Integration Services"
            print (u"(1) English")
            print (u"(2) Deutsch")
            print (u"(3) Español")
            print (u"(4) Français")
            print (u"(5) Italiano")
            print (u"(6) 日本語")
            print (u"(7) 한국어")
            print (u"(8) Português")
            print (u"(9) Русский")
            print (u"(10) 中文 – 简体")
            print (u"(11) 中文 （繁体）")

            languageOption = raw_input(_("Enter Option 1-11: "))

            optionToLcid = { '1': '1033', #en-US
                     '2': '1031', #de-DE
                     '3': '3082', #es-ES
                     '4': '1036', #fr-FR
                     '5': '1040', #it-IT
                     '6': '1041', #ja-JP
                     '7': '1042', #ko-KR
                     '8': '1046', #pt-BR
                     '9': '1049', #ru-RU
                     '10': '2052', #zh-CN
                     '11': '1028'} #zh-TW

            if (languageOption in optionToLcid.keys()):
                writeLcidToConfFile(optionToLcid[languageOption])
            else:
                printError(_("Invalid Option. Exiting."))
                exit(errorExitCode)

def checkTelemetryConfig():
    """Check the status of telemetry service
    """

    config = ConfigParser(allow_no_value=True)
    readConfigFromFile(config, configurationFilePath)
    # Return if telemetry option has been set
    #
    if config.has_section(telemetryConfigSection) and config.has_option(telemetryConfigSection, telemetryConfigEnabled):
        return

    enableTelemetryService(True, True)

def configTelemetryService():
    """Configure telemetry service
    """

    while True:
        agreement = raw_input(_("Send feature usage data to Microsoft. Feature usage data includes information\n\
about your hardware configuration and how you use %s.\n") % ("SQL Server Integration Services") + "[Yes/No]:")

        if agreement.strip().lower() == "yes" or agreement.strip().lower() == "y":
            enableTelemetryService(False)
            return
        elif agreement.strip().lower() == "no" or agreement.strip().lower() == "n":
            enableTelemetryService(False)
            return

def enableTelemetryService(enabled, silent=False):
    """Enable or disable ssis-telemetry service

    Args:
        enabled(boolean): True if enable ssis-telemetry, false otherwise
    """

    # if enabled:
    #     # Start the telemetry service
    #     #
    #     ret = subprocess.call(["systemctl", "start", "ssis-telemetry"])
    #     if ret != 0:
    #         printError(_("Attempting to start the telemetry service failed."))
    #         # Try enabling telemetry service so as to start it after next boot
    #         #
    #         FNULL = open(os.devnull, 'w')
    #         subprocess.call(["systemctl", "enable", "ssis-telemetry"], stdout = FNULL, stderr = subprocess.STDOUT)
    #         exit(ret)

    #     # Enable telemetry to run at startup
    #     #
    #     FNULL = open(os.devnull, 'w')
    #     ret = subprocess.call(["systemctl", "enable", "ssis-telemetry"], stdout = FNULL, stderr = subprocess.STDOUT)
    #     if ret != 0:
    #         printError(_("Attempting to enable the telemetry service to start at boot failed."))
    #         exit(ret)

    #     if not silent:
    #         print (_("Telemetry service is now running."))
    # else:
    #     # Stop the telemetry service
    #     #
    #     ret = subprocess.call(["systemctl", "stop", "ssis-telemetry"])
    #     if ret != 0:
    #         # Print error message and continue to disable the service
    #         #
    #         printError(_("Attempting to stop the telemetry service failed."))

    #     # Disable telemetry
    #     #
    #     FNULL = open(os.devnull, 'w')
    #     ret = subprocess.call(["systemctl", "disable", "ssis-telemetry"], stdout = FNULL, stderr = subprocess.STDOUT)
    #     if ret != 0:
    #         printError(_("Attempting to disable the telemetry service to start at boot failed."))
    #         exit(ret)

    #     if not silent:
    #         print (_("Telemetry service is disabled."))

    config = ConfigParser(allow_no_value=True)
    readConfigFromFile(config, configurationFilePath)
    if not config.has_section(telemetryConfigSection):
        config.add_section(telemetryConfigSection)

    config.set(telemetryConfigSection, telemetryConfigEnabled, "Y" if enabled else "N")
    writeConfigToFile(config, configurationFilePath)

def isValidLcid(lcidValue):
    """Check if a LCID value is valid.

    Args:
        lcidValue(int): LCID value
    """

    return lcidValue in supportedLcids

def writeLcidToConfFile(lcidValue):
    """Write LCID to configuration file

    Args:
        lcidValue(int): LCID value
    """

    if (isValidLcid(lcidValue) == False):
        print _("LCID %s is not supported.") % lcidValue
        exit(errorExitCode)

    config = ConfigParser(allow_no_value=True)
    readConfigFromFile(config, configurationFilePath)

    if (config.has_section(language) == False):
        config.add_section(language)

    config.set(language, lcid, lcidValue)
    writeConfigToFile(config, configurationFilePath)

def getFwlinkWithLocale(linkId):
    """Gets the correct Url for the fwlink based on the users locale

    Args:
        linkId(string): The fwlink ID

    Returns:
        The string with the complete url
    """

    baseUrl = "https://go.microsoft.com/fwlink/?LinkId=" + linkId
    localeCode = locale.getlocale()[0]
    localeToClcid = {'en_US': '0x409',  # en-US
                     'de_DE': '0x407',  # de-DE
                     'es_ES': '0x40a',  # es-ES
                     'fr_FR': '0x40c',  # fr-FR
                     'it_IT': '0x410',  # it-IT
                     'ja_JP': '0x411',  # ja-JP
                     'ko_KR': '0x412',  # ko-KR
                     'pt_BR': '0x416',  # pt-BR
                     'ru_RU': '0x419',  # ru-RU
                     'zh_CN': '0x804',  # zh-CN
                     'zh_TW': '0x404'}  # zh-TW

    if localeCode in localeToClcid:
        return baseUrl + "&clcid=" + localeToClcid[localeCode]
    else:
        return baseUrl

def checkEulaAgreement(eulaAccepted, configurationFilePath, isEvaluationEdition = False):
    """Check if the EULA agreement has been accepted.

    Args:
        eulaAccepted(boolean): User has indicated their acceptance via command-line
                               or environment variable.
        configurationFilePath(str): Configuration file path
        isEvaluationEdition(boolean): True if edition selected is evaluation, false otherwise

    Returns:
        True if accepted, False otherwise
    """

    print(_("The license terms for this product can be downloaded from:"))
    if isEvaluationEdition:
        print(getFwlinkWithLocale("855864"))
    else:
        print(getFwlinkWithLocale("855862"))
    print("")
    print(_("The privacy statement can be viewed at:"))
    print(getFwlinkWithLocale("853010"))
    print("")

    config = ConfigParser(allow_no_value=True)
    readConfigFromFile(config, configurationFilePath)

    if (
        not config.has_section(eulaConfigSection) or
        not config.has_option(eulaConfigSection, eulaConfigSetting) or
        config.get(eulaConfigSection, eulaConfigSetting) != "Y"
    ):
        if not eulaAccepted:
            agreement = raw_input(_("Do you accept the license terms?") + " [Yes/No]:")
            print("")

            if agreement.strip().lower() == "yes" or agreement.strip().lower() == "y":
                eulaAccepted = True
            else:
                return False

        if eulaAccepted:
            if not config.has_section(eulaConfigSection):
                config.add_section(eulaConfigSection)

            config.set(eulaConfigSection, eulaConfigSetting, "Y")
            writeConfigToFile(config, configurationFilePath)
            return True

    return True

def setupLicenseInfo(noprompt=False, checkStatus=True):
    """Check and set up product ID

    Args:
        noprompt (boolean): Don't prompt if True
        checkStatus (boolean): Check license status if True

    Returns:
        pid
    """

    if checkStatus:
        config = ConfigParser(allow_no_value=True)
        readConfigFromFile(config, configurationFilePath)

        if(
            config.has_section(licenseConfigSection) and
            config.has_option(licenseConfigSection, licenseConfigRegistered) and
            config.get(licenseConfigSection, licenseConfigRegistered) == "Y"
        ):
            return config.get(licenseConfigSection, licenseConfigPid)

    # Get product key
    #
    pid = getPid(noprompt)

    # Do nothing if pid is None
    #
    if pid is None:
        exit(errorExitCode)

    ret = writeLicenseInfo(pid)

    if ret != successExitCode:
        printError(_("Could not write licensing information."))
        exit(ret)

    config = ConfigParser(allow_no_value=True)
    readConfigFromFile(config, configurationFilePath)

    if not config.has_section(licenseConfigSection):
        config.add_section(licenseConfigSection)

    config.set(licenseConfigSection, licenseConfigRegistered, "Y")
    config.set(licenseConfigSection, licenseConfigPid, pid)

    writeConfigToFile(config, configurationFilePath)

    return pid

def isPaidEdition():
    """Check if the license is paid edition

    Returns:
        True if it is paid edition, False otherwise
    """

    config = ConfigParser(allow_no_value=True)
    readConfigFromFile(config, configurationFilePath)

    if config.has_section(licenseConfigSection) and config.has_option(licenseConfigSection, licenseConfigPid):
        pid = config.get(licenseConfigSection, licenseConfigPid)
        if pid is None:
            return False

        pid = pid.lower()
        if (
            pid != expressEdition and
            pid != evaluationEdition and
            pid != developerEdition
        ):
            return True

    return False

def checkSudo():
    """Check if we're running as root

    Returns:
        True if running as root, False otherwise
    """

    if (os.geteuid() == 0):
        return True

    return False

def checkSudoOrSsis():
    """Check if we're running as root or the user is in the ssis group.

    Returns:
        True if running as root or in ssis group, False otherwise
    """

    if(checkSudo() == True):
        return True

    user = getpass.getuser()
    groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
    gid = pwd.getpwnam(user).pw_gid
    groups.append(grp.getgrgid(gid).gr_name)

    if (('ssis' in groups) and (user == 'ssis')):
        return True

    return False

def makeDirectoryIfNotExists(directoryPath):
    """Make a directory if it does not exist

    Args:
        directoryPath(str): Directory path
    """

    try:
        if os.path.exists(directoryPath):
            return
        if not os.path.exists(os.path.dirname(directoryPath)):
            makeDirectoryIfNotExists(os.path.dirname(directoryPath))
        os.makedirs(directoryPath)
    except IOError, err:
        if err.errno == 13:
            printError(_("Permission denied to mkdir '%s'.") % (directoryPath))
            exit(errorExitCode)
        else:
            printError(err)
            exit(errorExitCode)

def writeConfigToFile(config, configurationFilePath):
    """Write configuration to a file

    Args:
        config(object): Config parser object
        configurationFilePath(str): Configuration file path
    """

    makeDirectoryIfNotExists(os.path.dirname(configurationFilePath))

    try:
        with open(configurationFilePath, 'w') as configFile:
            config.write(configFile)
    except IOError, err:
        if err.errno == 13:
            printError(_("Permission denied to modify %s configuration.") % ("Microsoft SQL Server Integration Services"))
        else:
            printError(err)
            exit(errorExitCode)

def readConfigFromFile(config, configurationFilePath):
    """"Read configuration from a file

    Args:
        config(object): Config parser object
        configurationFilePath(str): Configuration file path
    """

    if (os.path.exists(configurationFilePath) == True):
        try:
            config.read(configurationFilePath)
        except:
            printError(_("There was a parsing error in the configuration file."))
            exit(errorExitCode)

def listSupportedSettings(supportedSettingsList):
    """List supported settings
    """

    maxLength = 0

    for setting in supportedSettingsList:
        settingLength = len("%s.%s" % (setting.section, setting.name))
        if settingLength > maxLength:
            maxLength = settingLength

    formatString = "%-" + str(maxLength) + "s %s"
    for setting in supportedSettingsList:
        if setting.hidden == False:
            print(formatString % ("%s.%s" % (setting.section, setting.name), setting.description))

    exit(successExitCode)

def validatePid(pid):
    """Validate a product key

    Args:
        pid(str): Product key

    Returns:
        Product key if valid, otherwise None
    """

    if not (
        pid.lower() == expressEdition or
        pid.lower() == evaluationEdition or
        pid.lower() == developerEdition or
        pid.lower() == webEdition or
        pid.lower() == standardEdition or
        pid.lower() == enterpriseEdition or
        pid.lower() == enterpriseCoreEdition or
        re.match("^([A-Za-z0-9]){5}-([A-Za-z0-9]){5}\-([A-Za-z0-9]){5}\-([A-Za-z0-9]){5}\-([A-Za-z0-9]){5}$", pid)
    ):
        printError(_("Invalid PID specified: %s.") % (pid))
        print("")
        return None

    return pid

def getPidFromEditionSelected(edition):
    """Gets the correct pid to pass to the engine

    Args:
        edition(string): Edition option 1-8
    Returns:
        Pid as expected by the engine
    """
    if edition == "1":
        return evaluationEdition
    elif edition == "2":
        return developerEdition
    elif edition == "3":
        return expressEdition
    elif edition == "4":
        return webEdition
    elif edition == "5":
        return standardEdition
    elif edition == "6":
        return enterpriseEdition
    elif edition == "7":
        return enterpriseCoreEdition
    elif edition == "8":
        while(True):
            productKey = raw_input(_("Enter the 25-character product key: "))
            print("")
            if validatePid(productKey):
                break
        return productKey
    else:
        print(_("Invalid option %s.") % edition)
        exit(errorExitCode)

def getPid(noprompt=False):
    """Get product key from user

    Args:
        noprompt(bool): Don't prompt user if True

    Returns:
        Product key
    """

    pidFromEnv = os.environ.get(ssisPidEnvVariable)

    if (pidFromEnv != None):
        return validatePid(pidFromEnv)

    # If running with --noprompt return developer edition
    #
    if (noprompt):
        return developerEdition

    print(_("Choose an edition of SQL Server:"))
    print("  1) Evaluation " + _("(free, no production use rights, 180-day limit)"))
    print("  2) Developer " + _("(free, no production use rights)"))
    print("  3) Express " + _("(free)"))
    print("  4) Web " + _("(PAID)"))
    print("  5) Standard " + _("(PAID)"))
    print("  6) Enterprise " + _("(PAID)"))
    print("  7) Enterprise Core " + _("(PAID)"))
    print("  8) " + _("I bought a license through a retail sales channel and have a product key to enter."))
    print("")
    print(_("Details about editions can be found at"))
    print(getFwlinkWithLocale("2111701"))
    print("")
    print(_("Use of PAID editions of this software requires separate licensing through a"))
    print(_("Microsoft Volume Licensing program."))
    print(_("By choosing a PAID edition, you are verifying that you have the appropriate"))
    print(_("number of licenses in place to install and run this software."))
    print("")
    edition = raw_input(_("Enter your edition") + "(1-8): " )

    pid = getPidFromEditionSelected(edition)
    return validatePid(pid)

def readLicenseInfo():
    """Print SKU information
    """

    return subprocess.call([ssisLicenseBinPath, "-p", "dts", "-r"])

def writeLicenseInfo(pid):
    """Write license information
    """

    # Hide outputs from wrapper application.
    #
    FNULL = open(os.devnull, 'w')

    ret = subprocess.call([ssisLicenseBinPath, "-p", "dts", "-s", pid], stdout = FNULL, stderr = subprocess.STDOUT)

    if ret != successExitCode:
        return ret

    regFilePath = os.path.join(ssisPathRoot, "license/license.hiv")
    if os.path.exists(regFilePath):
        return subprocess.call(["chmod", "644", regFilePath])

    return errorExitCode

def configureSqlservrWithArguments(*args, **kwargs):
    """Configure SQL Server with arguments

    Args:
        args(str): Parameters to SQL Server
        kwargs(dict): Environment variables

    Returns:
        SQL Server exit code
    """

    args = [invokeSqlservrScript] + list(args)
    env = dict(os.environ)
    env.update(kwargs)
    print(_("Configuring SQL Server..."))
    return subprocess.call(args, env=env)

def runScript(pathToScript, runAsRoot=False):
    """Runs a script (optionally as root)

    Args:
        pathToScript(str): Path to script to run
        runAsRoot(boolean): Run script as root or not

    Returns:
        Script exit code
    """

    if (runAsRoot):
        if(checkSudo() == False):
            printError(_("Elevated privileges required for this action. Please run in 'sudo' mode."))
            return (errorExitCode)
        return subprocess.call([sudo, "-EH", pathToScript])
    else:
        return subprocess.call([pathToScript])

def checkInstall():
    """Checks installation of SQL Server

    Returns:
        True if there are no problems, False otherwise
    """

    return runScript(checkInstallScript, True) == 0

def addToSSISGroup():
    """Ask user to add into ssis group
    """

    user = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
    groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
    gid = pwd.getpwnam(user).pw_gid
    groups.append(grp.getgrgid(gid).gr_name)
    if (('ssis' in groups)):
        return

    agreement = raw_input(_("Only user in 'ssis' group can run 'dtexec' on Linux. Do you want to add current user into 'ssis' group?") + " [Yes/No]:")
    if agreement.strip().lower() == "yes" or agreement.strip().lower() == "y":
       subprocess.call(['bash', '-c', "usermod -aG ssis " + user])
       printWarning(_("Please logout to reload the group information."))
    elif agreement.strip().lower() == "no" or agreement.strip().lower() == "n":
       printWarning(_("Please run 'sudo usermod -aG ssis <user name>' and logout to reload the group information."))

def setupSSIS(eulaAccepted, noprompt=False):
    """Setup and initialize SSIS

    Args:
        eulaAccepted (boolean): Whether Eula was accepted on command line or via env variable
        noprompt (boolean): Don't prompt if True
    """

    # Make sure installation basics are OK
    #
    #if not checkInstall():
    #    exit(errorExitCode)

    pid = setupLicenseInfo(noprompt=noprompt)

    # Check for EULA acceptance and show EULA based on edition selected
    if not checkEulaAgreement(eulaAccepted, configurationFilePath, isEvaluationEdition = (pid == evaluationEdition)):
        printError(_("License terms not accepted. Exiting."))
        exit(errorExitCode)

    # Enable other user to read ssis.conf
    #
    if os.path.exists(configurationFilePath):
        subprocess.call(["chmod", "644", configurationFilePath])

    checkTelemetryConfig()

    languageSelect()

    print(_("Setup has completed successfully."))
    exit(successExitCode)

def _printTextInColor(text, bcolor):
    """_printTextInColor

    Args:
        text(str): Text to print
        bcolor(int): Color to use
    """

    if (checkColorSupported()):
        print(bcolor + text + bcolors.ENDC)
    else:
        print(text)

def initialize():
    """Initialize confhelper
    """

    try:
        defaultMoFilePath = os.path.dirname(os.path.realpath(__file__)) + "/loc/mo/ssis-conf-en_US.mo"
        locale.setlocale(locale.LC_ALL, '')
        localeCode = locale.getlocale()[0]

        if (localeCode == None):
            moFilePath = defaultMoFilePath
        else:
            moFilePath = os.path.dirname(os.path.realpath(__file__)) + "/loc/mo/ssis-conf-" + localeCode + ".mo"
            if (os.path.isfile(moFilePath) == False):
                print ("Locale %s not supported. Using en_US." % localeCode)
                moFilePath = defaultMoFilePath
    except:
        print ("Error in localization. Using en_US.")
        moFilePath = defaultMoFilePath

    locstrings = gettext.GNUTranslations(open(moFilePath, "rb"))
    locstrings.install()
