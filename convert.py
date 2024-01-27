from jinja2 import Environment, FileSystemLoader
import json
import re

def makeHTML(in_file):
    # Load template
    env = Environment(loader=FileSystemLoader('html/templates'))
    index_template = env.get_template('index.jinja')

    # Configure filename html parameters
    file_pattern = r"/([a-z0-9_]*)\."
    filename = re.search(file_pattern, in_file)[1]
    year = re.search(r'(\d+$)', filename)[1]
    user = re.search(r'^([a-zA-Z0-9]*)', filename)[1]

    # Read json file, covert to html
    f = open(in_file, 'r')
    posts = json.load(f)
    output = index_template.render(posts=posts, year=year, user=user)
    f.close()

    # if f'{filename}.html' not in [f for f in os.listdir('html/output')]:
    with open(f'html/output/{filename}.html', 'w') as page:
        print(f'writing {filename}.html now')
        page.write(output)

