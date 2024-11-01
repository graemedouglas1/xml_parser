import re

from io import BytesIO
from lxml import etree

group_number_regex = re.compile(r'^xccdf_org\..+\.benchmarks_group_((\d+\.?)+)_')
rule_number_regex = re.compile(r'^xccdf_org\..+\.benchmarks_rule_((\d+\.)+\d+)_')

class Parser():
  def __init__(self):
    self.rule_count = 0
    self.rule_list = []

  def parse(self, input_path):

    #xml = Parser.read_file(input_path)
    parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False, ns_clean=True)
    self.tree = etree.parse(input_path, parser=parser)
    
    #self.tree = etree.parse(input_path)
    self.benchmark_el = self.tree.getroot()
    self.get_root_namespace()
   
    # Dynamically create profile_mapping and result structure
    self.profile_mapping = {}
    self.profile_result  = {}
    
    # Find all Profile elements
    profiles = self.benchmark_el.findall('.//xccdf:Profile', self.namespaces)

    for profile in profiles:
        profile_id = profile.get('id')
        title = profile.find('xccdf:title', self.namespaces).text.lower()
        
        # Determine server_type and level
        if 'domain controller' in title:
            server_type = 'domain'
        elif 'member server' in title:
            server_type = 'member'
        elif 'server' in title:
            server_type = 'server'
        elif 'stand-alone' in title:
            server_type = 'standalone'
        else:
            server_type = 'standalone'
        
        if 'level 1' in title or 'l1' in title:
            level = 'level1'
        elif 'level 2' in title or 'l2' in title:
            level = 'level2'
        elif 'next generation' in title:
            level = 'nextgen'
        elif 'bitlocker' in title:
            level = 'bitlocker'
        else:
            level = 'other'
        
        # Add to profile_mapping
        self.profile_mapping[profile_id] = (server_type, level)
        
        # Initialize result structure
        if server_type not in self.profile_result:
            self.profile_result[server_type] = {}
        if level not in self.profile_result[server_type]:
            self.profile_result[server_type][level] = set()
        
        # Collect rule references
        selections = profile.findall('.//xccdf:select', self.namespaces)
        for selection in selections:
            idref = selection.get('idref')
            if idref:
                self.profile_result[server_type][level].add(idref)

    print(f'Namespaces: {self.namespaces}')
    self.profiles = self.find_profiles()
    print('Profiles:', len(self.profiles))
    self.groups = self.find_groups()
    print('Groups:', len(self.groups))
    print('Rules:', self.rule_count)

    return {
      'profiles': self.profiles,
      'groups': self.groups,
      'profile_mapping': self.profile_mapping,
      'profile_result': self.profile_result,
      'rule_list': self.rule_list,
    }

  def read_file(path):
    file = open(path, 'r', encoding='utf-8')
    content = file.read()
    file.close()
    return content

  def remove_namespaces(d):
      """Recursively remove namespaces from dictionary keys."""
      if isinstance(d, dict):
          return {k.split(":")[-1]: Parser.remove_namespaces(v) for k, v in d.items()}
      elif isinstance(d, list):
          return [Parser.remove_namespaces(i) for i in d]
      else:
          return d

  def get_root_namespace(self):
    if self.benchmark_el.tag[0] == '{':
      uri, tag = self.benchmark_el.tag[1:].split('}')
      self.namespaces = {
        'xccdf': uri
      }
    else:
      self.namespaces = None

  def find_profiles(self):
    profile_els = self.tree.xpath(f'./{self.make_el_name("Profile")}', namespaces=self.namespaces)
    return list(map(lambda profile_el: {
      'id': profile_el.get('id'),
      'title': profile_el.xpath(f'./{self.make_el_name("title")}', namespaces=self.namespaces)[0].text,
      'selections': list(map(lambda select_el: {
        'idref': select_el.get('idref'),
        'selected': select_el.get('selected')
      }, profile_el.xpath(f'.//{self.make_el_name("select")}', namespaces=self.namespaces)))
    }, profile_els))

  def find_groups(self):
    groups    = []
    group_els = self.tree.xpath("//*[local-name()='Group']")
    for group_el in group_els:
      #print(f"Group ID: {group_el.get('id')}")
      rule_els = group_el.xpath(f'./{self.make_el_name("Rule")}', namespaces=self.namespaces)      
      if len(rule_els) == 0:
        continue        
      rules = []
      for rule_el in rule_els:
        #print(f"Rule ID: {rule_el.get('id')}")
        rule_id = rule_el.get('id')
        impact = rule_el.get('weight')
        desc_el = rule_el.xpath(f'./{self.make_el_name("description")}', namespaces=self.namespaces)

        if desc_el:
            # Get all text nodes, preserving line breaks
            text_nodes = desc_el[0].xpath('.//text()')
            
            # Join text nodes and normalize whitespace
            fixed_description = ' '.join(text_nodes)
            
            # Remove extra spaces and tabs while preserving line breaks
            fixed_description = re.sub(r'^\s*|\s*$|\n\s*', ' ', fixed_description).strip()
            fixed_description = re.sub(r'\s*\.\s*', '.\n\n', fixed_description)  # Add breaks after sentences
            fixed_description = re.sub(r'\s*(Enabled|Note:)\s*', r'\n\1\n', fixed_description)  # Add breaks before key phrases
            fixed_description = re.sub(r'[ \t]+', ' ', fixed_description)  # Replace multiple spaces/tabs with single space
            fixed_description = re.sub(r'\n+', '\n', fixed_description).strip()  # Remove multiple newlines
        else:
            fixed_description = ''
        rule = {
          'id': rule_id,
          'title': rule_el.xpath(f'./{self.make_el_name("title")}', namespaces=self.namespaces)[0].text,
          'impact': impact,
          'desc': fixed_description
        }
        match = rule_number_regex.search(rule_id)
        if match:
          rule['number'] = match[1]
        severity = rule_el.get('severity')
        if severity:
          rule['severity'] = severity
        self.rule_count += 1
        
        parsed_rule = re.search('(\d+(\.\d+)+)_(\D.*)', rule_id)
        self.rule_list.append('{0} - {1}'.format(parsed_rule.group(1), parsed_rule.group(3).replace('_',' ')))
        rules.append(rule)
      group = {
        'id': group_el.get('id'),
        'title': group_el.xpath(f'./{self.make_el_name("title")}', namespaces=self.namespaces)[0].text,
        'rules': rules
      }
      match = group_number_regex.search(group['id'])
      if match:
        group['number'] = match[1]
      groups.append(group)
    return groups

  def make_el_name(self, name):
    if self.namespaces:
      return f'xccdf:{name}'
    else:
      return name
