import os
import re
import json
import time
import random
import argparse
import requests
from threading import Thread
from bs4 import BeautifulSoup
from pprint import pprint
from sys import argv, exit
from tqdm import tqdm

base_url = 'https://clip.unl.pt'
filename = 'clipData.json'
transform_path = {
    '\\' : '_',
    '/': '_',
    ':': '_',
    '*': '_',
    '?': '_',
    '"': '',
    '<': '_',
    '>': '_',
    '|': '_'
}

def extract_mine(soup: BeautifulSoup, only_course_name: [], only_year: []):
    #REGEXS
    year_patt = r'<a href="/utente/eu/aluno/ano_lectivo\?aluno=[0-9]*&amp;institui%E7%E3o=[0-9]{5}&amp;ano_lectivo=[0-9]{4}">[0-9]{4}/[0-9]{2}</a>'
    course_patt = r'<a href="/utente/eu/aluno/ano_lectivo/unidades\?ano_lectivo=[0-9]{4}&amp;institui%E7%E3o=[0-9]{5}&amp;aluno=[0-9]{5}&amp;unidade=([0-9]*)&amp;tipo_de_per%EDodo_lectivo=[a-z,A-Z]&amp;per%EDodo_lectivo=[0-9]">.*</a>'
    # DEPRECATED #TODO fix regex below #post note let this bug be here :') #poster note get it deeper in search instead of regex
    #course_code_patt = r'(?!<a href="/utente/eu/aluno/ano_lectivo/unidades\?ano_lectivo=[0-9]{4}&amp;institui%E7%E3o=[0-9]{5}&amp;aluno=[0-9]{5}&amp;unidade=)[0-9]*(?=&amp;tipo_de_per%EDodo_lectivo=[a-z,A-Z]&amp;per%EDodo_lectivo=[0-9]">.*</a>)'
    docs_patt = r'<a href="/utente/eu/aluno/ano_lectivo/unidades/unidade_curricular/actividade/documentos\?tipo_de_per%EDodo_lectivo=[a-z,A-Z]&amp;ano_lectivo=[0-9]{4}&amp;per%EDodo_lectivo=[0-9]&amp;aluno=[0-9]{5}&amp;institui%E7%E3o=97747&amp;unidade_curricular=[0-9]*&amp;tipo_de_documento_de_unidade=.*">.*</a>'
    file_patt = r'<a href="/objecto\?oid=[0-9]*&amp;oin=.*">'

    years_href = {}
    courses_href = {}
    status = tqdm(soup.findAll('a', href=True), desc='Checking all years')
    for elem in status:
        if re.match(year_patt, str(elem)) != None:
            years_href[elem.text] = elem['href']
    status = tqdm(years_href.items())
    delayed = []
    for year, elem in status:
        if only_year != None and not year in only_year:
            continue
        status.set_description(f'Extracting {year}')
        r = requests.get(f'{base_url}{str(elem)}', cookies=cookies)
        status.set_description(f'Extracted {year}')
        soup = BeautifulSoup(r.content, 'html.parser')
        hits = 0
        for sub in soup.findAll('a', href=True):
            status.set_description(f'Parsing {year}')
            if re.match(course_patt, str(sub)) != None:
                hits += 1
                tmp = courses_href.get(sub.text, {})
                tmp[year] = {
                    #DEPRECATED
                    #'codigo': re.findall(course_code_patt, str(sub))[0],
                    'codigo': re.search(course_patt, str(sub)).group(1),
                    'href': sub['href']
                }
                courses_href[sub.text] = tmp
        delayed.append(f'Parsed {year} with {hits} courses')
        if(len(delayed)==len(status)):
            status.set_description('All years parsed')
    for text in delayed:
        print(text)
    status = tqdm(courses_href.items())
    counter = 0
    for course_name, course_dic in status:
        if only_course_name != None and not course_name in only_course_name:
            continue
        counter += 1
        course_path = os.path.join(path, 'clip', str(course_name).translate(str(course_name).maketrans(transform_path)).strip())
        status.set_description(f'Checking if course {course_name} folder exists')
        if not os.path.exists(course_path):
            status.set_description(f'Creating course {course_name} folder')
            os.makedirs(course_path)
        for year, year_data in course_dic.items():
            year_path = os.path.join(course_path, str(year).translate(str(year).maketrans(transform_path)).strip())
            status.set_description(f'Checking if year {year} folder for course {course_name} exists')
            if not os.path.exists(year_path):
                status.set_description(f'Creating year {year} folder for course {course_name}')
                os.makedirs(year_path)
            status.set_description(f'Creating {course_name}({year}) metadata')
            save(year_data, name=os.path.join(year_path, 'metadata.json'))
            status.set_description(f'Requesting data of {course_name}({year})')
            r = requests.get(f'{base_url}{str(year_data["href"])}', cookies=cookies)
            soup = BeautifulSoup(r.content, 'html.parser')
            for sub in soup.findAll('a', href=True):
                status.set_description(f'Processing {course_name}({year})')
                if re.match(docs_patt, str(sub)) != None:
                    section_name = sub.text
                    docs_path = os.path.join(year_path, sub.text)
                    status.set_description(f'Checking if {section_name} folder of {course_name}({year}) exists')
                    if not os.path.exists(docs_path):
                        status.set_description(f'Creating {section_name} folder for {course_name}({year})')
                        os.makedirs(docs_path)
                    status.set_description(f'Requesting {section_name} of {course_name}({year})')
                    r = requests.get(f'{base_url}{str(sub["href"])}', cookies=cookies)
                    soup = BeautifulSoup(r.content, 'html.parser')
                    for sub in soup.findAll('a', href=True):
                        status.set_description(f'Processing files from {section_name} of {course_name}({year})')
                        if re.match(file_patt, str(sub)) != None:
                            file_name = str(sub.parent.parent.findChildren("td")[0].text).strip()
                            status.set_description(f'Requesting {file_name} in {section_name} of {course_name}({year})')
                            r = requests.get(f'{base_url}{str(sub["href"])}', cookies=cookies)
                            status.set_description(f'Saving {file_name} in {section_name} of {course_name}({year})')
                            open(os.path.join(docs_path, file_name.translate(file_name.maketrans(transform_path))), 'wb').write(r.content)
        if(counter == len(status)):
            status.set_description('Extraction Complete!')

