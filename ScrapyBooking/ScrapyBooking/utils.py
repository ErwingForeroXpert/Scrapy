import logging
import time
import os
import glob
import re
from datetime import datetime
from logging import warning
from . import constants as const
from date_extractor import extract_date
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def waitElement(driver, element, by=By.ID, exist=False):
    """wait for the element appear on the Screen

    Args:
        driver (WebDriver): web driver see https://www.selenium.dev/documentation/webdriver/
        element (Object<Any>): element see https://selenium-python.readthedocs.io/locating-elements.html
        by (String, optional): Searcher. Defaults to By.ID.
        exist (bool, optional): if element already existed. Defaults to False.

    Returns:
        WebDriverWait: Constructor, takes a WebDriver instance and timeout in seconds.
    """

    return WebDriverWait(driver, 30).until(
        lambda driver: driver.find_element(by,element) if exist else EC.visibility_of_element_located((by, element))
    )

def wait_element_is_interactable(driver, element, by=By.ID, wait=1):
    """Wait that element is intera

    Args:
        element ([type]): [description]
    """
    while not (elementIsVisible(driver, element, by, wait=wait)):
        time.sleep(1)

def waitElementDisable(driver, element, by=By.ID):
    """wait for the element disappear of the screen

    Args:
        driver (WebDriver): web driver see https://www.selenium.dev/documentation/webdriver/
        element (Object<Any>): element see https://selenium-python.readthedocs.io/locating-elements.html
        by (String, optional): Searcher. Defaults to By.ID.

    Returns:
        WebDriverWait: Constructor, takes a WebDriver instance and timeout in seconds.
    """

    return WebDriverWait(driver, 30).until(
        EC.invisibility_of_element_located((by, element))
    )

def elementIsVisible(driver, element, by=By.ID, wait=2):
    """Validate if element is visible

    Args:
        driver (WebDriver): web driver see https://www.selenium.dev/documentation/webdriver/
        element (Object<Any>): element see https://selenium-python.readthedocs.io/locating-elements.html
        by (String, optional): Searcher. Defaults to By.ID.
        wait (int, optional): delay before starting the process. Defaults to 2.

    Returns:
        bool: if element is visible
    """
    time.sleep(wait)
    try:
        return driver.find_element(by, element).is_displayed()
    except Exception as e:
        warning(e)
        return False
            
def waitDownload(path):
    """wait that elements in state downloading disappear

    Args:
        path (String): Folder of downloads
    """
    tempfiles = 0
    while tempfiles == 0:
        time.sleep(1)
        for fname in os.listdir(path):
            if "crdownload" in fname or "tmp" in fname:
                tempfiles = 0  
                break
            else:
                tempfiles = 1

def createNecesaryFolders(path, folders):
    """Create folders

    Args:
        path (String): Folder parents
        folders (String): Folder childrens
    """
    for folder in folders:
        if not os.path.exists(os.path.join(path, folder)):
            os.makedirs(os.path.join(path, folder))

def deleteTemporals(path):
    """Delete elements of path

    Args:
        path (String): Folder parent
    """
    for fname in os.listdir(path):
        os.remove(os.path.join(path, fname))


def getMostRecentFile(path, _filter=None):
    """Get most recent file for date

    Args:
        path (String): Folder parent
        _filter (function, optional): filter name of documents. Defaults to None.

    Returns:
        String: path of file most recent
    """
    list_of_files = glob.glob(fr'{path}/*')
    list_of_files = _filter(list_of_files) if _filter is not None else list_of_files
    return max(list_of_files, key=os.path.getctime)

def clickAlert(driver):
    """Click alert message if appear

    Args:
        driver (WebDriver): web driver see https://www.selenium.dev/documentation/webdriver/
    """
    try:
        WebDriverWait(driver, 5).until (EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()
    except Exception as e:
        insertInLog("alert does not Exist in page", "info")

def insertInLog(message, type="debug"):
    """Insert new line in file log

    Args:
        message (String): message
        type (str, optional): type of log. Defaults to "debug".
    """
    logging.basicConfig(filename='checklisteficacia.log', encoding='utf-8', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
    loger = {
        "debug": logging.debug,
        "warning": logging.warning,
        "info": logging.info,
        "error": logging.error,
    }[type]

    loger(f"{datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')} {message} \n")
    print(f"{datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')} {message} \n")

def ifErrorFalse(cb, *args):
    """if generate error return false

    Args:
        cb (function): function

    Returns:
        Any: function return or False
    """
    try:
        return cb(*args)
    except Exception as e:
        return False

def isEmpty(value):
    """if is empty value

    Args:
        value (String|int): posible empty value 

    Returns:
        bool: if is empty value
    """
    try:
        return str(value).strip() == ""
    except Exception as e:
        return True

def string2Number(value):
    """Convert String to Number

    Args:
        value (String): [description]

    Raises:
        Exception: [description]

    Returns:
        [type]: [description]
    """
    value = value if isinstance(value, str) else str(value)
    _temp_val = re.findall(r"\d+", value) 
    if _temp_val != []:
        return int(_temp_val[0])
    else:
        raise Exception(f"{value} has not number")

def exceptionHandler(func):
    """Manage Exceptions

    Args:
        func (function): callback function
    """
    def inner_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            _message = f"{func.__name__} - {e}"
            insertInLog(_message, "error")
            raise Exception(_message)
    return inner_function

def isIterable(posibleList):
    """Validate if element is iterable

    Args:
        posibleList (Any): posible iterable element

    Returns:
        bool: if element is iterable
    """
    try:
        if isinstance(posibleList, (tuple, list)) or hasattr(posibleList, "__iter__"):
            _ = posibleList[0]
            return True

        return False
    except Exception as e:
        return False

def extract_meters_and_kilometers(text: str, reg_extractor: str = r"(\d{1,3}.*\m)") -> str:

    results = re.findall(reg_extractor, text)

    return results[0]

def filter_empty_string(value: 'list[str]|str') -> 'list[str]|str':
    regex_empty = r'(\n|\t)+'
    if isinstance(value, (str)):
        return re.sub(regex_empty, "", value)
    elif isIterable(value):
        result = []
        for val in value:
            if (v:=re.sub(regex_empty, "", val)) != "":
                result.append(v)
        return result[0] if len(result) == 1 else result

def group_of_text(values: 'list[str]') -> 'list[str]':
    groups = []
    actual_group = ""
    for value in values:
        if (v:=filter_empty_string(value)) != "":
            actual_group = f"{actual_group} {v}".strip()
        else:
            if actual_group != "":
                groups.append(actual_group)
                actual_group = ""

def get_date(value: str, format: str = const.FORMAT_DATE) -> str:

    date_extracted = extract_date(value)

    if date_extracted is not None:
        return date_extracted.strftime(format)
    else:
        return ""