from jinja2 import Environment, FileSystemLoader
import json
import os

def makeHTML():
    # Load template
    env = Environment(loader=FileSystemLoader('html/templates'))
    index_template = env.get_template('index.jinja')

    # Read json file, covert to html
    f = open('output/output.json', 'r')
    posts = json.load(f)
    output = index_template.render(posts=posts)
    f.close()

    # Configure filename
    year = '20' + posts[0]['posts'][0]['date'][7:]
    filename = 'boysy1_' + year

    if f'{filename}.html' not in [f for f in os.listdir('html/output')]:
        with open(f'html/output/{filename}.html', 'w') as page:
            print(f'writing {filename}.html now')
            page.write(output)

