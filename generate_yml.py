import os
import re
from importlib import import_module
from generators import ansible_cis as cis
from generators import ansible_stig as stig
from parse_xml import Parser

def generate(input, output, generator_type, filter='.xml'):
  if os.path.isdir(input):
    files = list_files(input, filter)
    failures = []
    for file in files:
      input_file = os.path.join(input, file)
      print(f'\nProcessing input file: {input_file}')
      extracted_vars = re.search('^(.*)_v(\d+\.?\d+\.?\d*)', file)
      
      baseline = extracted_vars[1].lower()
      print('baseline: {0}'.format(baseline))

      file_version = extracted_vars[2]
      print('file_version: {0}'.format(file_version))

      #output_dir = re.sub(r'\.xml$', '', file)
      output_path = os.path.join(output, baseline)
      try:
        run(input_file, output_path, generator_type, file_version, baseline)
      except Exception as e:
        print(e)
        failures.append(input_file)
    if len(failures) > 0:
      print('Failed to process the following input files:')
      print('  ' + '\n  '.join(failures))
  else:
    run(input, output, generator_type, file_version, baseline)
  print('\nFinished!')

def run(input_path, output_path, generator_type, file_version, baseline):
  parser = Parser()
  data = parser.parse(input_path)
  if 'ansible_cis' in generator_type:
      cis.generate(data, parser, output_path, file_version, baseline)
  elif 'ansible_stig' in generator_type:
      stig.generate(data, parser, output_path, file_version, baseline)

def list_files(dir, regex):
  files = []
  directory = os.fsencode(dir)
  for file in os.listdir(directory):
    filename = os.fsdecode(file)
    if re.search(regex, filename): 
      files.append(filename)
  return files

def read_file(path):
  file = open(path, 'r', encoding='utf-8')
  content = file.read()
  file.close()
  return content