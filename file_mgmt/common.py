#!/usr/bin/env python3
'''
PiFire - File / Common Functions
================================

This file contains common functions for various file formats (i.e. Cookfile and Recipe Files). 

'''

'''
Imported Modules
================
'''
import zipfile
import json
import tempfile
import shutil

from pathlib import Path

HISTORY_FOLDER = Path('./history/')  # Path to historical cook files
RECIPE_FOLDER = Path('./recipes/')  # Path to recipe files

'''
Functions
=========
'''
def read_json_file_data(filename, jsonfile, unpackassets=True):
    '''
    Read File JSON File data out of the zipped pifire file:
        Must specify the file name, and the jsonfile element to be extracted (without the .json extension)
    '''
    status = 'OK'
    
    try:
        with zipfile.ZipFile(filename, mode="r") as archive:
            json_string = archive.read(jsonfile + '.json')
            dictionary = json.loads(json_string)
            
            if jsonfile == 'assets' and unpackassets:
                json_string = archive.read('metadata.json')
                metadata = json.loads(json_string)
                parent_id = metadata['id']

                for asset in range(0, len(dictionary)):
                    mediafile = dictionary[asset]['filename']
                    id = dictionary[asset]['id']
                    filetype = dictionary[asset]['type']
                    
                    data = archive.read(f'assets/{mediafile}')
                    thumb = archive.read(f'assets/thumbs/{mediafile}')
                    
                    tmp_pifire = Path('/tmp/pifire')
                    parent_dir = tmp_pifire / parent_id
                    thumbs_dir = parent_dir / 'thumbs'
                    
                    # Create all directories at once
                    thumbs_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Write files using Path
                    (parent_dir / f'{id}.{filetype}').write_bytes(data)
                    (thumbs_dir / f'{id}.{filetype}').write_bytes(thumb)

                    static_tmp = Path('./static/img/tmp')
                    static_parent = static_tmp / parent_id
                    static_tmp.mkdir(exist_ok=True)
                    
                    if not static_parent.exists():
                        static_parent.symlink_to(parent_dir)

    except zipfile.BadZipFile as error:
        status = f'Error: {error}'
        dictionary = {}
    except json.decoder.JSONDecodeError:
        status = 'Error: JSON Decoding Error.'
        dictionary = {}
    except Exception as e:
        if jsonfile == 'assets':
            status = f'Error: Error opening assets: {str(e)}'
        else:
            status = f'Error: Unspecified: {str(e)}'
        dictionary = {}

    return dictionary, status

def update_json_file_data(filedata, filename, jsonfile):
	'''
	Write an update to the recipe file
	'''
	status = 'OK'
	jsonfilename = jsonfile + '.json'

	# Borrowed from StackOverflow https://stackoverflow.com/questions/25738523/how-to-update-one-file-inside-zip-file
	# Submitted by StackOverflow user Sebdelsol

	# Start by creating a temporary file without the jsonfile that is being edited
	tmpname = tempfile.mkstemp(dir=Path(filename).parent)[1]
	Path(tmpname).unlink()
	try:
		# Create a temp copy of the archive without filename            
		with zipfile.ZipFile(filename, 'r') as zin:
			with zipfile.ZipFile(tmpname, 'w') as zout:
				zout.comment = zin.comment # Preserve the zip metadata comment
				for item in zin.infolist():
					if Path(item.filename).name != jsonfilename:
						zout.writestr(item, zin.read(item.filename))
		# Replace original with the temp archive
		Path(filename).unlink()
		Path(tmpname).rename(Path(filename))
		# Now add updated JSON file with its new data
		with zipfile.ZipFile(filename, mode='a', compression=zipfile.ZIP_DEFLATED) as zf:
			zf.writestr(Path(jsonfilename).name, json.dumps(filedata, indent=2, sort_keys=True))

	except zipfile.BadZipFile as error:
		status = f'Error: {error}'
	except:
		status = 'Error: Unspecified'
	
	return(status)