def extract_general():
    pass


modes = {
    'mine': extract_mine,
    'general': extract_mine
}

parser = argparse.ArgumentParser(description='Extracts all documents of all courses you were enrolled in [clip](https://clip.unl.pt)')
parser.add_argument('clip_user', type=str, help='Username for clip')
parser.add_argument('clip_password', type=str, help='Password of username')
parser.add_argument('-m', '--mode', nargs=1, default=extract_mine, choices=modes.keys(), help='Mode for extraction')
parser.add_argument('-oy', '--only_year', nargs='*', default=[], help='Only year(s) to extract e.g.: -oy 2019/20 or -oy 2019/2020 2020/2021')
parser.add_argument('-oc', '--only_course', nargs='*', default=[], help='Only course(s) to extract (e.g. similar to -oy)')

path = os.getcwd()

credentials = {'identificador':parser.parse_args().clip_user,'senha':parser.parse_args().clip_password}

only_course_name = parser.parse_args().only_course
only_year = parser.parse_args().only_year

def save(data: dict, name:str):
    with open(name, 'w') as outfile:
        json.dump(data, outfile)

def load(name:str) -> dict:
    try:
        with open(name) as infile:
            return json.load(infile)
    except Exception as eff:
        return {}

print('Request Login ...' , end='\r')
r = requests.post(f'{base_url}/utente/eu/aluno', data=credentials)
cookies = r.cookies
print(f'Request Login With {r.status_code}')

soup = BeautifulSoup(r.content, 'html.parser')
#Check if login failed
#login_succ = True
#for elem in soup.findAll('td'):
#    if elem.get('bgcolor', None)== "#ff0000" or elem.get('bgcolor', None)== '#ffcccc':
#        login_succ = False
#        break
if len(soup.findAll('td', bgcolor='#ff0000'))>0:
    print("Login Credentials Invalid!")
    os.system('pause')
    exit(1)

modes.get(parser.parse_args().mode, extract_mine)(soup, only_course_name, only_year)

os.system('pause')
