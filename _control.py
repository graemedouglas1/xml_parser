import json

class Control:
    def __init__(self, id: str, title: str = None, description: str = None, tags: dict = None):
        self.id = id
        self.title = title
        self.description = description
        self.tags = tags or {}

def generate_inspec_rules(json_data: str) -> str:
    """Convert JSON data to InSpec rules."""
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON data: {e}")

    controls = []

    # Check if 'Profile' exists in the JSON structure
    benchmark = data.get('Benchmark', [])
    profiles  = benchmark['Profile']
    values = {value["@id"]: value for value in benchmark.get('Value', [])}  # Create a mapping of values by ID
    
    if not profiles:
        raise ValueError("No profiles found in the provided JSON data.")

    for profile in profiles:
        profile_title = profile.get('title', {}).get('#text', 'No Title Provided')
        profile_description_parts = profile.get('description', {}).get('p', [])
        
        # Construct a full description from parts
        profile_description = ' '.join(part if isinstance(part, str) else part.get('#text', '') for part in profile_description_parts)

        # Extract selected rules from the profile
        for selection in profile.get('select', []):
            rule_id_ref = selection.get('@idref')
            
            if rule_id_ref:
                # Retrieve the corresponding value information for the rule
                value_info = values.get(rule_id_ref)
                
                # Check if '@operator' exists before creating a Control object
                if value_info and '@operator' in value_info:
                    control = Control(
                        id=rule_id_ref,
                        title=profile_title,
                        description=value_info['description'] if value_info else profile_description,
                        tags={
                            'severity': value_info.get('@operator', 'unknown'),  # Example tag extraction
                            'group': profile_title  # Adding group information (profile title)
                        }
                    )
                    controls.append(control.to_ruby())

    # Combine all controls into a single string
    return "\n".join(controls)