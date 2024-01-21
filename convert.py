from jinja2 import Environment, FileSystemLoader
import json
import re
import os

def makeHTML(in_file):
    # Load template
    env = Environment(loader=FileSystemLoader('html/templates'))
    index_template = env.get_template('index.jinja')

    # Read json file, covert to html
    f = open(in_file, 'r')
    posts = json.load(f)
    output = index_template.render(posts=posts)
    f.close()

    # Configure filename
    # in_file format    f'output/{user}_posts_{current_year}.json'
    file_pattern = r"/([a-z0-9_]*)\."
    filename = re.search(file_pattern, in_file)[1]
    # filename = in_file[:in_file.rfind('.')]

    # if f'{filename}.html' not in [f for f in os.listdir('html/output')]:
    with open(f'html/output/{filename}.html', 'w') as page:
        print(f'writing {filename}.html now')
        page.write(output)