def fixup_assets(filename, jsondata):
	jsondata['assets'], status = read_json_file_data(filename, 'assets', unpackassets=False)

	# Loop through assets list, check actual files exist, remove from assets list if not 
	#   - Get file list from cookfile / assets
	assetlist = []
	thumblist = []
	with zipfile.ZipFile(filename, mode="r") as archive:
		for item in archive.infolist():
			if 'assets' in Path(item.filename).name:
				if Path(item.filename).name == 'assets/':
					pass
				elif Path(item.filename).name == 'assets.json':
					pass
				elif Path(item.filename).name == 'assets/thumbs/':
					pass
				elif 'thumbs' in Path(item.filename).name:
					thumblist.append(Path(item.filename).name)
				else: 
					assetlist.append(Path(item.filename).name)
	
	#   - Loop through asset list / compare with file list
	for asset in jsondata['assets']:
		if Path(asset['filename']).name not in assetlist:
			jsondata['assets'].remove(asset)
		else: 
			for item in assetlist:
				if Path(asset['filename']).name in item:
					assetlist.remove(item)
					break 

	# Loop through remaining files in assets list and populate
	for filename in assetlist:
		asset = {
			'id' : filename.rsplit('.', 1)[0].lower(),
			'filename' : filename.replace(HISTORY_FOLDER, ''),
			'type' : filename.rsplit('.', 1)[1].lower()
		}
		jsondata['assets'].append(asset)

	# Check Metadata Thumbnail if asset exists 
	thumbnail = jsondata['metadata']['thumbnail']
	assetlist = []
	for asset in jsondata['assets']:
		assetlist.append(Path(asset['filename']).name)

	if thumbnail != '' and thumbnail not in assetlist:
		jsondata['metadata']['thumbnail'] = ''

	# Loop through comments and check if asset lists contain valid assets, remove if not 
	comments = jsondata['comments']
	for index, comment in enumerate(comments):
		for asset in comment['assets']: 
			if asset not in assetlist:
				jsondata['comments'][index]['assets'].remove(asset)

	update_json_file_data(jsondata['assets'], filename, 'assets')
	status = 'OK'
	return(jsondata, status)

def remove_assets(filename, assetlist, filetype='cookfile'):
	status = 'OK'

	if filetype == 'recipefile':
		recipe, status = read_json_file_data(filename, 'recipe')

	metadata, status = read_json_file_data(filename, 'metadata')
	comments, status = read_json_file_data(filename, 'comments')
	assets, status = read_json_file_data(filename, 'assets', unpackassets=False)

	# Check Thumbnail against assetlist
	if metadata['thumbnail'] in assetlist:
		metadata['thumbnail'] = ''
		if filetype == 'recipefile':
			metadata['image'] = ''
		update_json_file_data(metadata, filename, 'metadata')

	# Check comment.json assets against assetlist
	modified = False
	for index, comment in enumerate(comments):
		for asset in comment['assets']:
			if asset in assetlist:
				comments[index]['assets'].remove(asset)
				modified = True 
	if modified:
		update_json_file_data(comments, filename, 'comments')

	# Check recipe.json assets against assetlist
	if filetype == 'recipefile':
		modified = False
		for index, ingredient in enumerate(recipe['ingredients']):
			for asset in ingredient['assets']:
				if asset in assetlist:
					recipe['ingredients'][index]['assets'].remove(asset)
					modified = True 
		for index, instruction in enumerate(recipe['instructions']):
			for asset in instruction['assets']:
				if asset in assetlist:
					recipe['instructions'][index]['assets'].remove(asset)
					modified = True 
		if modified:
			update_json_file_data(recipe, filename, 'recipe')

	# Check asset.json against assetlist 
	modified = False 
	tempassets = assets.copy()
	for asset in tempassets:
		if Path(asset['filename']).name in assetlist:
			assets.remove(asset)
			modified = True
	if modified:
		update_json_file_data(assets, filename, 'assets')

	# Traverse list of asset files from the compressed file, remove asset and thumb
	try: 
		tmpdir = Path('/tmp/pifire') / metadata["id"]
		tmpdir.mkdir(parents=True, exist_ok=True)
		
		with zipfile.ZipFile(filename, mode="r") as archive:
			new_archive = zipfile.ZipFile(str(tmpdir / 'new.pifire'), 'w', zipfile.ZIP_DEFLATED)
			for item in archive.infolist():
				remove = False 
				for asset in assetlist:
					if asset in item.filename:  # Use original filename string
						remove = True
						break 
				if not remove:
					buffer = archive.read(item.filename)  # Use original filename string
					new_archive.writestr(item.filename, buffer)  # Use original filename string
			new_archive.close()

		Path(filename).unlink()
		(tmpdir / 'new.pifire').rename(filename)
	except Exception as e:
		status = f"Error: Error removing assets from file: {str(e)}"

	return status
