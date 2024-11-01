import re
import xml.etree.ElementTree as ET

from os import path
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader(Path(Path(__file__).parent, '..', 'templates').resolve()))

def generate(data, parser, output_path, file_version, baseline):
  
  rule_set = get_tagged_rule_ids(data['profiles'], data['profile_mapping'], data['profile_result'])
  
  # Create Version folder
  out_dir = path.join(output_path, file_version)
  Path(out_dir).mkdir(parents=True, exist_ok=True)
  
  # Write all.txt
  with open(path.join(output_path, file_version, 'all.txt'), 'w', encoding='utf-8') as file:
    file.write('\n'.join(data['rule_list']))

  if isinstance(rule_set, list):
    for rs in rule_set:
      out_dir = path.join(output_path, file_version, f'{rs["suffix"] or ""}')
      render_rule_set(data, rs['rules'], baseline, out_dir, 'common.yml')
  else:
    out_dir = path.join(output_path, file_version, 'standalone')
    render_rule_set(data, rule_set, baseline, out_dir, 'common.yml')

def render_rule_set(data, rule_elements, baseline, out_dir, file_path):

  filepath = path.join(out_dir, file_path)
  Path(out_dir).mkdir(parents=True, exist_ok=True)

  manifest = []
  tasks    = []

  for group in data['groups']:
    for rule in group['rules']:
      tags = []
      for t, r in rule_elements.items():
        if rule['id'] in r:
          tags.append(t)

          rule_name = re.sub(r'_', ' ', rule['id'].split(f'{rule["number"]}_')[1].strip())
          tasks.append({
          'name': rule_name,
          'number': rule['number'],
          'impact': rule['impact'],
          'desc': rule['desc'],
          'cis_section': group['title'],
          'tags': tags
          })

          tags.append(f'rule_{rule["number"]}')
          tags.append(baseline)

  sort_by_number(tasks)
  manifest.extend(map(lambda t: f'{t["number"]} - {t["name"]}', tasks))
  render_tasks(tasks, filepath)
  with open(path.join(out_dir, 'manifest.txt'), 'w', encoding='utf-8') as file:
    file.write('\n'.join(manifest))
  
def get_tagged_rule_ids(profiles, profile_mapping, profile_result):
    try:
        for profile in profiles:
            if profile['id'] in profile_mapping:
                server_type, level = profile_mapping[profile['id']]
                idrefs = set(map(lambda r: r['idref'], profile['selections']))
                
                if level in profile_result[server_type]:
                    profile_result[server_type][level] = idrefs
        
        # Determine the output format based on the profiles processed
        if len(profiles) == 1:
            server_type, level = profile_mapping[profiles[0]['id']]
            return {level: profile_result[server_type][level]}
        
        if len(profiles) == 2:
            server_type = profile_mapping[profiles[0]['id']][0]  # Assume both profiles are of the same server type
            return {
                'level1': profile_result[server_type]['level1'],
                'level2': profile_result[server_type]['level2'] - profile_result[server_type]['level1']  # Ensure level2 doesn't include level1 rules
            }

        if 'standalone' in [profile_mapping[p['id']][0] for p in profiles]:
            
            level1 = profile_result['standalone']['level1'] - profile_result['standalone'].get('bitlocker', set())
            level2 = profile_result['standalone']['level2'] - profile_result['standalone'].get('bitlocker', set()) - level1
            bitlocker = profile_result['standalone'].get('bitlocker', set())
            return {
                'level1': level1,
                'level2': level2,
                'bitlocker': bitlocker,
            }

        # Handle domain and member server profiles
        server_types = ['domain', 'member']
        results = []

        for server_type in server_types:
            if 'level1' in profile_result.get(server_type, {}) and 'level2' in profile_result.get(server_type, {}):
                suffix = 'domain_controller' if server_type == 'domain' else 'member_server'
                results.append({
                    'suffix': suffix,
                    'rules': {
                        'level1': profile_result[server_type]['level1'],
                        'level2': profile_result[server_type]['level2'] - profile_result[server_type]['level1'],
                        'nextgen': profile_result[server_type].get('nextgen', set())
                    }
                })

        if results:
            return results

        # If we get here, it means we didn't match any of the expected profile combinations
        raise Exception(f'Generator does not support the following profiles: {list(map(lambda p: p["id"], profiles))}')

    except Exception as e:
        raise Exception(f'Error processing profiles: {str(e)}. Profiles: {list(map(lambda p: p["id"], profiles))}')

def render_tasks(tasks, output_path):
  template = env.get_template('ansible_cis.yml.j2')
  result = template.render(tasks=tasks)
  with open(output_path, 'w', encoding='utf-8') as file:
    file.write(result)

def sort_by_number(items):
  items.sort(key=lambda item: [int(n) for n in item['number'].split('.')])