from generate_yml import generate


generator_type = 'ansible_cis'
input = './benchmarks'
output = './results'

generate(input, output, generator_type)
