#!/usr/bin/env python3
'''
PiFire - File / Recipe Functions
================================

This file contains functions for file managing the recipe file format. 

'''

'''
Imported Modules
================
'''
import datetime
import json
import shutil
import zipfile
from pathlib import Path

from common import read_settings, generate_uuid, convert_temp
from file_mgmt.common import read_json_file_data

RECIPE_FOLDER = Path('./recipes/')  # Path to recipe files

'''
Functions
=========
'''
def _default_recipe_metadata():
    settings = read_settings()
    metadata = {}
    metadata['author'] = ''
    metadata['username'] = ''
    metadata['id'] = generate_uuid()
    metadata['title'] = ''
    metadata['description'] = ''
    metadata['image'] = ''
    metadata['thumbnail'] = ''
    metadata['units'] = settings['globals']['units']
    metadata['prep_time'] = 0
    metadata['cook_time'] = 0
    metadata['rating'] = 5 
    metadata['difficulty'] = 'Easy'
    metadata['version'] = '1.1.0'
    metadata['food_probes'] = 2
    return(metadata)

def _default_recipe_ingredients():
    ingredients = []
    '''
    ingredient = {
        "name" : "",
        "quantity" : "",
        "assets" : []
    }
    ingredients.append(ingredient)
    '''
    return(ingredients)

def _default_recipe_instructions():
    instructions = []
    '''
    instruction = {
      "text" : "",
      "ingredients" : [],
      "assets" : [],
      "step" : 0
    }
    instructions.append(instruction)
    '''
    return(instructions)

def _default_recipe_comments():
    comments = [] 
    return(comments)

def _default_recipe_assets():
    assets = []
    return(assets)

def _default_recipe_steps():
    steps = []

    # Default Startup Step
    step = {
        'mode' : 'Startup', 
        'trigger_temps' : {
            'primary' : 0, 
            'food' : [0, 0] 
        }, 
        'hold_temp' : 0, 
        'timer' : 0, 
        'notify' : False, 
        'message' : '', 
        'pause' : False
    }
    steps.append(step) 

    # Debug Step
    step = {
        'mode' : 'Hold', 
        'trigger_temps' : {
            'primary' : 0, 
            'food' : [420, 0] 
        }, 
        'hold_temp' : 420, 
        'timer' : 0, 
        'notify' : True, 
        'message' : 'Your meat is done, it\'s time to shutdown.', 
        'pause' : True
    }
    steps.append(step) 

    # Default Shutdown Step
    step = {
        'mode' : 'Shutdown', 
        'trigger_temps' : {
            'primary' : 0, 
            'food' : [0, 0] 
        }, 
        'hold_temp' : 0, 
        'timer' : 0, 
        'notify' : False, 
        'message' : '', 
        'pause' : False
    }
    steps.append(step) 

    return(steps)

def create_recipefile(): 
    '''
    This function creates an empty recipe file in the RECIPE_FOLDER 
    '''
    global RECIPE_FOLDER
    now = datetime.datetime.now()
    nowstring = now.strftime('%Y-%m-%d--%H%M')
    title = nowstring + '-Recipe'

    metadata = _default_recipe_metadata()

    recipe = {}
    recipe['ingredients'] = _default_recipe_ingredients()
    recipe['instructions'] = _default_recipe_instructions()
    recipe['steps'] = _default_recipe_steps()

    comments = _default_recipe_comments()
    assets = _default_recipe_assets()
    
    file_data = {} 
    file_data['metadata'] = metadata 
    file_data['recipe'] = recipe
    file_data['comments'] = comments 
    file_data['assets'] = assets 

    # 1. Create all JSON data files
    files_list = ['metadata', 'recipe', 'comments', 'assets']
    RECIPE_FOLDER.mkdir(exist_ok=True)
    recipe_dir = RECIPE_FOLDER / title
    recipe_dir.mkdir(exist_ok=True)
    
    for item in files_list:
        json_data_string = json.dumps(file_data[item], indent=2, sort_keys=True)
        filename = recipe_dir / f'{item}.json'
        filename.write_text(json_data_string)
    
    # 2. Create empty data folder(s) & add default data 
    (recipe_dir / 'assets').mkdir(exist_ok=True)
    (recipe_dir / 'assets' / 'thumbs').mkdir(exist_ok=True)

    # 3. Create ZIP file of the folder 
    filename = RECIPE_FOLDER / f'{title}.pfrecipe'

    with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in recipe_dir.rglob("*"):
            archive.write(file_path, arcname=file_path.relative_to(recipe_dir))

    # 4. Cleanup temporary files
    shutil.rmtree(recipe_dir)
    return filename 

def read_recipefile(filename):
	'''
	Read FULL Recipe File into Python Dictionary
	'''
	file_data = {}
	status = 'OK'
	json_types = ['metadata', 'recipe', 'comments', 'assets']
	for jsonfile in json_types:
		file_data[jsonfile], status = read_json_file_data(filename, jsonfile)
		if status != 'OK':
			break  # Exit loop and function, error string in status

	return(file_data, status)

def convert_recipe_units(recipe, units):
    for index, step in enumerate(recipe['steps']):
        for probe, settemp in step['settemps']:
            recipe['steps'][index]['settemps'][probe] = 0 if settemp == 0 else convert_temp(units, settemp)
        recipe['steps'][index]['hold_temp'] = 0 if step['hold_temp'] == 0 else convert_temp(units, step['hold_temp'])
    return(recipe)
