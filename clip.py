import os
import json
import time
import random
import requests
import re
from threading import Thread
from bs4 import BeautifulSoup
from pprint import pprint
from sys import argv, exit

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
path = os.getcwd()
years_href = {}
courses_href = {}
credentials = {'identificador':argv[1],'senha':argv[2]}
#REGEXS
year_patt = r'<a href="/utente/eu/aluno/ano_lectivo\?aluno=[0-9]*&amp;institui%E7%E3o=[0-9]{5}&amp;ano_lectivo=[0-9]{4}">[0-9]{4}/[0-9]{2}</a>'
course_patt = r'<a href="/utente/eu/aluno/ano_lectivo/unidades\?ano_lectivo=[0-9]{4}&amp;institui%E7%E3o=[0-9]{5}&amp;aluno=[0-9]{5}&amp;unidade=[0-9]*&amp;tipo_de_per%EDodo_lectivo=[a-z,A-Z]&amp;per%EDodo_lectivo=[0-9]">.*</a>'
#TODO fix regex below #post note let this bug be here :') #poster note get it deeper in search instead of regex
course_code_patt = r'(?!<a href="/utente/eu/aluno/ano_lectivo/unidades\?ano_lectivo=[0-9]{4}&amp;institui%E7%E3o=[0-9]{5}&amp;aluno=[0-9]{5}&amp;unidade=)[0-9]*(?=&amp;tipo_de_per%EDodo_lectivo=[a-z,A-Z]&amp;per%EDodo_lectivo=[0-9]">.*</a>)'
docs_patt = r'<a href="/utente/eu/aluno/ano_lectivo/unidades/unidade_curricular/actividade/documentos\?tipo_de_per%EDodo_lectivo=[a-z,A-Z]&amp;ano_lectivo=[0-9]{4}&amp;per%EDodo_lectivo=[0-9]&amp;aluno=[0-9]{5}&amp;institui%E7%E3o=97747&amp;unidade_curricular=[0-9]*&amp;tipo_de_documento_de_unidade=.*">.*</a>'
file_patt = r'<a href="/objecto\?oid=[0-9]*&amp;oin=.*">'

def save(data, name=filename):
    with open(name, 'w') as outfile:
        json.dump(data, outfile)

def load(name=filename):
    try:
        with open(name) as infile:
            return json.load(infile)
    except Exception as eff:
        return {}

__counter__ = 0
def loadingBar(display, end='\r'):
    global __counter__
    stringy = ['|','/','-','\\', '|','/','-','\\']
    print(' '*151, end='\r') #adjust in case not enough
    print(f'{display} {stringy[__counter__]}', end=end)
    if __counter__ < len(stringy)-1:
        __counter__ += 1
    else:
        __counter__ = 0

if len(argv) < 3:
    print('Usage: clip.py clip_user clip_password')
    exit(1)

print('Logging in & Getting...' , end='\r')
r = requests.post(f'{base_url}/utente/eu/aluno', data=credentials)
cookies = r.cookies
print(f'Logged in & Get With {r.status_code}')

soup = BeautifulSoup(r.content, 'html.parser')

for elem in soup.findAll('a', href=True):
    loadingBar('Checking all years')
    if re.match(year_patt, str(elem)) != None:
        years_href[elem.text] = elem['href']
for year, elem in years_href.items():
    print(f'Extracting {year}: {base_url}{elem} ...', end='\r')
    r = requests.get(f'{base_url}{str(elem)}', cookies=cookies)
    print(f'Extracted {year}: {base_url}{elem} {" "*10}')
    soup = BeautifulSoup(r.content, 'html.parser')
    hits = 0
    for sub in soup.findAll('a', href=True):
        loadingBar(f'Parsing {year}')
        if re.match(course_patt, str(sub)) != None:
            hits += 1
            tmp = courses_href.get(sub.text, {})
            tmp[year] = {
                'codigo': re.findall(course_code_patt, str(sub))[0],
                'href': sub['href']
            }
            courses_href[sub.text] = tmp
    print(f'Parsed {year} with {hits} courses')
for course_name, course_dic in courses_href.items():
    course_path = os.path.join(path, 'clip', str(course_name).translate(str(course_name).maketrans(transform_path)).strip())
    if not os.path.exists(course_path):
        os.makedirs(course_path)
    for year, year_data in course_dic.items():
        year_path = os.path.join(course_path, str(year).translate(str(year).maketrans(transform_path)).strip())
        if not os.path.exists(year_path):
            os.makedirs(year_path)
        save(year_data, name=os.path.join(year_path, 'metadata.json'))
        r = requests.get(f'{base_url}{str(year_data["href"])}', cookies=cookies)
        soup = BeautifulSoup(r.content, 'html.parser')
        for sub in soup.findAll('a', href=True):
            loadingBar(f'Parsing files from {course_name}({year})')
            if re.match(docs_patt, str(sub)) != None:
                docs_path = os.path.join(year_path, sub.text)
                if not os.path.exists(docs_path):
                    os.makedirs(docs_path)
                r = requests.get(f'{base_url}{str(sub["href"])}', cookies=cookies)
                soup = BeautifulSoup(r.content, 'html.parser')
                for sub in soup.findAll('a', href=True):
                    loadingBar(f'Parsing files from {course_name}({year})')
                    if re.match(file_patt, str(sub)) != None:
                        r = requests.get(f'{base_url}{str(sub["href"])}', cookies=cookies)
                        file_name = str(sub.parent.parent.findChildren("td")[0].text).strip()
                        open(os.path.join(docs_path, file_name.translate(file_name.maketrans(transform_path))), 'wb').write(r.content)
print(' '*151, end='\r')
print('Extraction Complete!')
os.system('pause')
